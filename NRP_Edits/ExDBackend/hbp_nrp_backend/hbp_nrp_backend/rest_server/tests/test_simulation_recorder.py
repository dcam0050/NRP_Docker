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
Unit tests for the simulation recorder REST interface
"""
from mock import patch, MagicMock
from hbp_nrp_backend.simulation_control import simulations, Simulation
from hbp_nrp_backend.rest_server.tests import RestTest

from hbp_nrp_backend.cle_interface.ROSCLEClient import ROSCLEClientException

from cle_ros_msgs import srv


class TestSimulationRecorder(RestTest):
    def setUp(self):

        del simulations[:]
        simulations.append(Simulation(0, 'experiment1', None, 'default-owner', 'created'))
        simulations.append(Simulation(1, 'experiment2', None, 'other-owner', 'created'))

        for s in simulations:
            s.cle = MagicMock()
            s.cle.command_simulation_recorder = MagicMock(return_value=srv.SimulationRecorderResponse())

    def test_get(self):

        simulations[0].cle.command_simulation_recorder.return_value.value = True
        simulations[0].cle.command_simulation_recorder.return_value.message = ""
        simulations[0].cle.command_simulation_recorder.side_effect = None

        response = self.client.get('/simulation/0/recorder/is-recording')
        self.assertEqual(200, response.status_code)
        self.assertEqual('"True"', response.data.strip())

    def test_get_failure(self):

        simulations[0].cle.command_simulation_recorder.side_effect = None

        # invalid simulation id
        response = self.client.get('/simulation/123456/recorder/foo')
        self.assertEqual(404, response.status_code)
        self.assertEqual('The command you requested was not found on this server', response.data.strip())

        # invalid command / request path
        response = self.client.get('/simulation/0/recorder/foo')
        self.assertEqual(404, response.status_code)
        self.assertEqual('{"data": null, "message": "Invalid recorder query: foo", "type": "Client error"}', response.data.strip())

        # raise an exception for bad service call
        simulations[0].cle.command_simulation_recorder.side_effect = ROSCLEClientException('foo')
        response = self.client.get('/simulation/0/recorder/is-recording')
        self.assertEqual(500, response.status_code)
        self.assertEqual('{"data": null, "message": "foo", "type": "CLE error"}', response.data.strip())

    def test_post(self):

        # valid post successful
        simulations[0].cle.command_simulation_recorder.return_value.value = True
        simulations[0].cle.command_simulation_recorder.return_value.message = "success"
        simulations[0].cle.command_simulation_recorder.side_effect = None

        for command in ['start', 'stop', 'cancel', 'reset']:
            response = self.client.post('/simulation/0/recorder/%s' % command)
            self.assertEqual(200, response.status_code)
            self.assertEqual('"success"', response.data.strip())

        # call returns an error message
        simulations[0].cle.command_simulation_recorder.return_value.value = False
        simulations[0].cle.command_simulation_recorder.return_value.message = "error"
        simulations[0].cle.command_simulation_recorder.side_effect = None

        response = self.client.post('/simulation/0/recorder/start')
        self.assertEqual(400, response.status_code)
        self.assertEqual('{"data": null, "message": "error", "type": "Client error"}', response.data.strip())

    def test_post_failure(self):

        simulations[0].cle.command_simulation_recorder.side_effect = None

        # invalid simulation id
        response = self.client.post('/simulation/123456/recorder/foo')
        self.assertEqual(404, response.status_code)
        self.assertEqual('The command you requested was not found on this server', response.data.strip())

        # incorrect owner
        response = self.client.post('/simulation/1/recorder/start')
        self.assertEqual(401, response.status_code)
        self.assertEqual('{"data": null, "message": "You need to be the simulation owner to apply your changes.                If you are the owner, try leaving and then re-joining the experiment.", "type": "Wrong user"}', response.data.strip())

        # invalid command / request path
        response = self.client.post('/simulation/0/recorder/foo')
        self.assertEqual(404, response.status_code)
        self.assertEqual('{"data": null, "message": "Invalid recorder command: foo", "type": "Client error"}', response.data.strip())

        # raise an exception for bad service call
        simulations[0].cle.command_simulation_recorder.side_effect = ROSCLEClientException('foo')
        response = self.client.post('/simulation/0/recorder/start')
        self.assertEqual(500, response.status_code)
        self.assertEqual('{"data": null, "message": "foo", "type": "CLE error"}', response.data.strip())

