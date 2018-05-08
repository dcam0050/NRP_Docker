# ---LICENSE-BEGIN - DO NOT CHANGE OR MOVE THIS HEADER
# This file is part of the Neurorobotics Platform software
# Copyright (C) 2014,2015,2016,2017 Human Brain Project
# https://www.humanbrainproject.eu
#
# The Human Brain Project is a European Commission funded project
# in the frame of the Horizon2020 FET Flagship plan.
# http://ec.europa.eu/programmes/horizon2020/en/h2020-section/fet-flagships
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
# ---LICENSE-END
"""
Unit tests for the service that retrieves experiments
"""

__author__ = "Bernd Eckstein"

import unittest
import os
import sys
import json
from flask import Response, Request
from mock import patch, MagicMock
from hbp_nrp_backend.rest_server.tests import RestTest
from hbp_nrp_backend.rest_server.__ExperimentService import \
    ErrorMessages, get_experiment_basepath, save_file, \
    get_control_state_machine_files, get_evaluation_state_machine_files, get_experiments, \
    get_experiment_rel
from hbp_nrp_backend.rest_server import NRPServicesGeneralException
from hbp_nrp_commons.generated import exp_conf_api_gen


PATH = os.path.split(__file__)[0]
EXPERIMENTS_PATH = os.path.join(PATH, 'experiments')

imp1 = "@nrp.MapSpikeSink('left_wheel_neuron', nrp.brain.actors[1], nrp.population_rate)\n" \
       "@nrp.Neuron2Robot(Topic('/monitor/population_rate', cle_ros_msgs.msg.SpikeRate))\n" \
       "def left_wheel_neuron_rate_monitor(t, left_wheel_neuron):\n" \
       "    return cle_ros_msgs.msg.SpikeRate(t, left_wheel_neuron.rate, " \
       "'left_wheel_neuron_rate_monitor')\n"

imp2 = "@nrp.MapSpikeSink('all_neurons', nrp.brain.circuit[slice(0, 8, 1)], " \
       "nrp.spike_recorder)\n" \
       "@nrp.Neuron2Robot(Topic('/monitor/spike_recorder', cle_ros_msgs.msg.SpikeEvent))\n" \
       "def all_neurons_spike_monitor(t, all_neurons):\n" \
       "    return monitoring.create_spike_recorder_message(t, 8, all_neurons.times, " \
       "'all_neurons_spike_monitor')\n"


class DevNull(object):
    def write(self, data):
        pass


@patch("hbp_nrp_backend.rest_server.__ExperimentService.get_experiment_basepath")
class TestExperimentService(RestTest):

    def setUp(self):
        self.old_stderr = sys.stderr
        sys.stderr = DevNull()

    def tearDown(self):
        sys.stderr = self.old_stderr

    # TEST ExperimentService
    def test_experiment_get_ok(self, mock_bp0):
        mock_bp0.return_value = PATH

        response = self.client.get('/experiment')
        assert(isinstance(response, Response))
        self.assertEqual(response.status_code, 200)

    # TEST getStorageExperiment
    @patch('hbp_nrp_backend.storage_client_api.StorageClient.StorageClient')
    def test_storage_experiment_get_ok(self, storage_mock, mock_bp0):
        client_mock = MagicMock()
        exp_temp_path = os.path.join(os.path.split(__file__)[0], "experiments", "experiment_data", "test_1.exc")
        with open(exp_temp_path) as exp_xml:
            exp = exp_conf_api_gen.CreateFromDocument(exp_xml.read())
        client_mock.clone_file.return_value = exp_temp_path
        client_mock.parse_and_check_file_is_valid.return_value = exp
        storage_mock.return_value = client_mock
        mock_bp0.return_value = PATH

        response = self.client.get('/experiment/experiment_id')
        assert(isinstance(response, Response))
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.get_data(), {})

    # TEST getStorageExperiment
    @patch('hbp_nrp_backend.storage_client_api.StorageClient.StorageClient')
    def test_storage_experiment_get_not_ok(self, storage_mock, mock_bp0):
        client_mock = MagicMock()
        client_mock.clone_file.side_effect = NRPServicesGeneralException(
            ErrorMessages.EXPERIMENT_CONF_FILE_NOT_FOUND_404,
            "Experiment xml not found in the storage"
        )

        storage_mock.return_value = client_mock
        mock_bp0.return_value = PATH

        response = self.client.get('/experiment/test_context')
        assert(isinstance(response, Response))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.get_data())['message'], ErrorMessages.EXPERIMENT_CONF_FILE_NOT_FOUND_404)

    # TEST ExperimentPreview
    @patch("hbp_nrp_backend.rest_server.__ExperimentPreview.get_experiment_basepath")
    def test_experiment_preview_get_exp_not_found(self, mock_bp1, mock_bp0):
        mock_bp0.return_value = EXPERIMENTS_PATH
        mock_bp1.return_value = EXPERIMENTS_PATH

        response = self.client.get('/experiment/__NOT_EXISTING__/preview')
        self.assertEqual(response.status_code, 404)

        message = json.loads(response.get_data())['message']
        self.assertEqual(message, ErrorMessages.EXPERIMENT_NOT_FOUND_404)

    @patch("hbp_nrp_backend.rest_server.__ExperimentPreview.get_experiment_basepath")
    def test_experiment_preview_get_preview_not_found(self, mock_bp1, mock_bp0):
        mock_bp0.return_value = EXPERIMENTS_PATH
        mock_bp1.return_value = EXPERIMENTS_PATH

        response = self.client.get('/experiment/test_2/preview')
        self.assertEqual(response.status_code, 404)

        message = json.loads(response.get_data())['message']
        self.assertEqual(message, ErrorMessages.EXPERIMENT_PREVIEW_NOT_FOUND_404)

    @patch("hbp_nrp_backend.rest_server.__ExperimentPreview.get_experiment_basepath")
    def test_experiment_preview_get_ok(self, mock_bp1, mock_bp0):
        mock_bp0.return_value = EXPERIMENTS_PATH
        mock_bp1.return_value = EXPERIMENTS_PATH

        response = self.client.get('/experiment/test_1/preview')
        self.assertEqual(response.status_code, 200)

    # Test State Machine
    def test_get_control_state_machine_files(self, mock_bp0):
        mock_bp0.return_value = EXPERIMENTS_PATH

        files = get_control_state_machine_files("test_sm")
        self.assertEqual(len(files), 1)

        files = get_control_state_machine_files("test_1")
        self.assertEqual(len(files), 0)

    def test_get_evaluation_state_machine_files(self, mock_bp0):
        mock_bp0.return_value = EXPERIMENTS_PATH

        files = get_evaluation_state_machine_files("test_sm")
        self.assertEqual(len(files), 1)

        files = get_evaluation_state_machine_files("test_1")
        self.assertEqual(len(files), 0)


