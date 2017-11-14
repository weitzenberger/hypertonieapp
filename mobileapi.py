#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 23.10.17


@author: L.We
"""
import dbmodel as db
import form
import pprint
import awsapi
import random
import pymysql
import requests

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import constants as c


def get_all_entries(engine, model):
    session = db.start_session(engine=engine)
    ls = []
    for object in session.query(model).all():
        ls.append(object.as_dict())
    return ls

def scan_bls(event, context):
    search_word = event['body-json']['keyword']
    connection = pymysql.connect(**db.connection_kwargs)
    with connection.cursor() as cursor:
        query = "SELECT SBLS, ST FROM {tbl} WHERE ST " \
                "LIKE %s ORDER BY LENGTH(ST) LIMIT 15".format(tbl=c.MYSQL_BLS)
        cursor.execute(query, ('%' + search_word + '%'))
        d = cursor.fetchall()
    return d



def nutrients(event, context):
    return get_all_entries(engine=db.engine, model=db.Nutrients)

def allergies(event, context):
    return get_all_entries(engine=db.engine, model=db.Allergies)

def habits(event, context):
    return get_all_entries(engine=db.engine, model=db.Habits)

def intolerances(event, context):
    return get_all_entries(engine=db.engine, model=db.Intolerances)

def container_categories(event, context):
    return get_all_entries(engine=db.engine, model=db.ContainerCategories)

def input_range(event, context):
    session = db.start_session(engine=db.engine)

    input_height = session.query(db.InputRange).filter_by(NAME='height').first()
    input_age = session.query(db.InputRange).filter_by(NAME='age').first()
    input_pal = session.query(db.InputRange).filter_by(NAME='pal').first()
    input_weight = session.query(db.InputRange).filter_by(NAME='weight').first()

    return dict(
        birthday=dict(
            min=form.get_date_in_iso(input_age.LOW_BOUND),
            max=form.get_date_in_iso(input_age.UP_BOUND) if input_age.UP_BOUND else None,
            step=input_age.STEP),
        height=dict(
            min=input_height.LOW_BOUND,
            max=input_height.UP_BOUND,
            step=input_height.STEP),
        weight=dict(
            min=input_weight.LOW_BOUND,
            max=input_weight.UP_BOUND,
            step=input_weight.STEP),
        pal=dict(
            min=input_pal.LOW_BOUND,
            max=input_pal.UP_BOUND,
            step=input_pal.STEP)
    )

def daily_top(event, context):
    ls = get_all_entries(engine=db.engine, model=db.DailyTop)
    rand_int = random.randint(1, len(ls))
    return ls[rand_int]

def home_slides(event, context):
    return get_all_entries(engine=db.engine, model=db.HomeSlides)

def blood_pressure_for_week(event, context):
    cognito_id = event['context']['cognito-identity-id']
    week = event['body-json']['week']
    # week = "2017-W45"
    # cognito_id = "TEST_ID"
    client = awsapi.DynamoUserData()
    ls = []
    for day in form.get_dates_by_week(week=week):
        item = client.average_blood_pressure_for_day(unique_id=cognito_id, date=day)
        if item:
            item.update(dict(date=day))
            ls.append(item)
    return ls

def grocery_url(event, context):
    sbls = event['body-json']['key']
    bucket = event['body-json']['bucket']
    # sbls = 'B214000'
    # bucket = 'grocery'
    if bucket == 'grocery':
        url = awsapi.S3().get_img_url(sbls)
        if requests.get(url=url).status_code != 200:
            bucket_url = None
        else:
            bucket_url = url
        session = db.start_session(engine=db.engine)
        ST = session.query(db.BLS).filter_by(SBLS=sbls).first().ST
        return dict(
            URL=bucket_url,
            ST=ST
        )


def weight(event, context):
    cognito_id = event['context']['cognito-identity-id']
    week = event['body-json']['week']
    # week = "2017-W45"
    # cognito_id = "TEST_ID"
    client = awsapi.DynamoUserData()
    ls = []
    for day in form.get_dates_by_week(week=week):
        item = client.average_weight_for_day(unique_id=cognito_id, date=day)
        if item:
            item.update(dict(date=day))
            ls.append(item)
    return ls

def blood_pressure_input_check(event, context):
    date = event['body-json']['date']
    cognito_id = event['context']['cognito-identity-id']
    # date = "2017-11-09"
    # cognito_id = 'TEST_ID'
    client = awsapi.DynamoUserData()
    return client.check_blood_pressure_measurements(unique_id=cognito_id, date=date)

def check_item(event, context):
    sbls = event['body-json']['sbls']
    cognito_id = event['context']['cognito-identity-id']
    # sbls = "SBLS1"
    # cognito_id = 'TEST_ID'
    client = awsapi.DynamoUserData()
    return client.shopping_list_check_item(unique_id=cognito_id, sbls=sbls)

def shopping_list(event, context):
    cognito_id = event['context']['cognito-identity-id']

    client = awsapi.DynamoUserData()
    return client.shopping_list(unique_id=cognito_id)

def create_shopping_list(event, context):
    ls_date = event['body-json']['date_list']
    client = awsapi.DynamoUserData()
    return client.create_shopping_list(unique_id=cognito_id, ls_date=ls_date)

if __name__ == '__main__':
    # pprint.pprint(container_categories(1,1))
    # pprint.pprint(weight(1,1))
    # pprint.pprint(blood_pressure_for_week(1,1))
    # pprint.pprint(blood_pressure_input_check(1, 1))
    # pprint.pprint(scan_bls(1, 1))
    pprint.pprint(grocery_url(1,1))
    pass




