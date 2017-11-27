#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 22.08.17

This module contains a class to get data from all SQL Server tables.
Further there is a class to construct standard queries for the special
use cases of the nutrition app.

@author: L.We
"""

# import pymssql
import collections
import copy
from numbers import Number

import constants as c
import params
import pprint

#
# class StandardQuery(object):
#     """Constructor for standard queries in SQL Server. The basis of any query created
#     with this class is:
#         '''SELECT {columns} FROM {table} WHERE {conditions};'''
#
#     Further, statements to pull a randomized partial selection can be added if
#     'random_top' is set to an integer number. The number determines how many rows are
#     selected unless there are not enough rows meeting the conditions.
#
#     """
#
#     def __init__(self, tbl, select, condition, random_top=None):
#         """
#
#         :param tbl: table type
#         :param select: string | list, columns to select
#         :param condition: string | list, conditions have to be written in SQL Server
#         :param random_top: int, fetches x random entries that satisfy the conditions
#         """
#         self.tbl = tbl
#         self.select = select
#         self.condition = condition
#         self.random_top = random_top
#         self._is_concatenated = False
#         self._on_create(tbl, select, condition, random_top)
#
#
#     def __add__(self, other):
#         """After adding two StandardQuery objects, no further operations but adding
#         should be performed on the instance
#
#         :param other: StandardQuery
#         :return: StandardQuery
#         """
#         if isinstance(other, StandardQuery):
#             query_obj = copy.deepcopy(self)
#             query_obj.query += other.query
#             query_obj._is_concatenated = True
#             return query_obj
#         else:
#             raise TypeError(
#                 self.__class__.__name__ + "can only be concatenated with another "
#                 "instance of " + self.__class__.__name__ + " not " + type(other)
#             )
#
#
#     def __repr__(self):
#         return 'Statement: ' + self.query
#
#     def __str__(self):
#         return self.query
#
#     def _list_to_string(self, ls):
#         string = '], ['.join(ls)
#         return string.join(['[', ']'])
#
#     def _on_create(self, tbl, select, condition, random_top):
#         """
#
#         :param tbl:
#         :param select:
#         :param condition:
#         :param random_top:
#         :return:
#         """
#         if isinstance(select, basestring):
#             select_string = '[' + select + ']'
#         elif isinstance(select, collections.Iterable):
#             select_string = self._list_to_string(select)
#         elif not select:
#             select_string = '*'
#         else:
#             raise TypeError("'select' must be of type 'basestring', "
#                             "'list' or 'tuple' not " + type(select))
#
#         if isinstance(condition, basestring):
#             condition_string = condition
#         elif isinstance(condition, collections.Iterable):
#             condition_string = ' AND '.join(condition)
#         elif not condition:
#             condition_string = '1=1'
#         else:
#             raise TypeError("'condition' must be of type basestring, list or tuple not " + type(condition))
#
#         self.query = '''SELECT {col} FROM {tbl} WHERE {cond};'''.format(
#             cond=condition_string,
#             col=select_string,
#             tbl=tbl
#         )
#
#         if random_top:
#             self.insert_into_query(
#                 keyword='SELECT',
#                 statement='TOP(' + str(random_top) + ')',
#                 after=True
#             )
#             self.insert_into_query(
#                 keyword=';',
#                 statement=' ORDER BY NEWID()',
#                 after=False
#             )
#
#     def add_condition(self, condition):
#         """Adds another condition to query
#
#         :param condition: string | list | tuple, single condition or list/tuple of conditions
#         """
#         if isinstance(condition, basestring):
#             self.insert_into_query(
#                 keyword='WHERE',
#                 after=True,
#                 statement=condition + ' AND'
#             )
#         elif isinstance(condition, collections.Iterable):
#             self.insert_into_query(
#                 keyword='WHERE',
#                 after=True,
#                 statement=' AND '.join(condition) + ' AND'
#             )
#         else:
#             raise TypeError("'condition' must be of type 'basestring', "
#                             "'tuple' or 'list' not " + type(condition))
#
#     def insert_into_query(self, keyword, statement, after=True):
#         """Makes an insertion before or after the first occurrence
#         of the keyword in the query.
#
#         :param keyword: keyword before or after statement is inserted
#         :param statement: statement to insert
#         :param after: boolean
#         """
#         if after:
#             first_part = self.query[:self.query.find(keyword) + len(keyword)]
#             second_part = self.query[self.query.find(keyword) + len(keyword):]
#             self.query = first_part + ' ' + statement + second_part
#         else:
#             first_part = self.query[:self.query.find(keyword)]
#             second_part = self.query[self.query.find(keyword):]
#             self.query = first_part + statement + ' ' + second_part


