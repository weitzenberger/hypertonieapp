#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 09.05.2017 13:40

This module contains a couple of data processing tools to transform data
going to and coming from AWS and all methods to get datetime objects,
ISO 8601 formatted time strings or any other time related values. Further
there are some decorators for debugging purposes and performance evaluation.


@author: L.We
"""

import sys
import json
import decimal
from numbers import Number
import time
import datetime as dt
import dateutil.parser
import collections


decimal.getcontext().prec = 10


# Decorators for debugging purposes and performance evaluation


def simple_decorator(decorator):
    """This decorator can be used to turn simple functions
    into well-behaved decorators, as long as the decorators
    are fairly simple. If a decorator expects a function and
    returns a function (no descriptors), and if it doesn't
    modify function attributes or docstrings, then it is
    eligible to use this.
    """
    def _wrapper(f):
        g = decorator(f)
        g.__name__ = f.__name__
        g.__doc__ = f.__doc__
        g.__dict__.update(f.__dict__)
        return g
    _wrapper.__name__ = decorator.__name__
    _wrapper.__doc__ = decorator.__doc__
    _wrapper.__dict__.update(decorator.__dict__)
    return _wrapper


class CountCalls(object):
    """Decorator that keeps track of the number of times a function is called."""
    __instances = {}

    def __init__(self, function):
        self.__function = function
        self.__numcalls = 0
        CountCalls.__instances[function] = self

    def __call__(self, *args, **kwargs):
        self.__numcalls += 1
        return self.__function(*args, **kwargs)

    @staticmethod
    def count(function):
        """Return the number of times the function f was called."""
        return CountCalls.__instances[function].__numcalls

    @staticmethod
    def counts():
        """Return a dict of {function: # of calls} for all registered functions."""
        return dict([(f, CountCalls.count(f)) for f in CountCalls.__instances])


@simple_decorator
def time_it(function):
    """Times a function and prints the result."""
    def _wrapper(*args, **kwargs):
        t1 = time.time()
        ret = function(*args, **kwargs)
        t2 = time.time()
        print "Time it took to run " + function.__name__ + ": " + str((t2 - t1)) + "\n"
        return ret
    return _wrapper


@simple_decorator
def print_information(function):
    """Prints some AWS API information."""
    def _wrapper(event, context):
        print "Invoked function: " + str(function.__name__) + '\n' + \
              "Variable names: " + str(function.__code__.co_varnames) + '\n' + \
              "CognitoID: " + str(context.identity.cognito_identity_id) + '\n' + \
              "Invoked by ARN: " + str(context.invoked_function_arn) + '\n' + \
              "Invocation Request ID: " + str(context.aws_request_id) + '\n' + \
              "Event: "
        print event
        return function(event, context)
    return _wrapper


# All methods that are used to obtain or convert datetime objects
# and ISO 8601 time strings or any other time related values


def get_remaining_days(thisweek):
    """Remaining dates for this week or all dates for next week.

    :param thisweek: boolean
    :return: list of dates in ISO 8601
    """
    today = dt.datetime.today().weekday()
    if thisweek:
        return [get_date_in_iso(i) for i in xrange(7 - today)]
    else:
        return [get_date_in_iso(i + 7 - today) for i in xrange(7)]


def get_date_in_iso(day_delta=0, year_delta=None):
    """Relative date with regard to today.

    :param day_delta: days as Integer
    :return: date in ISO 8601
    """
    datetime = dt.datetime.today() + dt.timedelta(days=day_delta)
    if year_delta:
        time_string = get_iso_by_datetime(datetime)
        year = int(time_string[:4])
        updated_year = int(year - year_delta)
        return str(updated_year) + time_string[4:]
    else:
        return get_iso_by_datetime(datetime)

def get_week_in_iso(thisweek):
    """Returns this or next week in ISO 8601.

    :param thisweek: boolean
    :return: week in ISO 8601
    """
    isocal = dt.datetime.today().isocalendar()
    return str(isocal[0]) + '-' + str(isocal[1] + (0 if thisweek else 1))

def get_dates_by_week(week):
    """Returns a list of dates in ISO 8601

    :param week: YYYY-'W'WW
    :return:
    """
    ls = []
    for i in range(7):
        datetime = dt.datetime.strptime(week + '-' + str(i), "%Y-W%W-%w")
        iso_date = get_iso_by_datetime(datetime)
        ls.append(iso_date)
    return ls


def get_week_by_date(date):
    """Returns week for given date.

    :param date: date in ISO 8601
    :return: week in ISO 8601
    """
    values = date.split('-')
    isocal = dt.datetime(int(values[0]), int(values[1]), int(values[2])).isocalendar()
    return str(isocal[0]) + '-W' + str(isocal[1])


def get_week_day():
    """Returns day of the week. Value is continuous and considers day time"""
    return dt.datetime.today().weekday() + dt.datetime.today().hour / 24.0


def get_iso_by_datetime(datetime):
    """Converts datetime object to a ISO8601 string."""
    return dt.date.isoformat(datetime)


def get_date_time_by_iso(timestr):
    """Converts ISO 8601 string to a datetime object."""
    return dateutil.parser.parse(timestr)


# All converter methods to process data coming from or going to AWS


@simple_decorator
def lambda_body_map(function):
    """Decorator to process the event object for the standard
    "passthrough" template provided by AWS API Gateway. Standard
    variables in the method are:
        cognito_id
        whole_mapped_body"""
    def _wrapper(event, context):
        whole_mapped_body = event
        cognito_id = event["cognito-identity-id"]
        event = json.loads(event["body-json"])
        return function(event, context, cognito_id, whole_mapped_body)
    return _wrapper


@simple_decorator
def lambda_proxy(function):
    """Decorator to process the event object and to provide the
    correct response Syntax for Lambda functions that are integrated
    in API Gateway as lambda-proxies.
    """
    def _wrapper(event, context):
        event = convert_json(event)
        response = function(event, context)
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": {'Accept': "*",
                        'Content-Type': "application/json"
                # 'Access-Control-Allow-Origin': '*',
                #         'Access-Control-Allow-Headers':'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                #         'Access-Control-Allow-Credentials': True,
                #         'Content-Type': 'application/json'
                        },
            "body": json.dumps(response)
        }
    return _wrapper


