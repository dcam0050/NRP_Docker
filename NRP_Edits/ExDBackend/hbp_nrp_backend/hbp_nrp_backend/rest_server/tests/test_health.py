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

__author__ = 'Daniel Peppicelli, Luc Guyot'

import unittest
from hbp_nrp_backend.rest_server.tests import RestTest
from datetime import datetime, timedelta
from hbp_nrp_backend.simulation_control import simulations, Simulation
from pytz import timezone


tz = timezone('Europe/Zurich')


class SimulationMock(object):
    errors = Simulation.errors

    def __init__(self):
        self.creation_datetime = datetime.now(tz)


class TestHealth(RestTest):

    def _create_simulation(self, sim_id, experiment_conf, owner, gzserver_host, state):
        m = SimulationMock()
        m.sim_id = sim_id
        m.experiment_conf = experiment_conf
        m.owner = owner
        m.gzserver_host = gzserver_host
        m.state = state
        return m

    def setUp(self):
        del simulations[:]
        simulations.append(self._create_simulation(0, 'experiment_0', 'default-owner', 'local', 'created'))
        simulations.append(self._create_simulation(1, 'experiment_1', 'untrusted-owner', 'local', 'created'))
        simulations.append(self._create_simulation(2, 'experiment_2', 'untrusted-owner', 'local', 'created'))

    def testErrors(self):
        response = self.client.get('/health/errors')
        self.assertEqual(response.status_code, 200)
        self.assertIn("OK", response.data)
        simulations[0].state = 'halted'
        response = self.client.get('/health/errors')
        self.assertEqual(response.status_code, 200)
        self.assertIn("WARNING", response.data)
        simulations[1].state = 'failed'
        response = self.client.get('/health/errors')
        self.assertEqual(response.status_code, 200)
        self.assertIn("CRITICAL", response.data)

    def testErrorsLast24h(self):
        simulations[0].state = 'halted'
        simulations[0].creation_datetime = datetime.now(
            tz=tz) - timedelta(days=1, seconds=2)
        response = self.client.get('/health/errors-last-24h')
        self.assertEqual(response.status_code, 200)
        self.assertIn("OK", response.data)
        simulations[1].state = 'failed'
        simulations[1].creation_datetime = datetime.now(
            tz=tz) - timedelta(hours=23)
        simulations[2].creation_datetime = datetime.now(
            tz=tz) - timedelta(hours=23)
        response = self.client.get('/health/errors-last-24h')
        self.assertEqual(response.status_code, 200)
        self.assertIn("WARNING", response.data)


if __name__ == '__main__':
    unittest.main()
