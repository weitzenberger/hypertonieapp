#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 20.06.2017 07:33

{
  "version": 2,
  "eventType": "SyncTrigger",
  "region": "us-east-1",
  "identityPoolId": "identityPoolId",
  "identityId": "identityId",
  "datasetName": "datasetName",
  "datasetRecords": {
    "SampleKey1": {
      "oldValue": "oldValue1",
      "newValue": "newValue1",
      "op": "replace"
    },
    "SampleKey2": {
      "oldValue": "oldValue2",
      "newValue": "newValue2",
      "op": "replace"
    },..
  }
}

@author: L.We
"""

import constants as c
from params import Param
from awsapi import Lambda, DynamoUserData
import form as Formatter


def catch_stream(event, context):
    for record in event[c.RECORDS]:
        # new user
        if record['eventName'] == 'INSERT':
            payload = {'thisweek': True,
                       c.UNIQUE_IDENTIFIER: event[c.CONTENTS][c.UNIQUE_IDENTIFIER]}
            lambda_handler = Lambda()
            lambda_handler.invoke_lambda_function(func_name=c.HANDLER_GENERATE,
                                                  payload=payload)
            if (Formatter.get_week_day() >= 4.5):
                payload['thisweek'] = False
                lambda_handler.invoke_lambda_function(func_name=c.HANDLER_GENERATE,
                                                      payload=payload)
        elif record['eventName'] == 'MODIFY':
            pass
        elif record['eventName'] == 'REMOVE':
            pass

def check_last_login(event, context):
    if event[c.DATASET_NAME] == c.DATASET_LAST_LOGIN:
        old_timestr = event[c.DATASET_RECORDS][c.LAST_LOGIN][c.OLD_VALUE]
        new_timestr = event[c.DATASET_RECORDS][c.LAST_LOGIN][c.NEW_VALUE]
        old_datetime = Formatter.convert_iso_to_date_time(old_timestr)
        new_datetime = Formatter.convert_iso_to_date_time(new_timestr)
        delta_time = (new_datetime - old_datetime).total_seconds() / 3600.0 / 24.0
        if delta_time > Param.crit_time - 0.5:
            catch_stream_from_cognito(event=event, context=context)

def catch_stream_from_cognito(event, context):
    next_week = Formatter.get_week_in_iso(thisweek=False)
    current_week = Formatter.get_week_in_iso(thisweek=True)
    userDataStore = DynamoUserData()
    last_evaluated_week = userDataStore.get_last_evaluated_week(unique_id=context.identity.cognito_identity_id)
    if next_week == last_evaluated_week:
        return
    elif (current_week == last_evaluated_week):
        if (Formatter.get_week_day() >= 4.3):
            payload = {'thisweek': False,
                       c.UNIQUE_IDENTIFIER: context.identity.cognito_identity_id}
            lambda_handler = Lambda()
            lambda_handler.invoke_lambda_function(func_name=c.HANDLER_GENERATE,
                                                  payload=payload)
        else:
            return
    else:
        payload = {'thisweek': True,
                   c.UNIQUE_IDENTIFIER: context.identity.cognito_identity_id}
        lambda_handler = Lambda()
        lambda_handler.invoke_lambda_function(func_name=c.HANDLER_GENERATE,
                                              payload=payload)
        return


def pre_sign_up(event, context):
    cognito_id = context.identity.cognito_identity_id
    lambda_client = Lambda()
    lambda_client.invoke_lambda_function(func_name=c.HANDLER_GENERATE,
                                         payload=cognito_id)
    return


if __name__ == '__main__':
    #generate_for_next_week(event=None, context=None)
    print query_ddb()

def test_ddb_stream(event, context):
    for record in event[c.RECORDS]:
        new_image = record['dynamodb']['NewImage']
        old_image = record['dynamodb'].get('OldImage', None)
        if not old_image:
            return
        if new_image.get('user_sign_up_complete', None):
            print new_image.get('user_sign_up_complete', None)
            if not old_image.get('user_sign_up_complete', None):
                print old_image.get('user_sign_up_complete', None)
                # invoke Lambda thisweek
                payload = {'thisweek': True,
                           c.UNIQUE_IDENTIFIER: new_image[c.UNIQUE_IDENTIFIER]['S']}
                lambda_handler = Lambda()
                lambda_handler.invoke_lambda_function(func_name=c.HANDLER_GENERATE,
                                                      payload=payload)
                if Formatter.get_week_day() > 4.4:
                    # invoke lambda nextweek
                    print payload
                    payload['thisweek'] = False
                    lambda_handler.invoke_lambda_function(func_name=c.HANDLER_GENERATE,
                                                          payload=payload)