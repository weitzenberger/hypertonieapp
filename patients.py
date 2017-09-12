#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 22.08.17

This module contains all Patient classes that store user specific
parameters and calculate the upper and lower bounds for nutrients.

@author: L.We
"""

import abc

import constants as c
import form
import params


class Patient(object):
    """Abstract Base Class for Patients. Every kind of Patient class has to
    inherit from this class. The response syntax must be as defined in the
    docstring of each property. Every nutrient has a lower and a upper bound.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, height, weight, birthday, pal, sex, days):
        """This is a fake initializer and is to be called only by subclasses
        of Patient to set the standard user attributes.

        :param height: Number | basestring
        :param weight: Number | basestring
        :param birthday: basestring, ISO 8601
        :param pal: Number | basestring
        :param sex: 'm' | 'f'
        :param days: Iterable
        """
        self.days = days
        self.height = float(height)
        self.weight = float(weight)
        self.pal = float(pal)
        self.BMI = self.weight / (self.height ** 2) * 100 ** 2
        self.sex = sex
        self.birthday = birthday

    def __len__(self):
        return (self.height, self.weight,
                self.age, self.pal, self.sex, self.BMI)

    def __str__(self):
        return (self.height, self.weight,
                self.age, self.pal, self.sex, self.BMI)

    def __repr__(self):
        return (self.height, self.weight,
                self.age, self.pal, self.sex, self.BMI)

    @property
    def age(self):
        """Returns age by a given birthday date in ISO 8601.

        :return: float, age in years
        """
        return (form.convert_iso_to_date_time(form.get_date_in_iso()) -
                form.convert_iso_to_date_time(self.birthday)).days / 365.0

    @abc.abstractmethod
    def cal_bounds(self):
        """Calory bounds. Response syntax as defined in the following
        must be met.

        :return: dict,
        {c.LB: xxx,
         c.UB: xxx}
        """
        pass

    @abc.abstractmethod
    def macro_bounds(self):
        """Macro nutrient bounds. Response syntax as defined in the following
        must be met.

        :return: dict,
        {nutrient1: {c.LB: xxx,
                     c.UB: xxx},
         nutrient2: {c.LB: xxx,
                     c.UB: xxx},
         ...}
        """
        pass

    @abc.abstractmethod
    def splitted_macro_bounds(self):
        """Macros nutrient bounds splitted in Containers (Breakfast, Lunch, Dinner).
        Response syntax as defined in the following must be met.

        :return: dict,
        {Container1: {nutrient1: {c.LB: xxx,
                                  c.UB: xxx},
                      nutrient2: {c.LB: xxx,
                                  c.UB: xxx},
                      ...},
         Container2: {nutrient1: {c.LB: xxx,
                                  c.UB: xxx},
                      nutrient2: {c.LB: xxx,
                                 c.UB: xxx},
                      ...},
         ...}
        """
        pass

    @abc.abstractmethod
    def micro_bounds(self):
        """Micro nutrient bounds. Response syntax as defined in the following
        must be met.

        :return: dict,
        {nutrient1: {c.LB: xxx,
                     c.UB: xxx},
         nutrient2: {c.LB: xxx,
                     c.UB: xxx},
         ...}
        """
        pass

    def _get_cal_use_bro(self):
        if (self.sex == 'm'):
            cal_use_bro = params.mult_weight_m_bro * self.weight + \
                          params.mult_height_m_bro * self.height + \
                          params.mult_age_m_bro * self.age + \
                          params.add_m_bro
        elif (self.sex == 'f'):
            cal_use_bro = params.mult_weight_f_bro * self.weight + \
                          params.mult_height_f_bro * self.height + \
                          params.mult_age_f_bro * self.age + \
                          params.add_f_bro
        else:
            raise ValueError("Wrong Gender/Sex. Valid input: u'm' for male and u'f' for female")
        cal_use_bro *= self.pal
        return cal_use_bro

    def _get_cal_use_standard(self):
        if (self.sex == 'm'):
            cal_use_standard = params.mult_weight * self.weight + \
                               params.mult_height * self.height + \
                               params.mult_age * self.age + \
                               params.add_m
        elif (self.sex == 'f'):
            cal_use_standard = params.mult_weight * self.weight + \
                               params.mult_height * self.height + \
                               params.mult_age * self.age + \
                               params.add_f
        else:
            raise ValueError("Wrong Gender/Sex. Valid input: u'm' for male and u'f' for female")
        cal_use_standard *= self.pal
        return cal_use_standard

    @staticmethod
    def _get_average(bounds):
        return (bounds[c.LB] + bounds[c.UB]) * 0.5

    @staticmethod
    def _set_bounds_by_tolerance(value, tolerance=0.15):
        return {
            c.UB: value * (1 + tolerance),
            c.LB: value * (1 - tolerance)
        }


