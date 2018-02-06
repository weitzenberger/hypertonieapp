#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 21.12.17


@author: L.We
"""

import os

path = '/Users/l.we/Downloads/Gerichte-2'
os.chdir(path)

for file_name in os.listdir(path):
    print file_name
    new_name = "DE_L_" + file_name
    os.rename(file_name, new_name)