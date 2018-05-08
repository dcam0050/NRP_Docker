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
Test file for testing hbp_nrp_backend.simulation_control.Simulation
"""

__author__ = 'Stefan Deser'

import unittest
from os import path
from mock import patch, MagicMock, Mock
from hbp_nrp_backend.simulation_control import Simulation
from hbp_nrp_backend.simulation_control import __Simulation as sim_module
from hbp_nrp_excontrol import StateMachineManager as sm_manager_module

class TestSimulation(unittest.TestCase):

    def create_sm_mock(self, sm_id, sim_id, sm_path=None):
        sm = Mock(sm_id=sm_id, sim_id=sim_id, sm_path=sm_path)
        self.__simulation.state_machines.append(sm)
        return sm

    def setUp(self):
        self.patch_state = patch('hbp_nrp_backend.simulation_control.__Simulation.Simulation.state')
        self.mock_state = self.patch_state.start()

        #monkey patch StateMachineManager.create_state_machine
        self.original_sm_manager_create_state_machine = sm_manager_module.StateMachineManager.create_state_machine
        sm_manager_module.StateMachineManager.create_state_machine = self.create_sm_mock

        sim_id = 2
        experiment_conf = 'some_exp_id'
        owner = 'some_owner'
        sim_gzserver_host = 'some_gzserver_host'
        self.__simulation = Simulation(sim_id, experiment_conf, None, owner, sim_gzserver_host)
        sm_path = path.join(path.split(__file__)[0], "sm_mock.py")

        self.assertIsNotNone(self.__simulation.kill_datetime)
        self.assertIsNotNone(self.__simulation.lifecycle)
        self.assertIsNotNone(self.__simulation.creation_datetime)

        self.assertGreater(self.__simulation.kill_datetime, self.__simulation.creation_datetime)

        self.create_sm_mock('SM1', 0, sm_path)
        self.create_sm_mock('SM2', 0)
        self.create_sm_mock('SM3', 0, sm_path)

        with open(sm_path, "r") as sm_file:
            self.valid_sm_code = sm_file.read()

    def tearDown(self):
        self.mock_state = self.patch_state.stop()
        sm_manager_module.StateMachineManager.create_state_machine = self.original_sm_manager_create_state_machine

    def test_set_killtime_early(self):
        self.__simulation.kill_datetime = self.__simulation.creation_datetime
        self.assertEqual(self.__simulation.kill_datetime, self.__simulation.creation_datetime)

    def test_simulation_constructor(self):
        sim_id = 2
        experiment_conf = 'some_exp_id'
        owner = 'some_owner'
        sim_gzserver_host = 'some_gzserver_host'
        self.__simulation = Simulation(sim_id, experiment_conf, None, owner, sim_gzserver_host, 'view')
        self.__simulation = Simulation(
            sim_id, experiment_conf, None, owner,
            sim_gzserver_host, 'view', 'created'
        )
        self.__simulation = Simulation(
            sim_id, experiment_conf, None, owner,
            sim_gzserver_host, 'view', 'paused'
        )

    def test_simulation_get_state_machine_code(self):
        self.assertIsNotNone(self.__simulation.state_machine_manager)
        code = self.__simulation.get_state_machine_code('SM2')
        self.assertFalse(code)
        code = self.__simulation.get_state_machine_code('SM3')
        self.assertEqual(self.valid_sm_code, code)
        response = self.__simulation.get_state_machine_code('non-existing-SM')
        self.assertFalse(response)

    def test_simulation_set_state_machine_code(self):
        another_valid_code = "import smach_ros\n" +\
            "from mock import Mock\n" +\
            "sm = Mock()"
        self.__simulation.state = 'paused'
        response = self.__simulation.set_state_machine_code('SM2', another_valid_code)

        sm2_updated_code = self.__simulation.get_state_machine_code('SM2')
        self.assertEqual(another_valid_code, sm2_updated_code)
        self.__simulation.state_machines[1].request_termination.assert_called_once_with()
        self.__simulation.state_machines[1].wait_termination.assert_called_once_with()

        # The create method is mandatory in the state machine code
        self.__simulation.state_machines[0].initialize_sm = Mock(side_effect=AttributeError)
        self.__simulation.state_machines[0].is_running = False
        invalid_code = "def spwan_state_machine():\n return None"
        self.assertRaises(
            AttributeError,
            self.__simulation.set_state_machine_code, 'SM1',
            invalid_code
        )

        # Creation of a new state machine
        response = self.__simulation.set_state_machine_code('SM4', another_valid_code)
        sm4_updated_code = self.__simulation.get_state_machine_code('SM4')
        self.assertEqual(another_valid_code, sm4_updated_code)

    def test_simulation_delete_state_machine(self):
        self.assertIsNotNone(self.__simulation.state_machine_manager)
        number_of_state_machines = len(self.__simulation.state_machines)
        self.__simulation.delete_state_machine('SM2')
        self.assertEqual(number_of_state_machines - 1, len(self.__simulation.state_machines))
        success, error_message = self.__simulation.delete_state_machine('SM2')
        self.assertFalse(success)
        self.assertTrue(error_message)

        number_of_state_machines = len(self.__simulation.state_machines)
        self.__simulation.delete_state_machine('SM1')
        self.__simulation.delete_state_machine('SM3')
        self.assertEqual(number_of_state_machines - 2, len(self.__simulation.state_machines))

        success, error_message = self.__simulation.delete_state_machine('SM1')
        self.assertFalse(success)
        self.assertTrue(error_message)


if __name__ == '__main__':
    unittest.main()
