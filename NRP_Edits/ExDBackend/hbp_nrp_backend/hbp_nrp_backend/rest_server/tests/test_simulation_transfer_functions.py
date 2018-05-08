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
Unit tests for the service that patches transfer function sources
"""

__author__ = 'DanielPeppicelli, LucGuyot'

import unittest
import json
from mock import patch, MagicMock, Mock
from hbp_nrp_backend.rest_server import NRPServicesClientErrorException, \
    NRPServicesTransferFunctionException
from hbp_nrp_backend.rest_server.__SimulationTransferFunctions import get_tf_name
from hbp_nrp_backend.simulation_control import simulations, Simulation
from hbp_nrp_backend.rest_server.tests import RestTest


class TestSimulationTransferFunctions(RestTest):

    def setUp(self):
        del simulations[:]
        simulations.append(Simulation(0, 'experiment_0', None,
                                      'default-owner', 'local', 'created'))
        simulations.append(Simulation(1, 'experiment_1', None,
                                      'untrusted-owner', 'local', 'created'))
        self.sim = simulations[0]
        self.sim.cle = MagicMock()
        self.sim.cle.edit_simulation_transfer_function = MagicMock(
            return_value='')

    def test_get_tf_name(self):
        self.assertEqual(None, get_tf_name(" not valid :)"))
        self.assertEqual("tf1", get_tf_name("def tf1():\n return"))
        self.assertEqual("tf1", get_tf_name("def tf1(a,b,c):\n return"))
        self.assertEqual("tf1", get_tf_name("def tf1  (a,b,c):\n return"))
        self.assertEqual("tf1", get_tf_name(
            "def tf1(a,b,c):\n  def tf2(a):\n    return  return"))

    @patch('hbp_nrp_backend.rest_server.__SimulationTransferFunctions._get_simulation_or_abort')
    def test_simulation_transfer_functions_get(self, mocked_get_simulation_or_abort):
        mocked_simulation = MagicMock()
        mocked_simulation.cle = MagicMock()
        transfer_functions_list = [
            "def tf1(unused):\n return", "def tf2():\n return"]
        transfer_functions_list_activation_mask = [True, True]
        mocked_simulation.cle.get_simulation_transfer_functions = MagicMock(
            return_value=(transfer_functions_list, transfer_functions_list_activation_mask))
        mocked_get_simulation_or_abort.return_value = mocked_simulation
        response = self.client.get('/simulation/0/transfer-functions')
        self.assertEqual(
            mocked_simulation.cle.get_simulation_transfer_functions.call_count, 1)
        self.assertEqual(response.status_code, 200)
        transfer_functions_response = {
            "data":
            {"tf1": "def tf1(unused):\n return", "tf2": "def tf2():\n return"},
            "active":
            {"tf1": True, "tf2": True}
        }
        self.assertEqual(response.data.strip(), json.dumps(transfer_functions_response))

    @patch('hbp_nrp_backend.rest_server.__SimulationTransferFunctions._get_simulation_or_abort')
    def test_simulation_transfer_functions_post_success(self, mocked_get_simulation_or_abort):
        mocked_get_simulation_or_abort.return_value = self.sim
        self.sim.cle.add_simulation_transfer_function = MagicMock(
            return_value='')
        response = self.client.post('/simulation/0/transfer-functions',
                                    data=json.dumps(
                                        "def tf1  (a,b,c):\n return"),
                                    content_type='plain/text')
        self.assertEqual(response.data, '200\n')
    
    @patch('hbp_nrp_backend.rest_server.__SimulationTransferFunctions._get_simulation_or_abort')
    def test_simulation_transfer_functions_post_duplicate(self, mocked_get_simulation_or_abort):
        mocked_get_simulation_or_abort.return_value = self.sim
        self.sim.cle.add_simulation_transfer_function = MagicMock(
            return_value='duplicate')
        response = self.client.post('/simulation/0/transfer-functions',
                                    data=json.dumps(
                                        "def tf1  (a,b,c):\n return"),
                                    content_type='plain/text')
        self.assertIn('Transfer function patch failed',response.data )

    @patch('hbp_nrp_backend.rest_server.__SimulationTransferFunctions._get_simulation_or_abort')
    def test_simulation_transfer_functions_post_fail(self, mocked_get_simulation_or_abort):
        mocked_get_simulation_or_abort.return_value = self.sim
        self.sim.cle.add_simulation_transfer_function = MagicMock(
            return_value='Error')
        response = self.client.post('/simulation/0/transfer-functions',
                                    data=json.dumps(
                                        "def tf1  (a,b,c):\n return"),
                                    content_type='plain/text')
        self.assertIn('Adding a new Transfer Function failed',response.data )

    def test_simulation_transfer_function_delete(self):
        self.sim.cle.delete_simulation_transfer_function.return_value = True
        response = self.client.delete(
            '/simulation/0/transfer-functions/incredible_tf_12')
        self.assertEqual(
            self.sim.cle.delete_simulation_transfer_function.call_count, 1)
        self.assertEqual(response.status_code, 200)

        self.sim.cle.delete_simulation_transfer_function.return_value = False
        response = self.client.delete(
            '/simulation/0/transfer-functions/stunning_tf_34')
        self.assertRaises(NRPServicesTransferFunctionException)
        self.assertEqual(response.status_code, 400)

        sim = simulations[1]
        response = self.client.delete(
            '/simulation/1/transfer-functions/amazing_tf_35')
        self.assertRaises(NRPServicesClientErrorException)
        self.assertEqual(response.status_code, 401)
    
    @patch('hbp_nrp_backend.rest_server.__SimulationTransferFunctions._get_simulation_or_abort')
    def test_simulation_transfer_function_post_success(self, mocked_get_simulation_or_abort):
        mocked_get_simulation_or_abort.return_value = self.sim
        self.sim.cle.edit_simulation_transfer_function = MagicMock(
            return_value='')
        response = self.client.put('/simulation/0/transfer-functions/fake1',
                                    data=json.dumps(
                                        "def tf1  (a,b,c):\n return"),
                                    content_type='plain/text')
        self.assertEqual(response.data, '200\n')
    
    @patch('hbp_nrp_backend.rest_server.__SimulationTransferFunctions._get_simulation_or_abort')
    def test_simulation_transfer_function_put_duplicate(self, mocked_get_simulation_or_abort):
        mocked_get_simulation_or_abort.return_value = self.sim
        self.sim.cle.edit_simulation_transfer_function = MagicMock(
            return_value='duplicate')
        response = self.client.put('/simulation/0/transfer-functions/fake1',
                                    data=json.dumps(
                                        "def tf1  (a,b,c):\n return"),
                                    content_type='plain/text')
        self.assertIn('Transfer function patch failed', response.data)

    @patch('hbp_nrp_backend.rest_server.__SimulationTransferFunctions._get_simulation_or_abort')
    def test_simulation_transfer_function_put_fail(self, mocked_get_simulation_or_abort):
        mocked_get_simulation_or_abort.return_value = self.sim
        self.sim.cle.edit_simulation_transfer_function = MagicMock(
            return_value='Error')
        response = self.client.put('/simulation/0/transfer-functions/fake1',
                                    data=json.dumps(
                                        "def tf1  (a,b,c):\n return"),
                                    content_type='plain/text')
        self.assertIn('Transfer function patch failed', response.data)


class TestSimulationTransferFunctionActivate(RestTest):

    @patch('hbp_nrp_backend.rest_server.__SimulationTransferFunctions._get_simulation_or_abort')
    def test_simulation_transfer_function_activate_put(self, mocked_get_simulation_or_abort):

        mocked_simulation = MagicMock(owner="default-owner")
        mocked_simulation.cle = MagicMock()

        mocked_get_simulation_or_abort.return_value = mocked_simulation

        mocked_simulation.cle.activate_simulation_transfer_function = MagicMock(
            return_value="")

        response = self.client.put(
            '/simulation/0/transfer-functions/{transfer_function_name}/activation/{activate}'
            .format(transfer_function_name="a_tf", activate=False)
        )

        self.assertEqual(
            mocked_simulation.cle.activate_simulation_transfer_function.call_count, 1)
        self.assertEqual(response.status_code, 200)

    @patch('hbp_nrp_backend.rest_server.__SimulationTransferFunctions._get_simulation_or_abort')
    def test_simulation_transfer_function_activate_put_fail(self, mocked_get_simulation_or_abort):
        mocked_simulation = MagicMock(owner="default-owner")
        mocked_simulation.cle = MagicMock()
        mocked_get_simulation_or_abort.return_value = mocked_simulation

        mocked_simulation.cle.activate_simulation_transfer_function = MagicMock(
            return_value="SOME ERROR")

        response = self.client.put(
            '/simulation/0/transfer-functions/{transfer_function_name}/activation/{activate}'
            .format(transfer_function_name="a_tf", activate=False)
        )

        self.assertEqual(
            mocked_simulation.cle.activate_simulation_transfer_function.call_count, 1)
        self.assertEqual(response.status_code, 400)

    @patch('hbp_nrp_backend.rest_server.__SimulationTransferFunctions._get_simulation_or_abort')
    def test_simulation_transfer_function_activate_put_wrong_user(self, mocked_get_simulation_or_abort):
        mocked_simulation = MagicMock(owner="wrong-owner")
        mocked_simulation.cle = MagicMock()
        mocked_get_simulation_or_abort.return_value = mocked_simulation

        response = self.client.put(
            '/simulation/0/transfer-functions/{transfer_function_name}/activation/{activate}'
            .format(transfer_function_name="a_tf", activate=False)
        )

        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main()
