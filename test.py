#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 10.11.17


@author: L.We
"""

import awsapi

db = awsapi.DynamoUserData()

# db.create_shopping_list('TEST_ID', ['2017-11-11', '2017-11-10'])

print db.shopping_list('TEST_ID')
# db.shopping_list_check_item('TEST_ID', 'SBLS1')