# -*- coding: utf-8 -*-
"""
Created on Thu Mar 30 10:40:24 2017

Query when changing Items table

UPDATE [dbo].[Items]
SET MEAT_PLATE = Null,
VEGETABLES_PLATE = Null,
 WHOLE_GRAIN_PLATE = Null,
 LB_PLATE = Null,
 UB_PLATE = Null
WHERE SBLS = 'S151100';


GCAL    Kalorien
ZK      Kolenhydrate
ZB      Ballaststoffe
ZF      fat
FS      sat fat
FU      unsat fat
FP      mult unsat fat
FO6     omega-6 fat
FO3     omega3 fat
ZE      protein
EARG    Arginin
MK      Kalium
MNA     Natrium
MMG     Magnesium
MCA     Calcium
VC      Vitamin C
VD      Vitamin D
VE      Vitamin E


@author: L.We
"""

from collections import namedtuple


# constants for basal metabolism

MacroVal = namedtuple('MacroNutrientValues', 'ZE ZK ZF GCAL')
MicroVal = namedtuple('MicroNutrientValues', 'EARG MK MNA MMG MCA VC VD ZB')
NutVal = namedtuple('AllNutrientValues', 'EARG MK MNA MMG MCA VC VD ZB')

add_m = 5.0
add_f = -161

mult_weight = 10.0

mult_height = 6.25

mult_age = -5.0

# constants for broca-index
broca = {'mult': {'weight': {'m': 3.4,
                             'f': 2.4},
                  'height': {'m': 15.3,
                             'f': 9},
                  'age': {'m': -6.8,
                          'f': -4.7},
                  'add': {'m': -161,  # correct ?
                          'f': -65}}}

mult_weight_m_bro = 3.4
mult_weight_f_bro = 2.4

mult_height_m_bro = 15.3
mult_height_f_bro = 9

mult_age_m_bro = -6.8
mult_age_f_bro = -4.7

add_m_bro = -961
add_f_bro = -65

# BMI cases
BMI_bound_bro = 30.0
BMI_bound = 25.0

# standard cal reduction 500-800
cal_reduction = 0

# calory of nutrition per gramm c = calory




calPerMG = {'ZE': 4.1 / 1000.0,
           'ZK': 4.1 / 1000.0,
           'ZF': 9.3 / 1000.0,
           'GCAL': 7.1}

# scale factor
sc = {'yg': 1e-08,
      'mg': 1e-05,
      'g': 0.01}


# tolerance for nutrition goals tol = tolerance


tol = {'GCAL': 0.1,
       'ZE': 0.3,
       'ZF': 0.3,
       'ZK': 0.3,
       'STA': 0.25}

# nutrients distribution p = part

part = {'GCAL': 1,
        'ZF': 0.3,
        'ZK': 0.5,
        'ZE': 0.2,
        'F182': 0.025,
        'F183': 0.005}

# Vitamine E
age_bound1 = 25
age_bound2 = 51
age_bound3 = 65


# fats
f_sat_ub = 0.1  # 8-10%
f_unsat_lb = 0.12
f_unsat_ub = 0.2

f_FO6_lb = 0.015
f_FO6_ub = 0.04
f_FO3_lb = 0.003
f_FO3_ub = 0.04

# proportional part of nutrient need
split = {'BF': 0.25,
         'WM': 0.25,
         'PL': 0.25}

bfLbZf = 6000  # breakfast lower bound ZF
bfLbZe = 10000  # breakfast lower bound ZE

crit_nut = {'ZK': 40, 'ZB': 2000, 'ZF': 20000, 'FU': 10000, 'ZE': 17000, 'EARG': 800,
            'MK': 300, 'MNA': 120, 'MMG': 30, 'VC': 25000, 'VE': 1000}



nutrientsMacroList = [
    'GCAL',
    'ZF',
    'ZE',
    #'F182',
    #'F183',
    'ZK'
]

