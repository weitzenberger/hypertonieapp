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
import constants as C



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

# micro nutrtition
bounds = {'EARG':   {C.LB: 5000,    C.UB: None},
          'MK':     {C.LB: 3519,    C.UB: 4692},
          'MNA':    {C.LB: 1600,    C.UB: 2400},
          'MMG':    {C.LB: 300,     C.UB: None},
          'MCA':    {C.LB: 1200,    C.UB: None},
          'VC':     {C.LB: 500e03,  C.UB: 1e06},
          'VD':     {C.LB: 20.00,   C.UB: None},
          'ZB':     {C.LB: 30e3,    C.UB: None}}

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

bfLbZf = 6000 #breakfast lower bound ZF
bfLbZe = 10000 #breakfast lower bound ZE

crit_nut = {'ZK': 40, 'ZB': 2000, 'ZF': 20000, 'FU': 10000, 'ZE': 17000, 'EARG': 800,
            'MK': 300, 'MNA': 120, 'MMG': 30, 'VC': 25000, 'VE': 1000}

crit_nut_op = {'ZK': '>', 'ZB': '>', 'ZF': '>', 'FU': '>', 'ZE': '>', 'EARG': '>',
               'MK': '>', 'MNA': '<', 'MMG': '>', 'VC': '>', 'VE': '>'}

# nutrientset

nutrientset = ['SBLS', 'GCAL', 'ZK', 'ZB', 'ZF', 'FS', 'FU', 'FP', 'FO6', 'FO3', 'ZE', 'EARG',
               'MK', 'MNA', 'MMG', 'MCA', 'VC', 'VD', 'VE']

#nutrientList = ['GCAL', 'ZK', 'ZB', 'ZF', 'FS', 'FU', 'FP', 'FO6', 'FO3', 'ZE', 'EARG',
#                'MK', 'MNA', 'MMG', 'MCA', 'VC', 'VD', 'VE']

nutrientsMacroList = ['GCAL', 'ZF', 'ZE', 'F182', 'F183']

nutrientsMicroList = ['EARG',
                      'MMG',
                      'VC',
                      'VD',
                      'VE',
                      'ZB',
                      'MCA',
                      'MCL',
                      'MCU',
                     # 'MF',
                      'MFE',
                      'MJ',
                      'MK',
                      'MMN',
                      'MNA',
                      'MP',
                      'MZN',
                      'VA',
                      'VB1',
                      'VB12',
                      'VB2',
                     # 'VB3A',
                      'VB5',
                      'VB6',
                      'VB7',
                      'VB9G',
                      'VK'
                      ]
nutrientList = nutrientsMacroList + nutrientsMicroList

crit_time = 10  # in days


fieldnames = ['male19to25', 'male25to51', 'male51to65', 'male65plus', 'female19to25', 'female25to51', 'female51to65', 'female65plus']