class HypertensionPatient(Patient):
    """Class for Hypertension Patients. The nutritional needs are
    determined as in hypertension studies suggested. For every nutrient
    that is covered by the DGE, the DGE nutritional needs suggestion is
    used instead. The nutritional needs for people under the age of 19
    are not covered by the DGE, so that people of this age group cannot
    be considered in this class.
    """

    def __init__(self, height, weight, birthday, pal, sex, db, days):
        self._dB = db
        super(HypertensionPatient, self).__init__(height, weight, birthday, pal, sex, days)

    @property
    def age(self):
        """Overridden in base class because of age restrictions.

        :return: float, age in years
        """
        age = super(HypertensionPatient, self).age
        if age < 19.0:
            raise ValueError('Customer must be of age 19 or older')
        return age

    @property
    def cal_need(self):
        if self.BMI < params.BMI_bound:
            cal_need = self._get_cal_use_standard()
        elif ((self.BMI >= params.BMI_bound) and (self.BMI < params.BMI_bound_bro)):
            cal_need = self._get_cal_use_standard()
        else:
            cal_need = self._get_cal_use_bro()
        return cal_need

    @property
    def cal_bounds(self):
        return {
            c.LB: self.cal_need * (1 - params.tol['GCAL']),
            c.UB: self.cal_need * (1 + params.tol['GCAL'])
        }

    @property
    def macro_bounds(self):
        fat_bounds = {
            c.LB: self.cal_need / params.calPerMG['ZF'] * 0.3,
            c.UB: self.cal_need / params.calPerMG['ZF'] * 0.35
        }
        prot_bounds = {
            c.LB: 0.8 * self.weight * 1000,
            c.UB: 1.6 * self.weight * 1000
        }
        f182_bounds = {
            c.LB: 'None',
            c.UB: self.cal_need * params.part['F182'] / params.calPerMG['ZF'] * 10
        }
        f183_bounds = {
            c.LB: self.cal_need * params.part['F183'] / params.calPerMG['ZF'] / 10,
            c.UB: 'None'
        }
        fiber_bounds = {
            c.LB: 3e1,
            c.UB: 'None'
        }
        ch_bounds = {
            c.LB: (self.cal_bounds[c.LB] -
                  fat_bounds[c.UB] * params.calPerMG['ZF'] -
                  prot_bounds[c.UB] * params.calPerMG['ZE']) / params.calPerMG['ZK'],
            c.UB: (self.cal_bounds[c.UB] -
                   fat_bounds[c.LB] * params.calPerMG['ZF'] -
                   prot_bounds[c.LB] * params.calPerMG['ZE']) / params.calPerMG['ZK']
        }

        return dict(GCAL=self.cal_bounds,
                    ZF=fat_bounds,
                    ZE=prot_bounds,
                    F182=f182_bounds,
                    F183=f183_bounds,
                    ZB=fiber_bounds,
                    ZK=ch_bounds)

    @property
    def micro_bounds(self):
        bounds = params.bounds.copy()
        a = self._dB.get_dge(age=self.age, sex=self.sex)
        bounds.update(a)

        boundsForWeek = {}
        if isinstance(self.days, basestring):
            raise TypeError('days must be of type list not ' + type(self.days))
        length = len(self.days)
        for i in bounds.iterkeys():
            boundsForWeek.setdefault(i, {})[c.LB] = ((bounds[i][c.LB] * length)
                                                     if bounds[i][c.LB] else 'None')
            boundsForWeek.setdefault(i, {})[c.UB] = ((bounds[i][c.UB] * length)
                                                     if bounds[i][c.UB] else 'None')
        return boundsForWeek

    @property
    def splitted_macro_bounds(self):

        # Breakfast
        cal_need_bf = self._get_average(self.macro_bounds['GCAL']) * params.split['BF']
        fat_need_bf = self._get_average(self.macro_bounds['ZF']) * params.split['BF']
        prot_need_bf = self._get_average(self.macro_bounds['ZE']) * params.split['BF']

        # Lunch
        cal_need_wm = self._get_average(self.macro_bounds['GCAL']) * params.split['WM']
        fat_need_wm = self._get_average(self.macro_bounds['ZF']) * params.split['WM']
        prot_need_wm = self._get_average(self.macro_bounds['ZE']) * params.split['WM']

        # Dinner
        cal_need_cm = self._get_average(self.macro_bounds['GCAL']) * params.split['PL']
        fat_need_cm = self._get_average(self.macro_bounds['ZF']) * params.split['PL']
        prot_need_cm = self._get_average(self.macro_bounds['ZE']) * params.split['PL']

        ret_dict = dict(BF=dict(GCAL=self._set_bounds_by_tolerance(cal_need_bf),
                                ZF=self._set_bounds_by_tolerance(fat_need_bf),
                                ZE=self._set_bounds_by_tolerance(prot_need_bf)),
                        WM=dict(GCAL=self._set_bounds_by_tolerance(cal_need_wm),
                                ZF=self._set_bounds_by_tolerance(fat_need_wm),
                                ZE=self._set_bounds_by_tolerance(prot_need_wm)),
                        PL=dict(GCAL=self._set_bounds_by_tolerance(cal_need_cm),
                                ZF=self._set_bounds_by_tolerance(fat_need_cm),
                                ZE=self._set_bounds_by_tolerance(prot_need_cm)))

        return ret_dict




class DGEPatient(HypertensionPatient):
    """Class for Hypertension Patients only with DGE suggestions."""

    def __init__(self, height, weight, birthday, pal, sex, db, days):
        super(DGEPatient, self).__init__(
            height=height,
            weight=weight,
            birthday=birthday,
            pal=pal,
            sex=sex,
            db=db,
            days=days
        )

    @property
    def age(self):
        """Overridden in base class because of age restrictions.

        :return: float, age in years
        """
        age = super(DGEPatient, self).age
        if age < 19.0:
            raise ValueError('Customer must be of age 19 or older')
        return age

    @property
    def micro_bounds(self):
        pass