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
This module contains the abstract base class of a simulation assembly
"""

import os
import logging
from hbp_nrp_cleserver.server.ROSNotificator import ROSNotificator
from hbp_nrp_cleserver.bibi_config.notificator import Notificator

logger = logging.getLogger(__name__)


class SimulationAssembly(object):
    """
    This class is the abstract base class of a simulation assembly
    """

    def __init__(self, sim_id, exc, bibi, par):
        """
        Creates a new simulation assembly

        :param sim_id: The simulation ID
        :param exc: The experiment configuration
        :param bibi: The BIBI configuration
        :param token: the request token in case we want to use the storage
        :param ctx_id: the ctx_id of collab based simulations
        """
        self.__sim_id = sim_id
        self.__exc = exc
        self.__bibi = bibi
        self.__token = par.get('token')
        self.__ctx_id = par.get('ctx_id')

        self._abort_initialization = None
        self.ros_notificator = None

    @property
    def bibi(self):
        """
        Gets the BIBI configuration for this simulation assembly
        """
        return self.__bibi

    @property
    def exc(self):
        """
        Gets the experiment configuration for this simulation assembly
        """
        return self.__exc

    @property
    def token(self):
        """
        Returns the token assigned to this simulation
        """
        return self.__token

    @property
    def ctx_id(self):
        """
        Returns the context id assigned to this simulation
        """
        return self.__ctx_id

    @property
    def sim_id(self):
        """
        Gets the simulation id
        """
        return self.__sim_id

    def initialize(self, environment, except_hook):
        """
        Initializes the simulation
        :param environment: The environment that should be simulated
        :param except_hook: A method that should be called when there is a critical error
        """
        # Change working directory to experiment directory
        logger.info("Path is " + self.__exc.path)
        os.chdir(self.__exc.dir)

        # Create backend->frontend/client ROS notificator
        logger.info("Setting up backend Notificator")
        self.ros_notificator = ROSNotificator()
        Notificator.register_notification_function(
            lambda subtask, update_progress:
            self.ros_notificator.update_task(subtask, update_progress, True)
        )

        # Number of subtasks is not used in frontend notificator logic
        self.ros_notificator.start_task("Neurorobotics Platform",
                                        "Neurorobotics Platform",
                                        number_of_subtasks=1,
                                        block_ui=True)
        self._notify("Starting Neurorobotics Platform")

        self._initialize(environment, except_hook)

        # Loading is completed.
        self._notify("Finished")
        self.ros_notificator.finish_task()

        logger.info("CLELauncher Finished.")

    def _initialize(self, environment, except_hook):  # pragma: no cover
        """
        Internally initialize the simulation
        :param environment: The environment that should be simulated
        :param except_hook: A method that should be called when there is a critical error
        """
        raise NotImplementedError("This method must be overridden in an implementation")

    def _notify(self, message):
        """
        Checks whether the simulation should abort immediately
        """
        if self._abort_initialization is not None:
            raise Exception("The simulation must abort due to: " +
                            self._abort_initialization)
        Notificator.notify(message, True)

    def run(self):  # pragma: no cover
        """
        Runs the simulation
        """
        raise NotImplementedError("This method must be overridden in an implementation")

    def shutdown(self):  # pragma: no cover
        """
        Shuts down the simulation
        """
        raise NotImplementedError("This method must be overridden in an implementation")
