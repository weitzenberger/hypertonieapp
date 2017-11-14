#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 24.08.17

This module contains all context managers that are used
to perform operations on the meal plans. e.g. Generate
a new plan or modify existing plans.

@author: L.We
"""

import pulp
import abc
import traceback

import form
import constants as c
import params
import patients
import awsapi
from optimizationtools import Modeller, Evaluator
from database import SBLSDatabase

switch_patient = {'Hypertension': patients.HypertensionPatient,
                  'DGE': patients.DGEPatient}


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
        self.userDataStore = awsapi.DynamoNutrition()
        self.problem = pulp.LpProblem(name=self.probType)
        self.dB = SBLSDatabase()
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
        cognito_handler = awsapi.Cognito()

        data_sets = cognito_handler.get_records_as_dict(
            dataset=c.DATASET_VITAL,
            cognito_id=self.cognitoId
        )
        print 'this is container cat'
        print data_sets['containerCategory']
        try:
            container_category = data_sets['containerCategory']
        except:
            container_category = {u'BF': [{u'preference': u'obligatory', u'key': u'BREAD'}, {u'preference': u'unwanted', u'key': u'EGGS'}], u'LU': [{u'preference': u'obligatory', u'key': u'FRUIT'}]}


        for container_key, container_content in container_category.iteritems():
            self.meals[container_key] = []
            meal_type_exclusion = []
            for element in container_content:
                if element['preference'] == 'obligatory':
                    preference_condition = [element['key'] + ' = 1']
                    item = {'preference': 'obligatory',
                            'meals': self.dB.get_random_meals_for_container_version(
                                num=8,
                                container=container_key,
                                splitted_needs=self.splitted_macro_bounds,
                                conditions=self.exclusions + preference_condition
                            )}
                    self.meals[container_key].append(item)
                elif element['preference'] == 'unwanted':
                    meal_type_exclusion.append(element['key'] + ' IS NULL')
            item = {'preference': 'optional',
                    'meals': self.dB.get_random_meals_for_container_version(
                        num=20,
                        container=container_key,
                        splitted_needs=self.splitted_macro_bounds,
                        conditions=self.exclusions + meal_type_exclusion
                    )}
            self.meals[container_key].append(item)

        rest_container = {'BF', 'LU', 'DI', 'SN'} - set(container_category.keys())
        for container_key in rest_container:
            self.meals[container_key] = []
            item = {
                'preference': 'optional',
                'meals': self.dB.get_random_meals_for_container_version(
                    num=20,
                    container=container_key,
                    splitted_needs=self.splitted_macro_bounds,
                    conditions=self.exclusions
                )}
            self.meals[container_key].append(item)



        self.modeller.set_meals(
            meals=self.meals,
            needs=self.splitted_macro_bounds,
            add_meal=None
        )



    def _exclusions(self):
        cognito_handler = awsapi.Cognito()

        data_sets = cognito_handler.get_records_as_dict(dataset=c.DATASET_VITAL, cognito_id=self.cognitoId)

        try:
            ls_intol = [element.join(['[', ']']) for element in data_sets['intolerances']]
            ls_intol = [element + " IS NULL" for element in ls_intol]


            ls_al = [element.join(['[', ']']) for element in data_sets['allergies']]
            ls_al = [element + " IS NULL" for element in ls_al]

            ls_hab = [element.join(['[', ']']) for element in data_sets['habit']]
            ls_hab = [element + " = 1" for element in ls_hab]
        except:
            pass

        return [u'[VEGGIE] = 1', u'[AL_CRUSTACEAN] IS NULL', u'[AL_PEANUTS] IS NULL'] #ls_hab + ls_al + ls_intol



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
        self.boundsForWeek = self.userDataStore.get_reduced_bounds_for_week(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            redLb=0.8
        )
        self.splittedNeeds = self.userDataStore.get_from_nutrients_for_day(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            top_level=c.SPLITTED_NEEDS
        )
        self._set_splitted_macro_bounds()
        self.needs = self.userDataStore.get_from_nutrients_for_day(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            top_level=c.NUTRIENT_NEED_FOR_DAY
        )
        self.modeller = Modeller(
            model=self.problem,
            days=[self.event['body'][c.DATE]],
            bounds=self.boundsForWeek)

        element = self.userDataStore.get_from_nutrients_for_day(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            top_level=c.PLAN,
            second_level=self.event['body']['container'],
            third_level=self.event['body']['meal_key']
        )
        add_day = self.userDataStore.get_from_nutrients_for_day(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            top_level=c.NUTRIENTS_FOR_DAY
        )
        add_week = self.userDataStore.get_from_nutrients_for_week(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            toplevel=c.NUTRIENTS_FOR_WEEK
        )
        self.addWeek = {}
        self.addDay = {}

        for n in params.nutrientList:
            print add_week
            self.addWeek[n] = add_week[n]['VAL'] / params.switch_unit_inv[add_week[n]['UNIT']] / params.BLS2gramm[n] \
                             - element[n]['VAL'] / params.switch_unit_inv[element[n]['UNIT']] / params.BLS2gramm[n]
            self.addDay[n] = add_day[n]['VAL'] / params.switch_unit_inv[add_day[n]['UNIT']] / params.BLS2gramm[n] \
                             - element[n]['VAL'] / params.switch_unit_inv[add_day[n]['UNIT']] / params.BLS2gramm[n]
            print self.addWeek

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

            self.userDataStore.delete_element(
                unique_id=self.cognitoId,
                date=self.event['body'][c.DATE],
                container=self.event['body']['container'],
                key=self.event['body']['meal_key']
            )
            self.userDataStore.update_container(
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
            birthday=data_set_vital['age'],
            height=data_set_vital['height'],
            weight=data_set_vital['weight'],
            pal=data_set_vital['pal'],
            sex=data_set_vital['gender'],
            db=self.dB,
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


        if pulp.LpStatus[self.problem.status] == 'Optimal':
            cognito_id = self.cognitoId
            cognito_id = "eu-central-1:f0b34d2c-f014-4966-b851-9b088a3218f9"
            cognito_id = 'TEST'
            self.eval = Evaluator(
                model=self.problem,
                meals=self.modeller.all_meals,
                variable=self.modeller.variable,
                db=self.dB
            )
            self.nutrients = self.eval.get_all_nutrients()
            self.userDataStore.write_to_nutrients_for_day(
                plan=self.nutrients.plan,
                unique_id=cognito_id,
                status=pulp.LpStatus[self.problem.status],
                nutForDay=self.nutrients.nutrientsForDay,
                nutForMeal=self.nutrients.nutrientsForMeal,
                splittedNeeds=self.actualPatient.splitted_macro_bounds,
                nutNeedsForDay=self.actualPatient.macro_bounds
            )

            self.userDataStore.write_to_nutrients_for_week(
                unique_id=cognito_id,
                nutForWeek=self.nutrients.nutrientsForWeek,
                boundsForWeek=self.actualPatient.micro_bounds,
                time=self.problem.solutionTime
            )
        else:
            print 'hello'
            print self.problem.fixObjective
            print pulp.LpStatus[self.problem.status]
            raise RuntimeError('LP Problem could not be solved. No plan is stored for this user.')

        self.dB.cur.close()
        self.managerLog = dict(LpStatus=pulp.LpStatus[self.problem.status],
                               Time=self.problem.solutionTime)
        return None

    def _set_splitted_macro_bounds(self):
        self.splitted_macro_bounds = self.actualPatient.splitted_macro_bounds
