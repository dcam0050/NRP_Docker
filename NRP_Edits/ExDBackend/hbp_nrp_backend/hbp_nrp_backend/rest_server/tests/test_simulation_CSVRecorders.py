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
Unit tests for the simulation SDF services
"""
__author__ = 'LucGuyot'

import os
import json
import csv
from mock import patch, MagicMock, mock_open
from hbp_nrp_backend.simulation_control import simulations, Simulation
from hbp_nrp_backend.rest_server.tests import RestTest


class TestSimulationCSVRecorders(RestTest):
    def setUp(self):
        del simulations[:]
        simulations.append(Simulation(
            0, 'experiment1', None, 'default-owner', 'created'))
        simulations[0].cle = MagicMock()
        self.test_directory = os.path.split(__file__)[0]
        csv_path = os.path.join(self.test_directory,
                                "csv_mock", "csv_mock.csv")
        self.files = MagicMock(name='left_wheel_join_position.csv',
                               temporary_path=csv_path)

        simulations[0].cle.get_simulation_CSV_recorders_files = MagicMock(
            return_value=self.files)
        patch_StorageClient = patch(
            'hbp_nrp_backend.storage_client_api.StorageClient.StorageClient')
        self.addCleanup(patch_StorageClient.stop)
        self.mock_StorageClient = patch_StorageClient.start()
        self.mock_storageClient_instance = self.mock_StorageClient.return_value

    @patch('hbp_nrp_backend.rest_server.__SimulationCSVRecorders.get_date_and_time_string')
    def test_simulation_CSV_recorders_put_OK(self, mock_get_date_and_time_string):
        with patch("__builtin__.open", mock_open(read_data="data")) as mock_file:
            time = '2016-04-11_13-15-34'
            mock_get_date_and_time_string.return_value = time
            sim_id = 0

            self.mock_storageClient_instance.create_and_update.side_effect = None
            self.mock_storageClient_instance.create_folder.return_value = {
                "uuid": "mockUUID"}
            response = self.client.put(
                '/simulation/' + str(sim_id) + '/csv-recorders')
            self.assertEqual(response.status_code, 200)

    def test_simulation_CSV_recorders_get_OK(self):
        with patch("__builtin__.open", mock_open(read_data="data")) as mock_file:
            sim_id = 0
            response = self.client.get(
                '/simulation/' + str(sim_id) + '/csv-recorders')
            self.assertEqual(response.status_code, 200)


    def test_simulation_CSV_recorders_put_sim_not_found(self):
        response = self.client.put('/simulation/1/123456/csv-recorders')
        self.assertEqual(404, response.status_code)

    def test_simulation_CSV_recorders_get_ok(self):
        sim_id = 0
        response = self.client.get(
            '/simulation/' + str(sim_id) + '/csv-recorders')
        self.assertEqual(response.status_code, 200)
