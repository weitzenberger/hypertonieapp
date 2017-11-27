#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 09.11.17


@author: L.We
"""
from dbmodel import *
import dbupdatetools as updater

import sys
reload(sys)
sys.setdefaultencoding('utf8')

session = start_session()

PATH = '/Users/l.we/Dropbox/Exist Antrag/4_Mobile App/6_expositio/Content/Kategorien.xlsx'
PATH2 = '/Users/l.we/Dropbox/Exist Antrag/4_Mobile App/6_expositio/Content/Ernährungstipps.xlsx'
PATH3 = '/Users/l.we/Dropbox/Exist Antrag/4_Mobile App/6_expositio/Content/InputRange.xlsx'
PATH4 = '/Users/l.we/Dropbox/Exist Antrag/4_Mobile App/6_expositio/Content/HomeSlides.xlsx'
PATH5 = '/Users/l.we/Dropbox/Exist Antrag/11_Datenbank/BLS/BLS_3.02_Variablennamen_abgekuerzt.xlsx'
PATH6 = '/Users/l.we/Dropbox/Exist Antrag/11_Datenbank/Rezept-DB/aktuelle Version/Datenbank.xlsx'
PATH7 = '/Users/l.we/Dropbox/Exist Antrag/11_Datenbank/Rezept-DB/Zielwerte/Zielwerte Hypertonie.xls'

# updater.update_table(path=PATH, sheet_index=4, tbl=Nutrients, session=session)
# updater.update_table(path=PATH, sheet_index=2, tbl=Habits, session=session)
# updater.update_table(path=PATH, sheet_index=1, tbl=Intolerances, session=session)
# updater.update_table(path=PATH, sheet_index=0, tbl=Allergies, session=session)
# updater.update_table(path=PATH2, sheet_index=0, tbl=DailyTop, session=session)
# updater.update_table(path=PATH3, sheet_index=0, tbl=InputRange, session=session)
# updater.update_table(path=PATH, sheet_index=3, tbl=ContainerCategories, session=session)
# updater.update_table(path=PATH4, sheet_index=0, tbl=HomeSlides, session=session)
# updater.update_table(path=PATH5, sheet_index=0, tbl=BLS, session=session)
# updater.update_table(path=PATH6, sheet_index=0, tbl=StandardBLS, session=session)
# updater.update_table(path=PATH6, sheet_index=1, tbl=MealDescription, session=session)
# updater.update_table(path=PATH6, sheet_index=2, tbl=MealComposition, session=session)
updater.update_table(path=PATH7, sheet_index=1, tbl=HypertensionRecommendation, session=session)


