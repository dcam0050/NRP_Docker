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
Unit tests for the service that pushes and gets state machines
"""

__author__ = "Bernd Eckstein"

import unittest
import os
import json
from mock import patch, Mock, MagicMock, PropertyMock
from flask import Response, Request
from hbp_nrp_backend.rest_server.tests import RestTest
from hbp_nrp_backend.rest_server.__SimulationControl import _get_simulation_or_abort
from hbp_nrp_backend.rest_server.__SimulationControl import UserAuthentication
from hbp_nrp_backend.simulation_control import simulations, Simulation
from hbp_nrp_backend.rest_server import NRPServicesGeneralException, \
    NRPServicesStateMachineException, NRPServicesWrongUserException
from hbp_nrp_excontrol.StateMachineManager import StateMachineManager

SM = """
import mock
import time
sm=mock.Mock()
sm.execute=time.sleep
"""

PATH = os.path.split(__file__)[0]


class TestSimulationStateMachines(RestTest):

    os.environ['NRP_MODELS_DIRECTORY'] = PATH

    def setUp(self):

        self.patch_state = patch('hbp_nrp_backend.simulation_control.__Simulation.Simulation.state')
        self.mock_state = self.patch_state.start()

        self.patch_sm = patch('hbp_nrp_backend.simulation_control.__Simulation.StateMachineManager')
        self.mock_sm_manager = self.patch_sm.start()

        sm = StateMachineManager()
        self.mock_sm_manager_instance = MagicMock(name='SM_manager', wraps=sm)
        self.mock_sm_manager.return_value = self.mock_sm_manager_instance

        self.sm_instance_name = "Control1"
        self.sm_instance = sm.create_state_machine(self.sm_instance_name, 0)
        self.mock_sm_instance = MagicMock(name='SM_instance', sm_id=self.sm_instance_name, wraps=self.sm_instance)
        self.mock_sm_manager_instance.create_state_machine.return_value = self.mock_sm_instance
        self.mock_sm_manager_instance.get_state_machine =\
            Mock(side_effect=lambda name: self.mock_sm_instance if name == self.sm_instance_name else None)

        load_data = {
            "experimentConfiguration": "experiments/experiment_data/test_1.exc",
            "gzserverHost": "local"
        }
        self.client.post('/simulation', data=json.dumps(load_data))

        simulation = _get_simulation_or_abort(0)
        simulation.state = "paused"

    def tearDown(self):
        del simulations[:]
        self.patch_state.stop()
        self.patch_sm.stop()

    def __put_initialization_side_effect(self, mock_sm_instance, side_effect):
        if mock_sm_instance:
            mock_sm_instance.is_running = False
            mock_sm_instance.initialize_sm = Mock(name='initialize_sm', side_effect=side_effect)

    def __put_sm_path_side_effect(self, mock_sm_instance, side_effect):
        if mock_sm_instance:
            mock_sm_instance.is_running = False
            type(mock_sm_instance).sm_path = PropertyMock(name='sm_path', side_effect=side_effect)

    def test_simulation_state_machines_get_ok(self):
        response = self.client.get('/simulation/0/state-machines')
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.strip(), '{"data": {}}')

    def test_simulation_state_machines_get_ok2(self):
        self.mock_sm_manager_instance.state_machines = [self.mock_sm_instance]
        simulation = _get_simulation_or_abort(0)

        simulation.set_state_machine_code(self.sm_instance_name, SM)

        response = self.client.get('/simulation/0/state-machines')

        self.assertIsInstance(response, Response)
        print("Response data=" + response.data)
        self.assertMultiLineEqual(json.loads(response.data)["data"][self.sm_instance_name], SM)
        self.assertEqual(response.status_code, 200)

    def test_simulation_state_machines_put_source_code_error(self):
        simulation = _get_simulation_or_abort(0)
        simulation.set_state_machine_code(self.sm_instance_name, SM)
        self.__put_initialization_side_effect(self.mock_sm_instance, Exception)
        response = self.client.put('/simulation/0/state-machines/Control1', data="ERROR")
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, 500)

    def test_simulation_state_machines_put_OK(self):
        simulation = _get_simulation_or_abort(0)
        simulation.set_state_machine_code(self.sm_instance_name, SM)

        response = self.client.put('/simulation/0/state-machines/Control1', data=SM)
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, 200)

        simulation.state = "paused"
        response = self.client.put('/simulation/0/state-machines/Control1', data=SM)
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, 200)

    def test_simulation_state_machines_put_wrong_user(self):
        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "wrong-owner"}
        response = self.client.put('/simulation/0/state-machines/Control1', headers=hdr, data=SM)
        self.assertRaises(NRPServicesWrongUserException)
        self.assertEqual(response.status_code, 401)

    def test_simulation_state_machines_put_attribute_error(self):
        simulation = _get_simulation_or_abort(0)
        simulation.set_state_machine_code(self.sm_instance_name, SM)
        self.__put_initialization_side_effect(self.mock_sm_instance, AttributeError)
        response = self.client.put('/simulation/0/state-machines/Control1', data="X = 1")
        self.assertEqual(response.status_code, 400)

    def test_simulation_state_machines_put_syntax_error(self):
        simulation = _get_simulation_or_abort(0)
        self.__put_sm_path_side_effect(self.mock_sm_instance, SyntaxError)
        response = self.client.put('/simulation/0/state-machines/Control1', data="X = 1 + .")
        self.assertEqual(response.status_code, 400)

    def test_simulation_state_machines_delete_OK(self):
        self.mock_sm_manager_instance.state_machines = [self.mock_sm_instance]
        simulation = _get_simulation_or_abort(0)

        simulation.set_state_machine_code(self.sm_instance_name, SM)

        response = self.client.delete('/simulation/0/state-machines/Control1')
        self.assertEqual(response.status_code, 200)

    def test_simulation_state_machines_delete_not_found(self):
        simulation = _get_simulation_or_abort(0)
        simulation.set_state_machine_code(self.sm_instance_name, SM)

        response = self.client.delete('/simulation/0/state-machines/Control2')
        self.assertRaises(NRPServicesStateMachineException)
        self.assertEqual(response.status_code, 404)

    def test_simulation_state_machines_delete_wrong_user(self):
        self.mock_sm_manager_instance.state_machines = [self.mock_sm_instance]
        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "wrong-owner"}
        response = self.client.delete('/simulation/0/state-machines/Control1', headers=hdr)
        self.assertRaises(NRPServicesWrongUserException)
        self.assertEqual(response.status_code, 401)

if __name__ == '__main__':
        unittest.main()