class TestExperimentService2(unittest.TestCase):

    @patch("hbp_nrp_backend.rest_server.__ExperimentService.os")
    def test_get_experiment_basepath_ok(self, mock_os):
        mock_os.environ.get.return_value = "/test1"
        self.assertEqual("/test1", get_experiment_basepath())

    @patch("hbp_nrp_backend.rest_server.__ExperimentService.os")
    def test_get_experiment_basepath_error(self, mock_os):
        mock_os.environ.get.return_value = None
        self.assertRaises(NRPServicesGeneralException, get_experiment_basepath)

    @patch("hbp_nrp_backend.rest_server.__ExperimentService.get_experiment_basepath")
    def test_save_file(self, mock_basepath):
        mock_basepath.return_value = "/allowed/path"
        self.assertRaises(NRPServicesGeneralException, save_file, "SGVsbG8gV29ybGQK",
                          "/somewhere/else/test.xml")
        # Test break out of allowed path
        self.assertRaises(NRPServicesGeneralException, save_file, "SGVsbG8gV29ybGQK",
                          "/allowed/path/../../broken/out.xml")
        # Test relative path
        self.assertRaises(NRPServicesGeneralException, save_file, "SGVsbG8gV29ybGQK",
                          "../../../relative/path/out.xml")

    @patch("hbp_nrp_backend.rest_server.__ExperimentService.get_experiment_basepath")
    def test_get_experiments(self, mock_experiment_names):
        mock_experiment_names.return_value = EXPERIMENTS_PATH
        experiment_dict = get_experiments(empty_experiment=True)
        self.assertEqual(experiment_dict['TemplateEmpty']['experimentConfiguration'],
                         os.path.join(EXPERIMENTS_PATH,
                                      ".empty_experiment",
                                      "TemplateEmpty.exc"))

    @patch("hbp_nrp_backend.rest_server.__ExperimentService.get_experiments")
    def test_get_experiment_rel(self, mock_experiments):
        mock_experiments.return_value = {'TemplateEmpty':
                                         {'description': u'This empty experiment is based on the models that you have selected. You are free to edit the description.',
                                          'experimentConfiguration':  os.path.join(EXPERIMENTS_PATH,".empty_experiment","TemplateEmpty.exc"),
                                          'brainProcesses': 1L,
                                          'cameraPose': [4.5, 0.0, 1.8, 0.0, 0.0, 0.6],
                                             'maturity': u'development',
                                             'visualModelParams': None,
                                             'timeout': 840.0,
                                             'visualModel': None,
                                             'name': u'Empty template experiment'}}
        experiment_file = get_experiment_rel('newExperiment')
        self.assertEqual(experiment_file, os.path.join(EXPERIMENTS_PATH, ".empty_experiment","TemplateEmpty.exc"))
 
if __name__ == '__main__':
    unittest.main()
