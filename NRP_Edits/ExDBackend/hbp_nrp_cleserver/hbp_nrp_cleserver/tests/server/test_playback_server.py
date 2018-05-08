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
PlaybackServer unit test
"""

from hbp_nrp_cleserver.server.PlaybackServer import PlaybackServer
from mock import patch, MagicMock, Mock, PropertyMock, mock_open
import unittest

from cle_ros_msgs import srv
from std_srvs.srv import TriggerResponse


class TestPlaybackServer(unittest.TestCase):

    @patch("hbp_nrp_cleserver.server.PlaybackServer.PlaybackServerLifecycle")
    @patch("hbp_nrp_cleserver.server.SimulationServer.Timer")
    def setUp(self, mock_timer, mock_lifecycle):
        unittest.TestCase.setUp(self)

        # Mock the respective objects and make them available for all tests.
        # Also have a look at the following link:
        # https://docs.python.org/3.5/library/unittest.mock-examples.html#applying-the-same-patch-to-every-test-method
        rospy_patcher = patch('hbp_nrp_cleserver.server.PlaybackServer.rospy')
        base_rospy_patcher = patch('hbp_nrp_cleserver.server.SimulationServer.rospy')

        # Ensure that the patchers are cleaned up correctly even in exceptional cases
        # e.g. when an exception was thrown.
        self.addCleanup(rospy_patcher.stop)
        self.addCleanup(base_rospy_patcher.stop)

        self.__mocked_rospy = rospy_patcher.start()
        self.__mocked_base_rospy = base_rospy_patcher.start()

        self.__mocked_notificator = Mock()
        self.__mocked_notificator.task_notifier = mock_open()

        self.__playback_server = PlaybackServer(0, None, None, self.__mocked_notificator)
        self.assertEqual(mock_timer.Timer.call_count, 1)
        self.__playback_server.playback_path = 'foo'
        self.__playback_server.prepare_simulation(None)
        self.assertEqual(mock_lifecycle.call_count, 1)
        self.assertEqual(2, self.__mocked_base_rospy.Service.call_count)
        self.assertEqual(5, self.__mocked_rospy.ServiceProxy.call_count)
        self.assertEqual(1, self.__mocked_rospy.Subscriber.call_count)
        self.__playback_server._PlaybackServer__service_configure.assert_called_once_with('foo')

    def test_lifecycle_command_failure(self):

        # uninitialized rospy serviceproxy
        old = self.__playback_server._PlaybackServer__service_start
        self.__playback_server._PlaybackServer__service_start = None
        self.assertRaises(Exception, self.__playback_server.process_lifecycle_command, 'foo')

        # invalid command
        self.__playback_server._PlaybackServer__service_start = old
        self.assertRaises(ValueError, self.__playback_server.process_lifecycle_command, 'foo')

        # command failure
        self.__playback_server._PlaybackServer__service_start = Mock(return_value=TriggerResponse(success=False, message='foo'))
        self.assertRaises(Exception, self.__playback_server.process_lifecycle_command, 'start')

        # reset all of the mocks
        self.__playback_server._PlaybackServer__service_start = old
        self.__playback_server._PlaybackServer__service_start.reset_mock()
        self.__playback_server._PlaybackServer__service_stop.reset_mock()
        self.__playback_server._PlaybackServer__service_pause.reset_mock()

    def test_start(self):

        self.__playback_server._PlaybackServer__service_start.reset_mock()
        self.__playback_server.process_lifecycle_command('start')
        self.__playback_server._PlaybackServer__service_start.assert_called_once_with()

    def test_pause(self):

        self.__playback_server._PlaybackServer__service_pause.reset_mock()
        self.__playback_server.process_lifecycle_command('pause')
        self.__playback_server._PlaybackServer__service_pause.assert_called_once_with()

    def test_stop(self):

        self.__playback_server._PlaybackServer__service_stop.reset_mock()
        self.__playback_server.process_lifecycle_command('stop')
        self.__playback_server._PlaybackServer__service_stop.assert_called_once_with()

    def test_reset(self):

        self.__playback_server._PlaybackServer__service_reset.reset_mock()
        self.__playback_server.reset_simulation(None)
        self.assertEqual(self.__playback_server._PlaybackServer__sim_clock, 0)
        self.__playback_server._PlaybackServer__service_reset.assert_called_once_with('foo')

    def test_reset_not_configured(self):

        # simulate configure not being called
        self.__playback_server._PlaybackServer__playback_path = None
        res, _ = self.__playback_server.reset_simulation(None)
        self.assertEqual(False, res)
        self.__playback_server._PlaybackServer__playback_path = 'foo'

    def test_shutdown(self):
    
        ps = self.__playback_server
        ps.shutdown()

        # assert all of the shutdowns were called
        self.assertIsNone(ps._PlaybackServer__sim_clock_subscriber)
        ps._SimulationServer__service_reset.shutdown.assert_any_call()
        ps._SimulationServer__service_extend_timeout.shutdown.assert_any_call()

if __name__ == '__main__':
    unittest.main()
