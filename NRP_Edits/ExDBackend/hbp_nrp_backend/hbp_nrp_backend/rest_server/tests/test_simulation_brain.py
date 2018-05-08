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

__author__ = 'Bernd Eckstein'

import unittest
import json

from mock import MagicMock
from hbp_nrp_backend.rest_server import NRPServicesClientErrorException,\
    NRPServicesTransferFunctionException
from hbp_nrp_backend.simulation_control import simulations, Simulation
from hbp_nrp_backend.rest_server.tests import RestTest
from collections import defaultdict
from cle_ros_msgs import srv


class DefaultDotDict(defaultdict):
    """
    Creates a Dictionary that can be accessed via dot-Syntax
    e.g. data['more_data'] -> data.more_data
    Overkill but i like it to create my mock return value :)

    Credits go to Zaar Hai
    http://tech.zarmory.com/2013/08/python-putting-dot-in-dict.html
    """
    def __init__(self, *args, **kwargs):
        super(DefaultDotDict, self).__init__(DefaultDotDict)
        if args or kwargs:
            dict.__init__(self, *args, **kwargs)

    def __getattr__(self, attr):
        if attr.startswith('_'):
            raise AttributeError  # Magic only works for key that do not start with "_"
        val = self.__getitem__(attr)
        if isinstance(val, dict) and not isinstance(val, DefaultDotDict):
            val = DefaultDotDict(val)
        self[attr] = val
        return val

    def __setattr__(self, attr, val):
        return self.__setitem__(attr, val)

    def __delattr__(self, attr):
        return self.__delitem__(attr)

    def __deepcopy__(self, memo):
        return DefaultDotDict([(copy.deepcopy(k, memo), copy.deepcopy(v, memo))
                               for k, v in self.items()])


# Test Data
brain_populations_json = """
{
   "population_1": [1],
   "population_2": [2],
   "slice_1": {
     "from": 1,
     "to": 10,
     "step": 1
   },
   "slice_2": {
     "from": 1,
     "to": 10
   },
   "list_1": [1, 2, 3]
}
"""
brain_data = DefaultDotDict(
    brain_data="Data",
    brain_type="py",
    data_type="text",
    brain_populations=brain_populations_json
)
send_data = {
    'data': "Data",
    'brain_type': "py",
    'data_type': "text",
    'additional_populations': brain_populations_json,
    'change_population': srv.SetBrainRequest.DO_RENAME_POPULATION
}
get_return_data = {
    'data': "Data",
    'brain_type': "py",
    'data_type': "text",
    'additional_populations': json.loads(brain_populations_json)
}
set_ret_ok = DefaultDotDict(error_message="")
set_ret_error = DefaultDotDict(error_message="Crash boom bang", error_line=10, error_column=5)
set_ret_popl_change_handle = DefaultDotDict(error_message="change population name", error_line=0, error_column=0, handle_population_change = 1)

class TestSimulationBrain(RestTest):

    def setUp(self):
        del simulations[:]
        simulations.append(Simulation(0, 'experiment_0', None,
                                      'default-owner', 'local', 'created'))
        simulations.append(Simulation(1, 'experiment_1', None,
                                      'untrusted-owner', 'local', 'created'))

        self.sim = simulations[0]
        self.sim.cle = MagicMock()
        self.sim.cle.get_simulation_brain = MagicMock(return_value=brain_data)
        self.sim.cle.set_simulation_brain = MagicMock(return_value=set_ret_ok)

    def test_simulation_brain_get(self):
        response = self.client.get('/simulation/0/brain')
        self.assertEqual(self.sim.cle.get_simulation_brain.call_count, 1)
        self.assertEqual(json.loads(response.data.strip()), get_return_data)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/simulation/4/brain')
        self.assertEqual(response.status_code, 404)

    def test_simulation_brain_put(self):
        response = self.client.put('/simulation/0/brain', data=json.dumps(send_data))
        self.assertEqual(self.sim.cle.set_simulation_brain.call_count, 1)
        self.sim.cle.set_simulation_brain.assert_called_with("py", "Data", "text", json.dumps(brain_populations_json), 1)
        self.assertEqual(response.status_code, 200)

        self.sim.cle.set_simulation_brain = MagicMock(return_value=set_ret_error)
        response = self.client.put('/simulation/0/brain', data=json.dumps(send_data))
        self.assertEqual(response.status_code, 400)

        response = self.client.put('/simulation/4/brain')
        self.assertEqual(response.status_code, 404)

        response = self.client.put('/simulation/1/brain')
        self.assertEqual(response.status_code, 401, "Operation only allowed by simulation owner")

    def test_population_rename_feature(self):
        new_brain_populations_json = """
        {
           "population_1": [1],
           "population_2": [2],
           "slice_1": {
             "from": 1,
             "to": 10,
             "step": 1
           },
           "slice_2": {
             "from": 1,
             "to": 10
           },
           "list_X": [1, 2, 3]
        }
        """

        request = {
            'data': "Data",
            'brain_type': "py",
            'data_type': "text",
            'additional_populations': brain_populations_json,
            'change_population': 0
        }
        response = self.client.put('/simulation/0/brain', data=json.dumps(request))
        request['additional_populations'] = new_brain_populations_json
        self.sim.cle.set_simulation_brain = MagicMock(return_value=set_ret_popl_change_handle)
        response = self.client.put('/simulation/0/brain', data=json.dumps(request))
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
