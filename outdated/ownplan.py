#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""

"""

import constants as c
import form
import params
from awsapi import Lambda, Cognito
from outdated.database import SBLSDatabase


def scan_bls(event, context):
    """Scans BLS for groceries to add to a meal plan

    :param event: {'body': {'keyword': keywordSnipped}}
    :return:
    """

    dB = SBLSDatabase()
    response = dB.scan_bls(keyword=event['body']['keyword'])

    return response

def post_plan(event, context):
    """Posts meal plan to DynamoDB

    :param event: {'body': {SBLS: amount, SBLS: amount, ...}}
    :param context: Lambda context object (Mobile Device)
    :return:
    """
    dB = SBLSDatabase()
    d = {}
    for key, value in event['body'].iteritems():
        d.update(dB.get_vals_by_sbls(params.nutrientList,
                                     c.SQL_BLS,
                                     float(value),
                                     key))
    print context.identity.cognito_identity_id
    return dict(PostedPlan=d)

def reset_all_user_nutrients(event, context):
    """

    :param event: {}
    :param context: Lambda context object (CloudWatch Events)
    :return:
    """
    cognito_handler = Cognito()

    list_of_identities = cognito_handler.list_all_identies()
    response = cognito_handler.delete_nutrients_for_identities(list_of_identities)

    return dict(ValidIdentitiesFound=len(list_of_identities),
                IndentitiesWithoutDataset=response['Crashes'])

def invoke_generate_from_mobile_device(event, context):
    """

    :param event: {}
    :param context: Lambda context object (Mobile Device)
    :return:
    """
    lambda_handler = Lambda()

    payload = dict(unique_id=context.identity.cognito_identity_id,
                   thisweek=True)
    print payload
    print context.identity
    print context.identity.cognito_identity_id

    lambda_response = lambda_handler.invoke_lambda_function(func_name=c.HANDLER_GENERATE,
                                                            payload=payload)
    print lambda_response
    if form.get_week_day() > 4.4:
        payload['thisweek'] = False
        print payload
        response = lambda_handler.invoke_lambda_function(func_name=c.HANDLER_GENERATE,
                                                         payload=payload)

    return lambda_response









