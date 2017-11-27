#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 10.11.17


@author: L.We
"""

# import awsapi

# db = awsapi.DynamoUserData()

# db.create_shopping_list('TEST_ID', ['2017-11-11', '2017-11-10'])

# print db.shopping_list('TEST_ID')
# db.shopping_list_check_item('TEST_ID', 'SBLS1')

import boto3
import pprint
client = boto3.client('cognito-identity')

response = client.describe_identity(
    IdentityId='eu-central-1:099a01b6-76ae-41eb-ad05-7feec7ff1f3a'
)
pprint.pprint(response)