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
This module defines a job that runs in the background and looks for expired simulations
"""

import datetime
import time
from hbp_nrp_backend.simulation_control import simulations, timezone
import logging

__author__ = 'Georg Hinkel'


logger = logging.getLogger(__name__)


def clean_simulations():  # pragma: no cover
    """
    Wakes up every ten minutes and stops expired simulations

    This function is not unit-tested as it contains an endless loop
    """
    while True:
        time.sleep(300)
        remove_old_simulations()


def remove_old_simulations():
    """
    Stops expired simulations
    """
    logger.info("Start cleanup")
    current_time = datetime.datetime.now(timezone)
    for sim in simulations:
        if sim.kill_datetime is not None and sim.kill_datetime < current_time:
            logger.info("Stopping expired simulation " + str(sim.sim_id))
            sim.state = 'stopped'
