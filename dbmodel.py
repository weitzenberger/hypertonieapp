#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 10.11.17


@author: L.We
"""

import pymysql
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, Integer, String, Float, Boolean, MetaData, Table


MYSQL_PW = "dXY-TR9-W5B-Duu"
MYSQL_USER = "engelstrompete"
MYSQL_HOST = "kadiaappcontent.cxh7i7jlsgbr.eu-central-1.rds.amazonaws.com"
MYSQL_DB = "kadia"

connection_kwargs = dict(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PW,
    db=MYSQL_DB,
    charset='utf8',
    cursorclass=pymysql.cursors.DictCursor
)


connection_str = "mysql+pymysql://{user}:{pw}@{host}/{db}?charset=utf8".format(
    user=MYSQL_USER,
    pw=MYSQL_PW,
    host=MYSQL_HOST,
    db=MYSQL_DB
)

engine = create_engine(connection_str)


def start_session(engine=engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


class BaseClass(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    __table_args__ = {'mysql_engine': 'InnoDB'}


Base = declarative_base(cls=BaseClass)


class StandardNutrientMixin(object):

    GCAL = Column(Float())
    ZF = Column(Float())
    ZE = Column(Float())
    F182 = Column(Float())
    F183 = Column(Float())
    ZK = Column(Float())
    EARG = Column(Float())
    MMG = Column(Float())
    VC = Column(Float())
    VD = Column(Float())
    VE = Column(Float())
    ZB = Column(Float())
    MCA = Column(Float())
    MCL = Column(Float())
    MCU = Column(Float())
    MF = Column(Float())
    MFE = Column(Float())
    MJ = Column(Float())
    MK = Column(Float())
    MMN = Column(Float())
    MNA = Column(Float())
    MP = Column(Float())
    MZN = Column(Float())
    VA = Column(Float())
    VB1 = Column(Float())
    VB12 = Column(Float())
    VB2 = Column(Float())
    VB3A = Column(Float())
    VB5 = Column(Float())
    VB6 = Column(Float())
    VB7 = Column(Float())
    VB9G = Column(Float())
    VK = Column(Float())


    def __repr__(self):
        return "<BLS(SBLS='%s', name='%s')>" % (
            self.SBLS, self.ST)


class PreferenceMixin(object):
    AL_EGG = Column(Boolean)
    AL_PEANUTS = Column(Boolean)
    AL_CRUSTACEAN = Column(Boolean)
    AL_CELERY = Column(Boolean)
    AL_SOY = Column(Boolean)
    AL_FISH = Column(Boolean)
    AL_SQUID = Column(Boolean)
    AL_NUTS = Column(Boolean)
    AL_MUSTARD = Column(Boolean)
    AL_SESAM = Column(Boolean)
    IN_GLUT = Column(Boolean)
    IN_LAKT = Column(Boolean)
    VEGAN = Column(Boolean)
    VEGGIE = Column(Boolean)
    MEAT = Column(Boolean)
    DE_GLU = Column(Boolean)
    DE_LAKT = Column(Boolean)

metadata = MetaData()

bls = Table(
    'bls',
    metadata,
    Column('SBLS', String(50), primary_key=True),
    Column('ST', String(300)),
    Column('STE', String(50)),
    Column('GCAL', Float()),
    Column('GJ', Float()),
    Column('GCALZB', Float()),
    Column('GJZB', Float()),
    Column('ZW', Float()),
    Column('ZE', Float()),
    Column('ZF', Float()),
    Column('ZK', Float()),
    Column('ZB', Float()),
    Column('ZM', Float()),
    Column('ZO', Float()),
    Column('ZA', Float()),
    Column('VA', Float()),
    Column('VAR', Float()),
    Column('VAC', Float()),
    Column('VD', Float()),
    Column('VE', Float()),
    Column('VEAT', Float()),
    Column('VK', Float()),
    Column('VB1', Float()),
    Column('VB2', Float()),
    Column('VB3', Float()),
    Column('VB3A', Float()),
    Column('VB5', Float()),
    Column('VB6', Float()),
    Column('VB7', Float()),
    Column('VB9G', Float()),
    Column('VB12', Float()),
    Column('VC', Float()),
    Column('MNA', Float()),
    Column('MK', Float()),
    Column('MCA', Float()),
    Column('MMG', Float()),
    Column('MP', Float()),
    Column('MS', Float()),
    Column('MCL', Float()),
    Column('MFE', Float()),
    Column('MZN', Float()),
    Column('MCU', Float()),
    Column('MMN', Float()),
    Column('MF', Float()),
    Column('MJ', Float()),
    Column('KAM', Float()),
    Column('KAS', Float()),
    Column('KAX', Float()),
    Column('KA', Float()),
    Column('KMT', Float()),
    Column('KMF', Float()),
    Column('KMG', Float()),
    Column('KM', Float()),
    Column('KDS', Float()),
    Column('KDM', Float()),
    Column('KDL', Float()),
    Column('KD', Float()),
    Column('KMD', Float()),
    Column('KPOR', Float()),
    Column('KPON', Float()),
    Column('KPG', Float()),
    Column('KPS', Float()),
    Column('KP', Float()),
    Column('KBP', Float()),
    Column('KBH', Float()),
    Column('KBU', Float()),
    Column('KBC', Float()),
    Column('KBL', Float()),
    Column('KBW', Float()),
    Column('KBN', Float()),
    Column('EILE', Float()),
    Column('ELEU', Float()),
    Column('ELYS', Float()),
    Column('EMET', Float()),
    Column('ECYS', Float()),
    Column('EPHE', Float()),
    Column('ETYR', Float()),
    Column('ETHR', Float()),
    Column('ETRP', Float()),
    Column('EVAL', Float()),
    Column('EARG', Float()),
    Column('EHIS', Float()),
    Column('EEA', Float()),
    Column('EALA', Float()),
    Column('EASP', Float()),
    Column('EGLU', Float()),
    Column('EGLY', Float()),
    Column('EPRO', Float()),
    Column('ESER', Float()),
    Column('ENA', Float()),
    Column('EH', Float()),
    Column('EP', Float()),
    Column('F40', Float()),
    Column('F60', Float()),
    Column('F80', Float()),
    Column('F100', Float()),
    Column('F120', Float()),
    Column('F140', Float()),
    Column('F150', Float()),
    Column('F160', Float()),
    Column('F170', Float()),
    Column('F180', Float()),
    Column('F200', Float()),
    Column('F220', Float()),
    Column('F240', Float()),
    Column('FS', Float()),
    Column('F141', Float()),
    Column('F151', Float()),
    Column('F161', Float()),
    Column('F171', Float()),
    Column('F181', Float()),
    Column('F201', Float()),
    Column('F221', Float()),
    Column('F241', Float()),
    Column('FU', Float()),
    Column('F162', Float()),
    Column('F164', Float()),
    Column('F182', Float()),
    Column('F183', Float()),
    Column('F184', Float()),
    Column('F193', Float()),
    Column('F202', Float()),
    Column('F203', Float()),
    Column('F204', Float()),
    Column('F205', Float()),
    Column('F222', Float()),
    Column('F223', Float()),
    Column('F224', Float()),
    Column('F225', Float()),
    Column('F226', Float()),
    Column('FP', Float()),
    Column('FK', Float()),
    Column('FM', Float()),
    Column('FL', Float()),
    Column('FO3', Float()),
    Column('FO6', Float()),
    Column('FG', Float()),
    Column('FC', Float()),
    Column('GFPS', Float()),
    Column('GKB', Float()),
    Column('GMKO', Float()),
    Column('GP', Float())
)



class BLSNutrientMixin(object):

    SBLS = Column(String(50), primary_key=True)
    ST = Column(String(300))
    STE = Column(String(50))
    GCAL = Column(Float())
    GJ = Column(Float())
    GCALZB = Column(Float())
    GJZB = Column(Float())
    ZW = Column(Float())
    ZE = Column(Float())
    ZF = Column(Float())
    ZK = Column(Float())
    ZB = Column(Float())
    ZM = Column(Float())
    ZO = Column(Float())
    ZA = Column(Float())
    VA = Column(Float())
    VAR = Column(Float())
    VAC = Column(Float())
    VD = Column(Float())
    VE = Column(Float())
    VEAT = Column(Float())
    VK = Column(Float())
    VB1 = Column(Float())
    VB2 = Column(Float())
    VB3 = Column(Float())
    VB3A = Column(Float())
    VB5 = Column(Float())
    VB6 = Column(Float())
    VB7 = Column(Float())
    VB9G = Column(Float())
    VB12 = Column(Float())
    VC = Column(Float())
    MNA = Column(Float())
    MK = Column(Float())
    MCA = Column(Float())
    MMG = Column(Float())
    MP = Column(Float())
    MS = Column(Float())
    MCL = Column(Float())
    MFE = Column(Float())
    MZN = Column(Float())
    MCU = Column(Float())
    MMN = Column(Float())
    MF = Column(Float())
    MJ = Column(Float())
    KAM = Column(Float())
    KAS = Column(Float())
    KAX = Column(Float())
    KA = Column(Float())
    KMT = Column(Float())
    KMF = Column(Float())
    KMG = Column(Float())
    KM = Column(Float())
    KDS = Column(Float())
    KDM = Column(Float())
    KDL = Column(Float())
    KD = Column(Float())
    KMD = Column(Float())
    KPOR = Column(Float())
    KPON = Column(Float())
    KPG = Column(Float())
    KPS = Column(Float())
    KP = Column(Float())
    KBP = Column(Float())
    KBH = Column(Float())
    KBU = Column(Float())
    KBC = Column(Float())
    KBL = Column(Float())
    KBW = Column(Float())
    KBN = Column(Float())
    EILE = Column(Float())
    ELEU = Column(Float())
    ELYS = Column(Float())
    EMET = Column(Float())
    ECYS = Column(Float())
    EPHE = Column(Float())
    ETYR = Column(Float())
    ETHR = Column(Float())
    ETRP = Column(Float())
    EVAL = Column(Float())
    EARG = Column(Float())
    EHIS = Column(Float())
    EEA = Column(Float())
    EALA = Column(Float())
    EASP = Column(Float())
    EGLU = Column(Float())
    EGLY = Column(Float())
    EPRO = Column(Float())
    ESER = Column(Float())
    ENA = Column(Float())
    EH = Column(Float())
    EP = Column(Float())
    F40 = Column(Float())
    F60 = Column(Float())
    F80 = Column(Float())
    F100 = Column(Float())
    F120 = Column(Float())
    F140 = Column(Float())
    F150 = Column(Float())
    F160 = Column(Float())
    F170 = Column(Float())
    F180 = Column(Float())
    F200 = Column(Float())
    F220 = Column(Float())
    F240 = Column(Float())
    FS = Column(Float())
    F141 = Column(Float())
    F151 = Column(Float())
    F161 = Column(Float())
    F171 = Column(Float())
    F181 = Column(Float())
    F201 = Column(Float())
    F221 = Column(Float())
    F241 = Column(Float())
    FU = Column(Float())
    F162 = Column(Float())
    F164 = Column(Float())
    F182 = Column(Float())
    F183 = Column(Float())
    F184 = Column(Float())
    F193 = Column(Float())
    F202 = Column(Float())
    F203 = Column(Float())
    F204 = Column(Float())
    F205 = Column(Float())
    F222 = Column(Float())
    F223 = Column(Float())
    F224 = Column(Float())
    F225 = Column(Float())
    F226 = Column(Float())
    FP = Column(Float())
    FK = Column(Float())
    FM = Column(Float())
    FL = Column(Float())
    FO3 = Column(Float())
    FO6 = Column(Float())
    FG = Column(Float())
    FC = Column(Float())
    GFPS = Column(Float())
    GKB = Column(Float())
    GMKO = Column(Float())
    GP = Column(Float())

    def __repr__(self):
        return "<BLS(SBLS='%s', name='%s')>" % (
            self.SBLS, self.ST)


class BLS(Base, BLSNutrientMixin):
    pass



class MealDescription(Base, StandardNutrientMixin, PreferenceMixin):

    MEAL_ID = Column(String(50), primary_key=True)
    NAME = Column(String(300))
    DES = Column(String(1000))
    EGGS = Column(Boolean)
    MUSLI = Column(Boolean)
    QUARK = Column(Boolean)
    YOGURT = Column(Boolean)
    FRUIT = Column(Boolean)
    SALAD = Column(Boolean)
    BREAD = Column(Boolean)
    BREAD_ROLL = Column(Boolean)
    ROLL = Column(Boolean)
    TOAST = Column(Boolean)
    SMOOTHIE = Column(Boolean)
    WARM = Column(Boolean)
    JUICE = Column(Boolean)
    NUTS = Column(Boolean)
    SNACK = Column(Boolean)
    QUELLE = Column(String(50))


mealdescription = Table(
    'mealdescription',
    metadata,
    Column('MEAL_ID', String(50), primary_key=True),
    Column('NAME', String(300)),
    Column('DES', String(1000)),
    Column('EGGS', Boolean),
    Column('MUSLI', Boolean),
    Column('QUARK', Boolean),
    Column('YOGURT', Boolean),
    Column('FRUIT', Boolean),
    Column('SALAD', Boolean),
    Column('BREAD', Boolean),
    Column('BREAD_ROLL', Boolean),
    Column('ROLL', Boolean),
    Column('TOAST', Boolean),
    Column('SMOOTHIE', Boolean),
    Column('WARM', Boolean),
    Column('JUICE', Boolean),
    Column('NUTS', Boolean),
    Column('SNACK', Boolean),
    Column('QUELLE', String(50)),
    Column('AL_EGG', Boolean),
    Column('AL_PEANUTS', Boolean),
    Column('AL_CRUSTACEAN', Boolean),
    Column('AL_CELERY', Boolean),
    Column('AL_SOY', Boolean),
    Column('AL_FISH', Boolean),
    Column('AL_SQUID', Boolean),
    Column('AL_NUTS', Boolean),
    Column('AL_MUSTARD', Boolean),
    Column('AL_SESAM', Boolean),
    Column('IN_GLUT', Boolean),
    Column('IN_LAKT', Boolean),
    Column('VEGAN', Boolean),
    Column('VEGGIE', Boolean),
    Column('MEAT', Boolean),
    Column('DE_GLU', Boolean),
    Column('DE_LAKT', Boolean),
    Column('GCAL', Float()),
    Column('ZF', Float()),
    Column('ZE', Float()),
    Column('F182', Float()),
    Column('F183', Float()),
    Column('ZK', Float()),
    Column('EARG', Float()),
    Column('MMG', Float()),
    Column('VC', Float()),
    Column('VD', Float()),
    Column('VE', Float()),
    Column('ZB', Float()),
    Column('MCA', Float()),
    Column('MCL', Float()),
    Column('MCU', Float()),
    Column('MF', Float()),
    Column('MFE', Float()),
    Column('MJ', Float()),
    Column('MK', Float()),
    Column('MMN', Float()),
    Column('MNA', Float()),
    Column('MP', Float()),
    Column('MZN', Float()),
    Column('VA', Float()),
    Column('VB1', Float()),
    Column('VB12', Float()),
    Column('VB2', Float()),
    Column('VB3A', Float()),
    Column('VB5', Float()),
    Column('VB6', Float()),
    Column('VB7', Float()),
    Column('VB9G', Float()),
    Column('VK', Float()),
)


class MealComposition(Base):
    ID = Column(Integer, primary_key=True, autoincrement=True)
    MEAL_ID = Column(String(50))
    SBLS = Column(String(50))
    AMOUNT = Column(String(50))
    NAME = Column(String(50))


class StandardBLS(Base, PreferenceMixin):
    NAME = Column(String(150))
    SBLS = Column(String(50), primary_key=True)
    PORT_ALT = Column(String(50))
    PORT_EQ = Column(String(50))
    AUFTEILBAR = Column(String(50))
    PLURAL = Column(String(50))
    UNIT = Column(String(50))
    PENDANT = Column(String(50))
    PENDANT2 = Column(String(50))
    PENDANT3 = Column(String(50))



    def __repr__(self):
        return "<BLS(SBLS='%s', name='%s')>" % (
            self.SBLS, self.ST)


class DailyTop(Base):

    TIP_ID = Column(Integer, primary_key=True, autoincrement=True)
    DESCRIPTION = Column(String(50))
    CATEGORY = Column(String(length=50))
    TEXT = Column(String(length=500))
    COMMENT = Column(String(length=50))



    def __repr__(self):
        return "<User(name='%s', fullname='%s')>" % (
            self.TIP_ID, self.DESCRIPTION)


class InputRange(Base):

    NAME = Column(String(length=50), primary_key=True)
    LOW_BOUND = Column(Float())
    UP_BOUND = Column(Float())
    STEP = Column(Float())



class HomeSlides(Base):

    SLIDE_ID = Column(Integer, primary_key=True)
    TITLE = Column(String(50))
    TEXT = Column(String(300))
    URL = Column(String(150))


class Allergies(Base):

    KEYWORD = Column(String(50), primary_key=True)
    NAME = Column(String(150))



class ContainerCategories(Base):

    KEYWORD = Column(String(50), primary_key=True)
    NAME = Column(String(150))
    COMMENT = Column(String(150))
    BREAKFAST = Column(Boolean)
    LUNCH = Column(Boolean)
    DINNER = Column(Boolean)



class Habits(Base):

    KEYWORD = Column(String(50), primary_key=True)
    NAME = Column(String(150))




class Intolerances(Base):

    KEYWORD = Column(String(50), primary_key=True)
    NAME = Column(String(150))



class Nutrients(Base):

    KEYWORD = Column(String(50), primary_key=True)
    NAME = Column(String(50))
    UNIT = Column(String(50))
    CATEGORY = Column(String(50))
    INFO = Column(String(1000))
    # UNIT_BLS = Column(String(50))



class SBLSImage(Base):

    SBLS = Column(String(50), primary_key=True)
    URL = Column(String(250))



class DGERecommendation(Base):

    ID = Column(Integer, primary_key=True, autoincrement=True)
    NUTRIENT = Column(String(50))
    SEX = Column(String(50))
    AGE_LB = Column(Integer)
    AGE_UB = Column(Integer)
    LB = Column(Float)
    UB = Column(Float)
    UNIT = Column(String(50))
    COMMENT = Column(String(300))

class HypertensionRecommendation(Base):

    ID = Column(Integer, primary_key=True, autoincrement=True)
    NUTRIENT = Column(String(50))
    SEX = Column(String(50))
    AGE_LB = Column(Integer)
    AGE_UB = Column(Integer)
    LB = Column(Float)
    UB = Column(Float)
    UNIT = Column(String(50))
    COMMENT = Column(String(300))



if __name__ == '__main__':
    Base.metadata.create_all(engine)
    metadata.create_all(engine)


