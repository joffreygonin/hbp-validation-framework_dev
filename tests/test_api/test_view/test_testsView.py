"""
Tests of the ValidationFramework TestsView.
"""

from __future__ import unicode_literals

import os
import random
import json

from uuid import uuid4
import uuid

import time
from datetime import datetime


from django.test import TestCase, Client, RequestFactory
# SimpleTestCase, TransactionTestCase, TestCase, LiveServerTestCase, assertRedirects
from django.contrib.auth.models import User
from social.apps.django_app.default.models import UserSocialAuth
from hbp_app_python_auth.auth import get_access_token, get_token_type, get_auth_header

from rest_framework.test import APIRequestFactory

from model_validation_api.models import (ValidationTestDefinition, 
                        ValidationTestCode,
                        ValidationTestResult, 
                        ScientificModel, 
                        ScientificModelInstance,
                        ScientificModelImage,   
                        Comments,
                        Tickets,
                        # FollowModel,
                        CollabParameters,
                        Param_DataModalities,
                        Param_TestType,
                        Param_Species,
                        Param_BrainRegion,
                        Param_CellType,
                        Param_ModelType,
                        Param_ScoreType,
                        Param_organizations,
                        )

from validation_service.views import config, home

from model_validation_api.views import (
                    ModelCatalogView,
                    HomeValidationView,

                    ParametersConfigurationRest,
                    AuthorizedCollabParameterRest,
                    Models,
                    ModelAliases,
                    Tests,
                    TestAliases,
                    ModelInstances,
                    Images,
                    TestInstances,
                    TestCommentRest,
                    CollabIDRest,
                    AppIDRest,
                    AreVersionsEditableRest,
                    ParametersConfigurationModelView,
                    ParametersConfigurationValidationView,
                    TestTicketRest,
                    IsCollabMemberRest,
                    Results,
                    CollabAppID,

                    )

from model_validation_api.validation_framework_toolbox.fill_db import (
        create_data_modalities,
        create_organizations,
        create_test_types,
        create_score_type,
        create_species,
        create_brain_region,
        create_cell_type,
        create_model_type,
        create_models_test_results,
        create_fake_collab,
        create_all_parameters,
        create_specific_test,
        create_specific_testcode,
)

from ..auth_for_test_taken_from_validation_clien import BaseClient



from ..data_for_test import DataForTests


username_authorized = os.environ.get('HBP_USERNAME_AUTHORIZED')
password_authorized = os.environ.get('HBP_PASSWORD_AUTHORIZED')

# username_authorized = os.environ.get('HBP_USERNAME_NOT_AUTHORIZED')
# password_authorized = os.environ.get('HBP_PASSWORD_NOT_AUTHORIZED')

base_client_authorized = BaseClient(username = username_authorized, password=password_authorized)
client_authorized = Client(HTTP_AUTHORIZATION=base_client_authorized.token)

# username_not_authorized = os.environ.get('HBP_USERNAME_NOT_AUTHORIZED')
# password_not_authorized = os.environ.get('HBP_PASSWORD_NOT_AUTHORIZED')
# base_client_not_authorized = BaseClient(username = username_not_authorized, password=password_not_authorized)
# client_not_authorized = Client(HTTP_AUTHORIZATION=base_client_not_authorized.token)





    


class TestsViewTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        cls.data = DataForTests()
        

    def setUp(self):
        #Setup run before every test method.
        pass

    def compare_serializer_keys (self, tests, targeted_keys_list_type='all'):
        
        if targeted_keys_list_type == "standard" :
            targeted_keys = [
                            'id', 
                            'name', 
                            'alias',
                            'creation_date',
                            'species', 
                            'brain_region', 
                            'cell_type', 
                            'age', 
                            'data_location', 
                            'data_type',  
                            'data_modality', 
                            'test_type', 
                            'protocol', 
                            'author', 
                            'publication', 
                            'score_type',]
            for test in tests :
                self.assertEqual(set(test.keys()), set(targeted_keys))



        if targeted_keys_list_type == "full" :
            targeted_keys = [
                            'id', 
                            'name', 
                            'alias',
                            'creation_date',
                            'species', 
                            'brain_region', 
                            'cell_type', 
                            'age', 
                            'data_location', 
                            'data_type',  
                            'data_modality', 
                            'test_type', 
                            'protocol', 
                            'author', 
                            'publication', 
                            'codes',
                            # 'score',
                            # 'score_type',
                            ]

            for test in tests :
                self.assertEqual(set(test.keys()), set(targeted_keys))

            
                for code in test['codes'] :
                    self.assertEqual(set(code.keys()), set([
                                                    'description',
                                                    'repository',
                                                    'timestamp',
                                                    'version',
                                                    'path',
                                                    'id',
                                                    'test_definition_id',
                                                    ]))
                    

    def test_get_no_param (self):
        response = client_authorized.get('/tests/', data={})
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests), 3)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
        

    def test_get_param_id (self):
        response = client_authorized.get('/tests/', data={'id': self.data.uuid_test1})
        tests = json.loads(response._container[0])['tests']

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests), 1)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='full')

        self.assertEqual(len(tests[0]['codes']), 1)

        targeted_keys = [
                        'id', 
                        'description', 
                        'repository',
                        'timestamp',
                        'version', 
                        'path', 
                        'test_definition_id', 
                        ]

        for code in tests[0]['codes'] :
            self.assertEqual(set(code.keys()), set(targeted_keys))                    
        # raise ValueError('A very specific bad thing happened.')
        
        

    def test_get_param_name (self):
        response = client_authorized.get('/tests/', data={ 'name': "name 1"})
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests), 1)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
           

    def test_get_param_species (self):
        response = client_authorized.get('/tests/', data={'species': "Mouse (Mus musculus)"})
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),2)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
          

    def test_get_param_brain_region (self):
        response = client_authorized.get('/tests/', data={'brain_region' : "Hippocampus" })
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),2)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
         

    def test_get_param_cell_type (self):
        response = client_authorized.get('/tests/', data={ 'cell_type' :  "Interneuron"})
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),2)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
         

    def test_get_param_age (self):
        response = client_authorized.get('/tests/', data={'age': "12" })
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),2)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
        
        
    def test_get_param_data_location (self):
        response = client_authorized.get('/tests/', data={'data_location': "http://bbbb.com"})
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),2)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
        
        
    def test_get_param_data_type (self):
        response = client_authorized.get('/tests/', data={'data_type' : "data type"})
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),2)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
         

    def test_get_param_data_modality (self):
        response = client_authorized.get('/tests/', data={'data_modality' : "electrophysiology"})
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)        
        self.assertEqual(len(tests),2)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
           

    def test_get_param_test_type (self):
        response = client_authorized.get('/tests/', data={'test_type' : "single cell activity"})
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),2)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')   
        

    def test_get_param_protocol (self):
        response = client_authorized.get('/tests/', data={'protocol': "protocol"})
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),2)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')    
        

    def test_get_param_author (self):
        response = client_authorized.get('/tests/', data={'author' : "me"})
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),2)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
             

    def test_get_param_publication (self):
        response = client_authorized.get('/tests/', data={'publication' :"not published" })
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),2)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
          

    def test_get_param_score_type (self):
        response = client_authorized.get('/tests/', data={'score_type' : "p-value"})
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),2)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
            

    def test_get_param_alias (self):
        response = client_authorized.get('/tests/', data={'alias' : "T1" })
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),1)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
            

    def test_get_param_web_app (self):
        response = client_authorized.get('/tests/', data={'web_app' : True, 'app_id' : '1'})
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),2)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
        
        # raise ValueError('A very specific bad thing happened.')

    def test_get_param_app_id (self):
        response = client_authorized.get('/tests/', data={'app_id' : '1'  })
        tests = json.loads(response._container[0])['tests']
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tests),3)
        self.compare_serializer_keys(tests=tests, targeted_keys_list_type='standard')
        
        

