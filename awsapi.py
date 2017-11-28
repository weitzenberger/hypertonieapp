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
import pprint
import decimal
import datetime as dt
import collections

import constants as c
import form
import params

from boto3.dynamodb.conditions import Key, Attr

# Work around for decimal rounding bug. Monkey Patch!
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

class S3(object):
    def __init__(self):
        self.client = boto3.client('s3')

    def get_img_url(self, sbls):
        bucket3 = 'shutterstock-img-bucket'

        bucket_location = self.client.get_bucket_location(Bucket=bucket3)
        object_url = "https://s3-{0}.amazonaws.com/{1}/{2}.jpg".format(
            bucket_location['LocationConstraint'],
            bucket3,
            sbls)
        return object_url

class DynamoUserData(object):
    """Manages all interaction with the user data table in DynamoDB"""

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
        self.client = boto3.client('dynamodb', region_name='eu-central-1')
        self.table_user_data = self.dynamodb.Table(c.TABLE_USER_DATA)
        self.table_blood_pressure = self.dynamodb.Table(c.TABLE_BLOOD_PRESSURE)
        self.table_weight = self.dynamodb.Table(c.TABLE_WEIGHT)
        self.table_shopping_list = self.dynamodb.Table(c.TABLE_SHOPPING_LIST)
        self.table_nutrient_for_day = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        self.table_nutrient_for_week = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_WEEK)
        self._tree = lambda: collections.defaultdict(self._tree)


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

    def like_meal(self, unique_id, meal_key, put_meal):
        if put_meal:
            update_op = 'ADD'
        else:
            update_op = 'DELETE'

        response = self.table_user_data.update_item(
            Key={
                'unique_id': unique_id
            },
            UpdateExpression='{op} #likes :meal_key'.format(op=update_op),
            ExpressionAttributeNames={
                '#likes': 'likes'
            },
            ExpressionAttributeValues={
                ':meal_key': {meal_key}
            }
        )

        if update_op == 'ADD':
            response = self.table_user_data.update_item(
                Key={
                    'unique_id': unique_id
                },
                UpdateExpression='DELETE #dislikes :meal_key',
                ExpressionAttributeNames={
                    '#dislikes': 'dislikes'
                },
                ExpressionAttributeValues={
                    ':meal_key': {meal_key}
                }
            )

        return self.is_liked_or_disliked(unique_id=unique_id, meal_key=meal_key)

    def dislike_meal(self, unique_id, meal_key, put_meal):
        if put_meal:
            update_op = 'ADD'
        else:
            update_op = 'DELETE'

        response = self.table_user_data.update_item(
            Key={
                'unique_id': unique_id
            },
            UpdateExpression='{op} #dislikes :meal_key'.format(op=update_op),
            ExpressionAttributeNames={
                '#dislikes': 'dislikes'
            },
            ExpressionAttributeValues={
                ':meal_key': {meal_key}
            }
        )
        if update_op == 'ADD':
            response = self.table_user_data.update_item(
                Key={
                    'unique_id': unique_id
                },
                UpdateExpression='DELETE #likes :meal_key',
                ExpressionAttributeNames={
                    '#likes': 'likes'
                },
                ExpressionAttributeValues={
                    ':meal_key': {meal_key}
                }
            )
        return self.is_liked_or_disliked(unique_id=unique_id, meal_key=meal_key)

    def is_liked_or_disliked(self, unique_id, meal_key):
        response_like = self.table_user_data.get_item(
            Key={
                'unique_id': unique_id
            },
            ProjectionExpression='#attr',
            ExpressionAttributeNames={
                '#attr': 'likes'
            }
        )

        response_dislike = self.table_user_data.get_item(
            Key={
                'unique_id': unique_id
            },
            ProjectionExpression='#attr',
            ExpressionAttributeNames={
                '#attr': 'dislikes'
            }
        )
        if response_like['Item'].get('likes'):
            if meal_key in response_like['Item'].get('likes'):
                is_liked = True
            else:
                is_liked = False
        else:
            is_liked = False

        if response_dislike['Item'].get('dislikes'):
            if meal_key in response_dislike['Item'].get('dislikes'):
                is_disliked = True
            else:
                is_disliked = False
        else:
            is_disliked = False

        return dict(
            is_liked=is_liked,
            is_disliked=is_disliked
        )




    def create_shopping_list(self, unique_id, ls_date):
        """

        :param unique_id:
        :param ls_date:
        :return:
        """
        response = self.table_user_data.update_item(
            Key={
                'unique_id': unique_id
            },
            UpdateExpression='SET #shopping_list_days = :ls_date',
            ExpressionAttributeNames={
                '#shopping_list_days': 'shopping_list_days'
            },
            ExpressionAttributeValues={
                ":ls_date": ls_date
            }
        )

        pprint.pprint(response)

    def shopping_list(self, unique_id):
        """

        :param unique_id:
        :return:
        """

        response = self.table_user_data.get_item(
            Key={
                'unique_id': unique_id
            },
            ProjectionExpression='#attr',
            ExpressionAttributeNames={
                '#attr': 'shopping_list_days'
            }
        )
        pprint.pprint(response)
        shopping_list = self._tree()
        for date in response['Item']['shopping_list_days']:
            response = self.table_shopping_list.get_item(
                Key={
                    'unique_id': unique_id,
                    'date': date
                },
                ConsistentRead=True,
                ProjectionExpression='#attr',
                ExpressionAttributeNames={
                    '#attr': 'actual_list'
                }
            )
            pprint.pprint(response)
            for sbls_key, sbls_content in response['Item']['actual_list'].iteritems():
                if not sbls_content['CHECKED']:
                    shopping_list[sbls_key].setdefault('VAL', decimal.Decimal('0.0'))
                    shopping_list[sbls_key]['UNIT'] = 'g'  # TODO: Einheit einfügen
                    shopping_list[sbls_key]['VAL'] += sbls_content['VAL']
        return form.convert_to_float(shopping_list)

    def shopping_list_check_item(self, unique_id, sbls):
        """

        :param unique_id:
        :param sbls:
        :return:
        """
        response = self.table_user_data.get_item(
            Key={
                'unique_id': unique_id
            },
            ProjectionExpression='#attr',
            ExpressionAttributeNames={
                '#attr': 'shopping_list_days'
            }
        )
        for date in response['Item']['shopping_list_days']:
            response = self.table_shopping_list.update_item(
                Key={
                    'unique_id': unique_id,
                    'date': date
                },
                UpdateExpression='SET #actual_list.#sbls.#checked = :checked',
                ConditionExpression=Attr('#actual_list.#sbls').exists(),
                ExpressionAttributeNames={
                    '#actual_list': 'actual_list',
                    '#sbls': sbls,
                    '#checked': 'CHECKED'
                },
                ExpressionAttributeValues={
                    ":checked": True
                }
            )

    def shopping_list_uncheck_item(self, unique_id, sbls):
        """

        :param unique_id:
        :param sbls:
        :return:
        """
        response = self.table_user_data.get_item(
            Key={
                'unique_id': unique_id
            },
            ProjectionExpression='#attr',
            ExpressionAttributeNames={
                '#attr': 'shopping_list_days'
            }
        )
        for date in response['Item']['shopping_list_days']:
            response = self.table_shopping_list.update_item(
                Key={
                    'unique_id': unique_id,
                    'date': date
                },
                UpdateExpression='SET #actual_list.#sbls.#checked = :checked',
                ConditionExpression=Attr('#actual_list.#sbls').exists(),
                ExpressionAttributeNames={
                    '#actual_list': 'actual_list',
                    '#sbls': sbls,
                    '#checked': 'CHECKED'
                },
                ExpressionAttributeValues={
                    ":checked": False
                }
            )




    def average_blood_pressure_for_day(self, unique_id, date):
        """Returns average blood pressure for the considered day

        :param unique_id: cognito_id
        :param date: YYYY-MM-DD
        :return:
        """
        SYS_HIGH = 140
        SYS_HIGH_NORM = 120

        DIA_HIGH = 90
        DIA_HIGH_NORM = 80

        def check_blood_pressure(systolic, diastolic, date):
            if diastolic > DIA_HIGH:
                status_diastolic = 'increase'
            elif pressure_diastolic_average > DIA_HIGH_NORM:
                status_diastolic = 'normal'
            else:
                status_diastolic = 'optimal'

            if diastolic > SYS_HIGH:
                status_systolic = 'increase'
            elif systolic > SYS_HIGH_NORM:
                status_systolic = 'normal'
            else:
                status_systolic = 'optimal'
            return dict(
                systolic=systolic,
                diastolic=diastolic,
                status_systolic=status_systolic,
                status_diastolic=status_diastolic,
                date=date
            )


        tomorrow = form.get_date_time_by_iso(date) + dt.timedelta(days=1)
        tomorrow_str = form.get_iso_by_datetime(tomorrow)

        response = self.table_blood_pressure.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('unique_id').eq(unique_id) & Key('date').between(date, tomorrow_str),
            TableName=c.TABLE_BLOOD_PRESSURE
        )

        if not response['Items']:
            return None

        pressure_systolic_sum = 0
        pressure_diastolic_sum = 0

        detailed_date_pressure = []
        for item in response['Items']:
            pressure_diastolic_sum += item['diastolic']
            pressure_systolic_sum += item['systolic']
            detailed_date_pressure.append(
                check_blood_pressure(
                    systolic=item['systolic'],
                    diastolic=item['diastolic'],
                    date=item['date']
                )
            )

        measure_count = len(response['Items'])
        pressure_systolic_average = pressure_systolic_sum / measure_count
        pressure_diastolic_average = pressure_diastolic_sum / measure_count

        d = check_blood_pressure(
            systolic=pressure_systolic_average,
            diastolic=pressure_diastolic_average,
            date=date
        )
        d.update(dict(detailed_list=detailed_date_pressure))

        return form.convert_to_float(d)

    def average_weight_for_day(self, unique_id, date):
        """Returns average weight for considered day

        :param unique_id: cognito_id
        :param date: YYYY-MM-DD
        :return: None | weight, status
        """

        WEIGHT_HIGH = 150
        WEIGHT_NORMAL = 130

        def check_weight(weight, date):
            if weight > WEIGHT_HIGH:
                status = 'increase'
            elif weight > WEIGHT_NORMAL:
                status = 'normal'
            else:
                status = 'optimal'
            return dict(
                weight=weight,
                status=status,
                date=date
            )

        tomorrow = form.get_date_time_by_iso(date) + dt.timedelta(days=1)
        tomorrow_str = form.get_iso_by_datetime(tomorrow)

        response = self.table_weight.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('unique_id').eq(unique_id) & Key('date').between(date, tomorrow_str),
            TableName=c.TABLE_WEIGHT
        )

        if not response['Items']:
            return None

        weight_sum = 0
        detailed_date_weight= []

        for item in response['Items']:
            weight_sum += item['weight']
            detailed_date_weight.append(
                check_weight(
                    weight=item['weight'],
                    date=item['date']
                )
            )

        measure_count = len(response['Items'])
        weight_average = weight_sum / measure_count

        d = check_weight(weight=weight_average, date=date)
        d.update(dict(detailed_list=detailed_date_weight))

        return form.convert_to_float(d)


    def check_blood_pressure_measurements(self, unique_id, date):
        """

        :param unique_id: cognito_id
        :param date: YYYY-MM-DD
        :return:
        """
        MID_DAY = 14
        tomorrow_dt = form.get_date_time_by_iso(date) + dt.timedelta(days=1)
        tomorrow_str = form.get_iso_by_datetime(tomorrow_dt)

        response = self.table_blood_pressure.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('unique_id').eq(unique_id) & Key('date').between(date, tomorrow_str),
            TableName=c.TABLE_BLOOD_PRESSURE
        )
        measure_morning = False
        measure_evening = False
        for item in response['Items']:
            current_dt = form.get_date_time_by_iso(item['date'])
            if current_dt.hour < MID_DAY and current_dt.hour > 3:
                measure_morning = True
            if current_dt.hour > MID_DAY:
                measure_evening = True

        d = {}
        morning_passed = dt.datetime.now() > form.get_date_time_by_iso(date) + dt.timedelta(hours=MID_DAY)
        evening_passed = dt.datetime.now() > tomorrow_dt

        if morning_passed:
            d.update(dict(morning=measure_morning))
        else:
            if measure_morning:
                d.update(dict(morning=measure_morning))

        if evening_passed:
            d.update(dict(evening=measure_evening))
        else:
            if measure_evening:
                d.update(dict(measure_evening))
        return d

    def check_weight_measurements(self, unique_id, date):
        """

        :param unique_id: cognito_id
        :param date: YYYY-MM-DD
        :return:
        """
        MID_DAY = 14
        tomorrow_dt = form.get_date_time_by_iso(date) + dt.timedelta(days=1)
        tomorrow_str = form.get_iso_by_datetime(tomorrow_dt)

        response = self.table_weight.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('unique_id').eq(unique_id) & Key('date').between(date, tomorrow_str),
            TableName=c.TABLE_WEIGHT
        )
        measure_morning = False
        measure_evening = False
        for item in response['Items']:
            current_dt = form.get_date_time_by_iso(item['date'])
            if current_dt.hour < MID_DAY and current_dt.hour > 3:
                measure_morning = True
            if current_dt.hour > MID_DAY:
                measure_evening = True

        d = {}
        morning_passed = dt.datetime.now() > form.get_date_time_by_iso(date) + dt.timedelta(hours=MID_DAY)
        evening_passed = dt.datetime.now() > tomorrow_dt

        if morning_passed:
            d.update(dict(morning=measure_morning))
        else:
            if measure_morning:
                d.update(dict(morning=measure_morning))

        if evening_passed:
            d.update(dict(evening=measure_evening))
        else:
            if measure_evening:
                d.update(dict(measure_evening))
        return d

    def percentage_blood_pressure(self, unique_id, date):
        """

        :param unique_id:
        :return:
        """
        today = date
        measurements = self.check_blood_pressure_measurements(unique_id=unique_id, date=today)
        percentage = 0
        if measurements.get('morning'):
            percentage += 50
        if measurements.get('evening'):
            percentage += 50
        return percentage

    def insert_weight(self, unique_id, date, weight):
        if not weight:
            raise ValueError('No valid measurements')
        self.table_weight.update_item(
            Key={
                'unique_id': unique_id,
                'date': date
            },
            UpdateExpression='SET #weight = :weight',
            ExpressionAttributeNames={
                '#weight': 'weight'
            },
            ExpressionAttributeValues={
                ":weight": decimal.Decimal(weight)
            }
        )
        return {'message': 'success'}

    def insert_blood_pressure(self, unique_id, date, systolic, diastolic):
        if not systolic or not diastolic:
            raise ValueError('No valid measurements')

        self.table_blood_pressure.update_item(
            Key={
                'unique_id': unique_id,
                'date': date
            },
            UpdateExpression='SET #systolic = :systolic',
            ExpressionAttributeNames={
                '#systolic': 'systolic'
            },
            ExpressionAttributeValues={
                ":systolic": decimal.Decimal(systolic)
            }
        )
        self.table_blood_pressure.update_item(
            Key={
                'unique_id': unique_id,
                'date': date
            },
            UpdateExpression='SET #diastolic = :diastolic',
            ExpressionAttributeNames={
                '#diastolic': 'diastolic'
            },
            ExpressionAttributeValues={
                ":diastolic": decimal.Decimal(diastolic)
            }
        )
        return {'message': 'success'}


    def percentage_weight(self, unique_id, date):
        today = date
        measurements = self.check_weight_measurements(unique_id=unique_id, date=today)
        percentage = 0
        if measurements.get('morning'):
            percentage += 50
        if measurements.get('evening'):
            percentage += 50
        return percentage

    def set_shopping_list(self, unique_id, shoppinglist):
        for date, content in shoppinglist.iteritems():

            item = {
                'actual_list': content,
                 c.DATE: date,
                 c.UNIQUE_IDENTIFIER: unique_id
            }
            self.table_shopping_list.put_item(Item=form.convert_to_decimal(item))



    def query_table_for_active_users(self, delta_time):
        """Scans the user data table for active users. This method is invoked once
        every week when new plans are generated for the following week.

        :param delta_time: time in days since last login for which users
                           are still considered to be active
        :return: list of cognito ids that are considered to be active
        """
        unique_id_list = []
        response = self.client.query(
            TableName=c.TABLE_USER_DATA,
            Select='SPECIFIC_ATTRIBUTES',
            ProjectionExpression='#id',
            FilterExpression='#last_login > :critical_date',
            ExpressionAttributeNames={'#id': c.UNIQUE_IDENTIFIER,
                                      '#last_login': c.LAST_LOGIN},
            ExpressionAttributeValues={':critical_date': {'S': form.get_date_in_iso(-delta_time)}},
            ConsistentRead=True
        )
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
        self.table_nutrient_for_day = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        self.table_nutrient_for_week = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_WEEK)

    def _update_checked_nutrients(self, unique_id, date, plan, add):
        """

        :param unique_id:
        :param date:
        :param plan:
        :param add:
        :return:
        """
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        week = form.get_week_by_date(date)

        item_checked_nutrients_for_week = table.get_item(
            TableName=c.TABLE_NUTRITIONAL_NEEDS_WEEK,
            Key={
                c.UNIQUE_IDENTIFIER: unique_id,
                c.WEEK: week
            },
            ProjectionExpression='#toplevel',
            ExpressionAttributeNames={"#toplevel": c.NUTRIENTS_FOR_WEEK_CHECKED}
        )

        item_checked_nutrients_for_day = table.get_item(
            TableName=c.TABLE_NUTRITIONAL_NEEDS_DAY,
            Key={
                c.UNIQUE_IDENTIFIER: unique_id,
                c.DATE: date
            },
            ProjectionExpression='#toplevel',
            ExpressionAttributeNames={"#toplevel": c.NUTRIENTS_FOR_DAY_CHECKED}
        )
        pprint.pprint(item_checked_nutrients_for_day)
        pprint.pprint(plan)
        for container_key, container_content in plan['Item'][c.NUTRIENTS_FOR_MEAL].iteritems():
            for meal_key, meal_content in container_content.iteritems():
                for n in params.nutrientList:
                    item_checked_nutrients_for_week[c.ITEM][c.NUTRIENTS_FOR_WEEK_CHECKED][n]['VAL'] += \
                        meal_content['nutrients'][n]['VAL'] * (1 if add else -1)

                    item_checked_nutrients_for_week[c.ITEM][c.NUTRIENTS_FOR_WEEK_CHECKED][n]['UNIT'] = \
                        meal_content['nutrients'][n]['UNIT']

                    item_checked_nutrients_for_day[c.ITEM][c.NUTRIENTS_FOR_DAY_CHECKED][n]['VAL'] += \
                        meal_content['nutrients'][n]['VAL'] * (1 if add else -1)

                    item_checked_nutrients_for_day[c.ITEM][c.NUTRIENTS_FOR_DAY_CHECKED][n]['UNIT'] = \
                        meal_content['nutrients'][n]['UNIT']

        table.update_item(
            TableName=c.TABLE_NUTRITIONAL_NEEDS_DAY,
            Key={c.UNIQUE_IDENTIFIER: unique_id,
                 c.DATE: date},
            UpdateExpression='SET #toplevel = :value',
            ExpressionAttributeNames={
                "#toplevel": c.NUTRIENTS_FOR_DAY_CHECKED
            },
            ExpressionAttributeValues={
                ":value": item_checked_nutrients_for_day[c.ITEM][c.NUTRIENTS_FOR_DAY_CHECKED]
            }
        )

        table.update_item(
            TableName=c.TABLE_NUTRITIONAL_NEEDS_WEEK,
            Key={c.UNIQUE_IDENTIFIER: unique_id,
                 c.WEEK: week},
            UpdateExpression='SET #toplevel = :value',
            ExpressionAttributeNames={
                "#toplevel": c.NUTRIENTS_FOR_WEEK
            },
            ExpressionAttributeValues={
                ":value": item_checked_nutrients_for_week[c.ITEM][c.NUTRIENTS_FOR_WEEK_CHECKED]
            }
        )

    def _update_total_nutrition_values(self, unique_id, date, plan, add):
        """Updates total nutrition values for both Day and Week table

        :param unique_id:
        :param date:
        :param plan: {cat: {SBLS: {n1: xx, n2: xx}
        :param add: boolean
        """
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        week = form.get_week_by_date(date)

        item_nutrients_for_week = table.get_item(
            TableName=c.TABLE_NUTRITIONAL_NEEDS_WEEK,
            Key={
                c.UNIQUE_IDENTIFIER: unique_id,
                c.WEEK: week
            },
            ProjectionExpression='#toplevel',
            ExpressionAttributeNames={"#toplevel": c.NUTRIENTS_FOR_WEEK}
        )

        item_nutrients_for_day = table.get_item(
            TableName=c.TABLE_NUTRITIONAL_NEEDS_DAY,
            Key={
                c.UNIQUE_IDENTIFIER: unique_id,
                c.DATE: date
            },
            ProjectionExpression='#toplevel',
            ExpressionAttributeNames={"#toplevel": c.NUTRIENTS_FOR_DAY}
        )

        for container, container_content in plan.iteritems():
            item_nutrients_for_container = table.get_item(
                TableName=c.TABLE_NUTRITIONAL_NEEDS_DAY,
                Key={c.UNIQUE_IDENTIFIER: unique_id, c.DATE: date},
                ProjectionExpression='#toplevel.#container',
                ExpressionAttributeNames={
                    "#toplevel": c.NUTRIENTS_FOR_CONTAINER,
                    "#container": container
                }
            )
            for meal_key, meal_content in container_content.iteritems():



                for n in params.nutrientList:
                    pprint.pprint(item_nutrients_for_week)
                    item_nutrients_for_week[c.ITEM][c.NUTRIENTS_FOR_WEEK][n]['VAL'] += meal_content['nutrients'][n]['VAL'] * \
                                                                                       (1 if add else -1)
                    item_nutrients_for_week[c.ITEM][c.NUTRIENTS_FOR_WEEK][n]['UNIT'] = meal_content['nutrients'][n]['UNIT']
                    item_nutrients_for_day[c.ITEM][c.NUTRIENTS_FOR_DAY][n]['VAL'] += meal_content['nutrients'][n]['VAL'] * \
                                                                                     (1 if add else -1)
                    item_nutrients_for_day[c.ITEM][c.NUTRIENTS_FOR_DAY][n]['UNIT'] = meal_content['nutrients'][n]['UNIT']
                    item_nutrients_for_container[c.ITEM][c.NUTRIENTS_FOR_CONTAINER][container][n]['VAL'] += \
                        meal_content['nutrients'][n]['VAL'] * (1 if add else -1)
                    item_nutrients_for_container[c.ITEM][c.NUTRIENTS_FOR_CONTAINER][container][n]['UNIT'] = \
                        meal_content['nutrients'][n]['UNIT']


            table.update_item(
                TableName=c.TABLE_NUTRITIONAL_NEEDS_DAY,
                Key={c.UNIQUE_IDENTIFIER: unique_id,
                   c.DATE: date},
                UpdateExpression='SET #toplevel.#cat = :value',
                ExpressionAttributeNames={
                    "#toplevel": c.NUTRIENTS_FOR_CONTAINER,
                    "#cat": container
                },
                ExpressionAttributeValues={
                    ":value": item_nutrients_for_container[c.ITEM][c.NUTRIENTS_FOR_CONTAINER][container]
                }
            )

        table.update_item(
            TableName=c.TABLE_NUTRITIONAL_NEEDS_DAY,
            Key={c.UNIQUE_IDENTIFIER: unique_id,
               c.DATE: date},
            UpdateExpression='SET #toplevel = :value',
            ExpressionAttributeNames={
                "#toplevel": c.NUTRIENTS_FOR_DAY
            },
            ExpressionAttributeValues={
              ":value": item_nutrients_for_day[c.ITEM][c.NUTRIENTS_FOR_DAY]
            }
        )

        table.update_item(
            TableName=c.TABLE_NUTRITIONAL_NEEDS_WEEK,
            Key={
                c.UNIQUE_IDENTIFIER: unique_id,
                c.WEEK: week
            },
            UpdateExpression='SET #toplevel = :value',
            ExpressionAttributeNames={
                "#toplevel": c.NUTRIENTS_FOR_WEEK
            },
            ExpressionAttributeValues={
              ":value": item_nutrients_for_week[c.ITEM][c.NUTRIENTS_FOR_WEEK]
            }
        )


    def get_whole_item_for_day(self, unique_id, date):
        response = self.table_nutrient_for_day.get_item(
            Key={
                'unique_id': unique_id,
                'date': date
            }
        )
        return form.convert_to_float(response.get('Item'))

    def get_whole_item_for_week(self, unique_id, week):
        response = self.table_nutrient_for_day.get_item(
            Key={
                'unique_id': unique_id,
                'week': week
            }
        )
        print response
        return form.convert_to_float(response.get('Item'))

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

    def percentage_food(self, unique_id, date):
        """

        :param unique_id:
        :param date:
        :return:
        """
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        response = table.get_item(
            Key={
                'unique_id': unique_id,
                'date': date
            },
            ProjectionExpression='#attr',
            ExpressionAttributeNames={
                '#attr': 'plan_checked'
            }
        )
        meals_checked = 0
        meals_total = 0
        if not response.get('Item'):
            return 0
        for container_key, container_content in response['Item']['plan_checked'].iteritems():
            for key, val in container_content.iteritems():
                meals_total += 1.0
                if val:
                    meals_checked += 1.0

        return int((meals_checked/meals_total) * 100.0)

    def meal_eaten(self, unique_id, date, container_key, meal_key):
        """

        :param unique_id:
        :param date:
        :param container_key:
        :param meal_key:
        :return:
        """
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)


        response_plan = table.get_item(
            Key={
                'unique_id': unique_id,
                'date': date
            },
            ProjectionExpression='#plan.#container_key.#meal_key',
            ExpressionAttributeNames={
                '#plan': c.NUTRIENTS_FOR_MEAL,
                '#container_key': container_key,
                '#meal_key': meal_key
            }
        )
        if not response_plan.get('Item'):
            return {'status': 'no success',
                    'message': "Meal with key '" + meal_key + "' not stored in DynamoDB"}

        response = table.get_item(
            Key={
                'unique_id': unique_id,
                'date': date
            },
            ProjectionExpression='#plan_checked.#container_key.#meal_key',
            ExpressionAttributeNames={
                '#plan_checked': c.PLAN_CHECKED,
                '#container_key': container_key,
                '#meal_key': meal_key
            }
        )
        if response['Item'][c.PLAN_CHECKED][container_key][meal_key]:
            return {'status': 'no success',
                    'message': 'Meal already checked.'}

        self._update_checked_nutrients(unique_id=unique_id, date=date, plan=response_plan, add=True)

        response = table.update_item(
            Key={
                'unique_id': unique_id,
                'date': date
            },
            UpdateExpression='SET #plan_checked.#container_key.#meal_key = :checked',
            ExpressionAttributeNames={
                '#plan_checked': 'plan_checked',
                '#container_key': container_key,
                '#meal_key': meal_key
            },
            ExpressionAttributeValues={
                ":checked": True
            }
        )
        return {'status': 'success',
                'message': 'Everything worked fine.'}


    def write_to_nutrients_for_day(self, status, unique_id, plan, nut_for_day, meals_checked,
                                   nut_for_container, splittedNeeds, nutNeedsForDay):
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        with table.batch_writer() as batch:
            for day in plan.iterkeys():
                current_plan = {
                    c.PLAN: plan[day],
                    c.UNIQUE_IDENTIFIER: unique_id,
                    c.DATE: day,
                    c.STATUS: status,
                    c.NUTRIENTS_FOR_DAY: nut_for_day[day],
                    c.NUTRIENTS_FOR_CONTAINER: nut_for_container[day],
                    c.SPLITTED_NEEDS: splittedNeeds,
                    c.NUTRIENT_NEED_FOR_DAY: nutNeedsForDay,
                    c.CREATED_ON: form.get_date_in_iso(),
                    c.NUTRIENTS_FOR_DAY_CHECKED: params.default_nutrient_checked_dict,
                    "plan_checked": meals_checked[day]
                }
                # print 'this is current_plan'
                # pprint.pprint(current_plan)

                batch.put_item(Item=form.convert_to_decimal(current_plan))

    def write_to_nutrients_for_week(self, boundsForWeek, unique_id, nut_for_week, time):
        """

        :param boundsForWeek: {'EARG': {'LB': 35000}, 'VC': {...
        :param unique_id:
        :param nut_for_week: {'EARG': 38000, 'VC': 4100000, ..
        :return:
        """
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_WEEK)
        for week, nut_for_week in nut_for_week.iteritems():
            item = {
                c.BOUNDS_FOR_WEEK: form.convert_to_decimal(boundsForWeek),
                c.UNIQUE_IDENTIFIER: unique_id,
                c.WEEK: week,
                c.NUTRIENTS_FOR_WEEK: form.convert_to_decimal(nut_for_week),
                c.SOLUTION_TIME: form.convert_to_decimal(time),
                c.CREATED_ON: form.get_date_in_iso(),
                c.NUTRIENTS_FOR_WEEK_CHECKED: params.default_nutrient_checked_dict
            }
            last_week = week

            table.put_item(Item=form.convert_to_decimal(item))
        table = self.dynamodb.Table(c.TABLE_USER_DATA)
        item = {
            c.UNIQUE_IDENTIFIER: unique_id,
            c.LAST_EVALUATED_WEEK: last_week
        }
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
        plan = form.convert_to_decimal(nutrients.nutrients_for_meal)
        for_loop_broken = False
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        for date, day_plan in plan.iteritems():
            for container, container_content in day_plan.iteritems():
                for meal_key, meal_content in container_content.iteritems():
                    try:
                        response = table.update_item(
                            Key={
                                c.UNIQUE_IDENTIFIER: unique_id,
                                c.DATE: date
                            },
                            UpdateExpression='SET #toplevel.#secondlevel.#thirdlevel = :value',
                            ConditionExpression=Attr('#toplevel.#secondlevel').exists(),
                            ExpressionAttributeNames={
                                "#toplevel": c.PLAN,
                                "#secondlevel": container,
                                "#thirdlevel": meal_key
                            },
                            ExpressionAttributeValues={
                                ":value": meal_content
                            }
                        )
                    except:
                        for_loop_broken = True
                        break
                if for_loop_broken:
                    response = table.update_item(
                        Key={
                            c.UNIQUE_IDENTIFIER: unique_id,
                            c.DATE: date
                        },
                        UpdateExpression='SET #toplevel.#secondlevel = :value',
                        ExpressionAttributeNames={
                            "#toplevel": c.PLAN,
                            "#secondlevel": container,

                        },
                        ExpressionAttributeValues={
                            ":value": container_content
                        }
                    )

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
            Key={
                c.UNIQUE_IDENTIFIER: unique_id,
                c.DATE: date
            },
            ProjectionExpression='#plan.#container.#currentKey' if key else '#plan.#container',
            ExpressionAttributeNames=expression
        )
        return item[c.ITEM][c.PLAN][container]

    def get_from_nutrients_for_day(self, unique_id, date, top_level, second_level=None, third_level=None):
        """

        :param unique_id: basestring, cognito_id
        :param date: basestring | list, ISO-8601 date
        :param top_level: basestring, top level attribute
        :param second_level: basestring, second level attribute
        :param third_level: basestring, third level attribute
        :return: data structure that is in last defined level
        """
        table = self.dynamodb.Table(c.TABLE_NUTRITIONAL_NEEDS_DAY)
        # if isinstance(date, basestring):
        #     raise TypeError('date must be a list or tuple not basestring')

        if third_level:
            if not second_level:
                raise ValueError('second_level must be defined when third_level is.')

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
        current_item = table.get_item(
            Key={
                c.UNIQUE_IDENTIFIER: unique_id,
                c.WEEK: week
            },
            ProjectionExpression='#toplevel',
            ExpressionAttributeNames={'#toplevel': c.BOUNDS_FOR_WEEK}
        )

        current_item = form.convert_to_float(current_item)
        for n in params.nutrientsMicroList:
            current_item[c.ITEM][c.BOUNDS_FOR_WEEK][n][c.LB] *= redLb
        ret_val = current_item[c.ITEM][c.BOUNDS_FOR_WEEK]

        return ret_val
