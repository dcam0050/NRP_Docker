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
Test for ROS wrapper for Gazebo simulation recorder plugin.
"""

from mock import Mock, call
import unittest

from hbp_nrp_cleserver.server.GazeboSimulationRecorder import GazeboSimulationRecorder

from cle_ros_msgs import srv
from std_srvs.srv import Trigger

import rospy


class TestGazeboSimulationRecorder(unittest.TestCase):

    def setUp(self):
        rospy.Service = Mock()
        rospy.ServiceProxy = Mock()
        rospy.Service.shutdown = Mock()

    def test_init(self):

        # reset mocks to reset call counts
        rospy.Service.reset_mock()
        rospy.ServiceProxy.reset_mock()

        # ensure the constructor is calling our mocks properly
        recorder = GazeboSimulationRecorder(0)

        rospy.Service.assert_called_with('/ros_cle_simulation/0/simulation_recorder',
                                         srv.SimulationRecorder, 
                                         recorder._GazeboSimulationRecorder__command)

        rospy.ServiceProxy.assert_has_calls([call('/gazebo/recording/start', Trigger),
                                             call('/gazebo/recording/stop', Trigger),
                                             call('/gazebo/recording/cancel', Trigger),
                                             call('/gazebo/recording/cleanup', Trigger),
                                             call('/gazebo/recording/get_recording', Trigger)])

    def test_shutdown(self):

        # reset mocks to reset call counts
        rospy.Service.reset_mock()
        rospy.ServiceProxy.reset_mock()

        recorder = GazeboSimulationRecorder(0)
        recorder.shutdown()
        
        # ensure the shutdowns are properly called
        recorder._GazeboSimulationRecorder__service_simulation_recorder.shutdown.assert_called_once()
        recorder._GazeboSimulationRecorder__recorder_cleanup.assert_called_once()

    def test_command(self):

        # reset mocks to reset call counts
        rospy.Service.reset_mock()
        rospy.ServiceProxy.reset_mock()

        recorder = GazeboSimulationRecorder(0)
        
        # valid calls
        recorder._GazeboSimulationRecorder__command(srv.SimulationRecorderRequest(srv.SimulationRecorderRequest.STATE))
        recorder._GazeboSimulationRecorder__recorder_state.assert_called_once()
        recorder._GazeboSimulationRecorder__command(srv.SimulationRecorderRequest(srv.SimulationRecorderRequest.START))
        recorder._GazeboSimulationRecorder__recorder_start.assert_called_once()
        recorder._GazeboSimulationRecorder__command(srv.SimulationRecorderRequest(srv.SimulationRecorderRequest.STOP))
        recorder._GazeboSimulationRecorder__recorder_stop.assert_called_once()
        recorder._GazeboSimulationRecorder__command(srv.SimulationRecorderRequest(srv.SimulationRecorderRequest.CANCEL))
        recorder._GazeboSimulationRecorder__recorder_cancel.assert_called_once()
        recorder._GazeboSimulationRecorder__command(srv.SimulationRecorderRequest(srv.SimulationRecorderRequest.RESET))
        recorder._GazeboSimulationRecorder__recorder_cleanup.assert_called_once()

        # invalid call
        resp = recorder._GazeboSimulationRecorder__command(srv.SimulationRecorderRequest('foo'))
        self.assertEqual(False, resp.value)
        self.assertEqual('Invalid Simulation Recorder command: foo', resp.message)

