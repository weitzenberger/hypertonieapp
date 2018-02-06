#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 19.10.17


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




