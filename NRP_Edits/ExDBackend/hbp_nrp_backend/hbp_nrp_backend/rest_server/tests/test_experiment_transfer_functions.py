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
Unit tests for the experiment SDF services
"""
__author__ = 'Daniel Peppicelli'

import tempfile
import shutil
import os
import json
from mock import patch
from hbp_nrp_backend.rest_server.tests import RestTest
from hbp_nrp_commons.generated import bibi_api_gen


class TestExperimentTransferFunctions(RestTest):

    def setUp(self):
        patch_StorageClient = patch('hbp_nrp_backend.storage_client_api.StorageClient.StorageClient')
        self.addCleanup(patch_StorageClient.stop)
        self.mock_StorageClient = patch_StorageClient.start()
        self.mock_storageClient_instance = self.mock_StorageClient.return_value
        self.tf1_name = 'left_wheel_neuron_rate_monitor'
        self.tf1 = "@nrp.MapSpikeSink('left_wheel_neuron_aaa', nrp.brain.actors[1], nrp.population_rate)\n" \
                   "@nrp.Neuron2Robot(Topic('/monitor/population_rate', cle_ros_msgs.msg.SpikeRate))\n" \
                   "def " + self.tf1_name + "(t, left_wheel_neuron):\n" \
                   "    return cle_ros_msgs.msg.SpikeRate(t, left_wheel_neuron.rate, " \
                   "'left_wheel_neuron_rate_monitor')\n"
        self.tf2_name = 'all_neurons_spike_monitor'
        self.tf2 = "@nrp.MapSpikeSink('all_neurons_bbb', nrp.brain.circuit[slice(0, 8, 1)], " \
                   "nrp.spike_recorder)\n" \
                   "@nrp.Neuron2Robot(Topic('/monitor/spike_recorder', cle_ros_msgs.msg.SpikeEvent))\n" \
                   "def " + self.tf2_name + "(t, all_neurons):\n" \
                   "    return monitoring.create_spike_recorder_message(t, 8, all_neurons.times, " \
                   "'all_neurons_spike_monitor')\n"
        self.test_directory = os.path.split(__file__)[0]
        self.temp_directory = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.temp_directory):
            shutil.rmtree(self.temp_directory)

    def test_experiment_transfer_functions_put(self):
        experiment_id = '123456'
        data = {'transfer_functions': [self.tf1, self.tf2]}
        bibi_original_path = os.path.join(self.test_directory, "experiments", "experiment_data","bibi_1.bibi")
        bibi_temp_path = os.path.join(self.temp_directory, "bibi_test.xml")
        shutil.copyfile(bibi_original_path, bibi_temp_path)
        with open(bibi_temp_path) as bibi_xml:
            bibi = bibi_api_gen.CreateFromDocument(bibi_xml.read())

        exp_temp_path = os.path.join(os.path.split(__file__)[0], "experiments", "experiment_data", "test_1.exc")
        with open(exp_temp_path) as exp_xml:
            exp = exp_xml.read()

        self.mock_storageClient_instance.get_file.return_value = exp
        self.mock_storageClient_instance.parse_and_check_file_is_valid.return_value = bibi
        
        response = self.client.put('/experiment/' + experiment_id + '/transfer-functions', data=json.dumps(data))
        self.assertEqual(response.status_code, 200)
