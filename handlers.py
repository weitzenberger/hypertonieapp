#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 25.08.17

This module contains all AWS Lambda functions. Both internally
used Lambda functions and Lambda functions invoked mobile side.
Deployment information can be found in the serverless.yml
declaration file.

@author: L.We
"""

import sys

import form
import awsapi
from manager import GenerateManager, RegenerateManager
import traceback


context = None
place_holder_id = "eu-central-1:0265ffa7-f55b-4591-9cd8-c329f076fe0a"

@form.time_it
def generate(event, context):
    """Main Lambda Function to generate new meal plans."""

    try:
        cognito_id = event['unique_id']
    except:
        cognito_id = event['body']['unique_id']
        event = event['body']

    with GenerateManager(
            cognito_id=cognito_id,
            event=event,
            prob_type=generate.__name__,
            time_out=120,
            cbc_log=False
    ) as manager:
        manager.set_meal_by_container()
    return manager.managerLog


def regenerate(event, context):
    """Lambda Function to modify meal plans.

    :param event: dict, contains payload
    :param context: AWS context object
    :return: dict
    """

    cognito_id = event['context']['cognito-identity-id']
    date = event['body-json']['date']
    meal_key = event['body-json']['meal_key']
    container_key = event['body-json']['container_key']

    with RegenerateManager(
            cognito_id=cognito_id,
            event=event,
            prob_type=regenerate.__name__,
            time_out=30,
            cbc_log=True
    ) as manager:
        manager.set_meal_by_cat(container_key=container_key)

    return manager.managerLog



def invoke_generate_from_mobile_device(event, context):
    """This method invokes generate when a new user signs up or
    when a user is marked as inactive and wakes up again or when
    for any other reason no valid meal plan is stored in DynamoDB

    :param event: dict, contains payload
    :param context: AWS context object
    :return:
    """
    cognito_id = event["context"]["cognito-identity-id"]
    print cognito_id
    lambda_handler = awsapi.Lambda()
    payload = dict(unique_id=cognito_id, thisweek=True)
    func_name = 'escamedmobileapi-expo-generate'

    lambda_response = lambda_handler.invoke_lambda_function(
        func_name=func_name,
        payload=payload
    )
    if form.get_week_day() > 4.4:
        payload['thisweek'] = False
        response = lambda_handler.invoke_lambda_function(
            func_name=func_name,
            payload=payload
        )

    return lambda_response


def reset_all_user_nutrients(event, context):
    """This method resets all user nutrients to zero. It is
    invoked at once a day by CloudWatch Events.

    :param event: {}
    :param context: Lambda context object (CloudWatch Events)
    :return:
    """

    cognito_handler = awsapi.Cognito()

    list_of_identities = cognito_handler.list_all_identies()
    response = cognito_handler.delete_nutrients_for_identities(list_of_identities)

    return dict(ValidIdentitiesFound=len(list_of_identities),
                IndentitiesWithoutDataset=response['Crashes'])



def post_plan(event, context):
    """Posts meal plan to DynamoDB

    :param event: {'body': {SBLS: amount, SBLS: amount, ...}}
    :param context: Lambda context object (Mobile Device)
    :return:
    """
    cognito_id = event['context']['cognito-identity-id']
    db = SBLSDatabase()
    d = {}

    element = event['body']['ingredient'].items()[0]
    d.update(
        db.get_grocery_from_bls(
            sbls=element[0],
            amount=element[1]
        )
    )
    return dict(PostedPlan=d)


def generate_for_next_week(event, context):
    """This method scans User Database for active users and generates a
    new meal plan for the upcoming week. It is invoked once a week at
    the end of the week.
    """

    cognito_ids = awsapi.DynamoUserData().scan_table_for_active_users(delta_time=110)
    lambda_client = awsapi.Lambda()
    payload = {'thisweek': False}

    while cognito_ids:
        current_id = cognito_ids.pop()
        payload['unique_id'] = current_id
        lambda_client.invoke_lambda_function(func_name=generate.__name__,
                                             payload=payload)
    return



if __name__ == '__main__' and sys.platform == 'darwin':
    event = dict(
        unique_id="eu-central-1:0265ffa7-f55b-4591-9cd8-c329f076fe0a",
        thisweek=True
    )
    # print post_plan({'body': {'ingredient': {'H862100': 50}, 'unique_id_as_arg': 'asdf'}}, None)

    print generate(event, context)
    #regenerate(event={'body': {'container': 'LU', 'date': '2017-09-30', 'meal_key': 'M0020', "unique_id_as_arg": "eu-central-1:099a01b6-76ae-41eb-ad05-7feec7ff1f3a"}}, context=context)
    pass