# class SBLSDatabase(object):
#     """
#     Main class for all database interaction. The DB instance is a SQL Server.
#     Important methods:
#         - get_vals_by_sbls - to call values of the db
#
#     """
#
#     def __init__(self, cognito_id=None, rds_host=c.SQL_HOST, user=c.SQL_USER, pw=c.SQL_PW, db_name=c.SQL_DB_NAME):
#         self.cognito_id = cognito_id
#         self.rds_host = rds_host
#         self.user = user
#         self.pw = pw
#         self.db_name = db_name
#         try:
#             self._conn = pymssql.connect(rds_host, user, pw, db_name)
#         except OSError('SQL Server unavailable. Check Connection or Roles'):
#             pass
#         self.cur = self._conn.cursor()
#         # self.sblsStand = self._getCol()

    # def _getCol(self, col='SBLS'):
    #     sbls = []
    #     query1 = "sp_spaceused '{tbl}'".format(tbl=c.SQL_BLS)
    #     self.cur.execute(query1)
    #     db_length = int(self.cur.fetchone()[1])
    #     query2 = 'select [%s] from %s' % (col, self.table2)
    #     self.cur.execute(query2)
    #     for _ in range(db_length):
    #         sbls.append(str(self.cur.fetchone()[0]))
    #     return sbls
    #
    # @staticmethod
    # def _list_to_string(list):
    #     retString = '], ['.join(list)
    #     return retString.join(['[', ']'])
    #
    # def get_table_content_as_list(self, tbl):
    #     """
    #
    #     :param tbl: SQL Server table name
    #     :return: list witch dictionaries as items
    #              e.g.: [{..., ...},
    #                     {..., ...},
    #                     ...]
    #     """
    #     column_names = self.get_column_names(table_name=tbl)
    #     print column_names
    #     query = StandardQuery(
    #         tbl=tbl,
    #         select=column_names,
    #         condition=None
    #     )
    #     print query
    #     self.cur.execute(str(query))
    #     row = self.cur.fetchone()
    #     ls = []
    #     while row:
    #         d = {}
    #         for col, val in zip(column_names, row):
    #             d.update({col: val})
    #         d_copy = copy.deepcopy(d)
    #         ls.append(d_copy)
    #         row = self.cur.fetchone()
    #     return ls
    #
    # def get_all_column_entries(self, column, tb):
    #     """Returns a List of all values in the selected column.
    #     """
    #     query = "select [{col}] from {tbl}".format(col=column, tbl=tb)
    #
    #     self.cur.execute(query)
    #     allRows = self.cur.fetchall()
    #     retList = [row[0] for row in allRows]
    #     return retList
    #
    # def _fetch_data_to_dict(self, columns):
    #     """ input argument columns (all considered columns) must start with uniqueID
    #     """
    #
    #     ret_dict = {}
    #     next_set = True
    #     while next_set:
    #         row = self.cur.fetchone()
    #         while row:
    #             d = {}
    #             for c, t in zip(columns[1:], row[1:]):
    #                 d.update({c: t})
    #             ret_dict.update({str(row[0]): d})
    #             row = self.cur.fetchone()
    #         next_set = self.cur.nextset()
    #     return ret_dict
    #

    # def get_vals_by_sbls(self, vals, tbl, specified_amount=None, *sbls):
    #     """
    #     inputs:
    #         - list of SBLS IDs
    #         - list of nutrients
    #
    #     output example:
    #     {'B100000' : {'int': 'LpInteger', port_alt' : 30, 'ub' : 20}
    #      'B100200' : {'int': 'LpInteger', ''port_alt' : 60, 'ub' : 5}
    #      'C100010' : {'int': 'LpContinuous', ''port_alt' : 20, 'ub' : 2}
    #     """
    #     columns = (['SBLS'] + vals)
    #
    #     rows = "', '".join(sbls)
    #     rows = rows.join(["'", "'"])
    #
    #     query = StandardQuery(
    #         tbl=tbl,
    #         select=columns,
    #         condition='SBLS in ({row})'.format(row=rows)
    #     )
    #     self.cur.execute(str(query))
    #
    #     ret_dict = {}
    #     row = self.cur.fetchone()
    #     while row:
    #         d = {}
    #         current_sbls = row[0].encode('utf-8')
    #         for i, r in enumerate(row[1:]):
    #             if isinstance(r, basestring):
    #                 d.update({vals[i]: r.encode('utf-8')})
    #             elif r is None:
    #                 d.update({vals[i]: None})
    #             else:
    #                 if specified_amount:
    #                     d.update({vals[i]: float(r) * (specified_amount / 100.0)})
    #                     d.update(dict(amount=specified_amount))
    #                 else:
    #                     d.update({vals[i]: float(r)})
    #         ret_dict.update({current_sbls: d})
    #         row = self.cur.fetchone()
    #
    #     return ret_dict

    # def insert_new_meal(self, new_meal_id, ingredients):
    #     """Insert new meal into SQL Database
    #
    #
    #     :param new_meal_id: string, new meal id
    #     :param ingredients: {SBLS: AMOUND_IN_GRAMM,
    #                          SBLS: AMOUND_IN_GRAMM,
    #                          SBLS: AMOUND_IN_GRAMM,
    #                          SBLS: AMOUND_IN_GRAMM}
    #     :return:
    #     """
    #
    #     columns = ['meal_id', 'SBLS', 'AMOUNT']
    #     column_string = " ,".join(columns)
    #     query = StandardQuery(
    #         tbl=c.SQL_MEAL_ING,
    #         select=new_meal_id,
    #         condition="meal_id = " + new_meal_id
    #     )
    #     self.cur.execute(str(query))
    #     if self.cur.fetchone():
    #         raise KeyError('meal key: ' + new_meal_id + ' already exists in table')
    #
    #     values = ["'" + new_meal_id + "'"]
    #     for sbls_key, amount in ingredients.iteritems():
    #         values.append("'" + sbls_key + "'")
    #         values.append(amount)
    #         value_string = " ,".join(values)
    #
    #         query = "INSERT INTO {tbl} ({col}) VALUES ({values})".format(
    #             tbl=c.SQL_MEAL_DES,
    #             col=column_string,
    #             values=value_string
    #         )
    #         self.cur.execute(query)
    #
    # def get_dict_from_table(self, tbl, columns, condition):
    #     column_names = self.get_column_names(table_name=tbl)
    #     query = StandardQuery(
    #         tbl=tbl,
    #         select=columns,
    #         condition=condition
    #     )
    #     self.cur.execute(str(query))
    #     values = self.cur.fetchone()
    #
    #     d = {}
    #     for key, val in column_names, values:
    #         d.update({key: val})
    #
    #     if self.cur.fetchone():
    #         raise NameError('There is more than one entry that meets the condition!')
    #     return d
    #
    # def update_row(self, insertion, tbl, delete_id=True):
    #     values = []
    #     columns = []
    #     for key, val in insertion.iteritems():
    #         if isinstance(val, Number):
    #             columns.append("[" + key + "]")
    #             values.append(unicode(val))
    #         elif isinstance(val, basestring):
    #             columns.append("[" + key + "]")
    #             values.append("'" + unicode(val) + "'")
    #         elif val is None:
    #             pass
    #
    #     column_string = ", ".join(columns)
    #     value_string = ", ".join(values)
    #
    #     if delete_id:
    #         delete_condition = "{key} = '{val}'".format(key=delete_id, val=insertion[delete_id])
    #         query = "DELETE FROM {tbl} WHERE {cond}".format(tbl=tbl, cond=delete_condition)
    #         self.cur.execute(query)
    #
    #     query = u"INSERT INTO {tbl} ({col}) VALUES ({values})".format(tbl=tbl, col=column_string, values=value_string)
    #     print query
    #
    #     self.cur.execute(query)
    #     self._conn.commit()
    #
    # def insert_into(self, meal_key, meal_ing, tbl=c.SQL_MEAL_DES, delete_id=False):
    #     """Inserts new recipe into SQL Server
    #
    #     :param tbl:
    #     :param delete_id:
    #     :param meal_key:  e.g. 'M43'
    #     :param meal_ing: sum of nutrients for the considered meal
    #     """
    #     values = ["'" + meal_key + "'"]
    #     columns = ["MEAL_ID"]
    #
    #     for key, val in meal_ing.iteritems():
    #         if isinstance(val, Number):
    #             columns.append("[" + key + "]")
    #             values.append(unicode(val))
    #         elif isinstance(val, basestring):
    #             columns.append("[" + key + "]")
    #             values.append("'" + unicode(val) + "'")
    #         elif val is None:
    #             pass
    #
    #     column_string = ", ".join(columns)
    #     value_string = ", ".join(values)
    #
    #     if delete_id:
    #         query = "DELETE FROM {tbl} WHERE meal_ID = '{id}'".format(tbl=tbl, id=meal_key)
    #         self.cur.execute(query)
    #
    #     query = u"INSERT INTO {tbl} ({col}) VALUES ({values})".format(tbl=tbl, col=column_string, values=value_string)
    #     print query
    #
    #     self.cur.execute(query)
    #     self._conn.commit()
    #
    # def check_for_column_entries(self, columns, sbls):
    #
    #
    #     query = StandardQuery(
    #         tbl=c.SQL_STA,
    #         select=columns,
    #         condition="SBLS = " + sbls
    #     )
    #     print str(query)
    #     self.cur.execute(str(query))
    #     values = self.cur.fetchone()
    #     d = {}
    #     for i, col in enumerate(columns):
    #         d.update({col: values[i]})
    #     return d
    #
    # def get_grocery_from_bls(self, sbls, amount):
    #     d = self.get_vals_by_sbls(params.nutrientList,
    #                               c.SQL_BLS,
    #                               float(amount),
    #                               sbls)
    #     return d
    #
    #
    #
    # def get_random_meals_for_container_version(self, num, container, splitted_needs, conditions):
    #     """
    #
    #             :param num:
    #             :param container:
    #             :param splitted_needs:
    #             :return: nested dicts
    #                   {'M13': {'FP': 123, 'GCAL': 1234, 'meal_description': u'asdfhhlöjb'}
    #                    'M36': {'FP': 650, 'GCAL': 9889, 'meal_description': u'dsfmbjfzsdddbvsdf'}}
    #             """
    #
    #     columns = ('MEAL_ID', 'NAME', 'DES') + tuple(params.nutrientList)
    #
    #     if (container == "LU"):
    #         ubGcal = splitted_needs['LU']['GCAL'][c.UB]
    #         lbGcal = splitted_needs['LU']['GCAL'][c.LB]
    #         queryWmCond = "GCAL > {lb} AND GCAL < {ub}".format(lb=lbGcal, ub=ubGcal)
    #
    #         query = StandardQuery(
    #             tbl=c.SQL_MEAL_DES,
    #             select=columns,
    #             condition=conditions,
    #             random_top=num
    #         )
    #         #query.add_condition(queryWmCond)
    #
    #     elif (container == 'DI'):
    #         query = StandardQuery(
    #             tbl=c.SQL_MEAL_DES,
    #             select=columns,
    #             condition=conditions,
    #             random_top=num
    #         )
    #
    #
    #     elif (container == 'BF'):
    #         query = StandardQuery(
    #             tbl=c.SQL_MEAL_DES,
    #             select=columns,
    #             condition=conditions.append('ZE > {lb}'.format(lb=params.bfLbZe)),
    #             random_top=2
    #         )
    #         query += StandardQuery(
    #             tbl=c.SQL_MEAL_DES,
    #             select=columns,
    #             condition=conditions.append('ZF > {lb}'.format(lb=params.bfLbZf)),
    #             random_top=2
    #         )
    #         query += StandardQuery(
    #             tbl=c.SQL_MEAL_DES,
    #             select=columns,
    #             condition=conditions,
    #             random_top=num
    #         )
    #
    #     elif (container == 'SN'):
    #         query = StandardQuery(
    #             tbl=c.SQL_MEAL_DES,
    #             select=columns,
    #             condition=conditions,
    #             random_top=num
    #         )
    #     print str(query)
    #
    #     self.cur.execute(str(query))
    #
    #     ret = self._fetch_data_to_dict(columns=columns)
    #
    #     pprint.pprint(ret)
    #
    #     return ret
    #
    # def get_meal_vals(self, meal_id):
    #     """
    #
    #     :param meal_id: Mxxxx, e.g. M0034
    #     :return: {B140534: {PORTION: 40,
    #                         MK: 453,
    #                         MMG: 2345,
    #                         ...},
    #               ...,
    #
    #               C184723: {PORTION: 65,
    #                         MK: 453,
    #                         MMG: 2345,
    #                         ...}}
    #     """
    #
    #     columns = ("SBLS", "AMOUNT")
    #
    #     query = StandardQuery(
    #         tbl=c.SQL_MEAL_ING,
    #         select=columns,
    #         condition="meal_id = '{id}'".format(id=meal_id))
    #     self.cur.execute(str(query))
    #
    #     d = {}
    #     all_rows = self.cur.fetchall()
    #
    #     vals = params.nutrientList + ['ST']
    #
    #     for row in all_rows:
    #         nutrients = self.get_vals_by_sbls(vals, c.SQL_BLS, None, row[0])
    #         nutrients[row[0]].update(dict(portion=row[1]))
    #         d.update(nutrients)
    #     return d

    # def get_column_names(self, table_name="BLS_3.02"):
    #
    #     query = "SELECT COLUMN_NAME FROM Main.INFORMATION_SCHEMA.columns where TABLE_NAME = N%r" % table_name
    #     self.cur.execute(query)
    #
    #     ret_list = []
    #     row = self.cur.fetchone()
    #     while row:
    #         ret_list.append(row[0])
    #         row = self.cur.fetchone()
    #     return ret_list
    #
    #
    #
    # def get_dge(self, age, sex):
    #     """
    #
    #     :param age:
    #     :param sex:
    #     :return:
    #     """
    #     columns = ('NUTRIENT', c.LB, c.UB, 'UNIT')
    #     nuts = set(params.nutrientsMicroList) - set('EARG')
    #     query = "select {col} from {tbl} where age_lb <= {age} " \
    #             "and age_ub >= {age} and sex = '{sex}' " \
    #             "and [nutrient] in {nuts}".format(col=self._list_to_string(columns),
    #                                               tbl=c.SQL_DGE,
    #                                               age=age,
    #                                               sex=sex,
    #                                               nuts=tuple(nuts))
    #     self.cur.execute(query)
    #     retDict = self._fetch_data_to_dict(columns)
    #     return retDict
    #
    #
    # def scan_bls(self, keyword):
    #     """
    #
    #     :param keyword:
    #     :return:
    #     """
    #
    #     param = ("%" + keyword + "%")
    #
    #     query = "SELECT TOP(20) {get_columns} FROM {tbl} WHERE {compare_columns} " \
    #             "LIKE %s ORDER BY len(ST) ASC;".format(
    #                     get_columns=self._list_to_string(('SBLS', 'ST')),
    #                     tbl=c.SQL_BLS,
    #                     compare_columns='ST'
    #             )
    #     self.cur.execute(query, param)
    #     return self.cur.fetchall()

# import dbmodel as db
#
# class ORM(object):
#     def __init__(self):
#         pass
#     def get_dge(self, age, sex):
#         session = db.start_session(engine=db.engine)
#         session.query(db.DGERecommendation).filter_by(SEX=sex)

