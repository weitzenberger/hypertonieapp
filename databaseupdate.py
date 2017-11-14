#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 19.10.17

ALTER TABLE dbo.MEAL_DES ADD VEGAN INT NULL,
VEGGIE INT NULL,
AL_EGG INT NULL,
AL_PEANUTS INT NULL,
AL_CRUSTACEAN INT NULL,
AL_CELERY INT NULL,
AL_SOY INT NULL,
AL_FISH INT NULL,
AL_SQUID INT NULL,
AL_NUTS INT NULL,
AL_MUSTARD INT NULL,
AL_SESAM INT NULL,
IN_GLUT INT NULL,
IN_LAKT INT NULL;

ALTER TABLE [Main].[dbo].[meal_des] ADD F183 float NULL, F182 float NULL, GCAL float NULL, MK float NULL, MMG float NULL, MFE float NULL, MZN float NULL, MNA float NULL, MP float NULL, VA float NULL, VC float NULL, VD float NULL, VE INT NULL, ZK INT NULL, ZE INT NULL, ZF float NULL, VK float NULL, ZB float NULL, VB2 float NULL, MCL float NULL, VB9G float NULL, EARG float NULL, MCA float NULL, MJ float NULL, VB12 float NULL, VB1 float NULL, MMN float NULL, VB7 float NULL, VB6 float NULL, VB5 float NULL, MCU float NULL


@author: L.We
"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import traceback

import dbupdatetools as updater

#updater.update_sta_table()

all_meal_des = updater.get_all_meal_des_from_xlsx()

all_meal_ing = updater.get_all_meals_ingredients_from_xlsx()

for meal_key, meal_des in all_meal_des.iteritems():
    try:
        response = updater.characterize_and_insert_meal_des(meal_key, meal_des, all_meal_ing[meal_key])

        if response['insertion']['IN_GLUT']:
            kwargs = updater.create_and_insert_de_meal(meal_key, meal_des, response['meal_ing'], de_glut=True)
            if kwargs:
                ret = updater.characterize_and_insert_meal_des(**kwargs)
        if response['insertion']['IN_LAKT']:
            kwargs = updater.create_and_insert_de_meal(meal_key, meal_des, response['meal_ing'], de_lakt=True)
            if kwargs:
                ret = updater.characterize_and_insert_meal_des(**kwargs)
        if response['insertion']['IN_LAKT'] and response['insertion']['IN_GLUT']:
            kwargs = updater.create_and_insert_de_meal(meal_key, meal_des, response['meal_ing'], de_lakt=True, de_glut=True)
            if kwargs:
                ret = updater.characterize_and_insert_meal_des(**kwargs)
    except:
        traceback.print_exc()



