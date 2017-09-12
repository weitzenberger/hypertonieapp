#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 22.08.17

This module contains a class to get data from all SQL Server tables.
Further there is a class to construct standard queries for the special
use cases of the nutrition app.

@author: L.We
"""

import pymssql
import random
import collections
import copy

import constants as c
import params
import awsapi


class StandardQuery(object):
    """Constructor for standard queries in SQL Server. The basis of any query created
    with this class is:
        '''SELECT {columns} FROM {table} WHERE {conditions};'''

    Further, statements to pull a randomized partial selection can be added if
    'random_top' is set to an integer number. The number determines how many rows are
    selected unless there are not enough rows meeting the conditions.

    """

    def __init__(self, tbl, select, condition, random_top=None, exclusion_conditions=None):
        """

        :param tbl: table type
        :param select: string | list, columns to select
        :param condition: string | list, conditions have to be written in SQL Server
        :param random_top: int, fetches x random entries that satisfy the conditions
        :param exclusion_conditions: list, conditions to exclude allergies and intolerances
                                     and to consider habits
        """
        self.tbl = tbl
        self.select = select
        self.condition = condition
        self.random_top = random_top
        self._exclusion_conditions = exclusion_conditions
        self._on_create(tbl, select, condition, random_top, exclusion_conditions)


    def __copy__(self):
        return copy.deepcopy(self)

    def __add__(self, other):
        """After adding two StandardQuery objects, no further operations but adding
        should be performed on the instance

        :param other: StandardQuery
        :return: StandardQuery
        """
        if isinstance(other, StandardQuery):
            query_obj = copy.deepcopy(self)
            query_obj.query += other.query
            return query_obj
        else:
            raise TypeError(
                self.__class__.__name__ + "can only be concatenated with another "
                "instance of " + self.__class__.__name__ + " not " + type(other)
            )


    def __repr__(self):
        return 'Statement: ' + self.query

    def __str__(self):
        return self.query

    def _list_to_string(self, ls):
        string = '], ['.join(ls)
        return string.join(['[', ']'])

    def _on_create(self, tbl, select, condition, random_top, exclusion_conditions):
        """

        :param tbl:
        :param select:
        :param condition:
        :param random_top:
        :param exclusion_conditions:
        :return:
        """
        if isinstance(select, basestring):
            col = '[' + select + ']'
        elif isinstance(select, collections.Iterable):
            col = self._list_to_string(select)
        else:
            raise TypeError("'select' must be of type 'basestring', "
                            "'list' or 'tuple' not " + type(select))

        if isinstance(condition, basestring):
            self.all_conditions = \
                [condition] + exclusion_conditions if exclusion_conditions else []
        elif isinstance(condition, collections.Iterable):
            self.all_conditions = \
                tuple(condition) + tuple(exclusion_conditions) if exclusion_conditions else []
        else:
            raise TypeError("'condition' must be of type basestring, "
                            "list or tuple not " + type(condition))

        self.query = '''SELECT {col} FROM {tbl} WHERE {cond};'''.format(
            cond=condition,
            col=col,
            tbl=tbl
        )
        if random_top:
            self.insert_into_query(
                keyword='SELECT',
                statement='TOP(' + str(random_top) + ')'
            )
            self.insert_into_query(
                keyword=';',
                statement=' ORDER BY NEWID()',
                after=False
            )

    def add_condition(self, condition):
        """Adds another condition to query

        :param condition: string | list | tuple, single condition or list/tuple of conditions
        """
        if isinstance(condition, basestring):
            self.insert_into_query(
                keyword='WHERE',
                statement=condition + ' AND'
            )
        elif isinstance(condition, collections.Iterable):
            self.insert_into_query(
                keyword='WHERE',
                statement=' AND '.join(condition) + ' AND'
            )
        else:
            raise TypeError("'condition' must be of type 'basestring', "
                            "'tuple' or 'list' not " + type(condition))

    def insert_into_query(self, keyword, statement, after=True):
        """Makes an insertion before or after the first occurrence
        of the keyword in the query.

        :param keyword: keyword before or after statement is inserted
        :param statement: statement to insert
        :param after: boolean
        """
        if after:
            first_part = self.query[:self.query.find(keyword) + len(keyword)]
            second_part = self.query[self.query.find(keyword) + len(keyword):]
            self.query = first_part + ' ' + statement + second_part
        else:
            first_part = self.query[:self.query.find(keyword)]
            second_part = self.query[self.query.find(keyword):]
            self.query = first_part + statement + ' ' + second_part

    def _get_exclusion_cond(self, exclusion):
        """

        :param exclusion:
        :return:
        """
        ls = [element.join(['[', ']']) for element in exclusion]
        ls = [element + " != 1" for element in ls]
        return ls


class PersonalDatabaseManager(object):
    def __init__(self):
        pass

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass




class SBLSDatabase(object):
    """
    Main class for all database interaction. The DB instance is a SQL Server.
    Important methods:
        - get_vals_by_sbls - to call values of the db

    """

    def __init__(self, cognito_id=None, rds_host=c.SQL_HOST, user=c.SQL_USER, pw=c.SQL_PW, db_name=c.SQL_DB_NAME):
        self.cognito_id = cognito_id
        self.rds_host = rds_host
        self.user = user
        self.pw = pw
        self.db_name = db_name
        try:
            self._conn = pymssql.connect(rds_host, user, pw, db_name, charset='utf8')
        except OSError('SQL Server unavailable. Check Connection or Roles'):
            pass
        self.cur = self._conn.cursor()
        # self.sblsStand = self._getCol()

    def _getCol(self, col='SBLS'):
        sbls = []
        query1 = "sp_spaceused '{tbl}'".format(tbl=c.SQL_BLS)
        self.cur.execute(query1)
        db_length = int(self.cur.fetchone()[1])
        query2 = 'select [%s] from %s' % (col, self.table2)
        self.cur.execute(query2)
        for _ in range(db_length):
            sbls.append(str(self.cur.fetchone()[0]))
        return sbls

    @staticmethod
    def _list_to_string(list):
        retString = '], ['.join(list)
        return retString.join(['[', ']'])

    def get_all_column_entries(self, column, tb):
        """Returns a List of all values in the selected column.
        """
        query = "select [{col}] from {tbl}".format(col=column, tbl=tb)

        self.cur.execute(query)
        allRows = self.cur.fetchall()
        retList = [row[0] for row in allRows]
        return retList

    def _fetch_data_to_dict(self, columns):
        """ input argument columns (all considered columns) must start with uniqueID
        """

        ret_dict = {}
        next_set = True
        while next_set:
            row = self.cur.fetchone()
            while row:
                d = {}
                for c, t in zip(columns[1:], row[1:]):
                    d.update({c: t})
                ret_dict.update({str(row[0]): d})
                row = self.cur.fetchone()
            next_set = self.cur.nextset()
        return ret_dict

    def conditions(self, cognito_id):
        if self.cognito_id:
            cognito_handler = awsapi.Cognito()
            datasets = cognito_handler.get_records_as_dict(dataset=c.DATASET_VITAL, cognito_id=cognito_id)

            ls_intol = [element.join(['[', ']']) for element in datasets['intolerances']]
            ls_intol = [element + " != 1" for element in ls_intol]

            ls_al = [element.join('[', ']') for element in datasets['allergies']]
            ls_al = [element + " != 1" for element in ls_al]

            ls_hab = [element.join('[', ']') for element in datasets['habit']]
            ls_hab = [element + " = 1" for element in ls_hab]

            return tuple(ls_al + ls_hab + ls_intol)
        else:
            return None

    def get_vals_by_sbls(self, vals, tbl, specified_amount=None, *sbls):
        """
        inputs:
            - list of SBLS IDs
            - list of nutrients

        output example:
        {'B100000' : {'int': 'LpInteger', port_alt' : 30, 'ub' : 20}
         'B100200' : {'int': 'LpInteger', ''port_alt' : 60, 'ub' : 5}
         'C100010' : {'int': 'LpContinuous', ''port_alt' : 20, 'ub' : 2}
        """
        columns = (['SBLS'] + vals)

        rows = "', '".join(sbls)
        rows = rows.join(["'", "'"])

        query = StandardQuery(
            tbl=tbl,
            select=columns,
            condition='SBLS in ({row})'.format(row=rows)
        )
        self.cur.execute(str(query))

        ret_dict = {}
        row = self.cur.fetchone()
        while row:
            d = {}
            current_sbls = row[0].encode('utf-8')
            for i, r in enumerate(row[1:]):
                if isinstance(r, basestring):
                    d.update({vals[i]: r.encode('utf-8')})
                elif r is None:
                    d.update({vals[i]: None})
                else:
                    if specified_amount:
                        d.update({vals[i]: float(r) * (specified_amount / 100.0)})
                        d.update(dict(amount=specified_amount))
                    else:
                        d.update({vals[i]: float(r)})
            ret_dict.update({current_sbls: d})
            row = self.cur.fetchone()

        return ret_dict

    def insert_into(self, mealID, **mealIng):
        """Inserts new recipe into SQL Server

        :param mealID:  e.g. 'M43'
        :param mealIng: sum of nutrients for the considered meal
        """
        l = [str(key) + " = " + str(val) for key, val in mealIng.iteritems()]

        queryCol = ", ".join(l)
        query = "update {tbl} set {col} where meal_ID = '{id}'".format(tbl=c.SQL_MEAL_DES, col=queryCol, id=mealID)

        self.cur.execute(query)
        self._conn.commit()

    def get_grocery_from_bls(self, sbls, amount):
        d = self.get_vals_by_sbls(params.nutrientList,
                              c.SQL_BLS,
                              float(amount),
                              sbls)
        return d


    def get_random_meals(self, num, mealtype, splittedneeds, exclusion=None):
        """

        :param num:
        :param mealtype:
        :param splittedneeds:
        :return: nested dicts
              {'M13': {'FP': 123, 'GCAL': 1234, 'meal_description': u'asdfhhlöjb'}
               'M36': {'FP': 650, 'GCAL': 9889, 'meal_description': u'dsfmbjfzsdddbvsdf'}}
        """


        columns = ('MEAL_ID', 'NAME', 'DES') + tuple(params.nutrientList)

        if (mealtype == "WM"):
            ubGcal = splittedneeds['WM']['GCAL'][c.UB]
            lbGcal = splittedneeds['WM']['GCAL'][c.LB]
            queryWmCond = "GCAL > {lb} AND GCAL < {ub}".format(lb=lbGcal, ub=ubGcal)

            query = StandardQuery(
                tbl=c.SQL_MEAL_DES,
                select=columns,
                condition='WM = 1',
                random_top=num
              #  exclusion_conditions=exclusion
            )
            query.add_condition(queryWmCond)


        elif (mealtype == 'BF'):

            query = StandardQuery(
                tbl=c.SQL_MEAL_DES,
                select=columns,
                condition='BF = 1 AND ZE > {lb}'.format(lb=params.bfLbZe),
                random_top=2,
            )
            query += StandardQuery(
                tbl=c.SQL_MEAL_DES,
                select=columns,
                condition='BF = 1 AND ZF > {lb}'.format(lb=params.bfLbZf),
                random_top=2
            )
            query += StandardQuery(
                tbl=c.SQL_MEAL_DES,
                select=columns,
                condition='BF = 1',
                random_top=num
            )


        elif (mealtype == 'SNACK'):

            query = StandardQuery(
                tbl=c.SQL_MEAL_DES,
                select=columns,
                condition='SNACK = 1',
                random_top=num
            )

        self.cur.execute(str(query))

        return self._fetch_data_to_dict(columns=columns)

    def get_meal_vals(self, meal_id):
        """

        :param meal_id: Mxxxx, e.g. M0034
        :return: {B140534: {PORTION: 40,
                            MK: 453,
                            MMG: 2345,
                            ...},
                  ...,

                  C184723: {PORTION: 65,
                            MK: 453,
                            MMG: 2345,
                            ...}}
        """

        columns = ("SBLS", "AMOUNT")

        query = StandardQuery(
            tbl=c.SQL_MEAL_ING,
            select=columns,
            condition="meal_id = '{id}'".format(id=meal_id))
        self.cur.execute(str(query))

        d = {}
        all_rows = self.cur.fetchall()

        vals = params.nutrientList + ['ST']

        for row in all_rows:
            nutrients = self.get_vals_by_sbls(vals, c.SQL_BLS, None, row[0])
            nutrients[row[0]].update(dict(portion=row[1]))
            d.update(nutrients)
        return d

    def get_random_salad(self, num, exclusion):
        """

        :param num:
        :return:
        """
        sample = random.sample(range(16), num)
        retDict = {}
        for s in sample:
            randMealID = 'GS' + str(s)

            queryCombi = "select SBLS from {tbl} where MEAL_ID = '{id}'".format(tbl=c.SQL_SALAD_COMBI, id=randMealID)
            self.cur.execute(queryCombi)
            row = self.cur.fetchall()
            sbls = [r[0] for r in row]

            querySalad = "select top(1) SBLS from {tbl} where salad = 1 order by newid()".format(tbl=c.SQL_SALAD)
            self.cur.execute(querySalad)
            sbls.append(self.cur.fetchone()[0])

            col = ['NAME', 'INT', 'LB', 'UB']

            retDict[randMealID] = self.get_vals_by_sbls(col, c.SQL_SALAD, None, *sbls)

            d = self.get_vals_by_sbls(params.nutrientList, c.SQL_BLS, None, *sbls)
            for k in retDict[randMealID].keys():
                retDict[randMealID][k].update(d[k])

        return retDict

    def get_random_plate(self, meat=10, veg=10, grain=10, exclusion=None):
        """

        :param meat:
        :param veg:
        :param grain:
        :return:
        """
        columns = ('SBLS', 'NAME', 'MEAT', 'VEGETABLES', 'WHOLE_GRAIN', 'LB', 'UB', c.INT)

        queryMeat = StandardQuery(
            tbl=c.SQL_PLATE,
            select=columns,
            condition='MEAT = 1',
            random_top=meat
        )
        queryVeg = StandardQuery(
            tbl=c.SQL_PLATE,
            select=columns,
            condition='VEGETABLES = 1',
            random_top=veg
        )
        queryGrain = StandardQuery(
            tbl=c.SQL_PLATE,
            select=columns,
            condition='WHOLE_GRAIN = 1',
            random_top=grain
        )

        query = queryMeat + queryVeg + queryGrain

        self.cur.execute(str(query))

        retDict = self._fetch_data_to_dict(columns=columns)

        nutVal = self.get_vals_by_sbls(params.nutrientList, c.SQL_BLS, None, *retDict.keys())
        for key, val in retDict.iteritems():
            val.update(nutVal[key])
        return retDict

    def get_random_smoothie(self, fluid=10, primary=10, secondary=10, boost=10, exclusion=None):
        """

        :param fluid:
        :param primary:
        :param secondary:
        :param boost:
        :return:
        """

        columns = ('SBLS', 'NAME', 'INT', 'LB', 'UB', 'fluid', 'primary', 'secondary', 'boost')

        queryFluid = StandardQuery(
            tbl=c.SQL_SMOOTHIES,
            select=columns,
            condition='fluid = 1',
            random_top=fluid
        )
        queryPrimary = StandardQuery(
            tbl=c.SQL_SMOOTHIES,
            select=columns,
            condition='[primary] = 1',
            random_top=primary
        )
        querySecondary = StandardQuery(
            tbl=c.SQL_SMOOTHIES,
            select=columns,
            condition='secondary = 1',
            random_top=secondary
        )
        queryBoost = StandardQuery(
            tbl=c.SQL_SMOOTHIES,
            select=columns,
            condition='boost = 1',
            random_top=boost
        )

        query = queryFluid + queryPrimary + querySecondary + queryBoost


        self.cur.execute(str(query))

        ret_dict = self._fetch_data_to_dict(columns=columns)

        nut_val = self.get_vals_by_sbls(params.nutrientList, c.SQL_BLS, None, *ret_dict.keys())
        for key, val in ret_dict.iteritems():
            val.update(nut_val[key])
        return ret_dict

    def get_random_sandwich(self, bread=3, butter=3, topping=3, exclusion=None):
        """

        :param bread:
        :param butter:
        :param topping:
        :return:
        """

        columns = ('SBLS', 'NAME', 'INT', 'LB', 'UB', 'bread', 'butter', 'topping')

        query = StandardQuery(
            tbl=c.SQL_SANDWICH,
            select=columns,
            condition='bread = 1',
            random_top=bread
        )
        query += StandardQuery(
            tbl=c.SQL_SANDWICH,
            select=columns,
            condition='butter = 1',
            random_top=butter
        )
        query += StandardQuery(
            tbl=c.SQL_SANDWICH,
            select=columns,
            condition='topping = 1',
            random_top=topping
        )

        self.cur.execute(str(query))

        retDict = self._fetch_data_to_dict(columns=columns)

        nutVal = self.get_vals_by_sbls(params.nutrientList, c.SQL_BLS, None, *retDict.keys())
        for key, val in retDict.iteritems():
            val.update(nutVal[key])
        return retDict

    def get_column_names(self, table_name="BLS_3.02"):

        query = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.columns where TABLE_NAME = N%r" % table_name
        self.cur.execute(query)

        ret_list = []
        row = self.cur.fetchone()
        while row:
            ret_list.append(row[0])
            row = self.cur.fetchone()
        return ret_list

    def get_milk(self):
        columns = ('SBLS') + tuple(params.nutrientList)
        query = "select {} from {} where SBLS = 'M111200'".format(col=columns, tbl=c.SQL_BLS)

        self.cur.execute(query)
        row = self.cur.fetchone()
        for i, r in enumerate(row[1:]):
            d = {row[0]: {params.nutrientList[i]: row}}
        return d

    def get_dge(self, age, sex):
        """

        :param age:
        :param sex:
        :return:
        """
        columns = ('NUTRIENT', c.LB, c.UB, 'UNIT')
        nuts = set(params.nutrientsMicroList) - set('EARG')
        query = "select {col} from {tbl} where age_lb <= {age} " \
                "and age_ub >= {age} and sex = '{sex}' " \
                "and [nutrient] in {nuts}".format(col=self._list_to_string(columns),
                                                  tbl=c.SQL_DGE,
                                                  age=age,
                                                  sex=sex,
                                                  nuts=tuple(nuts))
        self.cur.execute(query)
        retDict = self._fetch_data_to_dict(columns)
        return retDict

    def scan_bls(self, keyword):
        """

        :param keyword:
        :return:
        """

        param = ("%" + keyword + "%")

        query = "SELECT TOP(20) {get_columns} FROM {tbl} WHERE {compare_columns} " \
                "LIKE %s ORDER BY len(ST) ASC;".format(
                        get_columns=self._list_to_string(('SBLS', 'ST')),
                        tbl=c.SQL_BLS,
                        compare_columns='ST'
                )
        self.cur.execute(query, param)
        return self.cur.fetchall()


class Condition(object):
    def __init__(self):
        pass

    def _on_create(self):
        pass

    def __repr__(self):
        pass

    def __add__(self, other):
        pass
