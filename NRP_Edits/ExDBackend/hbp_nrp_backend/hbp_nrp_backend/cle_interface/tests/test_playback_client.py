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
PlaybackClient unit test
"""

import rospy
from hbp_nrp_backend.cle_interface.ROSCLEState import ROSCLEState
from hbp_nrp_backend.cle_interface import PlaybackClient, \
    SERVICE_SIM_RESET_ID, SERVICE_SIM_EXTEND_TIMEOUT_ID
from mock import patch, MagicMock, Mock
import unittest

from cle_ros_msgs import srv


class TestPlaybackClient(unittest.TestCase):

    LOGGER_NAME = PlaybackClient.__name__
    NUMBER_OF_SERVICE_PROXIES = 2

    def setUp(self):
        patcher = patch('rospy.ServiceProxy')
        self.addCleanup(patcher.stop)
        self.serviceProxyMock = patcher.start()
        self.serviceProxyMocks = [MagicMock() for _ in range(self.NUMBER_OF_SERVICE_PROXIES)]
        self.serviceProxyMock.side_effect = self.serviceProxyMocks

    @patch('hbp_nrp_backend.cle_interface.PlaybackClient.ROSCLEServiceWrapper')
    def test_roscleclient_constructor(self, service_wrapper_mock):
        client = PlaybackClient.PlaybackClient(0)
        listened_services = [x[0][0] for x in service_wrapper_mock.call_args_list]
        expected_services = [
            SERVICE_SIM_RESET_ID(0), SERVICE_SIM_EXTEND_TIMEOUT_ID(0),
        ]
        self.assertNotIn(False, [x in listened_services for x in expected_services])

if __name__ == '__main__':
    unittest.main()
