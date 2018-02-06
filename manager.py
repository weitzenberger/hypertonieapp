#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 24.08.17

This module contains all context managers that are used
to perform operations on the meal plans. e.g. Generate
a new plan or modify existing plans.

@author: L.We
"""

import abc
import traceback
import sys

import collections

import pulp
from sqlalchemy.sql.expression import func, select, and_

import form
import constants as c
import params
import patients
import awsapi
from optimizationtools import Modeller, Evaluator
from dbmodel import mealdescription, engine


switch_patient = {
    'Hypertension': patients.HypertensionPatient,
    'DGE': patients.DGEPatient
}


class ModelManager(object):
    """Abstract Base Class for all context managers that perform
    operations on user meal plans.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, cognito_id, event, prob_type, time_out, cbc_log,
                 patient, strong_branching):
        """This is a fake initializer and is to be called only by subclasses
        of ModelManager to set the standard modelling attributes.

        :param cognito_id: basestring
        :param event: dict, coming from AWS, consider that syntax might
                      differ between lambda and lambda-proxy integration
        :param prob_type: generate | regenerate, name of invoking method
        :param time_out: Number, time out for cbc solver in seconds
        :param cbc_log: True | False, prints log from cbc solver
        :param patient: Patient, instance of a Patient class
        :param strong_branching: True | False, enables strong branching
        """
        self.cognitoId = cognito_id
        self.event = event
        self.probType = prob_type
        self.timeOut = time_out
        self.cbcLog = 1 if cbc_log else 0
        self.patient = patient
        self.strongBranching = strong_branching
        self.userNutritionStore = awsapi.DynamoNutrition()
        self.userDataStore = awsapi.DynamoUserData()
        self.problem = pulp.LpProblem(name=self.probType)
        self._tree = lambda: collections.defaultdict(self._tree)
        self.meals = {}
        self.managerLog = {}
        self.exclusions = self._exclusions()
        self.conn = engine.connect()

    @abc.abstractmethod
    def __enter__(self):
        pass

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __repr__(self):
        return self.probType

    @abc.abstractmethod
    def _set_splitted_macro_bounds(self):
        self.splitted_macro_bounds = None

    def get_meals(self, num, conditions, container_key):
        switch_cond = {
            'BF': [],  # TODO: extra Conditions einfügen für container??
            'DI': [],
            'LU': [],
            'SN': []
        }
        conditions += switch_cond[container_key]
        s = select([mealdescription]).where(and_(*conditions)).order_by(func.rand()).limit(num)
        rows = self.conn.execute(s)
        d = {}
        for row in rows:
            dict_ = dict(zip(row.keys(), row.values()))
            key = dict_.pop('MEAL_ID')
            d[key] = dict_
        return d

    def set_meal_by_container(self):
        """

        :return:
        """
        conn = engine.connect()
        cognito_handler = awsapi.Cognito()

        data_sets = cognito_handler.get_records_as_dict(
            dataset=c.DATASET_VITAL,
            cognito_id=self.cognitoId
        )
        try:
            container_category = data_sets['containerCategory']
        except:
            container_category = {
                u'BF': [{u'preference': u'obligatory', u'key': u'BREAD'}, {u'preference': u'unwanted', u'key': u'EGGS'}], u'LU': [{u'preference': u'obligatory', u'key': u'FRUIT'}]}

        container_category = {u'BF': [], u'LU': []}

        def get_meals(num, conditions, container_key):
            switch_cond = {
                'BF': [mealdescription.c.WARM == None,
                       mealdescription.c.SALAD == None
                       ],
                'LU': [mealdescription.c.BREAD_ROLL == None,
                       mealdescription.c.SMOOTHIE == None,
                       mealdescription.c.TOAST == None,
                       mealdescription.c.EGGS == None,
                       ],
                'DI': [mealdescription.c.MUSLI == None,
                       mealdescription.c.QUARK == None,
                       mealdescription.c.YOGURT == None,
                       mealdescription.c.FRUIT == None,
                       mealdescription.c.BREAD == None,
                       mealdescription.c.BREAD_ROLL == None,
                       mealdescription.c.TOAST == None,
                       mealdescription.c.JUICE == None,
                       mealdescription.c.NUTS == None],
                'SN': [mealdescription.c.BREAD_ROLL == None,
                       mealdescription.c.BREAD == None,
                       mealdescription.c.BREAD_ROLL == None,
                       mealdescription.c.TOAST == None,
                       mealdescription.c.SALAD == None,
                       mealdescription.c.EGGS == None,
                       mealdescription.c.WARM == None,]
            }
            conditions += switch_cond[container_key]
            s = select([mealdescription]).where(and_(*conditions)).order_by(func.rand()).limit(num)
            rows = conn.execute(s)
            d = {}
            for row in rows:
                dict_ = dict(zip(row.keys(), row.values()))
                key = dict_.pop('MEAL_ID')
                d[key] = dict_
            return d

        for container_key, container_content in container_category.iteritems():
            self.meals[container_key] = []
            meal_type_exclusion = []
            for element in container_content:
                if element['preference'] == 'obligatory':
                    preference_condition = [mealdescription.c.__getattr__(element['key']) == True]
                    print 'this is key'
                    print element['key']
                    item = {
                        'preference': 'obligatory',
                        'meals': get_meals(
                            num=12,
                            conditions=self.exclusions + preference_condition,
                            container_key=container_key
                        )
                    }
                    self.meals[container_key].append(item)
                elif element['preference'] == 'unwanted':
                    meal_type_exclusion += [mealdescription.c.__getattr__(element['key']) == None]
            item = {
                'preference': 'optional',
                'meals': get_meals(
                    num=12,
                    conditions=self.exclusions + meal_type_exclusion,
                    container_key=container_key
                )
            }
            self.meals[container_key].append(item)

        rest_container = {'BF', 'LU', 'DI', 'SN'} - set(container_category.keys())
        for container_key in rest_container:
            self.meals[container_key] = []
            item = {
                'preference': 'optional',
                'meals': get_meals(
                    num=20,
                    container_key=container_key,
                    conditions=self.exclusions
                )
            }
            self.meals[container_key].append(item)


        self.modeller.set_meals(
            meals=self.meals,
            needs=self.splitted_macro_bounds,
            add_meal=None
        )



    def _exclusions(self):
        """Returns a list of sqlalchemy condition expression hased on
        cognito dataset intolerances/habits/allergies

        :return: list
        """

        ls_cond_intol = []
        ls_cond_al = []
        ls_cond_hab = []

        cognito_handler = awsapi.Cognito()
        data_sets = cognito_handler.get_records_as_dict(dataset=c.DATASET_VITAL, cognito_id=self.cognitoId)

        # Da in data_set nicht immer 'tolerances' durch die App hinterlegt ist (wie eigentlich abgesprochen)
        # prüf ich mit ".get()", ob der Eintrag hinterlegt ist. Eine Else Bedingung für den Fall das gar nichts
        # hinterlegt ist fehlte. Für diesen Fall sollen weder "entlaktosifizierte" Gerichte, noch "entglutenisierte"
        # Gerichte vorkommen.
        if data_sets.get('intolerances'):
            for element in data_sets['intolerances']:
                try:
                    ls_cond_intol.append(mealdescription.c.__getattr__(element) == None)
                except:
                    pass
            if not 'IN_LAKT' in data_sets['intolerances']:
                ls_cond_intol.append(mealdescription.c.DE_LAKT == None)
            if not 'IN_GLU' in data_sets['intolerances']:
                ls_cond_intol.append(mealdescription.c.DE_GLU == None)
        else:
            ls_cond_intol.append(mealdescription.c.DE_LAKT == None)
            ls_cond_intol.append(mealdescription.c.DE_GLU == None)

        if data_sets.get('allergies'):
            for element in data_sets['allergies']:
                try:
                    ls_cond_al.append(mealdescription.c.__getattr__(element) == None)
                except:
                    pass

        if data_sets.get('habits'):
            for element in data_sets['habits']:
                if element == 'VEGAN':
                    element = 'VEGGIE'
                ls_cond_hab.append(mealdescription.c.__getattr__(element) == True)





        print data_sets

        return ls_cond_al + ls_cond_intol + ls_cond_hab


