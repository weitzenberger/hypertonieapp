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
import pprint

import pulp

import form
import constants as c
import params
import patients
import awsapi
from optimizationtools import Modeller, Evaluator
# from database import SBLSDatabase
from dbmodel import mealdescription, engine
from sqlalchemy.sql.expression import func, select, and_

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
        # self.dB = SBLSDatabase()
        self.meals = {}
        self.managerLog = {}
        self.exclusions = self._exclusions()

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

    def set_meal_by_container(self):
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

        container_category = {}

        def get_meals(num, conditions, container_key):
            switch_cond = {
                'BF': [],  # TODO: extra Conditions einfügen für container??
                'DI': [],
                'LU': [],
                'SN': []
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

        # pprint.pprint(self.meals)


        #
        # for container_key, container_content in container_category.iteritems():
        #     self.meals[container_key] = []
        #     meal_type_exclusion = []
        #     for element in container_content:
        #         if element['preference'] == 'obligatory':
        #             preference_condition = [element['key'] + ' = 1']
        #             item = {'preference': 'obligatory',
        #                     'meals': self.dB.get_random_meals_for_container_version(
        #                         num=8,
        #                         container=container_key,
        #                         splitted_needs=self.splitted_macro_bounds,
        #                         conditions=self.exclusions + preference_condition
        #                     )}
        #             self.meals[container_key].append(item)
        #         elif element['preference'] == 'unwanted':
        #             meal_type_exclusion.append(element['key'] + ' IS NULL')
        #     item = {'preference': 'optional',
        #             'meals': self.dB.get_random_meals_for_container_version(
        #                 num=20,
        #                 container=container_key,
        #                 splitted_needs=self.splitted_macro_bounds,
        #                 conditions=self.exclusions + meal_type_exclusion
        #             )}
        #     self.meals[container_key].append(item)
        #
        #
        # rest_container = {'BF', 'LU', 'DI', 'SN'} - set(container_category.keys())
        # for container_key in rest_container:
        #     self.meals[container_key] = []
        #     item = {
        #         'preference': 'optional',
        #         'meals': self.dB.get_random_meals_for_container_version(
        #             num=20,
        #             container=container_key,
        #             splitted_needs=self.splitted_macro_bounds,
        #             conditions=self.exclusions
        #         )
        #     }
        #     self.meals[container_key].append(item)



        self.modeller.set_meals(
            meals=self.meals,
            needs=self.splitted_macro_bounds,
            add_meal=None
        )



    def _exclusions(self):
        cognito_handler = awsapi.Cognito()

        data_sets = cognito_handler.get_records_as_dict(dataset=c.DATASET_VITAL, cognito_id=self.cognitoId)
        # data_sets['intolerances'].append('IN_LAKT')
        # try:
        # ls_intol = [element.join(['[', ']']) for element in data_sets['intolerances']]
        # ls_intol = [element + " IS NULL" for element in ls_intol]
        ls_cond_intol = [mealdescription.c.__getattr__(element) == None for element in data_sets['intolerances']]

        if not 'IN_LAKT' in data_sets['intolerances']:
            ls_cond_intol.append(mealdescription.c.DE_LAKT == None)
        if not 'IN_GLU' in data_sets['intolerances']:
            ls_cond_intol.append(mealdescription.c.DE_GLU == None)


        # ls_al = [element.join(['[', ']']) for element in data_sets['allergies']]
        # ls_al = [element + " IS NULL" for element in ls_al]
        ls_cond_al = [mealdescription.c.__getattr__(element) == None for element in data_sets['allergies']]


        # ls_hab = [element.join(['[', ']']) for element in data_sets['habit']]
        # ls_hab = [element + " = 1" for element in ls_hab]
        ls_cond_hab = [mealdescription.c.__getattr__(element) == True for element in data_sets['habits']]
        print data_sets

        return []  # ls_cond_al + ls_cond_hab + ls_cond_intol
        # except:
        #     print 'heyyy'


        # return [u'[VEGGIE] = 1', u'[AL_CRUSTACEAN] IS NULL', u'[AL_PEANUTS] IS NULL'] #ls_hab + ls_al + ls_intol



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
        self.boundsForWeek = self.userNutritionStore.get_reduced_bounds_for_week(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            redLb=0.8
        )
        self.splittedNeeds = self.userNutritionStore.get_from_nutrients_for_day(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            top_level=c.SPLITTED_NEEDS
        )
        self._set_splitted_macro_bounds()
        self.needs = self.userNutritionStore.get_from_nutrients_for_day(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            top_level=c.NUTRIENT_NEED_FOR_DAY
        )
        self.modeller = Modeller(
            model=self.problem,
            days=[self.event['body'][c.DATE]],
            bounds=self.boundsForWeek)

        element = self.userNutritionStore.get_from_nutrients_for_day(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            top_level=c.PLAN,
            second_level=self.event['body']['container'],
            third_level=self.event['body']['meal_key']
        )
        add_day = self.userNutritionStore.get_from_nutrients_for_day(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            top_level=c.NUTRIENTS_FOR_DAY
        )
        add_week = self.userNutritionStore.get_from_nutrients_for_week(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            toplevel=c.NUTRIENTS_FOR_WEEK
        )
        self.addWeek = {}
        self.addDay = {}

        for n in params.nutrientList:
            # print add_week
            self.addWeek[n] = add_week[n]['VAL'] / params.switch_unit_inv[add_week[n]['UNIT']] / params.BLS2gramm[n] \
                             - element[n]['VAL'] / params.switch_unit_inv[element[n]['UNIT']] / params.BLS2gramm[n]
            self.addDay[n] = add_day[n]['VAL'] / params.switch_unit_inv[add_day[n]['UNIT']] / params.BLS2gramm[n] \
                             - element[n]['VAL'] / params.switch_unit_inv[add_day[n]['UNIT']] / params.BLS2gramm[n]
            # print self.addWeek

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
                meals=self.meals,
                variable=self.modeller.variable,
                db=self.dB
            )
            nutrients = evaluator.get_all_nutrients()

            self.userNutritionStore.delete_element(
                unique_id=self.cognitoId,
                date=self.event['body'][c.DATE],
                container=self.event['body']['container'],
                key=self.event['body']['meal_key']
            )
            self.userNutritionStore.update_container(
                unique_id=self.cognitoId,
                nutrients=nutrients
            )
        else:
            print self.problem.fixObjective()
            raise RuntimeError('LP Problem could not be solved. Plan remains unchanged.')

        self.managerLog = dict(LpStatus=pulp.LpStatus[self.problem.status],
                               Time=self.problem.solutionTime)

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

        days = form.get_remaining_days(thisweek=self.event['thisweek'])
        self.actualPatient = switch_patient[self.patient](
            birthday=data_set_vital['birthday'],
            height=data_set_vital['height'],
            weight=data_set_vital['weight'],
            pal=data_set_vital['pal'],
            sex=data_set_vital['gender'],
            db=None,  # TODO: db entfernen
            days=days
        )
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


        self.problem.solve(
            solver=pulp.PULP_CBC_CMD(
                maxSeconds=self.timeOut,
                msg=self.cbcLog,
                presolve=False,
                strong=self.strongBranching
            )
        )
        print 'solved'

        if pulp.LpStatus[self.problem.status] == 'Optimal':
            cognito_id = self.cognitoId
            # Optimalcognito_id = "eu-central-1:0265ffa7-f55b-4591-9cd8-c329f076fe0a"
            # # cognito_id = 'TEST_ID'
            self.eval = Evaluator(
                model=self.problem,
                meals=self.modeller.all_meals,
                variable=self.modeller.variable,
                db=None  # TODO: DB entfernen
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
            print 'hello'
            print self.problem.fixObjective
            print pulp.LpStatus[self.problem.status]
            print self.problem.solutionTime
            raise RuntimeError('LP Problem could not be solved. No plan is stored for this user.')

        # self.dB.cur.close()
        self.managerLog = dict(LpStatus=pulp.LpStatus[self.problem.status],
                               Time=self.problem.solutionTime)
        return None

    def _set_splitted_macro_bounds(self):
        self.splitted_macro_bounds = self.actualPatient.splitted_macro_bounds
