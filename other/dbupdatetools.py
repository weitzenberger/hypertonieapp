#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 21.10.17


@author: L.We
"""
import xlrd
import pprint
import params
import constants as c
import form
import copy
# import database
import sys

from dbmodel import MealDescription, MealComposition, StandardBLS, BLS, start_session
reload(sys)
sys.setdefaultencoding('utf-8')

#db = database.SBLSDatabase()
session = start_session()

PATH = '/Users/l.we/Dropbox/Exist Antrag/11_Datenbank/Rezept-DB/aktuelle Version/Datenbank.xlsx'

workbook = xlrd.open_workbook(filename=PATH)

SHEET_0 = workbook.sheet_by_index(0)
SHEET_1 = workbook.sheet_by_index(1)
SHEET_2 = workbook.sheet_by_index(2)


def get_index_2_name_switch(workbook, sheet_index):
    """

    :param workbook:
    :param sheet_index:
    :return:
    """
    sheet = workbook.sheet_by_index(sheet_index)
    switch_index_2_name = {}

    for col in xrange(sheet.ncols):
        switch_index_2_name[col] = sheet.cell_value(0, col)
    return switch_index_2_name

SWITCH_INDEX_SHEET_0 = get_index_2_name_switch(workbook, 0)
SWITCH_INDEX_SHEET_1 = get_index_2_name_switch(workbook, 1)
SWITCH_INDEX_SHEET_2 = get_index_2_name_switch(workbook, 2)

def update_sta_table(sheet=SHEET_0, switch_index_sheet=SWITCH_INDEX_SHEET_0):
    """

    :return:
    """
    current_row = {}
    for row in xrange(1, sheet.nrows):
        for col in xrange(sheet.ncols):
            current_row[switch_index_sheet[col]] = sheet.cell_value(rowx=row, colx=col)
        if current_row[switch_index_sheet[0]]:
            current_row = form.convert_empty_string_to_None(current_row)
            # db.update_row(current_row, tbl=c.SQL_STA, delete_id='SBLS')
            insert_into_new(insertion=current_row, tbl=StandardBLS, session=session)

def update_table(path, sheet_index, tbl, session):
    """

    :param path: path for xlsx file
    :param sheet_index: which index is used in xlsx file
    :param tbl: table in SQL Server database
    :return:
    """
    workbook = xlrd.open_workbook(filename=path)
    sheet = workbook.sheet_by_index(sheet_index)
    switch_sheet_by_index = get_index_2_name_switch(workbook, sheet_index)

    current_row = {}
    for row in xrange(1, sheet.nrows):
        for col in xrange(sheet.ncols):
            if switch_sheet_by_index[col]:
                current_row[switch_sheet_by_index[col]] = sheet.cell_value(rowx=row, colx=col)
        if current_row[switch_sheet_by_index[0]]:
            current_row = form.convert_empty_string_to_None(current_row)
            print current_row
            element = tbl(**current_row)
            session.merge(element)
    session.commit()


def get_all_meal_des_from_xlsx():
    """

    :return:
    """
    current_row = {}
    meals = {}
    for row in xrange(1, SHEET_1.nrows):
        for col in xrange(SHEET_1.ncols):
            current_row[SWITCH_INDEX_SHEET_1[col]] = SHEET_1.cell_value(rowx=row, colx=col)
        current_meal_id = current_row.pop('MEAL_ID')
        if current_meal_id:
            meals.setdefault(current_meal_id, {}).update(current_row)
    meals = form.convert_empty_string_to_None(meals)
    pprint.pprint(meals)
    return meals


def get_all_meals_ingredients_from_xlsx():
    """

    :return:
    """
    current_row = {}
    meals = {}
    for row in xrange(1, SHEET_2.nrows):
        for col in xrange(SHEET_2.ncols):
            current_row[SWITCH_INDEX_SHEET_2[col]] = SHEET_2.cell_value(rowx=row, colx=col)
        current_meal_id = current_row.pop('Meal_ID')
        if current_meal_id:
            current_row_copy = copy.deepcopy(current_row)
            meals.setdefault(current_meal_id, []).append(current_row_copy)
    meals = form.convert_empty_string_to_None(meals)
    print 'this is meals'
    pprint.pprint(meals)
    return meals


def insert_meal_ing(meal_key, meal_ing):
    """

    :param meal_key:
    :param meal_ing:
    :return:
    """
    # delete_id = True
    for element in meal_ing:
    #     db.insert_into(
    #         meal_key=meal_key,
    #         meal_ing=element,
    #         tbl=c.SQL_MEAL_ING,
    #         delete_id=delete_id
    #     )
    #     delete_id = False
        element['MEAL_ID'] = meal_key
        insert_into_new(insertion=element, tbl=MealComposition, session=session)

def insert_into_new(insertion, tbl, session):
    if not insertion.get(None, True):
        insertion.pop(None)
    print insertion
    session.merge(tbl(**insertion))
    session.commit()

def select_from(session, tbl, ):
    session.query(tbl)

def characterize_and_insert_meal_des(meal_key, meal_des, meal_ing):
    nut_vals = {}
    characterized_meal = {}
    insertion = {}

    insert_meal_ing(meal_key, meal_ing)

    # set default values
    for n in params.nutrientList:
        nut_vals[n] = 0.0
    for key in params.habits:
        characterized_meal[key] = 1
    for key in params.allergies:
        characterized_meal[key] = None
    for key in params.intolerances:
        characterized_meal[key] = None

    for element in meal_ing:
        sbls = element['SBLS']
        print sbls
        # characterized_sbls = db.check_for_column_entries(
        #     columns=params.habits + params.allergies + params.intolerances,
        #     sbls="'" + sbls + "'"
        # )
        characterized_sbls = session.query(StandardBLS).filter_by(SBLS=sbls).all()[0].as_dict()
        for key, val in characterized_sbls.iteritems():
            if key in params.allergies + params.intolerances:
                if val:
                    characterized_meal[key] = val
            elif key in params.habits:
                if not val:
                    characterized_meal[key] = None
        # nutrients = db.get_vals_by_sbls(params.nutrientList, c.SQL_BLS, None, sbls)
        nutrients = session.query(BLS).filter_by(SBLS=sbls).all()[0].as_dict()
        for n in params.nutrientList:
            # nut_vals[n] += nutrients[sbls][n] * element['AMOUNT'] / 100.0
            nut_vals[n] += nutrients[n] * element['AMOUNT'] / 100.0
    if '_L_' in meal_key:
        insertion['DE_LAKT'] = True
    if '_G_' in meal_key:
        insertion['DE_GLU'] = True
    insertion.update(nut_vals)
    insertion.update(characterized_meal)
    insertion.update(meal_des)
    insertion['MEAL_ID'] = meal_key
    # db.insert_into(meal_key, insertion, delete_id=True)
    insert_into_new(insertion=insertion, tbl=MealDescription, session=session)
    return dict(insertion=insertion, meal_ing=meal_ing)



def create_and_insert_de_meal(meal_key, meal_des, meal_ing, de_glut=False, de_lakt=False):
    """

    :param meal_key:
    :param meal_des:
    :param meal_ing:
    :param intolerance:
    :return:
    """
    de_possible = True
    de_meal_ing = []
    for element in meal_ing:
        if de_possible:
            # characterized_sbls = db.check_for_column_entries(
            #     columns=params.habits + params.allergies + params.intolerances + ['PENDANT'],
            #     sbls="'" + element['SBLS'] + "'"
            # )
            characterized_sbls = session.query(StandardBLS).filter_by(SBLS=element['SBLS']).all()[0].as_dict()
            current_amount = copy.deepcopy(element['AMOUNT'])
            current_pendant = copy.deepcopy(characterized_sbls['PENDANT'])
            current_sbls = copy.deepcopy(element['SBLS'])
            current_name = copy.deepcopy(element['NAME'])

            if de_lakt and de_glut:
                if characterized_sbls['IN_LAKT'] or characterized_sbls['IN_GLUT']:
                    if characterized_sbls['PENDANT']:
                        de_meal_ing.append({'AMOUNT': current_amount,
                                            'SBLS': current_pendant,
                                            'NAME': current_name
                                            })
                    else:
                        de_possible = False
                else:
                    de_meal_ing.append({'AMOUNT': current_amount,
                                        'SBLS': current_sbls,
                                        'NAME': current_name
                                        })
            elif de_lakt:
                if characterized_sbls['IN_LAKT']:
                    if characterized_sbls['PENDANT']:
                        de_meal_ing.append({'AMOUNT': current_amount,
                                            'SBLS': current_pendant,
                                            'NAME': current_name
                                            })
                    else:
                        de_possible = False
                else:
                    de_meal_ing.append({'AMOUNT': current_amount,
                                        'SBLS': current_sbls,
                                        'NAME': current_name
                                        })
            elif de_glut:
                if characterized_sbls['IN_GLUT']:
                    if characterized_sbls['PENDANT']:
                        de_meal_ing.append({'AMOUNT': current_amount,
                                            'SBLS': current_pendant,
                                            'NAME': current_name
                                            })
                    else:
                        de_possible = False

                else:
                    de_meal_ing.append({'AMOUNT': current_amount,
                                        'SBLS': current_sbls,
                                        'NAME': current_name
                                        })

    if de_possible:
        if de_glut and de_lakt:
            de_meal_key = 'DE_L_G_' + meal_key
        elif de_glut:
            de_meal_key = 'DE_G_' + meal_key
        elif de_lakt:
            de_meal_key = 'DE_L_' + meal_key
        else:
            de_meal_key = meal_key
        return dict(
            meal_key=de_meal_key,
            meal_des=meal_des,
            meal_ing=de_meal_ing
        )
