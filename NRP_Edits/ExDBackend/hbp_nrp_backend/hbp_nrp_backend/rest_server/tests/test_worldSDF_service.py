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
Unit tests for the simulation setup
"""
__author__ = 'UgoAlbanese'


import rospy
import mock
import unittest
import json
from hbp_nrp_backend.rest_server.tests import RestTest


class MockServiceResponse:
    def __init__(self):
        pass

    sdf_dump = '<sdf>Dummy</sdf>'


class TestWorldSDFService(RestTest):

    @mock.patch('hbp_nrp_backend.rest_server.__WorldSDFService.rospy')
    def test_worldSDF_service_get(self, mckd_rospy):
        # setup the mocks
        mckd_rospy.wait_for_service = mock.MagicMock(return_value=None)

        mckd_rospy.ServiceProxy = mock.MagicMock(return_value=MockServiceResponse)

        # call the service
        response = self.client.get('/simulation/sdf_world')

        expected_response_data = json.dumps({'sdf': '<sdf>Dummy</sdf>'})

        # check the response
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data.strip(), expected_response_data)

    @mock.patch('hbp_nrp_backend.rest_server.__WorldSDFService.rospy.wait_for_service')
    def test_worldSDF_service_wait_for_service_fail(self, mckd_wait_for_service):
        mckd_wait_for_service.side_effect = rospy.ROSException('Mocked ROSException')

        # call the service
        response = self.client.get('/simulation/sdf_world')

        # check the status code
        self.assertEqual(response.status_code, 500)

    @mock.patch('hbp_nrp_backend.rest_server.__WorldSDFService.rospy.wait_for_service')
    @mock.patch('hbp_nrp_backend.rest_server.__WorldSDFService.rospy.ServiceProxy')
    def test_worldSDF_service_serviceProxy_fail(self, mckd_ServiceProxy, _):
        mckd_ServiceProxy.return_value = mock.MagicMock(
            side_effect=rospy.ServiceException('Mocked ServiceException'))

        # call the service
        response = self.client.get('/simulation/sdf_world')

        # check the status code
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()
