#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 29.05.2017 14:54


@author: L.We
"""

import os

""" DYNAMO DB """
# table names
TABLE_NUTRITIONAL_NEEDS_WEEK = 'NutrientsForWeek'
TABLE_NUTRITIONAL_NEEDS_DAY = 'NutrientsForDay'
TABLE_USER_DATA = 'UserDataTable'

# top level attributes
NUTRIENTS_FOR_WEEK = 'nutrients_for_plan'
NUTRIENTS_FOR_DAY = 'nutrients_for_plan'
NUTRIENTS_FOR_MEAL = 'nutrients_for_meal'
UNIQUE_IDENTIFIER = 'unique_id'  # partition key (hash)

LAST_LOGIN = 'last_login'
LAST_EVALUATED_WEEK = 'last_evaluated_week'
# top level attributes
BOUNDS_FOR_WEEK = 'bounds'
NUTRIENT_NEED_FOR_DAY = 'needs_for_day'
PLAN = 'plan'
STATUS = 'status'
DATE = 'date'
WEEK = 'week'
SPLITTED_NEEDS = 'splitted_needs'
ITEM = 'Item'
ITEMS = 'Items'
SOLUTION_TIME = 'solution_time'
CREATED_ON = 'created_on'

""" SQL DATABASE """
SQL_HOST = "main.cxh7i7jlsgbr.eu-central-1.rds.amazonaws.com"
SQL_USER = "engelstrompete"
SQL_PW = "escagang69"
SQL_DB_NAME = "main"
SQL_BLS = '[Main].[dbo].[BLS_3.02]'
SQL_STA = '[Main].[dbo].[standard]'
SQL_MEAL_DES = '[Main].[dbo].[meal_des]'
SQL_MEAL_ING = '[Main].[dbo].[meal_comp]'
SQL_SALAD = '[Main].[dbo].[gs_ing]'
SQL_SALAD_COMBI = '[Main].[dbo].[gs_comp]'
SQL_SALAD_FRUIT = '[BLSmaindb].[dbo].[salad_fruit]'
SQL_CURD = '[BLSmaindb].[dbo].[curd]'
SQL_SALAD_BREAD = '[BLSmaindb].[dbo].[salad_bread]'
SQL_ITEMS = '[Main].[dbo].[Items]'
SQL_SMOOTHIES = '[BLSmaindb].[dbo].[Smoothie]'
SQL_SANDWICH = '[BLSmaindb].[dbo].[Sandwich]'
SQL_DGE = '[Main].[dbo].[DGE]'
SQL_PLATE = '[Main].[dbo].[PLATE]'

""" key words """
LB = 'LB'
UB = 'UB'
INT = 'INT'
OFFSET = 'OFFSET'
COUNT = 'COUNT'
BREAD = 'BREAD'
BUTTER = 'BUTTER'
COMBI = 'COMBI'
TOPPING = 'TOPPING'

""" COGNITO AND DDB STREAM """
COGNITO_ID_POOL = 'eu-central-1:2958e585-ef38-463e-aed4-ba59a0857566'
RECORDS = 'Records'
CONTENTS = 'Contents'
DATASET_NAME = 'datasetName'
DATASET_RECORDS = 'datasetRecords'
OLD_VALUE = 'oldValue'
NEW_VALUE = 'newValue'
VALUE = 'Value'

DATASET_VITAL = 'userInformation'
DATASET_NUTRIENTS = 'userNutrients'
DATASET_LIKE = 'userLikes'
DATASET_DISLIKE = 'asdf'
DATASET_CAT = 'asdf'
DATASET_LAST_LOGIN = 'iso8601'


HANDLER_GENERATE = 'escamed-mac-generate'


LOREM_IPSUM = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, ' \
              'sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. ' \
              'Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris ' \
              'nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in ' \
              'reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla ' \
              'pariatur. Excepteur sint occaecat cupidatat non proident, sunt in ' \
              'culpa qui officia deserunt mollit anim id est laborum.'



