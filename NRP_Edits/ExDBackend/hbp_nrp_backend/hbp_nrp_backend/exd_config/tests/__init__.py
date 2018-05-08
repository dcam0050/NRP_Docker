"""
Contains unit tests of the ExD configuration script
"""
import os

__author__ = 'Lorenzo Vannucci'
NRP_MODELS_DIRECTORY = None


def setUpModule():
    global NRP_MODELS_DIRECTORY
    NRP_MODELS_DIRECTORY = os.environ.get('NRP_MODELS_DIRECTORY')
    if NRP_MODELS_DIRECTORY is not None:
        del os.environ['NRP_MODELS_DIRECTORY']


def tearDownModule():
    if NRP_MODELS_DIRECTORY is not None:
        os.environ['NRP_MODELS_DIRECTORY'] = NRP_MODELS_DIRECTORY
