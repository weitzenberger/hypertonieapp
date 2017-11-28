#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 23.10.17


@author: L.We
"""



import pprint
import random
import pymysql
import requests
from sqlalchemy.sql.expression import select

import awsapi
import params
import dbmodel as db
import form
from dbmodel import BLS, engine
import constants as c

import sys
reload(sys)
sys.setdefaultencoding('utf-8')


def _get_all_entries(engine, model):
    session = db.start_session(engine=engine)
    ls = []
    for object in session.query(model).all():
        ls.append(object.as_dict())
    return ls


def _input_range():
    session = db.start_session(engine=db.engine)

    input_height = session.query(db.InputRange).filter_by(NAME='height').first()
    input_age = session.query(db.InputRange).filter_by(NAME='age').first()
    input_pal = session.query(db.InputRange).filter_by(NAME='pal').first()
    input_weight = session.query(db.InputRange).filter_by(NAME='weight').first()
    input_systolic = session.query(db.InputRange).filter_by(NAME='systolic').first()
    input_diastolic = session.query(db.InputRange).filter_by(NAME='diastolic').first()

    return dict(
        birthday=dict(
            min=form.get_date_in_iso(year_delta=input_age.LOW_BOUND),
            max=form.get_date_in_iso(year_delta=input_age.UP_BOUND) if input_age.UP_BOUND else None,
            step=input_age.STEP
        ),
        height=dict(
            min=int(input_height.LOW_BOUND),
            max=int(input_height.UP_BOUND),
            step=int(input_height.STEP)
        ),
        weight=dict(
            min=input_weight.LOW_BOUND,
            max=input_weight.UP_BOUND,
            step=input_weight.STEP
        ),
        pal=dict(
            min=input_pal.LOW_BOUND,
            max=input_pal.UP_BOUND,
            step=input_pal.STEP
        ),
        systolic=dict(
            min=int(input_systolic.LOW_BOUND) if input_systolic.LOW_BOUND else None,
            max=int(input_systolic.UP_BOUND) if input_systolic.UP_BOUND else None,
            step=int(input_systolic.STEP)
        ),
        diastolic=dict(
            min=int(input_diastolic.LOW_BOUND) if input_diastolic.LOW_BOUND else None,
            max=int(input_diastolic.UP_BOUND) if input_diastolic.UP_BOUND else None,
            step=int(input_diastolic.STEP)
        )
    )


def _diseases():
    return [
        {
            'NAME': "Bluthochdruck",
            'KEYWORD': 'HYPERTENSION'
        }
    ]


def _daily_top():
    ls = _get_all_entries(engine=db.engine, model=db.DailyTop)
    rand_int = random.randint(0, len(ls)-1)
    return ls[rand_int]


def scan_bls(event, context):
    search_words = event['body-json']['keyword']
    connection = pymysql.connect(**db.connection_kwargs)
    search_words_list = search_words.split()[:4]
    search_words_list_final = []
    for word in search_words_list:
        search_words_list_final.append("%" + word + "%")
    length = len(search_words_list_final)
    switch_query={
        1: "SELECT SBLS, ST FROM {tbl} WHERE ST LIKE %s ORDER BY LENGTH(ST) LIMIT 15",
        2: "SELECT SBLS, ST FROM {tbl} WHERE ST LIKE %s AND ST LIKE %s ORDER BY LENGTH(ST) LIMIT 15",
        3: "SELECT SBLS, ST FROM {tbl} WHERE ST LIKE %s AND ST LIKE %s AND ST LIKE %s ORDER BY LENGTH(ST) LIMIT 15",
        4: "SELECT SBLS, ST FROM {tbl} WHERE ST LIKE %s AND ST LIKE %s AND ST LIKE %s AND ST LIKE %s ORDER BY LENGTH(ST) LIMIT 15"
    }
    query = switch_query[length].format(tbl=c.MYSQL_BLS)
    with connection.cursor() as cursor:
        cursor.execute(query, tuple(search_words_list_final))
    d = cursor.fetchall()
    return d


def get_kadia_content(event, context):
    print event
    keyword = event['body-json']['keyword']
    if keyword == "nutrients":
        return _get_all_entries(engine=db.engine, model=db.Nutrients)
    elif keyword == "allergies":
        return _get_all_entries(engine=db.engine, model=db.Allergies)
    elif keyword == "habits":
        return _get_all_entries(engine=db.engine, model=db.Habits)
    elif keyword == 'intolerances':
        return _get_all_entries(engine=db.engine, model=db.Intolerances)
    elif keyword == 'input_range':
        return _input_range()
    elif keyword == "container_categories":
        return _get_all_entries(engine=db.engine, model=db.ContainerCategories)
    elif keyword == 'diseases':
        return _diseases()
    elif keyword == 'home_slides':
        return _get_all_entries(engine=db.engine, model=db.HomeSlides)
    elif keyword == "daily_top":
        return _daily_top()


def blood_pressure_for_week(event, context):
    cognito_id = event['context']['cognito-identity-id']
    week = event['body-json']['week']
    client = awsapi.DynamoUserData()
    d = {}
    d['average'] = []
    d['detailed_date'] = []
    for day in form.get_dates_by_week(week=week):
        item = client.average_blood_pressure_for_day(unique_id=cognito_id, date=day)
        print item
        if item:
            d['detailed_date'] += item.pop('detailed_list')
            d['average'].append(item)
    return d


def grocery_url(event, context):
    key = event['body-json']['key']
    bucket = event['body-json']['bucket']
    if bucket == 'grocery':
        url = awsapi.S3().get_img_url(key)
        if requests.get(url=url).status_code != 200:
            bucket_url = None
        else:
            bucket_url = url
        session = db.start_session(engine=db.engine)
        if session.query(db.BLS).filter_by(SBLS=key).first():
            ST = session.query(db.BLS).filter_by(SBLS=key).first().ST
            return dict(
                URL=bucket_url,
                ST=ST
            )
        return dict(
                URL=bucket_url,
                ST=None
        )
    else:
        session = db.start_session(engine=db.engine)
        if session.query(db.MealDescription).filter_by(MEAL_ID=key).first():
            ST = session.query(db.MealDescription).filter_by(MEAL_ID=key).first().MEAL_ID
            return dict(
                URL=None,
                ST=ST
            )
        return dict(
            URL=None,
            ST=None
        )


def percentage(event, context):
    cognito_id = event['context']['cognito-identity-id']
    date = event['body-json']['date']
    client_user = awsapi.DynamoUserData()
    client_nut = awsapi.DynamoNutrition()
    return dict(
        weight=client_user.percentage_weight(
            unique_id=cognito_id,
            date=date
        ),
        food=client_nut.percentage_food(
            unique_id=cognito_id,
            date=date
        ),
        blood_pressure=client_user.percentage_blood_pressure(
            unique_id=cognito_id,
            date=date
        )
    )


def weight_for_week(event, context):
    cognito_id = event['context']['cognito-identity-id']
    week = event['body-json']['week']
    client = awsapi.DynamoUserData()
    d = {}
    d['average'] = []
    d['detailed_date'] = []
    for day in form.get_dates_by_week(week=week):
        item = client.average_weight_for_day(unique_id=cognito_id, date=day)
        print item
        if item:
            d['detailed_date'] += item.pop('detailed_list')
            d['average'].append(item)
    return d


def blood_pressure_input_check(event, context):
    date = event['body-json']['date']
    cognito_id = event['context']['cognito-identity-id']
    client = awsapi.DynamoUserData()
    return client.check_blood_pressure_measurements(unique_id=cognito_id, date=date)


def check_item(event, context):
    sbls = event['body-json']['SBLS']
    cognito_id = event['context']['cognito-identity-id']
    client = awsapi.DynamoUserData()
    return client.shopping_list_check_item(unique_id=cognito_id, sbls=sbls)


def shopping_list(event, context):
    cognito_id = event['context']['cognito-identity-id']
    client = awsapi.DynamoUserData()
    d = client.shopping_list(unique_id=cognito_id)
    conn = engine.connect()
    for sbls in d.iterkeys():
        s = select([BLS.ST]).where(BLS.SBLS == sbls)
        rows = conn.execute(s)
        for row in rows:
            dict_ = dict(zip(row.keys(), row.values()))
            d[sbls].update(dict_)
    return d


def set_shopping_list_dates(event, context):
    cognito_id = event['context']['cognito-identity-id']
    ls_date = event['body-json']['date_list']
    client = awsapi.DynamoUserData()
    return client.create_shopping_list(unique_id=cognito_id, ls_date=ls_date)


def meal_eaten(event, context):
    cognito_id = event['context']['cognito-identity-id']
    date = event['body-json']['date']
    container_key = event['body-json']['container_key']
    meal_key = event['body-json']['meal_key']
    client = awsapi.DynamoNutrition()
    response = client.meal_eaten(
        unique_id=cognito_id,
        date=date,
        container_key=container_key,
        meal_key=meal_key
    )
    return response


def like_meal(event, context):
    cognito_id = event['context']['cognito-identity-id']
    meal_key = event['body-json']['meal_key']
    put_meal = event['body-json']['put_meal']
    client = awsapi.DynamoUserData()
    return client.like_meal(unique_id=cognito_id, meal_key=meal_key, put_meal=put_meal)


def dislike_meal(event, context):
    cognito_id = event['context']['cognito-identity-id']
    meal_key = event['body-json']['meal_key']
    put_meal = event['body-json']['put_meal']
    client = awsapi.DynamoUserData()
    return client.dislike_meal(unique_id=cognito_id, meal_key=meal_key, put_meal=put_meal)


def is_liked_or_disliked(event, context):
    cognito_id = event['context']['cognito-identity-id']
    meal_key = event['body-json']['meal_key']
    client = awsapi.DynamoUserData()
    return client.is_liked_or_disliked(unique_id=cognito_id, meal_key=meal_key)


def hints(event, context):

    cognito_id = event['context']['cognito-identity-id']
    date = event['body-json']['date']
    percentages = percentage(event=event, context=context)

    hints = {}

    hints.update(percentages)

    if percentages['weight'] > 0:
        hints.update({'weight_message': params.weight_2})
    else:
        hints.update({'weight_message': params.weight_1})

    if percentages['food'] > 0:
        hints.update({'food_message': params.meal_plan_3})
    elif percentages['food'] == 100:
        hints.update({'food_message': params.meal_plan_2})
    else:
        hints.update({'food_message': params.meal_plan_1})

    client = awsapi.DynamoUserData()
    blood_measure = client.check_blood_pressure_measurements(unique_id=cognito_id, date=date)
    hints.update({"blood_pressure_input_check": blood_measure})

    if not blood_measure:
        hints.update({'blood_pressure_message': params.blood_pressure_1})
    elif blood_measure.get('morning') and blood_measure.get('evening'):
        hints.update({'blood_pressure_message': params.blood_pressure_3})
    elif blood_measure.get('morning') and not blood_measure.get('evening'):
        hints.update({'blood_pressure_message': params.blood_pressure_2})
    elif not blood_measure.get('morning') and blood_measure.get('evening'):
        hints.update({'blood_pressure_message': params.blood_pressure_4})
    else:
        hints.update({'blood_pressure_message': params.blood_pressure_5})
    return hints


def measure_blood_pressure(event, context):
    cognito_id = event['context']['cognito-identity-id']
    date = event['body-json']['date']
    systolic = event['body-json']['systolic']
    diastolic = event['body-json']['diastolic']

    client = awsapi.DynamoUserData()
    return client.insert_blood_pressure(unique_id=cognito_id, date=date, systolic=systolic, diastolic=diastolic)


def measure_weight(event, context):
    cognito_id = event['context']['cognito-identity-id']
    date = event['body-json']['date']
    weight = event['body-json']['weight']
    client = awsapi.DynamoUserData()

    return client.insert_weight(unique_id=cognito_id, date=date, weight=weight)


def get_whole_item(event, context):
    cognito_id = event['context']['cognito-identity-id']
    date = event['body-json'].get('date')
    week = event['body-json'].get('week')
    if date:
        return awsapi.DynamoNutrition().get_whole_item_for_day(
            unique_id=cognito_id,
            date=date,
        )
    if week:
        return awsapi.DynamoNutrition().get_whole_item_for_week(
            unique_id=cognito_id,
            week=week,
        )





