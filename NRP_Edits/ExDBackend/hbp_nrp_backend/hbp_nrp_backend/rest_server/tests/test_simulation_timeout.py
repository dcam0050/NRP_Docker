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
Tests the simulation state service
"""

from flask import Response
from mock import MagicMock
from hbp_nrp_backend.rest_server.tests import RestTest
from hbp_nrp_backend.rest_server.__SimulationTimeout import _get_simulation_or_abort
from hbp_nrp_backend.simulation_control import simulations, Simulation
from hbp_nrp_backend.rest_server.__SimulationTimeout import SIMULATION_TIMEOUT_EXTEND
import json


class TestSimulationTimeout(RestTest):

    def setUp(self):
        del simulations[:]
        simulations.append(Simulation(0, 'experiment_0', None, 'default-owner', 'local', 'created'))
        self.sim = simulations[0]
        self.sim.cle = MagicMock()
        self.sim.cle.extend_simulation_timeout = MagicMock(return_value=True)

    def tearDown(self):
        del simulations[:]

    def test_extend_timeout_sucessful(self):
        initial_kill_timeout = self.sim.kill_datetime
        response = self.client.post('/simulation/0/extend_timeout')
        assert(isinstance(response, Response))
        self.assertEqual(response.status_code, 200)
        delta_seconds = (self.sim.kill_datetime-initial_kill_timeout).seconds
        self.assertEqual(delta_seconds, SIMULATION_TIMEOUT_EXTEND*60)

    def test_extend_timeout_sim_not_found(self):
        response = self.client.post('/simulation/1/extend_timeout')
        assert(isinstance(response, Response))
        self.assertEqual(response.status_code, 404)

    def test_extend_timeout_refused(self):
        initial_kill_timeout = self.sim.kill_datetime
        self.sim.cle.extend_simulation_timeout = MagicMock(return_value=False)
        response = self.client.post('/simulation/0/extend_timeout', data=json.dumps({"sim_id": 0}))
        assert(isinstance(response, Response))
        self.assertEqual(response.status_code, 402)
        self.assertEqual(self.sim.kill_datetime, initial_kill_timeout)
