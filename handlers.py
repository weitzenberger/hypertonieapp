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
from database import SBLSDatabase
import traceback


context = None
kwargs_cat = {
    'PL': dict(meat=10, veg=10, grain=10),
    'SM': dict(fluid=6, primary=6, secondary=6, boost=6),
    'WM': dict(num=5),
    'BF': dict(num=10),
    'SW': dict(bread=5, butter=2, topping=2),
    'SA': dict(num=5),
    'SN': dict(num=5)
}

@form.time_it
def generate(event, context):
    """Main Lambda Function to generate new meal plans."""

    print event
    with GenerateManager(
            cognito_id=event['unique_id'],
            event=event,
            prob_type=generate.__name__,
            time_out=120,
            cbc_log=False
    ) as manager:
        manager.set_meal_by_container()


        # manager.set_breakfast(num=10)
        # manager.set_warm_meal(num=10)
        # manager.set_plate(meat=10, veg=10, grain=10)copy.deepcopy(self)
        # manager.set_snack(num=15)
        # manager.set_salad(num=5)
    return None


def regenerate(event, context):
    """Lambda Function to modify meal plans.

    :param event: dict, contains payload
    :param context: AWS context object
    :return: dict
    """

    cognito_id = event["body"]["unique_id_as_arg"]

    cat = _determine_cat(event=event)
    print event["body"]["meal_key"]
    print event["body"]["container"]
    with RegenerateManager(
            cognito_id=cognito_id,
            event=event,
            prob_type=regenerate.__name__,
            time_out=30,
            cbc_log=True
    ) as manager:
        manager.set_meal_by_cat(cat=cat, **kwargs_cat[cat])

    return manager.managerLog


def _determine_cat(event):
    """Ugly container reassignment. Is to be replaced by a proper solution"""

    container = event['body']['container']
    meal_key = event['body']['meal_key']

    if meal_key in ['PL', 'SM', 'SA', 'SN']:
        return meal_key
    elif len(meal_key) > 2:
        if container == 'LU':
            return 'WM'
        elif container == 'BF':
            return 'BF'
        elif container == 'SN':
            return 'SN'


def invoke_generate_from_mobile_device(event, context):
    """This method invokes generate when a new user signs up or
    when a user is marked as inactive and wakes up again or when
    for any other reason no valid meal plan is stored in DynamoDB

    :param event: dict, contains payload
    :param context: AWS context object
    :return:
    """
    cognito_id = event["body"]["unique_id_as_arg"]
    print cognito_id
    lambda_handler = awsapi.Lambda()
    payload = dict(unique_id=cognito_id, thisweek=True)
    func_name = 'escamed-expositio-generate'

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

def scan_bls(event, context):
    """Scans BLS for groceries to add to a meal plan

    :param event: {'body': {'keyword': keywordSnipped}}
    :return:
    """

    dB = SBLSDatabase()
    print event
    response = dB.scan_bls(keyword=event['body']['keyword'])

    return response


def post_plan(event, context):
    """Posts meal plan to DynamoDB

    :param event: {'body': {SBLS: amount, SBLS: amount, ...}}
    :param context: Lambda context object (Mobile Device)
    :return:
    """
    cognito_id = event['body']['unique_id_as_arg']
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


def _get_cognito_id(event, context):
    """Returns CognitoID or placeholder for testing purposes or in case
    of exceptions.

    :param event: dict
    :param context: AWS context object
    :return:
    """

    print 'Event Object:'
    print event
    placeholder_id = "eu-central-1:099a01b6-76ae-41eb-ad05-7feec7ff1f3a"

    if sys.platform == 'darwin':
        return placeholder_id
    else:
        try:
            print 'Lambda proxy call'
            print event["requestContext"]["identity"]["cognitoIdentityId"]
            cognito_id = event["requestContext"]["identity"]["cognitoIdentityId"]
        except NotImplementedError('Apparently there is no proxy integration for this lambda or '
                                   'Lambda is invoked from API Gateway.' + '\n'
                                   'CognitoID could not be retrieved, placeholder ID is used instead.'):
            return placeholder_id
        if cognito_id is None:
            print 'CognitoID is pointing None, placeholder ID is used instead'
            try:
                cognito_id = event['body']['unique_id_as_arg']
            except AttributeError('unique_id_as_arg could not be found in event payload.'
                                  'placeholder_id is used instead'):
                return placeholder_id


        return cognito_id

if __name__ == '__main__' and sys.platform == 'darwin':
    event = dict(unique_id=_get_cognito_id(None, context),
                 thisweek=True)
    # print post_plan({'body': {'ingredient': {'H862100': 50}, 'unique_id_as_arg': 'asdf'}}, None)

    generate(event, context)
    #regenerate(event={'body': {'container': 'LU', 'date': '2017-09-30', 'meal_key': 'M0020', "unique_id_as_arg": "eu-central-1:099a01b6-76ae-41eb-ad05-7feec7ff1f3a"}}, context=context)
    pass