class RegenerateManager(ModelManager):
    def __init__(self, cognito_id, event, time_out, cbc_log, patient='Hypertension',
                 strong_branching=False, prob_type='generate'):
        super(RegenerateManager, self).__init__(
            cognito_id=cognito_id,
            event=event,
            prob_type=prob_type,
            time_out=time_out,
            cbc_log=cbc_log,
            patient=patient,
            strong_branching=strong_branching
        )

    def set_meal_by_cat(self, container_key):
        cognito_handler = awsapi.Cognito()

        data_sets = cognito_handler.get_records_as_dict(
            dataset=c.DATASET_VITAL,
            cognito_id=self.cognitoId
        )
        try:
            container_category = data_sets['containerCategory']
        except:
            container_category = {
                u'BF': [
                    {u'preference': u'obligatory', u'key': u'BREAD'},
                    {u'preference': u'unwanted', u'key': u'EGGS'}
                ],
                u'LU': [
                    {u'preference': u'obligatory', u'key': u'FRUIT'}
                ]
            }

        container_category = {u'BF': [{u'preference': u'obligatory', u'key': u'BREAD'}, {u'preference': u'unwanted', u'key': u'EGGS'}], u'LU': [{u'preference': u'obligatory', u'key': u'FRUIT'}]}


        container_content = container_category[container_key]




        self.meals[container_key] = []
        if not container_content:
            item = {
                'preference': 'optional',
                'meals': self.get_meals(
                    num=20,
                    container_key=container_key,
                    conditions=self.exclusions
                )
            }
            self.meals[container_key].append(item)
        else:
            meal_type_exclusion = []
            for element in container_content:
                if element['preference'] == 'obligatory':
                    preference_condition = [mealdescription.c.__getattr__(element['key']) == True]
                    item = {
                        'preference': 'obligatory',
                        'meals': self.get_meals(
                            num=12,
                            conditions=self.exclusions + preference_condition,
                            container_key=container_key
                        )
                    }
                    self.meals[container_key].append(item)
                elif element['preference'] == 'unwanted':
                    meal_type_exclusion += [mealdescription.c.__getattr__(element['key']) == None]
            item = {
                'preference': 'optional',
                'meals': self.get_meals(
                    num=12,
                    conditions=self.exclusions + meal_type_exclusion,
                    container_key=container_key
                )
            }
            self.meals[container_key].append(item)
        print self.element
        if self.event['body-json'].get('meal_key'):
            self.modeller.set_meals(
                meals=self.meals,
                needs=self.splitted_macro_bounds,
                add_meal=self.element
            )
        else:
            self.modeller.set_meals(
                meals=self.meals,
                needs=self.splitted_macro_bounds,
                add_meal=None
            )



    def __enter__(self):
        """Enter logic for regenerate function
        Steps in this function:
            - get all bounds from DynamoDB for the specific user
            - set up an instance of Modeller
            - get the meal/container that is to be changed
            - get the nutrient values for the current plan and substract
              the meal/container that is to be changed from it

        :return: self
        """
        add_day = self.userNutritionStore.get_from_nutrients_for_day(
            unique_id=self.cognitoId,
            date=self.event['body-json'][c.DATE],
            top_level=c.NUTRIENTS_FOR_DAY
        )
        add_week = self.userNutritionStore.get_from_nutrients_for_week(
            unique_id=self.cognitoId,
            date=self.event['body-json'][c.DATE],
            toplevel=c.NUTRIENTS_FOR_WEEK
        )

        params.nutrientList = set(add_week.keys()) & set(add_day.keys()) & params.nutrientList

        bounds_for_week = self.userNutritionStore.get_reduced_bounds_for_week(
            unique_id=self.cognitoId,
            date=self.event['body-json'][c.DATE],
            redLb=0.8
        )
        self.splittedNeeds = self.userNutritionStore.get_from_nutrients_for_day(
            unique_id=self.cognitoId,
            date=self.event['body-json'][c.DATE],
            top_level=c.SPLITTED_NEEDS
        )
        self._set_splitted_macro_bounds()
        self.needs = self.userNutritionStore.get_from_nutrients_for_day(
            unique_id=self.cognitoId,
            date=self.event['body-json'][c.DATE],
            top_level=c.NUTRIENT_NEED_FOR_DAY
        )
        if self.event['body-json'].get('meal_key'):
            self.element = self.userNutritionStore.get_from_nutrients_for_day(
                unique_id=self.cognitoId,
                date=self.event['body-json'][c.DATE],
                top_level=c.PLAN,
                second_level=self.event['body-json']['container_key'],
                third_level=self.event['body-json']['meal_key']
            )
        else:
            self.element = self.userNutritionStore.get_from_nutrients_for_day(
                unique_id=self.cognitoId,
                date=self.event['body-json'][c.DATE],
                top_level=c.NUTRIENTS_FOR_CONTAINER,
                second_level=self.event['body-json']['container_key']
            )

        self.addWeek = {}
        self.addDay = {}
        self.bounds = self._tree()

        for n in params.nutrientList:
            # print add_week
            self.addWeek[n] = add_week[n]['VAL'] / params.switch_unit_inv[add_week[n]['UNIT']] / params.BLS2gramm[n] \
                              - self.element[n]['VAL'] / params.switch_unit_inv[self.element[n]['UNIT']] / params.BLS2gramm[n]
            self.addDay[n] = add_day[n]['VAL'] / params.switch_unit_inv[add_day[n]['UNIT']] / params.BLS2gramm[n] \
                             - self.element[n]['VAL'] / params.switch_unit_inv[add_day[n]['UNIT']] / params.BLS2gramm[n]
            if self.bounds[n]['UB']:
                self.bounds[n]['UB'] = bounds_for_week[n]['UB'] / params.switch_unit_inv[bounds_for_week[n]['UNIT'] ] / params.BLS2gramm[n]
            else:
                self.bounds[n]['UB'] = None
            if self.bounds[n]['LB']:
                self.bounds[n]['LB'] = bounds_for_week[n]['LB'] / params.switch_unit_inv[bounds_for_week[n]['UNIT'] ] / params.BLS2gramm[n]
            else:
                self.bounds[n]['LB'] = None

                # print self.addWeek

        self.modeller = Modeller(
            model=self.problem,
            days=[self.event['body-json'][c.DATE]],
            bounds=self.bounds
        )
        print 'addWeek'
        print self.addWeek
        print 'addDay'
        print self.addDay

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit logic for generate function.
        Steps in this function:
            - invoke set_global for Modeller instance
            - solve the LP Problem
            - if Optimal: evaluate the results and write
              it to DynamoDB
            - if not Optimal: raise an error


        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return: None
        """
        traceback.print_exc()

        self.modeller.set_global(
            needs=self.needs,
            add_day=self.addDay,
            add_week=self.addWeek
        )
        self.problem.solve(
            solver=pulp.PULP_CBC_CMD(
                maxSeconds=self.timeOut,
                msg=self.cbcLog,
                presolve=False,
                strong=False
            )
        )
        if pulp.LpStatus[self.problem.status] == 'Optimal':
            evaluator = Evaluator(
                model=self.problem,
                meals=self.modeller.all_meals,
                variable=self.modeller.variable,
            )
            nutrients = evaluator.get_all_nutrients()

            self.userNutritionStore.delete_element(
                unique_id=self.cognitoId,
                date=self.event['body-json'][c.DATE],
                container=self.event['body-json']['container_key']
#                key=self.event['body-json']['meal_key']
            )
            self.userNutritionStore.update_container(
                unique_id=self.cognitoId,
                nutrients=nutrients
            )
            self.userNutritionStore.update_meal_checked_list(
                unique_id=self.cognitoId,
                date=self.event['body-json'][c.DATE],
                nutrients=nutrients
            )
        else:
            print self.problem.fixObjective
            raise RuntimeError('LP Problem could not be solved. Plan remains unchanged.')

        self.managerLog = dict(lp_status=pulp.LpStatus[self.problem.status],
                               time=self.problem.solutionTime)
        if pulp.LpStatus[self.problem.status] != 'Optimal':
            self.managerLog.update(dict(message="Leider kann für die gewählten Präferenzen kein Plan generiert werden."))

        return None

    def _set_splitted_macro_bounds(self):
        self.splitted_macro_bounds = self.splittedNeeds


class GenerateManager(ModelManager):
    def __init__(self, cognito_id, event, time_out, cbc_log, patient='Hypertension',
                 strong_branching=True, prob_type='generate'):
        super(GenerateManager, self).__init__(
            cognito_id=cognito_id,
            event=event,
            prob_type=prob_type,
            time_out=time_out,
            cbc_log=cbc_log,
            patient=patient,
            strong_branching=strong_branching
        )


    def __enter__(self):
        """Enter logic for generate function.
        Steps in this function:
            - get the dataset with all user specific attributes (e.g. age, sex, ...)
            - get days for which a plan is to be generated
            - set up an instance of Patient
            - set up an instance of Modeller

        :return: self
        """
        data_set_vital = awsapi.Cognito().get_records_as_dict(
            dataset=c.DATASET_VITAL,
            cognito_id=self.cognitoId
        )
        # TODO: Call Patient from dataset

        days = form.get_remaining_days(thisweek=self.event['thisweek'])
        self.actualPatient = switch_patient[self.patient](
            birthday=data_set_vital['birthday'],
            height=data_set_vital['height'],
            weight=data_set_vital['weight'],
            pal=data_set_vital['pal'],
            sex=data_set_vital['gender'],
            days=days
        )
        print 'patient'
        print self.actualPatient.cal_need
        print self.actualPatient.scale_micro(5)
        self._set_splitted_macro_bounds()
        self.modeller = Modeller(
            model=self.problem,
            days=days,
            bounds=self.actualPatient.micro_bounds)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit logic for generate function.
        Steps in this function:
            - invoke set_global for Modeller instance
            - solve the LP Problem
            - if Optimal: evaluate the results and write
              it to DynamoDB
            - if not Optimal: raise an error

        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return: None
        """
        print exc_type
        print exc_val
        print exc_tb
        traceback.print_exc()
        self.modeller.set_global(needs=self.actualPatient.macro_bounds)

        print 'start solving'
        self.problem.solve(
            solver=pulp.PULP_CBC_CMD(
                maxSeconds=self.timeOut,
                msg=self.cbcLog,
                presolve=False,
                strong=self.strongBranching
            )
        )

        if pulp.LpStatus[self.problem.status] == 'Optimal':
            cognito_id = self.cognitoId
            # if sys.platform == 'darwin':
            #     cognito_id = 'TEST_ID'
            self.eval = Evaluator(
                model=self.problem,
                meals=self.modeller.all_meals,
                variable=self.modeller.variable
            )
            self.nutrients = self.eval.get_all_nutrients()
            self.userNutritionStore.write_to_nutrients_for_day(
                plan=self.nutrients.nutrients_for_meal,
                unique_id=cognito_id,
                status=pulp.LpStatus[self.problem.status],
                nut_for_day=self.nutrients.nutrients_for_day,
                nut_for_container=self.nutrients.nutrients_for_container,
                meals_checked=self.nutrients.meals_checked,
                splittedNeeds=self.actualPatient.splitted_macro_bounds,
                nutNeedsForDay=self.actualPatient.macro_bounds
            )
            self.userNutritionStore.write_to_nutrients_for_week(
                unique_id=cognito_id,
                nut_for_week=self.nutrients.nutrients_for_week,
                boundsForWeek=self.actualPatient.micro_bounds,
                time=self.problem.solutionTime
            )
            self.userDataStore.set_shopping_list(
                unique_id=cognito_id,
                shoppinglist=self.nutrients.shopping_list
            )
        else:
            print self.problem.fixObjective
            print pulp.LpStatus[self.problem.status]
            # print self.problem.solutionTime
            raise RuntimeError('LP Problem could not be solved. No plan is stored for this user.')

        self.managerLog = dict(lp_status=pulp.LpStatus[self.problem.status],
                               time=self.problem.solutionTime)
        if pulp.LpStatus[self.problem.status] != 'Optimal':
            self.managerLog.update(dict(message="Es können keine weiteren Änderungen am Plan vorgenommen werden."))
        return None

    def _set_splitted_macro_bounds(self):
        self.splitted_macro_bounds = self.actualPatient.splitted_macro_bounds
