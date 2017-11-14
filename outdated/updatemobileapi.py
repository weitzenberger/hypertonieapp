#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 23.10.17


@author: L.We
"""


import dbupdatetools as updater
import constants as c

PATH = '/Users/l.we/Dropbox/Exist Antrag/11_Datenbank/Kategorien.xlsx'

updater.update_table(path=PATH, sheet_index=4, tbl=c.SQL_NUTRIENTS)
updater.update_table(path=PATH, sheet_index=2, tbl=c.SQL_HABITS)
updater.update_table(path=PATH, sheet_index=1, tbl=c.SQL_INTOLERNACES)
updater.update_table(path=PATH, sheet_index=0, tbl=c.SQL_ALLERGIES)
