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
Unit tests for the simulation neurons rest call
"""

__author__ = 'Bernd Eckstein'

import unittest
import mock
import rospy
import json
from hbp_nrp_backend.rest_server.tests import RestTest

ros_service_object = mock.Mock()
rospy.wait_for_service = mock.Mock(return_value=ros_service_object)
rospy.ServiceProxy = mock.Mock(return_value=ros_service_object)

from hbp_nrp_backend.simulation_control import simulations, Simulation

neurons = {'populations': [
              {
               'name': "Test",
               'neuron_model': "NeuronModel",
               'parameters': [
                  {'parameterName': "string",
                   'value': 0.0}],
               'gids': [0]
              }
            ]
           }

class TestSimulationService(RestTest):

    def setUp(self):
        del simulations[:]
        simulations.append(Simulation(0, 'experiment1', None, 'default-owner', 'created'))
        simulations[0].cle = mock.MagicMock()
        simulations[0].cle.get_populations = mock.MagicMock(return_value=neurons)

    def test_get_neurons_sim_ok(self):
        response = self.client.get('/simulation/0/populations')
        self.assertEqual(200, response.status_code)
        # deserialilze
        neurons = json.loads(response.data)
        self.assertEqual("NeuronModel", neurons['populations'][0]['neuron_model'])

    def test_get_neurons_sim_not_found(self):
        response = self.client.get('/simulation/1/populations')
        self.assertEqual(404, response.status_code)

if __name__ == '__main__':
    unittest.main()