nutrientsMicroList = [
    'EARG',
    'MMG',
    'VC',
    'VD',
    'VE',
    'ZB',
    'MCA',
    'MCL',
    'MCU',
    #'MF',
    'MFE',
    'MJ',
    'MK',
    'MMN',
    'MNA',
    #'MP',
    'MZN',
    'VA',
    'VB1',
    'VB12',
    'VB2',
    'VB3A',
    'VB5',
    'VB6',
    'VB7',
    'VB9G',
    'VK'
]

nutrientList = nutrientsMacroList + nutrientsMicroList

BLS2gramm = {
    'GCAL': 1,
    'ZF': 1e-3,
    'ZE': 1e-3,
    'F182': 1e-3,
    'F183': 1e-3,
    'ZK': 1e-3,
    'EARG': 1e-3,
    'MMG': 1e-3,
    'VC': 1e-6,
    'VD': 1e-6,
    'VE': 1e-6,
    'ZB': 1e-3,
    'MCA': 1e-3,
    'MCL': 1e-3,
    'MCU': 1e-6,
    'MF': 1e-6,
    'MFE': 1e-6,
    'MJ': 1e-6,
    'MK': 1e-3,
    'MMN': 1e-6,
    'MNA': 1e-3,
    'MP': 1e-3,
    'MZN': 1e-6,
    'VA': 1e-6,
    'VB1': 1e-6,
    'VB12': 1e-6,
    'VB2': 1e-6,
    'VB3A': 1e-6,
    'VB5': 1e-6,
    'VB6': 1e-6,
    'VB7': 1e-6,
    'VB9G': 1e-6,
    'VK': 1e-6
}

assignUnit = {
    'GCAL': 1,
    'ZF': 1,
    'ZE': 1,
    'F182': 1,
    'F183': 1,
    'ZK': 1,
    'EARG': 1e3,
    'MMG': 1e3,
    'VC': 1e6,
    'VD': 1e6,
    'VE': 1e6,
    'ZB': 1,
    'MCA': 1e3,
    'MCL': 1e3,
    'MCU': 1e6,
    # 'MF': ,
    'MFE': 1e3,
    'MJ': 1e6,
    'MK': 1e3,
    'MMN': 1e6,
    'MNA': 1e3,
    'MP': 1e3,
    'MZN': 1e3,
    'VA': 1e6,
    'VB1': 1e6,
    'VB12': 1e6,
    'VB2': 1e6,
    'VB3A': 1e6,
    'VB5': 1e6,
    'VB6': 1e6,
    'VB7': 1e6,
    'VB9G': 1e6,
    'VK': 1e6
}

switch_unit = {1: u'g',
               1e3: u'mg',
               1e6: u'µm'}

switch_unit_inv = {v: k for k, v in switch_unit.iteritems()}
switch_unit_inv['kcal'] = 1

unit = {k: switch_unit[v] for (k, v) in assignUnit.iteritems()}

unit['GCAL'] = u'kcal'

default_nutrient_checked_dict = {key: {'VAL': 0.0, 'UNIT': unit[key]} for key in nutrientList}

crit_time = 10  # in days

habits = [
    'VEGAN',
    'VEGGIE'
]

allergies = [
    'AL_EGG',
    'AL_PEANUTS',
    'AL_CRUSTACEAN',
    'AL_CELERY',
    'AL_SOY',
    'AL_FISH',
    'AL_SQUID',
    'AL_NUTS',
    'AL_MUSTARD',
    'AL_SESAM'
]

intolerances = [
    'IN_GLUT',
    'IN_LAKT'
]


meal_plan_1 = "Schau Dir meine Empfehlungen an."
meal_plan_2 = "Super, Du hast Dich optimal erhöht!"
meal_plan_3 = "Klasse, weiter so!"

blood_pressure_1 = "Miss bitte Deinen Blutdruck!"
blood_pressure_2 = "Trage bitte Deinen abendlichen Blutdruck ein!"
blood_pressure_3 = "Klasse!"
blood_pressure_4 = "Denk bitte daran auch morgens deinen Blutdruck zu messen!"
blood_pressure_5 = "Denk in Zukunft daran Deinen regelmäßig Blutdruck zu messen."

weight_1 = "Trag bitte Dein Gewicht ein."
weight_2 = "Klasse!"

denutritionized = [
    'DE_GLUT',
    'DE_LAKT'
]

