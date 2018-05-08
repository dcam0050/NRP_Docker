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
ROS wrapper for Gazebo Simulation Recorder plugin
"""

from hbp_nrp_cleserver.server import SERVICE_SIMULATION_RECORDER

from cle_ros_msgs import srv
from std_srvs.srv import Trigger, TriggerResponse

import rospy
import logging

logger = logging.getLogger(__name__)


class GazeboSimulationRecorder(object):
    """
    A ROS wrapper to convert internal NRP/REST commands into Gazebo simulator recorder
    plugin actions.
    """

    def __init__(self, sim_id):
        """
        Initialize ROS service for handling command requests and service proxies for issuing
        commands to the Gazebo plugin.
        """

        # internal NRP interface from ROS CLE Client / REST interface
        self.__service_simulation_recorder = rospy.Service(
            SERVICE_SIMULATION_RECORDER(sim_id),
            srv.SimulationRecorder,
            self.__command
        )

        # interfaces to the recorder plugin
        self.__recorder_start = rospy.ServiceProxy('/gazebo/recording/start', Trigger)
        self.__recorder_stop = rospy.ServiceProxy('/gazebo/recording/stop', Trigger)
        self.__recorder_cancel = rospy.ServiceProxy('/gazebo/recording/cancel', Trigger)
        self.__recorder_cleanup = rospy.ServiceProxy('/gazebo/recording/cleanup', Trigger)
        self.__recorder_state = rospy.ServiceProxy('/gazebo/recording/get_recording', Trigger)

    def shutdown(self):
        """
        Shutdown the internal NRP ROS handler and issues a cleanup command to the Gazebo plugin.
        """

        # shutdown the internal ROS handler and ignore any further user commands
        logger.info("Shutting down simulation recorder services")
        self.__service_simulation_recorder.shutdown()

        # perform the actual recorder shutdown
        logger.info("Shutting down simulation recorder")
        self.__recorder_cleanup()

    def __command(self, req):
        """
        ROS service callback, handle command requests and route them to the Gazebo plugin.

        :param req The SimulationRecorder request, see definition for details.
        :return SimulationRecorderResponse with success of command and any status/error message.
        """

        # call the appropriate service based on the request type
        if req.request_type == srv.SimulationRecorderRequest.STATE:
            resp = self.__recorder_state()

        elif req.request_type == srv.SimulationRecorderRequest.START:
            resp = self.__recorder_start()

        elif req.request_type == srv.SimulationRecorderRequest.STOP:
            resp = self.__recorder_stop()

        elif req.request_type == srv.SimulationRecorderRequest.CANCEL:
            resp = self.__recorder_cancel()

        # reset the recorder by discarding any saved files
        elif req.request_type == srv.SimulationRecorderRequest.RESET:
            resp = self.__recorder_cleanup()

        # invalid request type, notify caller of failure
        else:
            resp = TriggerResponse()
            resp.success = False
            resp.message = "Invalid Simulation Recorder command: %s" % str(req.request_type)

        # populate our internal response based on the actual call
        return srv.SimulationRecorderResponse(value=resp.success, message=resp.message)
