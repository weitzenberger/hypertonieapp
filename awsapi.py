#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 22.08.17

This module creates an AWS API with a higher abstraction level for the
special use cases of the Nutrition App. It consists of a Lambda, Cognito and
DynamoDB Interface.

@author: L.We
"""
import json
import boto3

import constants as c
import form
import params

# Work around for decimal rounding bug. Monkey Patch!
import decimal
from boto3.dynamodb.types import DYNAMODB_CONTEXT
DYNAMODB_CONTEXT.traps[decimal.Inexact] = 0
DYNAMODB_CONTEXT.traps[decimal.Rounded] = 0
decimal.getcontext().prec = 10


class Lambda(object):
    """Class to manage Lambda interaction.
    """

    def __init__(self):
        self.client = boto3.client('lambda')

    def invoke_lambda_function(self, func_name, payload):
        """Invokes Lambda functions from another Lambda function. Note that
        permissions have to be set for each Lambda function in serverless.yml

        :param func_name: function name as defined in AWS Console
        :param payload: Event for invoked Lambda function
        """
        self.client.invoke(
            FunctionName=func_name,
            InvocationType='Event',
            Payload=json.dumps(payload))


class Cognito(object):
    """Class to manage Cognito interaction
    """

    def __init__(self):
        self.client_sync = boto3.client('cognito-sync')
        self.client_identity = boto3.client('cognito-identity')

    def list_records(self, dataset, cognito_id):
        """Lists all record of the given dataset.

        :param dataset: dataset type
        :return: List of dicts (very unhandy)
        """
        response = self.client_sync.list_records(IdentityPoolId=c.COGNITO_ID_POOL,
                                                 IdentityId=cognito_id,
                                                 DatasetName=dataset)
        return response[c.RECORDS]

    def reformat_listed_records(self, list_of_records):
        """Reformats the return value from list_records.

        :return: dict of dataset records
        """
        d = {}
        for record in list_of_records:
            current_key = record.get('Key', None)
            current_value = record.get('Value', None)
            if current_key:
                d.update({current_key: current_value})
        return form.convert_json(d)

    def get_records_as_dict(self, dataset, cognito_id):
        list_of_records = self.list_records(dataset=dataset,
                                            cognito_id=cognito_id)
        return self.reformat_listed_records(list_of_records=list_of_records)

    def subscribe_to_dataset(self, name, cognito_id):
        response = self.client_sync.subscribe_to_dataset(IdentityPoolId=c.COGNITO_ID_POOL,
                                                         IdentityId=cognito_id,
                                                         DatasetName=name,
                                                         DeviceId='string')
        return response[c.RECORDS]

    def get_datasets(self, cognito_id):
        response = self.client_sync.list_datasets(IdentityPoolId=c.COGNITO_ID_POOL,
                                                  IdentityId=cognito_id)
        return response

    def list_all_identies(self):
        """Lists all identities that are registered
        in the Cognito Identity Pool

        :return: List of Cognito IDS
        """
        list_of_identities = []

        response = self.client_identity.list_identities(
            IdentityPoolId=c.COGNITO_ID_POOL,
            MaxResults=60,
            HideDisabled=True
        )
        for identity in response['Identities']:
            list_of_identities.append(identity['IdentityId'])

        next_token = response['NextToken']
        while next_token:
            response = self.client_identity.list_identities(
                    IdentityPoolId=c.COGNITO_ID_POOL,
                    MaxResults=60,
                    HideDisabled=True,
                    NextToken=next_token)
            for identity in response['Identities']:
                list_of_identities.append(identity['IdentityId'])
            next_token = response.get('NextToken', None)

        print len(list_of_identities)

        return list_of_identities

    def delete_nutrients_for_identities(self, list_of_identities):
        """Deletes Nutrient dataset for each given identity

        :param list_of_identities: List of Cognito IDs
        """
        crash_counter = 0
        print list_of_identities

        for identity in list_of_identities:
            response = self.client_sync.list_records(
                IdentityPoolId=c.COGNITO_ID_POOL,
                IdentityId=identity,
                DatasetName=c.DATASET_NUTRIENTS)
            sync_session_token = response['SyncSessionToken']
            record_patches = []
            for record in response['Records']:
                record_patches.append({
                            'Op': 'replace',
                            'Key': record['Key'],
                            'Value': unicode(0),
                            'SyncCount': record['SyncCount']
                }
                )
            self.client_sync.update_records(
                IdentityPoolId=c.COGNITO_ID_POOL,
                IdentityId=identity,
                DatasetName=c.DATASET_NUTRIENTS,
                RecordPatches=record_patches,
                SyncSessionToken=sync_session_token
            )
            crash_counter += 1

        return dict(Crashes=crash_counter)


if __name__ == '__main__':
    handler = Cognito()
    print handler.get_records_as_dict(c.DATASET_VITAL, "eu-central-1:f0b34d2c-f014-4966-b851-9b088a3218f9")


class DynamoUserData(object):
    """Manages all interaction with the user data table in DynamoDB"""

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
        self.client = boto3.client('dynamodb', region_name='eu-central-1')
        self.table = self.dynamodb.Table(c.Tab)

    def _reformat_unique_id_list(self, input_list, output_list):
        """Reformats the list of cognito ids that is returned from the DynamoDB
        user data table and appends it to output_list

        :param input_list: list response from DynamoDB
        :param output_list: reformatted list
        :return: see output list above
        """
        for identity in input_list[c.ITEMS]:
            output_list.append(identity[c.UNIQUE_IDENTIFIER].values()[0])
        return output_list

    def scan_table_for_active_users(self, delta_time):
        """Scans the user data table for active users. This method is invoked once
        every week when new plans are generated for the following week.

        :param delta_time: time in days since last login for which users
                           are still considered to be active
        :return: list of cognito ids that are considered to be active
        """
        unique_id_list = []
        response = self.client.scan(
            TableName=c.TABLE_USER_DATA,
            Select='SPECIFIC_ATTRIBUTES',
            ProjectionExpression='#id',
            FilterExpression='#last_login > :critical_date',
            ExpressionAttributeNames={'#id': c.UNIQUE_IDENTIFIER,
                                      '#last_login': c.LAST_LOGIN},
            ExpressionAttributeValues={':critical_date': {'S': form.get_date_in_iso(-delta_time)}},
            ConsistentRead=True)
        last_key = response.get('LastEvaluatedKey', None)
        unique_id_list = self._reformat_unique_id_list(input_list=response, output_list=unique_id_list)
        while last_key:
            response = self.client.scan(
                TableName=c.TABLE_USER_DATA,
                Select='SPECIFIC_ATTRIBUTES',
                ExclusiveStartKey=last_key,
                ProjectionExpression='#id',
                FilterExpression='#last_login > :critical_date',
                ExpressionAttributeNames={'#id': c.UNIQUE_IDENTIFIER,
                                          '#last_login': c.LAST_LOGIN},
                ExpressionAttributeValues={':critical_date': {'S': form.get_date_in_iso(-delta_time)}},
                ConsistentRead=True)
            last_key = response.get('LastEvaluatedKey', None)
            unique_id_list = self._reformat_unique_id_list(input_list=response, output_list=unique_id_list)
        return unique_id_list

    def get_last_evaluated_week(self, unique_id):
        """

        :param unique_id: CognitoID
        :return: table response
        """
        table = self.dynamodb.Table(c.TABLE_USER_DATA)
        response = table.get_item(Key={c.UNIQUE_IDENTIFIER: unique_id},
                                  ProjectionExpression='#lastweek',
                                  ExpressionAttributeNames={"#lastweek": c.LAST_EVALUATED_WEEK})
        return response


class DynamoNutrition(object):
    """

    :param unique_id: Cognito ID
    :param date: date in ISO 8601
    """

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
        self.client = boto3.client('dynamodb', region_name='eu-central-1')

    def _update_total_nutrition_values(self, unique_id, date, plan, add):
        """Updates total nutrition values for both Day and Week table

        :param unique_id:
        :param date:
        :param plan: {cat: {SBLS: {n1: xx, n2: xx}
        :param add: boolean
        """
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        week = form.get_week_by_date(date)

        item_nutrients_for_week = table.get_item(TableName=c.TABLE_NUTRITIONAL_NEEDS_WEEK,
                                                 Key={c.UNIQUE_IDENTIFIER: unique_id,
                                                      c.WEEK: week},
                                                 ProjectionExpression='#toplevel',
                                                 ExpressionAttributeNames={"#toplevel": c.NUTRIENTS_FOR_WEEK})

        item_nutrients_for_day = table.get_item(TableName=c.TABLE_NUTRITIONAL_NEEDS_DAY,
                                                Key={c.UNIQUE_IDENTIFIER: unique_id,
                                                     c.DATE: date},
                                                ProjectionExpression='#toplevel',
                                                ExpressionAttributeNames={"#toplevel": c.NUTRIENTS_FOR_DAY})

        for container, container_content in plan.iteritems():
            item_nutrients_for_container = table.get_item(
                TableName=c.TABLE_NUTRITIONAL_NEEDS_DAY,
                Key={c.UNIQUE_IDENTIFIER: unique_id, c.DATE: date},
                ProjectionExpression='#toplevel.#container',
                ExpressionAttributeNames={
                    "#toplevel": c.NUTRIENTS_FOR_MEAL,
                    "#container": container
                }
            )
            for cat, cat_content in container_content.iteritems():



                for n in params.nutrientList:
                    item_nutrients_for_week[c.ITEM][c.NUTRIENTS_FOR_DAY][n] += cat_content[n] * (1 if add else -1)
                    item_nutrients_for_day[c.ITEM][c.NUTRIENTS_FOR_DAY][n] += cat_content[n] * (1 if add else -1)
                    item_nutrients_for_container[c.ITEM][c.NUTRIENTS_FOR_MEAL][container][n] += cat_content[n] * (1 if add else -1)

            table.update_item(TableName=c.TABLE_NUTRITIONAL_NEEDS_DAY,
                              Key={c.UNIQUE_IDENTIFIER: unique_id,
                                   c.DATE: date},
                              UpdateExpression='SET #toplevel.#cat = :value',
                              ExpressionAttributeNames={"#toplevel": c.NUTRIENTS_FOR_MEAL,
                                                        "#cat": container},
                              ExpressionAttributeValues={":value": item_nutrients_for_container[c.ITEM][c.NUTRIENTS_FOR_MEAL][container]})

        table.update_item(TableName=c.TABLE_NUTRITIONAL_NEEDS_DAY,
                              Key={c.UNIQUE_IDENTIFIER: unique_id,
                                   c.DATE: date},
                              UpdateExpression='SET #toplevel = :value',
                              ExpressionAttributeNames={"#toplevel": c.NUTRIENTS_FOR_DAY},
                              ExpressionAttributeValues={
                                  ":value": item_nutrients_for_day[c.ITEM][c.NUTRIENTS_FOR_DAY]
                              }
                          )

        table.update_item(TableName=c.TABLE_NUTRITIONAL_NEEDS_WEEK,
                              Key={c.UNIQUE_IDENTIFIER: unique_id,
                                   c.WEEK: week},
                              UpdateExpression='SET #toplevel = :value',
                              ExpressionAttributeNames={"#toplevel": c.NUTRIENTS_FOR_WEEK},
                              ExpressionAttributeValues={
                                  ":value": item_nutrients_for_week[c.ITEM][c.NUTRIENTS_FOR_WEEK]
                              }
                          )




    def _set_dynamo_table(self, hash, range, name):
        """Method to set a new DynamoDB table

        :param hash: partition key
        :param range: sort key (optional parameter)
        :param name: type of the table
        """
        self.client.create_table(
            TableName=name,
            KeySchema=[
                {
                    'AttributeName': hash,
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': range,
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': hash,
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': range,
                    'AttributeType': 'S'
                },

            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }
        )
        return

    def write_to_nutrients_for_day(self, status, unique_id, plan, nutForDay,
                                   nutForMeal, splittedNeeds, nutNeedsForDay):
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        with table.batch_writer() as batch:
            for day in plan.iterkeys():
                current_plan = {c.PLAN: plan[day],
                                c.UNIQUE_IDENTIFIER: unique_id,
                                c.DATE: day,
                                c.STATUS: status,
                                c.NUTRIENTS_FOR_DAY: nutForDay[day],
                                c.NUTRIENTS_FOR_MEAL: nutForMeal[day],
                                c.SPLITTED_NEEDS: splittedNeeds,
                                c.NUTRIENT_NEED_FOR_DAY: nutNeedsForDay,
                                c.CREATED_ON: form.get_date_in_iso()}
                print 'this is current_plan'
                print current_plan

                batch.put_item(Item=form.convert_to_decimal(current_plan))

    def write_to_nutrients_for_week(self, boundsForWeek, unique_id, nutForWeek, time):
        """

        :param boundsForWeek: {'EARG': {'LB': 35000}, 'VC': {...
        :param unique_id:
        :param nutForWeek: {'EARG': 38000, 'VC': 4100000, ..
        :return:
        """
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_WEEK)
        for week, nutForWeek in nutForWeek.iteritems():
            item = {c.BOUNDS_FOR_WEEK: form.convert_to_decimal(boundsForWeek),
                    c.UNIQUE_IDENTIFIER: unique_id,
                    c.WEEK: week,
                    c.NUTRIENTS_FOR_WEEK: form.convert_to_decimal(nutForWeek),
                    c.SOLUTION_TIME: form.convert_to_decimal(time),
                    c.CREATED_ON: form.get_date_in_iso()}
            last_week = week

            table.put_item(Item=item)
        table = self.dynamodb.Table(c.TABLE_USER_DATA)
        item = {c.UNIQUE_IDENTIFIER: unique_id,
                c.LAST_EVALUATED_WEEK: last_week}
        print item
        try:
            table.update_item(Item=item)
        except:
            table.put_item(Item=item)

    def delete_element(self, unique_id, date, container, key=None):
        """
        Deletes Element and also updates NUTRITIONAL_NEEDS_DAY and NUTRITIONAL_NEEDS_WEEK table

        :param unique_id: PARTITION KEY
        :param date: SORT KEY
        :param container: BF, SA, Mxxx, SM, SN, PL
        :param key: SBLS or Mxxxx
        :return:
        """
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        expression = {"#plan": c.PLAN,
                      "#container": container}
        if key:
            expression.update({"#currentKey": key})

        item = table.get_item(
            Key={c.UNIQUE_IDENTIFIER: unique_id,
                 c.DATE: date},
            ProjectionExpression='#plan.#container.#currentKey' if key else '#plan.#container',
            ExpressionAttributeNames=expression
        )
        print "this is the deleted item"
        print item
        table.update_item(
            Key={c.UNIQUE_IDENTIFIER: unique_id,
                 c.DATE: date},
            UpdateExpression='REMOVE #plan.#container.#currentKey' if key else 'REMOVE #plan.#container',
            ExpressionAttributeNames=expression
        )
        print item
        self._update_total_nutrition_values(unique_id=unique_id, date=date,
                                            plan=item[c.ITEM][c.PLAN], add=False)

        return item[c.ITEM][c.PLAN][container]


    def update_container(self, unique_id, nutrients):
        """
        :param unique_id: PARTITION KEY
        :param date: SORT KEY
        :param cat: BF, SA, WM, ...
        :param item: {'BF': {SBLS1 oder Mxxxx: {'EARG' : xxx, ..}, SBLS2...}}
        """
        plan = form.convert_to_decimal(nutrients.plan)
        print plan
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        for date, day_plan in plan.iteritems():
            for container, container_content in day_plan.iteritems():
                for meal_key, meal_content in container_content.iteritems():
                    response = table.update_item(
                        Key={
                            c.UNIQUE_IDENTIFIER: unique_id,
                            c.DATE: date
                        },
                        UpdateExpression='SET #toplevel.#secondlevel.#thirdlevel = :value',
                        ExpressionAttributeNames={
                            "#toplevel": c.PLAN,
                            "#secondlevel": container,
                            "#thirdlevel": meal_key
                        },
                        ExpressionAttributeValues={":value": meal_content})

                    self._update_total_nutrition_values(unique_id=unique_id, date=date,
                                                        plan=plan[date], add=True)

        return response

    def get_element(self, unique_id, date, container, key=None):
        """Deletes Element and also updates NUTRITIONAL_NEEDS_DAY and NUTRITIONAL_NEEDS_WEEK table

        :param unique_id: PARTITION KEY
        :param date: SORT KEY
        :param container: BF, SA, Mxxx, SM, SN, PL
        :param key: SBLS or Mxxxx
        :return:
        """
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        expression = {"#plan": c.PLAN,
                      "#container": container}
        if key:
            expression.update({"#currentKey": key})

        item = table.get_item(
            Key={c.UNIQUE_IDENTIFIER: unique_id,
                 c.DATE: date},
            ProjectionExpression='#plan.#container.#currentKey' if key else '#plan.#container',
            ExpressionAttributeNames=expression
        )
        return item[c.ITEM][c.PLAN][container]

    def get_from_nutrients_for_day(self, unique_id, date, top_level, second_level=None, third_level=None):
        """

        :param unique_id: basestring, cognito_id
        :param date: basestring, ISO-8601 date
        :param top_level: basestring, top level attribute
        :param second_level: basestring, second level attribute
        :param third_level: basestring, third level attribute
        :return: data structure that is in last defined level
        """
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        if third_level:
            if not second_level:
                raise ValueError('second_level must be defined when third_level is.')
            print top_level
            print second_level
            print third_level
            print unique_id
            print date
            item = table.get_item(Key={c.UNIQUE_IDENTIFIER: unique_id,
                                       c.DATE: date},
                                  ProjectionExpression='#toplevel.#secondlevel.#thirdlevel',
                                  ExpressionAttributeNames={"#toplevel": top_level,
                                                            "#secondlevel": second_level,
                                                            "#thirdlevel": third_level})
            print item

            if not item[c.ITEM]:
                raise ValueError('Item is empty. ExpressionAttributeNames do not match.')

            return form.convert_to_float(item[c.ITEM][top_level][second_level][third_level])
        elif second_level:
            item = table.get_item(Key={c.UNIQUE_IDENTIFIER: unique_id,
                                       c.DATE: date},
                                  ProjectionExpression='#toplevel.#secondlevel',
                                  ExpressionAttributeNames={"#toplevel": top_level,
                                                            "#secondlevel": second_level})
            if not item[c.ITEM]:
                raise ValueError('Item is empty. ExpressionAttributeNames do not match.')
            return form.convert_to_float(item[c.ITEM][top_level][second_level])
        else:
            item = table.get_item(Key={c.UNIQUE_IDENTIFIER: unique_id,
                                       c.DATE: date},
                                  ProjectionExpression='#toplevel',
                                  ExpressionAttributeNames={"#toplevel": top_level})
            if not item[c.ITEM]:
                raise ValueError('Item is empty. ExpressionAttributeNames do not match.')
            return form.convert_to_float(item[c.ITEM][top_level])

    def get_from_nutrients_for_week(self, unique_id, date, toplevel, secondlevel=None):
        """

        :param unique_id:
        :param date:
        :param toplevel:
        :param secondlevel:
        :return:
        """
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_WEEK)
        if secondlevel:
            item = table.get_item(Key={c.UNIQUE_IDENTIFIER: unique_id,
                                       c.WEEK: form.get_week_by_date(date)},
                                  ProjectionExpression='#toplevel.#secondlevel',
                                  ExpressionAttributeNames={"#toplevel": toplevel,
                                                            "#secondlevel": secondlevel})
            return form.convert_to_float(item[c.ITEM][toplevel][secondlevel])
        else:
            item = table.get_item(Key={c.UNIQUE_IDENTIFIER: unique_id,
                                       c.WEEK: form.get_week_by_date(date)},
                                  ProjectionExpression='#toplevel',
                                  ExpressionAttributeNames={"#toplevel": toplevel})
            return form.convert_to_float(item[c.ITEM][toplevel])

    def get_reduced_bounds_for_week(self, unique_id, date, redLb):
        """

        :param unique_id:
        :param date:
        :param redLb:
        :return:
        """
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_WEEK)
        week = form.get_week_by_date(date)
        currentItem = table.get_item(Key={c.UNIQUE_IDENTIFIER: unique_id,
                                          c.WEEK: week},
                                     ProjectionExpression='#toplevel',
                                     ExpressionAttributeNames={'#toplevel': c.BOUNDS_FOR_WEEK})

        currentItem = form.convert_to_float(currentItem)
        for n in params.nutrientsMicroList:
            currentItem[c.ITEM][c.BOUNDS_FOR_WEEK][n][c.LB] *= redLb
        ret_val = currentItem[c.ITEM][c.BOUNDS_FOR_WEEK]

        return ret_val
