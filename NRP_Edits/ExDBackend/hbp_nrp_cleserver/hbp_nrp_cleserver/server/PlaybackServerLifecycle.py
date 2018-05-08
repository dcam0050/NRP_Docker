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
This module contains the playback server implementation of the simulation playback lifecycle
"""

from hbp_nrp_commons.simulation_lifecycle import SimulationLifecycle
from hbp_nrp_cleserver.server import TOPIC_LIFECYCLE
import threading
import logging
import sys


logger = logging.getLogger(__name__)
# Sometimes previous handlers are cleared, make sure they are set
stdout_hdlr = logging.StreamHandler(sys.stdout)
stderr_hdlr = logging.StreamHandler(sys.stderr)
log_format = '%(asctime)s [%(threadName)-12.12s] [%(name)-12.12s] [%(levelname)s]  %(message)s'
stdout_hdlr.setFormatter(logging.Formatter(log_format))
stderr_hdlr.setFormatter(logging.Formatter(log_format))
logger.handlers.append(stdout_hdlr)
logger.handlers.append(stderr_hdlr)


class PlaybackServerLifecycle(SimulationLifecycle):
    """
    Implements the playback server lifecycle of a simulation playback lifecycle
    """

    def __init__(self, sim_id, server, except_hook=None):
        self.stopped = lambda: None
        super(PlaybackServerLifecycle, self).__init__(TOPIC_LIFECYCLE(sim_id))
        self.__server = server
        self.__except_hook = except_hook or logger.exception
        self.__done_event = threading.Event()

    @property
    def done_event(self):
        """
        Gets the event that represents when the simulation is done

        :return: An event that will be set as soon as the lifecycle is done
        """
        return self.__done_event

    def shutdown(self, shutdown_event):
        """
        Shuts down this instance of the simulation lifecycle

        :param shutdown_event: The event that caused the shutdown
        """
        self.__done_event.set()
        super(PlaybackServerLifecycle, self).shutdown(shutdown_event)

    def start(self, state_change):
        """
        Starts the simulation playback

        :param state_change: The state change that caused the playback to start
        """
        self.__server.process_lifecycle_command('start')

    def stop(self, state_change):
        """
        Stops the simulation playback and releases required resources

        :param state_change: The state change that caused the playback to stop
        """
        self.__server.process_lifecycle_command('stop')

    def pause(self, state_change):
        """
        Pauses the simulation playback

        :param state_change: The state change that caused the pause request
        """
        self.__server.process_lifecycle_command('pause')

    def fail(self, state_change):
        """
        Reacts on failures in the simulation playback

        :param state_change: The state change according to the failure
        """
        self.__server.publish_state_update()

    def initialize(self, state_change):
        """
        Implements parent interface, does nothing

        :param state_change: The state change that caused the playback to initialize
        """
        pass

    def reset(self, state_change):
        """
        Implements parent interface, handles by PlaybackServer ROS service call

        :param state_change:
        :return:
        """
        pass
