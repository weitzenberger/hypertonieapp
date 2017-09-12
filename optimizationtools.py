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

import collections
import pulp

import constants as c
import form
import params


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
        if isinstance(ub, basestring):
            self.ub = None
        else:
            self.ub = ub
        if isinstance(lb, basestring):
            self.lb = None
        else:
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

    def __init__(self, model, days, bounds, nutrientMicroList=params.nutrientsMicroList,
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
            raise TypeError('days must be a list of iso8601 dates not ' + type(days))
        self.days = days
        self.bounds = bounds
        self.nutrientMicroList = nutrientMicroList
        self.nutrientMacroList = nutrientMacroList
        self.nutrientList = nutrientMicroList + nutrientMacroList
        self.tol = tol
        self._tree = lambda: collections.defaultdict(self._tree)
        self.variable = self._tree()
        self.counter = self._tree()
        self.offset = self._tree()
        self.crossSum = self._tree()
        self.crossCounter = self._tree()
        self.sumGlobal = {}

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

    def _set_generator(self, foods, cat):
        """Sets all standard variables and constraints for meal generators. A meal generator can consider
        different types of foods and set constraints for each type, such as number of included foods.
        NOTE: Does not work for salad mixer.

        :param foods: foods that come from Database (SQL Server)
        :param cat: cat in ['SM', 'SW', ....]
        """
        self._set_variables(foods=foods, cat=cat)
        self._set_counter(foods=foods, cat=cat)
        self._set_offset(foods=foods, cat=cat)

    def _set_local_and_global_sum(self, foods, needs, cat,
                                  add_meal=None, local_nut=None, is_meal=False):
        """Sets local sum for 'local_nut' and adds it to the model. Also sets sum
        for all nutrients for global sum, but does not add it to the model yet

        :param foods: dict of foods come from Database (SQL Server)
        :param needs: dict of needs come from PatientClass
        :param cat: cat in ['SM', 'SW', ...]
        :param add_meal: dict of constants for each nutrition that is added to the constraints
                         comes from user data from DDB.
        :param local_nut: nutrition that is to be considered for local constraint
        :param is_meal: boolean, is True when recipe
        """

        for day in self.days:
            for n in self.nutrientList:
                sum_local = None
                current_sum = \
                    [value[n] * self.variable[day][cat][key] * (1 if is_meal else value[c.LB] * 0.01)
                     for key, value in foods.iteritems()]
                if n == local_nut:
                    sum_local = current_sum + (add_meal[n] if add_meal else [])
                self.sumGlobal.setdefault(day, {}).setdefault(n, []).append(current_sum)

                if sum_local:
                    constraint = StandardConstraint(
                        name=self._join(day, cat, local_nut),
                        sum=sum_local,
                        ub=needs[cat][local_nut][c.UB],
                        lb=needs[cat][local_nut][c.LB]
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

        for n in self.nutrientMicroList:
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
                self.crossCounter[key] * 100000000.0 >= pulp.m(self.crossSum[key])
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

    def set_breakfast(self, meals, needs, add_meal=None):
        """Breakfast consists of meals"""
        cat = 'BF'
        for day in self.days:
            for k in meals.keys():
                self.variable[day][cat][k] = pulp.LpVariable(
                    name=self._join(day, cat, k),
                    cat=pulp.LpBinary
                )

        self._set_local_and_global_sum(
            foods=meals,
            needs=needs,
            cat=cat,
            add_meal=add_meal,
            local_nut='GCAL',
            is_meal=True
        )

    def set_meal_the_other_way(self, meals, needs, add_meal=None):
        """Salad consists of mixed green salads according to the flavour bible"""
        cat = 'SA'
        for day in self.days:
            dayList = []
            for meal_key, meal_ingredients in meals.iteritems():
                previous_variable = None
                ls_ingredients = []
                meal_counter = pulp.LpVariable(
                    name=self._join(day, cat, 'MEAL', 'COUNTER', meal_key),
                    cat=pulp.LpBinary
                )
                for ingredient, values in meal_ingredients.iteritems():
                    current_variable = pulp.LpVariable(
                        name=self._join(day, cat, meal_key, k),
                        cat=pulp.LpBinary
                    )

                    self.variable[day][cat][meal_key][k] = current_variable * values['AMOUNT'] / 100.0

                    if previous_variable:
                        equality_constraint = \
                            previous_variable == current_variable

                        self.model.addConstraint(equality_constraint)

                    ls_ingredients.append(current_variable)

                    previous_variable = current_variable

                counter_constraint1 = pulp.lpSum(ls_ingredients) * 1e-08 <= meal_counter
                counter_constraint2 = pulp.lpSum(ls_ingredients) >= meal_counter
                self.model.addConstraint(counter_constraint1)
                self.model.addConstraint(counter_constraint2)

                dayList.append(meal_counter)

                for n in self.nutrientList:
                    sum = [v[n] * self.variable[day][cat][meal_key][k] * v['AMOUNT'] * 0.01 for k, v in meal_ingredients.iteritems()]
                    self.sumGlobal.setdefault(day, {}).setdefault(n, []).append(sum)

            self.model.addConstraint(pulp.lpSum(dayList) == 1)

    def set_warm_meal(self, meals, needs, add_meal=None):
        """Warm meal consists of one single meal"""
        cat = 'WM'
        for day in self.days:
            for k in meals.keys():
                self.variable[day][cat][k] = pulp.LpVariable(name=self._join(day, cat, k), cat=pulp.LpBinary)

            sum1 = [self.variable[day][cat][k] for k in meals.keys()]

            constraint_day = StandardConstraint(
                name=self._join(day, cat, 'SUM'),
                sum=sum1,
                eq=1
            )

            constraint_day.add_to_model(model=self.model)

        self._set_local_and_global_sum(
            foods=meals,
            needs=needs,
            cat=cat,
            add_meal=add_meal,
            local_nut='GCAL',
            is_meal=True
        )

        # constraintWeek = StandardConstraint('TOT' + '_WM_' + 'GCAL', sum=sumWeek, ub=3)
        # constraintWeek.add_to_model(model=self.model)

    def set_salad(self, foods):
        """Salad consists of mixed green salads according to the flavour bible"""
        cat = 'SA'
        for day in self.days:
            dayList = []
            for gskey, val in foods.iteritems():
                previousCounter = None
                for k in val.iterkeys():
                    current_variable = pulp.LpVariable(
                        name=self._join(day, cat, gskey, k),
                        lowBound=0,
                        upBound=val[k][c.UB] / val[k][c.LB],
                        cat=pulp.LpInteger if val[k][c.INT] else pulp.LpContinuous
                    )
                    current_counter = pulp.LpVariable(name=day + '_COUNTER_SA_' + gskey + '_' + k, cat=pulp.LpBinary)
                    current_offsetter = pulp.LpVariable(
                        name=day + '_OFFSET_SA_' + gskey + '_' + k,
                        lowBound=0,
                        upBound=val[k][c.UB] / val[k][c.LB] - 1,
                        cat=pulp.LpInteger if val[k][c.INT] else pulp.LpContinuous
                    )

                    self.variable[day][cat][gskey][k] = current_variable
                    self.counter[day][cat][gskey][k] = current_counter
                    self.offset[day][cat][gskey][k] = current_offsetter

                    helperConstraint = \
                        current_counter + current_offsetter == current_variable
                    counterConstraint = \
                        current_counter >= current_offsetter / val[k][c.UB]

                    self.model.addConstraint(helperConstraint)
                    self.model.addConstraint(counterConstraint)

                    if previousCounter:
                        equalityConstraint = \
                            current_counter == previousCounter

                        self.model.addConstraint(equalityConstraint)

                    previousCounter = current_counter

                dayList.append(current_counter)

                for n in self.nutrientList:
                    sum = [v[n] * self.variable[day][cat][gskey][k] * v[c.LB] * 0.01 for k, v in val.iteritems()]
                    self.sumGlobal.setdefault(day, {}).setdefault(n, []).append(sum)

            self.model.addConstraint(pulp.lpSum(dayList) == 1)
            # constraint = StandardConstraint(day + '_SA_' + nut, sum=sumLocal, ub=True, lb=True, eq=needs['CM']['GCAL'])
            # constraint.add_to_model(model=self.model)

    def set_snacks(self, foods):
        """Snacks are like small meals and
        """

        cat = 'SN'

        for day in self.days:
            for k in foods.keys():
                self.variable[day][cat][k] = pulp.LpVariable(name=self._join(day, cat, k), cat=pulp.LpBinary)

        self._set_local_and_global_sum(
            foods=foods,
            needs=None,
            cat=cat,
            add_meal=None,
            local_nut=None,
            is_meal=True
        )

    def set_plate(self, foods, needs, add_meal=None):
        """Plate Generator
        1 type of meat
        1-2 types of vegetables
        1 type of grain
        """

        cat = 'PL'
        self._set_generator(foods=foods, cat=cat)

        for day in self.days:
            sum1 = [self.counter[day][cat][key] for key, val in foods.iteritems() if val['MEAT']]
            sum2 = [self.counter[day][cat][key] for key, val in foods.iteritems() if val['VEGETABLES']]
            sum3 = [self.counter[day][cat][key] for key, val in foods.iteritems() if val['WHOLE_GRAIN']]

            const_local1 = StandardConstraint(
                name=day + '_PL_MEAT',
                sum=sum1,
                eq=1
            )
            const_local2 = StandardConstraint(
                name=day + '_PL_VEG',
                sum=sum2,
                lb=1,
                ub=2
            )
            const_local3 = StandardConstraint(
                name=day + '_PL_GRAIN',
                sum=sum3,
                eq=1
            )

            const_local1.add_to_model(model=self.model)
            const_local2.add_to_model(model=self.model)
            const_local3.add_to_model(model=self.model)

        self._set_local_and_global_sum(
            foods=foods,
            needs=needs,
            cat=cat,
            add_meal=add_meal,
            local_nut='GCAL',
            is_meal=False
        )

    def set_smoothie(self, foods):
        """Smoothie Generator
        1 Fluid
        1 Primary
        1-2 Secondary
        1 Boost
        """

        cat = 'SM'
        self._set_generator(foods=foods, cat=cat)

        for day in self.days:
            sum1 = [self.counter[day][cat][key] for key, val in foods.iteritems() if val['fluid']]
            sum2 = [self.counter[day][cat][key] for key, val in foods.iteritems() if val['primary']]
            sum3 = [self.counter[day][cat][key] for key, val in foods.iteritems() if val['secondary']]
            sum4 = [self.counter[day][cat][key] for key, val in foods.iteritems() if val['boost']]

            const_local1 = StandardConstraint(
                name=day + '_SM_FLUID',
                sum=sum1,
                eq=1
            )
            const_local2 = StandardConstraint(
                name=day + '_SM_PRIM',
                sum=sum2,
                eq=1
            )
            const_local3 = StandardConstraint(
                name=day + '_SM_SEC',
                sum=sum3,
                lb=1,
                ub=2
            )
            const_local4 = StandardConstraint(
                name=day + '_SM_BOOST',
                sum=sum4,
                lb=0,
                ub=1
            )

            const_local1.add_to_model(model=self.model)
            const_local2.add_to_model(model=self.model)
            const_local3.add_to_model(model=self.model)
            const_local4.add_to_model(model=self.model)

        self._set_local_and_global_sum(
            foods=foods,
            needs=None,
            cat=cat,
            add_meal=None,
            local_nut=None,
            is_meal=False
        )

    def set_sandwich(self, foods):
        """Sandwich Generator
        1 type of Bread
        1 type of Butter
        1-3 types of Toppings
        """

        cat = 'SW'
        self._set_generator(foods=foods, cat=cat)

        for day in self.days:
            sum1 = [self.counter[day][cat][key] for key, val in foods.iteritems() if val['bread']]
            sum2 = [self.counter[day][cat][key] for key, val in foods.iteritems() if val['butter']]
            sum3 = [self.counter[day][cat][key] for key, val in foods.iteritems() if val['topping']]
            sum4 = [-self.variable[day][cat][key] for key, val in foods.iteritems() if val['butter']]
            sum5 = [self.variable[day][cat][key] for key, val in foods.iteritems() if val['bread']]

            constLocal1 = StandardConstraint(self._join(day, cat, 'BREAD'), sum=sum1, eq=1)
            constLocal2 = StandardConstraint(self._join(day, cat, 'BUTTER'), sum=sum2, eq=1)
            constLocal3 = StandardConstraint(self._join(day, cat, 'TOP'), sum=sum3, lb=1, ub=3)
            constLocal4 = StandardConstraint(self._join(day, cat, 'COMBI'), sum=sum4 + sum5, eq=0)

            constLocal1.add_to_model(model=self.model)
            constLocal2.add_to_model(model=self.model)
            constLocal3.add_to_model(model=self.model)
            constLocal4.add_to_model(model=self.model)

        self._set_local_and_global_sum(foods=foods, needs=None, cat=cat,
                                       add_meal=None, local_nut=None, is_meal=False)


class Evaluator(object):
    """Evaluator formats data to store it in DDB
    """

    def __init__(self, model, meals, variable, db):
        self.model = model
        self.meals = meals
        self.variable = variable
        self._tree = lambda: collections.defaultdict(self._tree)
        self._dB = db
        self.assignMeal = {'BF': 'BF',
                           'WM': 'LU',
                           'PL': 'DI',
                           'SW': 'DI',
                           'SA': 'DI',
                           'SM': 'SN',
                           'SN': 'SN'}
        self.nutrientsForMeal = self._tree()
        self.nutrientsForDay = self._tree()
        self.nutrientsForWeek = self._tree()
        self.nutrientsForContainer = self._tree()
        self.plan = self._tree()

    def evaluate_gen(self):
        for day, day_plan in self.variable.iteritems():
            for cat, meal in day_plan.iteritems():
                if cat in ['PL', 'SW', 'SM']:
                    self.plan[day][self.assignMeal[cat]][cat]['DES'] = c.LOREM_IPSUM
                    for key, var in meal.iteritems():
                        if var.varValue != 0:
                            current_key_element = self.meals[cat][key]
                            current_portion = var.varValue * float(current_key_element[c.LB])
                            self.plan[day][self.assignMeal[cat]][cat]['ingredients'][key]['portion'] = current_portion
                            self.plan[day][self.assignMeal[cat]][cat]['ingredients'][key]['varValue'] = var.varValue
                            self.plan[day][self.assignMeal[cat]][cat]['ingredients'][key]['ST'] = self.meals[cat][key]['NAME']

                            for n in params.nutrientList:
                                current_scaled_nutrient = current_key_element[n] * current_portion / 100.0
                                self.plan[day][self.assignMeal[cat]][cat].setdefault(n, 0.0)
                                self.plan[day][self.assignMeal[cat]][cat][n] += current_scaled_nutrient
                                self.plan[day][self.assignMeal[cat]][cat]['ingredients'][key][n] = current_scaled_nutrient

    def evaluate_salad(self):
        for day, dayplan in self.variable.iteritems():
            for cat, meal in dayplan.iteritems():
                if cat in ['SA']:
                    self.plan[day][self.assignMeal[cat]][cat]['DES'] = c.LOREM_IPSUM

                    for gskey, saladcombo in meal.iteritems():
                        for key, var in saladcombo.iteritems():
                            if var.varValue != 0:
                                current_key = self.meals[cat][gskey][key]
                                current_portion = var.varValue * float(current_key[c.LB])
                                self.plan[day][self.assignMeal[cat]][cat]['ingredients'][key]['portion'] = current_portion
                                self.plan[day][self.assignMeal[cat]][cat]['ingredients'][key]['varValue'] = var.varValue
                                self.plan[day][self.assignMeal[cat]][cat]['ingredients'][key]['ST'] = self.meals[cat][gskey][key]['NAME']

                                for n in params.nutrientList:
                                    current_scaled_nutrient = current_key[n] * current_portion / 100.0

                                    self.plan[day][self.assignMeal[cat]][cat].setdefault(n, 0.0)
                                    self.plan[day][self.assignMeal[cat]][cat][n] += current_scaled_nutrient
                                    self.plan[day][self.assignMeal[cat]][cat]['ingredients'][key][n] = current_scaled_nutrient


    def evaluate_meal_the_other_way(self):
        for day, dayplan in self.variable.iteritems():
            for cat, meal in dayplan.iteritems():
                if cat in ['SN', 'WM', 'BF']:
                    self.plan[day][self.assignMeal[cat]][cat]['DES'] = c.LOREM_IPSUM
                    for meal_key, meal_content in meal.iteritems():
                        for key, var in meal_content.iteritems():
                            if var.varValue != 0:
                                current_key = self.meals[cat][meal_key][key]
                                current_portion = var.varValue * float(current_key[c.LB])
                                self.plan[day][self.assignMeal[cat]][cat]['ingredients'][key]['portion'] = current_portion
                                self.plan[day][self.assignMeal[cat]][cat]['ingredients'][key]['varValue'] = var.varValue
                                self.plan[day][self.assignMeal[cat]][cat]['ingredients'][key]['ST'] = self.meals[cat][meal_key][key]['NAME']

                                for n in params.nutrientList:
                                    current_scaled_nutrient = current_key[n] * current_portion / 100.0

                                    self.plan[day][self.assignMeal[cat]][cat].setdefault(n, 0.0)
                                    self.plan[day][self.assignMeal[cat]][cat][n] += current_scaled_nutrient
                                    self.plan[day][self.assignMeal[cat]][cat]['ingredients'][key][n] = current_scaled_nutrient

    def evaluate_meal(self):
        for day, dayplan in self.variable.iteritems():
            for cat, meal in dayplan.iteritems():
                if cat in ['SN', 'WM', 'BF']:
                    for key, var in meal.iteritems():
                        if var.varValue != 0:
                            current_key_element = self.meals[cat][key]

                            self.plan[day][self.assignMeal[cat]][key]['ST'] = self.meals[cat][key]['NAME']
                            self.plan[day][self.assignMeal[cat]][key]['varValue'] = var.varValue
                            self.plan[day][self.assignMeal[cat]][key]['ingredients'].update(self._dB.get_meal_vals(key))

                            for sbls_key, sbls_value in self.plan[day][self.assignMeal[cat]][key]['ingredients'].iteritems():
                                current_portion = sbls_value['portion']
                                for n in params.nutrientList:
                                    sbls_value[n] *= current_portion / 100.0
                            for n in params.nutrientList:
                                self.plan[day][self.assignMeal[cat]][key].setdefault(n, 0.0)
                                self.plan[day][self.assignMeal[cat]][key][n] += current_key_element[n] * var.varValue
    @form.time_it
    def evaluat_for_container(self):
        for day, dayplan in self.plan.iteritems():
            for container, container_content in dayplan.iteritems():
                for cat in container_content.iterkeys():
                    for n in params.nutrientList:
                        self.nutrientsForContainer[day][container].setdefault(n, 0.0)
                        self.nutrientsForContainer[day][container][n] += self.plan[day][container][cat][n]
                        self.nutrientsForDay[day].setdefault(n, 0.0)
                        self.nutrientsForDay[day][n] += self.plan[day][container][cat][n]
                        self.nutrientsForWeek[form.get_week_by_date(day)].setdefault(n, 0.0)
                        self.nutrientsForWeek[form.get_week_by_date(day)][n] += self.plan[day][container][cat][n]





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


        nutrientsForMeal = self._tree()
        nutrientsForDay = self._tree()
        nutrientsForWeek = self._tree()
        plan = self._tree()

        for day, dayplan in self.variable.iteritems():
            for cat, meal in dayplan.iteritems():
                if cat == 'SA':
                    for gskey, saladcombo in meal.iteritems():
                        for key, var in saladcombo.iteritems():
                            if var.varValue != 0:
                                currentKey = self.meals[cat][gskey][key]
                                currentPortion = var.varValue * float(currentKey[c.LB])
                                plan[day][self.assignMeal[cat]][cat][key]['portion'] = currentPortion
                                plan[day][self.assignMeal[cat]][cat][key]['varValue'] = var.varValue
                                plan[day][self.assignMeal[cat]][cat][key]['type'] = self.meals[cat][gskey][key]['NAME']

                                for n in params.nutrientList:
                                    plan[day][self.assignMeal[cat]][cat][key][n] = currentKey[n] * currentPortion / 100.0

                                    nutrientsForMeal[day][cat].setdefault(n, 0.0)
                                    nutrientsForMeal[day][cat][n] += plan[day][self.assignMeal[cat]][cat][key][n]

                else:
                    for key, var in meal.iteritems():
                        if var.varValue != 0:
                            currentKey = self.meals[cat][key]
                            if cat in ['PL', 'SW', 'SM']:
                                currentPortion = var.varValue * float(currentKey[c.LB])

                                plan[day][self.assignMeal[cat]][cat][key]['portion'] = currentPortion
                                plan[day][self.assignMeal[cat]][cat][key]['varValue'] = var.varValue
                                plan[day][self.assignMeal[cat]][cat][key]['type'] = self.meals[cat][key]['NAME']
                                for n in params.nutrientList:
                                    current_scaled_ingredient = currentKey[n] * currentPortion / 100.0
                                    plan[day][self.assignMeal[cat]][cat][key][n] = current_scaled_ingredient

                                    nutrientsForMeal[day][cat].setdefault(n, 0.0)
                                    nutrientsForMeal[day][cat][n] += current_scaled_ingredient
                            else:
                                plan[day][self.assignMeal[cat]][cat][key]['type'] = self.meals[cat][key]['NAME']
                                plan[day][self.assignMeal[cat]][cat][key]['varValue'] = var.varValue
                                plan[day][self.assignMeal[cat]][cat][key]['ingredients'].update(self._dB.get_meal_vals(key))

                                for sbls_key, sbls_value in plan[day][self.assignMeal[cat]][cat][key]['ingredients'].iteritems():

                                    current_portion = sbls_value['portion']
                                    for n in params.nutrientList:
                                        sbls_value[n] *= current_portion / 100.0
                                for n in params.nutrientList:
                                    plan[day][self.assignMeal[cat]][cat][key][n] = currentKey[n] * var.varValue

                                    nutrientsForMeal[day][cat].setdefault(n, 0.0)
                                    nutrientsForMeal[day][cat][n] += currentKey[n] * var.varValue

        for day, dayplan in nutrientsForMeal.iteritems():
            for mealKey in dayplan.iterkeys():
                # nutrientsForDay
                for n in params.nutrientList:
                    nutrientsForDay[day].setdefault(n, 0.0)
                    nutrientsForDay[day][n] += nutrientsForMeal[day][mealKey][n]
            # nutrientsForWeek
            for n in params.nutrientList:
                nutrientsForWeek[format.get_week_by_date(day)].setdefault(n, 0.0)
                nutrientsForWeek[format.get_week_by_date(day)][n] += nutrientsForDay[day][n]

        Nutrients = collections.namedtuple('nutrients',
                                           ['nutrientsForMeal', 'nutrientsForDay', 'nutrientsForWeek', 'plan'])

        return Nutrients(
            nutrientsForMeal=dict(nutrientsForMeal),
            nutrientsForDay=dict(nutrientsForDay),
            nutrientsForWeek=dict(nutrientsForWeek),
            plan=dict(plan)
        )"""

        self.evaluate_gen()
        self.evaluate_salad()
        self.evaluate_meal()
        self.evaluat_for_container()

        Nutrients = collections.namedtuple('nutrients',
                                           ['nutrientsForMeal', 'nutrientsForDay', 'nutrientsForWeek', 'plan'])

        return Nutrients(
            nutrientsForMeal=dict(self.nutrientsForContainer),
            nutrientsForDay=dict(self.nutrientsForDay),
            nutrientsForWeek=dict(self.nutrientsForWeek),
            plan=dict(self.plan)
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






