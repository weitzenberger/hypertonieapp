#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 16.11.17


@author: L.We
"""

import unittest
placeholder_id = 'TEST_ID'
placeholder_week = '2017-W46'
placeholder_date = '2017-11-27'
placeholder_container = 'BF'
placeholder_meal = 'adsfasdfdfdfeedd'
placeholder_date_list = ['2017-11-16', '2017-11-17', '2017-11-18']
placeholder_sbls = 'B10000'
event = {
    'context': {'cognito-identity-id': placeholder_id},
    'body-json': {
        'week': placeholder_week,
        'date': placeholder_date,
        'container_key': placeholder_container,
        'meal_key': placeholder_meal,
        'ls_date': placeholder_date_list,
        'keyword': 'Hühnerei',
        'key': placeholder_sbls,
        'bucket': 'grocery',
        'SBLS': placeholder_sbls,
        'put_meal': True,
        'table_name': 'NutrientsForDay',
        'weight': 90,
        'systolic': 120,
        'diastolic': 80
        }
}


# print s

from mobileapi import *

if __name__ == '__main__':
    pprint.pprint(hints(event, context=None))
    pprint.pprint(scan_bls(event=event, context=None))
    for content in ['nutrients', "allergies", "intolerances", "input_range", "diseases", "daily_top", "home_slides"]:
        pprint.pprint(get_kadia_content(event={'body-json': {'keyword': content}}, context=None))
    # pprint.pprint(container_categories(event=event, context=None))
    pprint.pprint(blood_pressure_for_week(event=event, context=None))
    pprint.pprint(grocery_url(event=event, context=None))
    pprint.pprint(weight_for_week(event=event, context=None))
    pprint.pprint(blood_pressure_input_check(event=event, context=None))
    # pprint.pprint(check_item(event=event, context=None))
    # pprint.pprint(shopping_list(event=event, context=None))
    pprint.pprint(percentage(event=event, context=None))
    pprint.pprint(meal_eaten(event=event, context=None))
    pprint.pprint(like_meal(event,context=None))
    pprint.pprint(get_whole_item(event, None))
    pprint.pprint(is_liked_or_disliked(event, None))
    pprint.pprint(hints(event, context=None))
    pprint.pprint(measure_blood_pressure(event, None))
    pprint.pprint(measure_weight(event, None))
    pprint.pprint(dislike_meal(event, None))
    pprint.pprint(like_meal(event, None))



    pass