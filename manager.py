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

    @form.time_it
    def set_breakfast(self, num):
        self.meals['BF'] = self.dB.get_random_meals(
            num=num,
            mealtype='BF',
            splittedneeds=self.splitted_macro_bounds,
            exclusion=None
        )
        print 'bullshit'
        self.modeller.set_breakfast(
            meals=self.meals['BF'],
            needs=self.splitted_macro_bounds
        )

    def set_warm_meal(self, num):
        self.meals['WM'] = self.dB.get_random_meals(
            num=num,
            mealtype='WM',
            splittedneeds=self.splitted_macro_bounds,
            exclusion=None
        )
        self.modeller.set_warm_meal(
            meals=self.meals['WM'],
            needs=self.splitted_macro_bounds
        )

    def set_salad(self, num):
        self.meals['SA'] = self.dB.get_random_salad(
            num=num,
            exclusion=None
        )
        self.modeller.set_salad(foods=self.meals['SA'])

    def set_snack(self, num):
        self.meals['SN'] = self.dB.get_random_meals(
            num=num,
            mealtype='SNACK',
            splittedneeds=self.splitted_macro_bounds,
            exclusion=None
        )
        self.modeller.set_snacks(foods=self.meals['SN'])

    def set_plate(self, meat, veg, grain):
        self.meals['PL'] = self.dB.get_random_plate(
            meat=meat,
            veg=veg,
            grain=grain,
            exclusion=None
        )
        self.modeller.set_plate(
            foods=self.meals['PL'],
            needs=self.splitted_macro_bounds
        )

    def set_smoothie(self, fluid, primary, secondary, boost):
        self.meals['SM'] = self.dB.get_random_smoothie(
            fluid=fluid,
            primary=primary,
            secondary=secondary,
            boost=boost,
            exclusion=self.conditions
        )
        self.modeller.set_smoothie(foods=self.meals['SM'])

    def set_sandwich(self, bread, butter, topping):
        self.meals['SW'] = self.dB.get_random_sandwich(
            bread=bread,
            butter=butter,
            topping=topping,
            exclusion=self.conditions
        )
        self.modeller.set_sandwich(foods=self.meals['SW'])

    def set_meal_by_cat(self, cat, **kwargs):
        switch_meal = {
            'PL': self.set_plate,
            'SM': self.set_smoothie,
            'WM': self.set_warm_meal,
            'BF': self.set_breakfast,
            'SW': self.set_sandwich,
            'SA': self.set_salad,
            'SN': self.set_snack
        }
        switch_meal[cat](**kwargs)

    @property
    def conditions(self):
        cognito_handler = awsapi.Cognito()

        data_sets = cognito_handler.get_records_as_dict(dataset=c.DATASET_VITAL, cognito_id=self.cognitoId)
        print data_sets

        ls_intol = [element.join(['[', ']']) for element in data_sets['intolerances']]
        ls_intol = [element + " != 1" for element in ls_intol]

        ls_al = [element.join('[', ']') for element in data_sets['allergies']]
        ls_al = [element + " != 1" for element in ls_al]

        ls_hab = [element.join('[', ']') for element in data_sets['habit']]
        ls_hab = [element + " = 1" for element in ls_hab]

        return tuple(ls_hab + ls_intol + ls_al)



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

        self.element = self.userDataStore.get_from_nutrients_for_day(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            top_level=c.PLAN,
            second_level=self.event['body']['container'],
            third_level=self.event['body']['meal_key']
        )
        self.addDay = self.userDataStore.get_from_nutrients_for_day(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            top_level=c.NUTRIENTS_FOR_DAY
        )
        self.addWeek = self.userDataStore.get_from_nutrients_for_week(
            unique_id=self.cognitoId,
            date=self.event['body'][c.DATE],
            toplevel=c.NUTRIENTS_FOR_WEEK
        )

        for n in params.nutrientList:
            self.addWeek[n] -= self.element[n]
            self.addDay[n] -= self.element[n]

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
                 strong_branching=False, prob_type='generate'):
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
            birthday=data_set_vital['Age'],
            height=data_set_vital['Height'],
            weight=data_set_vital['Weight'],
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
            self.eval = Evaluator(
                model=self.problem,
                meals=self.meals,
                variable=self.modeller.variable,
                db=self.dB
            )
            self.nutrients = self.eval.get_all_nutrients()
            self.userDataStore.write_to_nutrients_for_day(
                plan=self.nutrients.plan,
                unique_id=self.cognitoId,
                status=pulp.LpStatus[self.problem.status],
                nutForDay=self.nutrients.nutrientsForDay,
                nutForMeal=self.nutrients.nutrientsForMeal,
                splittedNeeds=self.actualPatient.splitted_macro_bounds,
                nutNeedsForDay=self.actualPatient.macro_bounds
            )

            self.userDataStore.write_to_nutrients_for_week(
                unique_id=self.cognitoId,
                nutForWeek=self.nutrients.nutrientsForWeek,
                boundsForWeek=self.actualPatient.micro_bounds,
                time=self.problem.solutionTime
            )
        else:
            print self.problem.fixObjective()
            raise RuntimeError('LP Problem could not be solved. No plan is stored for this user.')

        self.dB.cur.close()
        self.managerLog = dict(LpStatus=pulp.LpStatus[self.problem.status],
                                 Time=self.problem.solutionTime)
        return None

    def _set_splitted_macro_bounds(self):
        self.splitted_macro_bounds = self.actualPatient.splitted_macro_bounds
