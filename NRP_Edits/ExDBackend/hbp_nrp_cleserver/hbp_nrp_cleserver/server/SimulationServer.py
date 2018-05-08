# pylint: disable=too-many-lines
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
Playback ROS wrapper overriding the ROSCLEServer implementation for playback
"""

from hbp_nrp_cleserver.bibi_config.notificator import NotificatorHandler

import rospy
from cle_ros_msgs import srv
from hbp_nrp_watchdog import Timer
from hbp_nrp_cleserver.server import ROS_CLE_NODE_NAME, SERVICE_SIM_RESET_ID, \
    SERVICE_SIM_EXTEND_TIMEOUT_ID

import json
import time
import dateutil.parser as datetime_parser
import datetime
import logging

logger = logging.getLogger(__name__)

# We use the logger hbp_nrp_cle.user_notifications in the CLE to log
# information that is useful to know for the user.
# In here, we forward any info message sent to this logger to the notificator
gazebo_logger = logging.getLogger('hbp_nrp_cle.user_notifications')
gazebo_logger.setLevel(logging.INFO)
notificator_handler = NotificatorHandler()


class SimulationServer(object):
    """
    Playback ROS server overriding the ROSCLEServer implementation for playback
    """
    STATUS_UPDATE_INTERVAL = 1.0

    def __init__(self, sim_id, timeout, gzserver, notificator):
        """
        Create the playback server

        :param sim_id: The simulation id
        :param timeout: The datetime when the simulation runs into a timeout
        :param gzserver: Gazebo simulator launch/control instance
        :param notificator: ROS state/error notificator interface
        """
        rospy.init_node(ROS_CLE_NODE_NAME, anonymous=True)

        self.__lifecycle = None

        self.__timer = Timer.Timer(SimulationServer.STATUS_UPDATE_INTERVAL,
                                   self.publish_state_update)
        self.__timeout = timeout
        self.__gzserver = gzserver
        self._notificator = notificator

        self.__simulation_id = sim_id

        # services to extend timeouts
        self.__service_extend_timeout = None
        self.__service_reset = None

    @property
    def simulation_id(self):
        """
        Gets the simulation id that is serviced
        """
        return self.__simulation_id

    @property
    def lifecycle(self):
        """
        Gets the lifecycle instance representing the current ROSCLEServer
        """
        return self.__lifecycle

    def _create_lifecycle(self, except_hook):  # pragma: no cover
        """
        Creates the lifecycle for the current simulation
        :param except_hook: An exception handler
        :return: The created lifecycle
        """
        raise NotImplementedError("This method must be overridden in derived classes")

    def prepare_simulation(self, except_hook=None):
        """
        The CLE will be initialized within this method and ROS services for
        starting, pausing, stopping and resetting are setup here.

        :param except_hook: A handler method for critical exceptions
        """
        self.__lifecycle = self._create_lifecycle(except_hook)

        logger.info("Registering ROS Service handlers")

        self.__service_reset = rospy.Service(
            SERVICE_SIM_RESET_ID(self.__simulation_id), srv.ResetSimulation,
            self.reset_simulation
        )

        self.__service_extend_timeout = rospy.Service(
            SERVICE_SIM_EXTEND_TIMEOUT_ID(self.__simulation_id), srv.ExtendTimeout,
            self.__extend_timeout
        )
        self.__timer.start()

    def __extend_timeout(self, request):
        """
        Extend the simulation timeout

        :param request: The new timeout
        :return: whether it could extend the timeout
        """
        new_timeout = datetime_parser.parse(request.timeout)

        if self.__gzserver is not None and not self.__gzserver.try_extend(new_timeout):
            return False

        self.__timeout = new_timeout

        return True

    def _create_state_message(self):
        """
        Creates a status message
        :return: A dictionary with status information
        """
        raise NotImplementedError("This method must be overridden in derived classes")

    def publish_state_update(self):
        """
        Publish the playback state and the remaining timeout
        """
        try:
            if self.__lifecycle is None:
                logger.warn("Trying to publish state even though no simulation is active")
                return
            message = self._create_state_message()
            message['state'] = self.__lifecycle.state
            message['timeout'] = self.__get_remaining()
            logger.debug(json.dumps(message))
            self._notificator.publish_state(json.dumps(message))
        # pylint: disable=broad-except
        except Exception as e:
            logger.exception(e)

    def __get_remaining(self):
        """
        Get the remaining time of the simulation
        """
        if self.__timeout is not None:
            # pylint: disable=E1103
            # false positive
            remaining = (self.__timeout - datetime.datetime.now(self.__timeout.tzinfo)) \
                .total_seconds()
            # pylint: enable=E1103
            if remaining < 0:
                self.__lifecycle.stopped()
            return max(0, int(remaining))
        else:
            return 0

    def shutdown(self):
        """
        Shutdown the playback
        """
        # try to shutdown the service proxies, ignore failures and continue shutdown
        # pylint: disable=bare-except
        try:
            self.__service_extend_timeout.shutdown()
            self.__service_reset.shutdown()
        except:
            pass

        # items initialized in the constructor
        self.__lifecycle = None
        self.__timer.cancel_all()

    def reset_simulation(self, request):
        """
        Reset the playback

        :param request: the ROS service request message (cle_ros_msgs.srv.ResetSimulation).
        """
        raise NotImplementedError("This method must be overridden in derived classes")

    def run(self):
        """
        This method blocks the caller until the simulation is finished
        """
        self.__lifecycle.done_event.wait()

        self.publish_state_update()
        time.sleep(1.0)
        logger.info("Finished main loop")
