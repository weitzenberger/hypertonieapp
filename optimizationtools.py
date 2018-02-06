#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 09.05.2017 13:40

This module contains all tools for optimization processes such as a
constructor for standard constraints (StandardConstraint), a modeller
class to define LP nutrition problems (Modeller) and an Evaluator to
store the results in a proper data structure.

@author: L.We
"""

import array
import collections
import fractions
import pprint

import pulp
from sqlalchemy.sql.expression import select

import form
import params
import constants as c
from dbmodel import MealComposition, BLS, StandardBLS, engine


class StandardConstraint(object):
    """Constructor for Standard Contraints.
    """

    def __init__(self, name, sum, ub=None, lb=None, eq=None, tol=params.tol['STA']):
        """
        :param name: date or 'TOT' (for whole week)
                     + cat or 'GLOB' (for whole day)
                     + foodType (for generators) or nutrient (SBLS ab)
        :param sum: list of pulp.LpVariables, nested lists are also allowed

        eq=value:
            --> hard equality constraint.
        eq=value and lb=True and/or ub=True:
            --> elastic constraint, tolerance is set with regard to
                the input value in eq. Depending on the booleans for lb
                and ub it results in one or two constraints.
        lb=value and/or ub=value:
            --> upper and/or lower bound constraint, actual values for ub and lb
                are set for lower and upper bounds.
        """
        self.name = name
        self.sum = sum
        self.ub = ub
        self.lb = lb
        self.eq = eq
        self.tol = tol
        self.constraintDict = {}
        self._create_constraints()

    def _create_constraints(self):
        if self.ub and self.eq:
            self.constraintDict.update({self.name + '_EQ_UB': (pulp.lpSum(self.sum) <= (1 + self.tol) * self.eq)})
        if (self.lb and self.eq):
            self.constraintDict.update({self.name + '_EQ_LB': pulp.lpSum(self.sum) >= (1 - self.tol) * self.eq})

        if (self.eq and not (self.ub or self.lb)):
            self.constraintDict.update({self.name + '_EQ': pulp.lpSum(self.sum) == self.eq})

        if (self.ub and not self.eq):
            self.constraintDict.update({self.name + '_UB': pulp.lpSum(self.sum) <= self.ub})

        if (self.lb and not self.eq):
            self.constraintDict.update({self.name + '_LB': pulp.lpSum(self.sum) >= self.lb})

    def add_to_model(self, model):
        """
        :param model: pulp.LpProblem instance
        """
        for name, const in self.constraintDict.iteritems():
            model.addConstraint(const, name)


class Modeller(object):
    """This is the main API to set up nutrition problem models as a
    Constraint Satisfaction Problem. Any constellation of meals can
    be realized as long as global and local constraints are satisfied.

    Inputs for methods:
    :param meals: meals from Database instance
    :param foods: foods from Database instance (from BLS)
    :param needs: individual needs from Patient instance
    :param add_XXX: dict of constant nutrient values for each nutrition that is added to
                       the constraints, comes from user plan from DDB. This parameter is used
                       when parts of the plan are regenerated, the nutrients of the remaining
                       plan are fixed as a constant (add_meal, add_day, add_week)
    """

    def __init__(self, model, days, bounds, nutrientMicroList=params.nutrientList - params.nutrientsMacroList,
                 nutrientMacroList=params.nutrientsMacroList, tol=params.tol):
        """

        :param model: instance of pulp.LpProblem
        :param days: list of dates in ISO 8601
        :param bounds: dict of ub and lb for each nutrition
        :param nutrientMicroList: list of micro nutrients
        :param nutrientMacroList: list of macro nutrients

        :parameter _tree: nested default-dict so that any sub-dict contains a dict as default.
                    variable, counter, offset, crossSum, crossCounter use this data format
        :parameter variable: actual variable for food
        :parameter counter: binary that is:
                            0 if variable = 0 and
                            1 if variable > 0
        :parameter offset: corresponds to variable - lb, is used to realize non-convex solution spaces for variable,
                           i.e. including 0 so that {x | x = 0 ∨ lb ≤ x ≤ ub}
        :parameter crossCounter: binary that is:
                                 0 if a certain food does not occur in whole week plan and
                                 1 if a certain food does occur at least once
        :parameter crossSum: sum of all crossCounter
        :parameter sumGlobal: dict with lists of all variable * nutrient for each nutrient,
                              these lists get updated every time meals are added to the model
        """
        self.model = model
        if not isinstance(days, collections.Iterable):
            raise TypeError('days must be a list/tuple of iso8601 dates not ' + type(days))
        self.days = days
        self.bounds = bounds
        self.nutrientMicroList = nutrientMicroList
        self.nutrientMacroList = nutrientMacroList
        self.nutrientList = params.nutrientList
        self.tol = tol
        self._tree = lambda: collections.defaultdict(self._tree)
        self.variable = self._tree()
        self.counter = self._tree()
        self.offset = self._tree()
        self.crossSum = self._tree()
        self.crossCounter = self._tree()
        self.sumGlobal = {}
        self.all_meals = self._tree()
        self.all_meals_evo = self._tree()

    def _join(self, *names):
        """Joins names with underscores for constraint
        and variable naming
        """
        return '_'.join(names)

    def _set_variables(self, foods, cat):
        """Sets standard variables for all "foods" in "cat"."""
        for day in self.days:
            for key, value in foods.iteritems():
                self.variable[day][cat][key] = pulp.LpVariable(
                    name=self._join(day, cat, key),
                    lowBound=0,
                    upBound=value[c.UB] / value[c.LB],
                    cat=pulp.LpInteger if value[c.INT] else pulp.LpContinuous
                )

    def _set_counter(self, foods, cat):
        """Sets binary counter variables for all "foods" in "cat". The counter (LpInteger) is forced to be 0 if variable = 0
        and 1 if variable > 0 due to the following constraints:

            C1: 0 ≤ counter ≤ 1
            C2: variable ≤ counter * ub
            C3: counter * lb ≤ variable
        """
        for day in self.days:
            for key, value in foods.iteritems():
                self.counter[day][cat][key] = pulp.LpVariable(
                    name=self._join(day, c.COUNT, cat, key),
                    cat=pulp.LpBinary
                )

                counter_constraint1 = \
                    self.counter[day][cat][key] * value[c.UB] / value[c.LB] >= self.variable[day][cat][key]
                counter_constraint2 = \
                    self.counter[day][cat][key] <= self.variable[day][cat][key]

                self.model.addConstraint(counter_constraint1)
                self.model.addConstraint(counter_constraint2)

    def _set_offset(self, foods, cat):
        """Sets offset variables for all "foods" in "cat". With offset (LpContinuous) and counter, variable has a
        non-convex solution space i.e. {variable | variable = 0 ∨ lb ≤ variable ≤ ub}. This is obtained
        by the following constraints:

            C1: 0 ≤ offset ≤ ub - lb
            C2: offset + lb * counter == variable
        """
        for day in self.days:
            for key, value in foods.iteritems():
                if not value[c.INT]:
                    self.offset[day][cat][key] = pulp.LpVariable(
                        name=self._join(day, c.OFFSET, cat, key),
                        lowBound=0,
                        upBound=value[c.UB] / value[c.LB] - 1,
                        cat=pulp.LpContinuous
                    )
                    offset_constraint = \
                        self.variable[day][cat][key] == self.offset[day][cat][key] + self.counter[day][cat][key]
                    self.model.addConstraint(offset_constraint)

    def _set_local_and_global_sum_for_container(self, container_content, needs, container_key,
                                                add_meal=None, local_nut=None):
        """Sets local sum for 'local_nut' and adds it to the model. Also sets sum
        for all nutrients for global sum, but does not add it to the model yet

        :param container_content: dict of foods come from Database (SQL Server)
        :param needs: dict of needs come from PatientClass
        :param container_key: cat in ['SM', 'SW', ...]
        :param add_meal: dict of constants for each nutrition that is added to the constraints
                         comes from user data from DDB.
        :param local_nut: nutrition that is to be considered for local constraint
        :param is_meal: boolean, is True when recipe
        """
        self.all_meals[container_key] = {}
        local_nut = 'GCAL'

        for item in container_content:
            self.all_meals[container_key].update(item['meals'])

        for day in self.days:
            for n in self.nutrientList:
                current_sum_for_nutrient = []
                for meal_key, variable in self.variable[day][container_key].iteritems():
                    sum_local = None
                    current_sum_for_nutrient.append(self.all_meals[container_key][meal_key][n] * variable)
                if n == local_nut:
                    sum_local = current_sum_for_nutrient + ([add_meal[n]['VAL']] if add_meal else [])

                self.sumGlobal.setdefault(day, {}).setdefault(n, []).append(current_sum_for_nutrient)

                if sum_local:
                    if needs.get(container_key):
                        constraint = StandardConstraint(
                            name=self._join(day, container_key, local_nut),
                            sum=sum_local,
                            ub=needs[container_key][local_nut][c.UB],
                            lb=needs[container_key][local_nut][c.LB]
                        )

                        constraint.add_to_model(model=self.model)

    def set_global(self, needs, add_day=None, add_week=None):
        """Sets the constraints for all nutrients for the whole week. This function is to be
        called after all meal types are set

        :param needs: dict of needs come from PatientClass
        :param add_day: dict of constant nutrient values for each nutrition that is added to
                        the constraints, comes from user data from DDB nutrientsForDay
        :param add_week: dict of constant nutrient values for each nutrition that is added to
                         the constraints, comes from user data from DDB nutrientsForDay
        """
        # elasticNutrients = ['GCAL', 'ZE', 'ZF', 'ZK']
        for day in self.days:
            for n in self.nutrientMacroList:
                # if n in elasticNutrients:
                day_constraint = StandardConstraint(
                    name=self._join(day, 'GLOB', n),
                    sum=self.sumGlobal[day][n] + ([add_day[n]] if add_day else []),
                    ub=needs[n][c.UB],
                    lb=needs[n][c.LB]
                )
                day_constraint.add_to_model(model=self.model)

        for n in self.nutrientList - self.nutrientMacroList:
            week_constraint = StandardConstraint(
                name=self._join('TOT', 'GLOB', n),
                sum=[self.sumGlobal[day][n] for day in self.days] + ([add_week[n]] if add_week else []),
                ub=self.bounds[n][c.UB],
                lb=self.bounds[n][c.LB]
            )

            week_constraint.add_to_model(model=self.model)

    def set_cross_counter_and_constraint(self, lb, ub):
        """Sets CrossCounter variables and constraints. The constraint restricts the
        number of different foods that are included in the plan. This method is called
        once after all meals are added to the model.

        :param lb: lower bound for number of foods that are to be included in the plan
        :param ub: upper bound for number of foods that are to be included in the plan
        """

        ls_key = []
        ls_cat = []

        # get all cats and keys
        for day, dayplan in self.variable.iteritems():
            for cat, meal in dayplan.iteritems():
                ls_cat.append(cat)
                for key, var in meal.iteritems():
                    ls_key.append(key)

        set_key = set(ls_key)
        set_cat = set(ls_cat)

        for key in set_key:
            self.crossSum[key] = []
            for cat in set_cat:
                for day in self.days:
                    current_var = self.variable[day].get(cat).get(key)
                    if current_var:
                        self.crossSum[key].append(current_var)

            self.crossCounter[key] = pulp.LpVariable(
                name=self._join('CROSS_COUNTER', key),
                cat=pulp.LpBinary
            )
            counter_constraint1 = \
                self.crossCounter[key] * 100000000.0 >= pulp.lpSum(self.crossSum[key])
            counter_constraint2 = \
                self.crossCounter[key] <= pulp.lpSum(self.crossSum[key])

            self.model.addConstraint(counter_constraint1)
            self.model.addConstraint(counter_constraint2)

        cross_counter_constraint = StandardConstraint(
            name='CROSS_COUNTER',
            sum=self.crossCounter.values(),
            lb=lb,
            ub=ub
        )
        cross_counter_constraint.add_to_model(model=self.model)

    def set_meals(self, meals, needs, add_meal=None):

        for day in self.days:
            for container_key, container_content in meals.iteritems():
                for item in container_content:
                    for k in item['meals'].keys():
                        if not self.variable[day][container_key].get(k):
                            current_variable = pulp.LpVariable(
                                name=self._join(day, container_key, k),
                                cat=pulp.LpBinary
                            )
                            self.variable[day][container_key][k] = current_variable


                    if item['preference'] == 'obligatory':
                        sum1 = [self.variable[day][container_key][k] for k in item['meals'].keys()]

                        constraint_day = StandardConstraint(
                            name=self._join(day, container_key, 'OBLIGATORY'),
                            sum=sum1,
                            lb=1
                        )
                        constraint_day.add_to_model(model=self.model)

        switch_nut = {'BF': 'GCAL',
                      'DI': 'GCAL',
                      'LU': 'GCAL',
                      'SN': None}

        for container_key in meals.keys():
            self._set_local_and_global_sum_for_container(
                container_content=meals[container_key],
                needs=needs,
                container_key=container_key,
                add_meal=add_meal,
                local_nut=switch_nut[container_key]
            )

                        # constraintWeek = StandardConstraint('TOT' + '_WM_' + 'GCAL', sum=sumWeek, ub=3)
                        # constraintWeek.add_to_model(model=self.model)

    def set_meals_evo(self, meals, needs, add_meal=None):
        gcal = array.array('f')
        index = 0
        for day in self.days:
            for container_key, container_content in meals.iteritems():
                for item in container_content:
                    for meal_key, meal_content in item['meals'].iteritems():
                        if not self.all_meals_evo[day][container_key].get(meal_key):

                            self.all_meals_evo[day][container_key][meal_key] = meal_content
                            self.all_meals_evo[day][container_key][meal_key]['index'] = index
                            index += 1
                            gcal.append(meal_content['GCAL'])


        for container_key in meals.keys():
            self._set_local_and_global_sum_evo(
                container_content=meals[container_key],
                needs=needs,
                container_key=container_key,
                add_meal=add_meal,
                local_nut=None
            )
        return self.all_meals_evo, self.bounds

    def _set_local_and_global_sum_evo(self, container_key, container_content, needs, add_meal, local_nut):
        self.all_meals[container_key] = {}
        local_nut = 'GCAL'

        for item in container_content:
            self.all_meals[container_key].update(item['meals'])

        for day in self.days:
            for meal_key, index in self.all_meals_evo[day][container_key].iteritems():
                self.all_meals[container_key][meal_key]['index'] = index
                if n == local_nut:
                    sum_local = current_sum_for_nutrient + (add_meal[n] if add_meal else [])

                self.sumGlobal.setdefault(day, {}).setdefault(n, []).append(current_sum_for_nutrient)

                if sum_local:
                    if needs.get(container_key):
                        constraint = StandardConstraint(
                            name=self._join(day, container_key, local_nut),
                            sum=sum_local,
                            ub=needs[container_key][local_nut][c.UB],
                            lb=needs[container_key][local_nut][c.LB]
                        )

                        constraint.add_to_model(model=self.model)




class Evaluator(object):
    """Evaluator formats data to store it in DDB
    """

    def __init__(self, model, meals, variable):
        self.model = model
        self.meals = meals
        self.variable = variable
        self.switchUnit = {
            nut: params.BLS2gramm[nut] * pot for nut, pot in params.assignUnit.iteritems()
            }
        self._tree = lambda: collections.defaultdict(self._tree)
        self.nutrientsForMeal = self._tree()
        self.nutrientsForDay = self._tree()
        self.nutrientsForWeek = self._tree()
        self.nutrientsForContainer = self._tree()
        self.plan = self._tree()
        self.shoppinglist = self._tree()
        self.meals_checked = self._tree()

    def get_meal_vals(self, meal_key):
        conn = engine.connect()
        s = select([MealComposition]).where(MealComposition.MEAL_ID == meal_key)
        rows = conn.execute(s)
        d = {}
        for row in rows:
            dict_ = dict(zip(row.keys(), row.values()))
            sbls = dict_.pop('SBLS')
            amount = dict_['AMOUNT']
            d[sbls] = self.get_vals_by_sbls(sbls, amount)
            d[sbls]['AMOUNT'] = float(dict_['AMOUNT'])
            d[sbls]['NAME'] = dict_['NAME']

        return d

    def get_vals_by_sbls(self, sbls, amount):
        conn = engine.connect()
        s = select([BLS.__getattribute__(BLS, n) for n in params.nutrientList | {'ST'}]).where(BLS.SBLS == sbls)
        rows = conn.execute(s)
        for row in rows:
            d = dict(zip(row.keys(), row.values()))
            for n in params.nutrientList:
                d[n] *= float(amount) / 100.0

        s = select([StandardBLS.__getattribute__(StandardBLS, column)
                    for column in ['NAME', 'UNIT', 'PORT_ALT', 'PLURAL', 'PORT_EQ']]).where(StandardBLS.SBLS == sbls)

        portion_dict ={}
        rows = conn.execute(s)
        for row in rows:
            portion_dict = dict(zip(row.keys(), row.values()))

        rel_amount = fractions.Fraction(float(amount) / float(portion_dict['PORT_ALT']))
        try:
            if rel_amount > 1:
                portion_size = str(rel_amount) + " " + portion_dict.pop('PLURAL') + " | " + amount + " " + portion_dict['UNIT']
            else:
                portion_size = str(rel_amount) + " " + portion_dict.pop('PORT_EQ') + " | " + amount + " " + portion_dict['UNIT']
        except:
            if portion_dict['UNIT']:
                portion_size = amount + " " + portion_dict['UNIT']
            else:
                portion_size = amount + " g"

        d['portion_size'] = portion_size

        return d

    def evaluate_meals_for_container(self):
        for day, day_plan in self.variable.iteritems():
            for container_key, container_content in day_plan.iteritems():
                for meal_key, variable in container_content.iteritems():
                    if variable.varValue != 0:
                        current_key_element = self.meals[container_key][meal_key]
                        self.plan[day][container_key][meal_key]['ST'] = self.meals[container_key][meal_key]['NAME']
                        self.plan[day][container_key][meal_key]['DES'] = self.meals[container_key][meal_key]['DES']
                        self.plan[day][container_key][meal_key]['varValue'] = variable.varValue
                        self.plan[day][container_key][meal_key]['ingredients'].update(self.get_meal_vals(meal_key))
                        self.meals_checked[day][container_key][meal_key] = False
                        amount = 0

                        for sbls_key, sbls_value in self.plan[day][container_key][meal_key]['ingredients'].iteritems():
                            self.shoppinglist[day][sbls_key].setdefault('VAL', 0.0)
                            self.shoppinglist[day][sbls_key].setdefault('CHECKED', False)
                            self.shoppinglist[day][sbls_key].setdefault('ST', sbls_value['ST'])
                            self.shoppinglist[day][sbls_key].setdefault('UNIT', 'g')  # TODO: Unit aus STA table einfügen
                            self.shoppinglist[day][sbls_key]['VAL'] += sbls_value['AMOUNT']
                            amount += sbls_value['AMOUNT']
                        self.plan[day][container_key][meal_key]['AMOUNT'] = amount

                        for n in params.nutrientList:
                            self.plan[day][container_key][meal_key]['nutrients'][n]['UNIT'] = params.unit[n]
                            self.plan[day][container_key][meal_key]['nutrients'][n]['VAL'] = \
                                current_key_element[n] * self.switchUnit[n]

    @form.time_it
    def evaluate_container(self):
        for day, dayplan in self.plan.iteritems():
            for container_key, container_content in dayplan.iteritems():
                for meal_key in container_content.iterkeys():
                    for n in params.nutrientList:
                        self.nutrientsForContainer[day][container_key][n].setdefault('VAL', 0.0)
                        self.nutrientsForContainer[day][container_key][n].setdefault('UNIT', params.unit[n])
                        self.nutrientsForContainer[day][container_key][n]['VAL'] += \
                            self.plan[day][container_key][meal_key]['nutrients'][n]['VAL']

                        self.nutrientsForDay[day][n].setdefault('VAL', 0.0)
                        self.nutrientsForDay[day][n].setdefault('UNIT', params.unit[n])
                        self.nutrientsForDay[day][n]['VAL'] += \
                            self.plan[day][container_key][meal_key]['nutrients'][n]['VAL']

                        self.nutrientsForWeek[form.get_week_by_date(day)][n].setdefault('VAL', 0.0)
                        self.nutrientsForWeek[form.get_week_by_date(day)][n].setdefault('UNIT', params.unit[n])
                        self.nutrientsForWeek[form.get_week_by_date(day)][n]['VAL'] += \
                            self.plan[day][container_key][meal_key]['nutrients'][n]['VAL']


    def get_all_nutrients(self):
        """
        currentXXX always refers to self.meals
        Iterations always conducted over optimization variables
        overwrites self.meals

        :return:'nutrientsForMeal': nutrientsForMeal,
                'nutrientsForDay': nutrientsForDay,
                'nutrientsForWeek': nutrientsForWeek,
                'varsNotInPlan': varsNotInPlan,
                'meals': self.meals
        )"""

        self.evaluate_meals_for_container()
        self.evaluate_container()

        Nutrients = collections.namedtuple('nutrients',
                                           ['nutrients_for_container',
                                            'nutrients_for_day',
                                            'nutrients_for_week',
                                            'nutrients_for_meal',
                                            'meals_checked',
                                            'shopping_list'
                                            ]
                                           )

        return Nutrients(
            nutrients_for_container=dict(self.nutrientsForContainer),
            nutrients_for_day=dict(self.nutrientsForDay),
            nutrients_for_week=dict(self.nutrientsForWeek),
            nutrients_for_meal=dict(self.plan),
            meals_checked=self.meals_checked,
            shopping_list=self.shoppinglist
        )

    def pop_vars_not_in_plan(self):
        """Pops out all variables that equal zero from self.variables
        :return: dictionary of variables that do not occur in plan
        """

        vars_not_in_plan = {}
        for day, dayplan in self.variable.iteritems():
            for mealKey, meal in dayplan.iteritems():
                if mealKey == 'SA':
                    for gskey, saladcombo in meal.iteritems():
                        for key, var in saladcombo.iteritems():
                            if var.varValue == 0:
                                vars_not_in_plan.setdefault(day, {}).setdefault(mealKey, {})[gskey] = dayplan[mealKey].pop(
                                    gskey)
                else:
                    for key, var in meal.iteritems():
                        if var.varValue == 0:
                            vars_not_in_plan.setdefault(day, {}).setdefault(mealKey, {})[key] = dayplan[mealKey].pop(key)
        return vars_not_in_plan

if __name__ == '__main__':
    pass
