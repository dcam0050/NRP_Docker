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
This module contains the classes needed to have all gazebo services running locally.
"""

from hbp_nrp_cleserver.server.GazeboInterface import IGazeboServerInstance, IGazeboBridgeInstance
from hbp_nrp_watchdog.Watchdog import Watchdog
import os
from hbp_nrp_cle import config
import logging

__author__ = 'Alessandro Ambrosano'

# Info messages sent to this logger will be forwarded as notifications
logger = logging.getLogger('hbp_nrp_cle.user_notifications')


class LocalGazeboServerInstance(IGazeboServerInstance):
    """
    Represents a local instance of gzserver.
    """
    def __init__(self):
        super(LocalGazeboServerInstance, self).__init__()
        self.__watchdog = None

    # pylint: disable=unused-argument
    def start(self, ros_master_uri, models_path=None, gzserver_args=None):
        """
        Starts a gzserver instance connected to the local roscore (provided by
        ros_master_uri)

        :param: ros_master_uri The ros master uri where to connect gzserver.
        :param models_path: An additional path where Gazebo may find models
        :param gzserver_args: Additional formatted string of command line arguments to pass to
                              gzserver (e.g. --seed 123456 -e simbody)
        """
        logger.info("Starting gzserver")

        prefix = ""
        if models_path is not None:
            prefix += 'export GAZEBO_MODELS_PATH={0}:$GAZEBO_MODELS_PATH && '.format(models_path)
        if gzserver_args is not None:
            prefix += 'export GZSERVER_ARGS="{0}" && '.format(gzserver_args)

        os.system(prefix + config.config.get('gazebo', 'restart-cmd'))
        self.__ensure_watchdog_running()

    def __ensure_watchdog_running(self):
        """
        Makes sure that a watchdog is running
        """
        if self.__watchdog is None:
            self.__watchdog = Watchdog("gzserver", self._raise_gazebo_died)
            self.__watchdog.start()

    def stop(self):
        """
        Stops the gzserver instance.
        """
        logger.info("Stopping gzserver")
        os.system(config.config.get('gazebo', 'stop-cmd'))
        if self.__watchdog is not None:
            self.__watchdog.stop()
            self.__watchdog = None

    def restart(self, ros_master_uri):
        """
        Restarts the gzserver instance.
        """
        logger.info("Restarting gzserver")
        os.system(config.config.get('gazebo', 'restart-cmd'))
        self.__ensure_watchdog_running()

    # pylint: disable=R0201
    def try_extend(self, new_timeout): # pylint: disable=unused-argument
        """
        Always accept new simulation timeout
        """

        return True

    @property
    def gazebo_master_uri(self):
        """
        Returns a string containing the gazebo master
        URI (like:'http://bbpviz001.cscs.ch:11345')
        """

        result = os.environ.get("GAZEBO_MASTER_URI")
        if (not result):
            # Default gazebo URI (when environment variable is empty)
            result = "http://localhost:11345"
        return result


class LocalGazeboBridgeInstance(IGazeboBridgeInstance):
    """
    Represents a local instance of gzbridge.
    """

    def start(self): # pylint: disable=unused-argument
        """
        Starts the gzbridge instance represented by the object.
        """
        logger.info("Starting Gazebo web client communication adapter")
        os.system(config.config.get('gzbridge', 'start-cmd'))

    def stop(self):
        """
        Stops the gzbridge instance represented by the object.
        """
        logger.info("Stopping Gazebo web client communication adapter")
        os.system(config.config.get('gzbridge', 'stop-cmd'))

    def restart(self): # pylint: disable=unused-argument
        """
        Restarts the gzbridge instance represented by the object.
        """
        logger.info("Restarting Gazebo web client communication adapter")
        os.system(config.config.get('gzbridge', 'restart-cmd'))