def _convert(type_to_process):
    """Decorator for processing Numbers, basestrings,
    or dicts in any given data structure

    :param type_to_process: 'number' | 'basestring' | 'mapping',
                             which data type is to be processed
    :return: actual decorator function
    """
    def _real_decorator(function):
        """Actual decorator for processing data

        :param function: function to process data of given type
        :return: wrapped converter function
        """
        process = {'number': lambda data: data,
                   'basestring': lambda data: data,
                   'mapping': lambda data: dict(map(_wrapper, data.iteritems())),
                   type_to_process: function}

        def _wrapper(data):
            if isinstance(data, Number):
                return process['number'](data)
            elif isinstance(data, basestring):
                return process['basestring'](data)
            elif isinstance(data, collections.Mapping):
                return process['mapping'](data)
            elif isinstance(data, collections.Iterable):
                return type(data)(map(_wrapper, data))
            else:
                return data
        return _wrapper
    return _real_decorator


@_convert(type_to_process='basestring')
def convert_empty_string_to_None(data):
    if data == u'':
        return None
    return data


@_convert(type_to_process='basestring')
def convert_json(data):
    """Loads any JSON formatted string that is
    anywhere in the given data structure.

    :param data:
    :return:
    """
    try:
        return json.loads(data)
    except ValueError:
        return data



@_convert(type_to_process='number')
def convert_to_decimal(data):
    """Converts all Numbers in any given data structure
    to Decimal rounded to 10 digits

    :param data:
    :return:
    """
    if (data is True) or (data is False):
        return data
    data = int(round(data, 0))
    return decimal.Decimal(data)


@_convert(type_to_process='number')
def convert_to_float(data):
    """Converts all Numbers in any
    given data structure to floats
    """
    if (data is True) or (data is False):
        return data
    return float(data)


@_convert(type_to_process='mapping')
def convert_ddb_response(data):
    """Removes all data format keywords: 'M' for Mapping,
    'S' for String and 'N' for Number
    """
    if data.keys()[0] in ['M', 'S', 'N']:
        if data.keys()[0] == unicode('M'):
            return convert_ddb_response(data.values()[0])
        elif data.keys()[0] == unicode('S'):
            return data.values()[0]
        elif data.keys()[0] == unicode('N'):
            return float(data.values()[0])
    else:
        return dict((map(convert_ddb_response, data.iteritems())))
