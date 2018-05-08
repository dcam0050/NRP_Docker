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
Unit tests for the service that retrieves structured transfer functions
"""

__author__ = 'Georg Hinkel'

import unittest
import json
from mock import MagicMock
from hbp_nrp_backend.simulation_control import simulations, Simulation
from hbp_nrp_backend.rest_server.tests import RestTest


class MockObject(object):
    def __init__(self, dict):
        self.__dict__ = dict


class TestSimulationTransferFunctions(RestTest):

    def setUp(self):
        del simulations[:]
        simulations.append(Simulation(0, 'experiment_0', None, 'default-owner', 'local', 'created'))
        simulations.append(Simulation(1, 'experiment_1', None, 'untrusted-owner', 'local', 'created'))
        self.sim = simulations[0]
        self.sim.cle = MagicMock()

        self.object_tfs = [
            MockObject({
                "devices": [
                    MockObject({
                        'name': 'foo',
                        'type': 'footype',
                        'neurons': MockObject({
                          'name': 'foopop',
                            'type': 'foopoptype',
                            'ids': [0,8,15],
                            'start': 0,
                            'stop': 8,
                            'step': 15
                        })
                    })
                ],
                'topics': [
                    MockObject({
                        'name': 'bar',
                        'topic': 'bartopic',
                        'type': 'bartype',
                        'publishing': 'barpub'
                    })
                ],
                'variables': [
                    MockObject({
                        'name': 'varname',
                        'type': 'vartype',
                        'initial_value': 'varvalue'
                    })
                ],
                'name': 'tf',
                'type': 'tf_type',
                'code': 'pass'
            })
        ]

        self.dict_tf = {
                    u'name': u'tf',
                    u'type': u'tf_type',
                    u'code': u'pass',
                    u'devices': [{
                        u'name': u'foo',
                        u'type': u'footype',
                        u'neurons': {
                            u'name': u'foopop',
                            u'type': u'foopoptype',
                            u'ids': [
                                {u'id': 0},
                                {u'id': 8},
                                {u'id': 15}
                            ],
                            u'start': 0,
                            u'stop': 8,
                            u'step': 15
                        }
                    }],
                    u'topics': [{
                        u'name': u'bar',
                        u'topic': u'bartopic',
                        u'type': u'bartype',
                        u'publishing': u'barpub'
                    }],
                    u'variables': [{
                        u'name': u'varname',
                        u'type': u'vartype',
                        u'initial_value': u'varvalue'
                    }]
                }

    def test_structured_tf_get(self):
        self.sim.cle.get_structured_transfer_functions.return_value = self.object_tfs
        response = self.client.get('/simulation/0/simulation-structured-transfer-functions')
        self.assertEqual(response.status_code, 200)
        self.sim.cle.get_structured_transfer_functions.assert_called_once_with()
        json_tfs = json.loads(response.data)
        self.maxDiff = None
        self.assertDictEqual(json_tfs, {
            u'transferFunctions': [
                self.dict_tf
            ]
        })

    def test_structured_tf_put(self):
        self.sim.cle.set_structured_transfer_function.return_value = ""
        response = self.client.put('/simulation/0/simulation-structured-transfer-functions',
                                   data=json.dumps(self.dict_tf))
        self.assertEqual(response.status_code, 200)
        self.sim.cle.set_structured_transfer_function.assert_called_once()


if __name__ == '__main__':
    unittest.main()
