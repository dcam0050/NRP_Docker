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
This module contains the REST services used to check the
health of the servers (by a nagios compatible system).
"""

import logging
import string
from flask_restful_swagger import swagger
from datetime import datetime, timedelta
from hbp_nrp_backend.simulation_control import simulations
from hbp_nrp_backend.rest_server.RestSyncMiddleware import RestSyncMiddleware
from flask_restful import Resource
from pytz import timezone

# pylint: disable=R0201

logger = logging.getLogger(__name__)


def _get_level(number_of_errors, number_of_simulations):
    """
    Helper function that returns a string containing CRITICAL, WARNING and OK.
    """
    if number_of_errors <= 0:
        return "OK"
    elif number_of_errors <= number_of_simulations / 2:
        return "WARNING"
    else:
        return "CRITICAL"


class Last24HoursErrorCheck(Resource):
    """
    Resource to monitor the number of errors that did happen in the last 24 hours.
    """

    @swagger.operation(
        notes='Get an Inciga2 status (OK, WARNING or ERROR) regarding the number of'
              ' errors that did happen in the last 24 hours',
        responseClass=string.__name__,
        responseMessages=[
            {
                "code": 200,
                "message": "Success"
            }
        ]
    )
    @RestSyncMiddleware.threadsafe
    def get(self):
        """
        Get a nagios status regarding the number of errors that happened in the last 24 hours.
        """
        has_simulation_been_run_in_the_last_24h = lambda simulation: (datetime.now(
                tz=timezone('Europe/Zurich')) - simulation.creation_datetime) < timedelta(1)
        filtered_simulations = filter(has_simulation_been_run_in_the_last_24h, simulations)
        number_of_errors = sum(simulation.errors for simulation in filtered_simulations)
        number_of_simulations = len(filtered_simulations)
        status = {'state': _get_level(number_of_errors, number_of_simulations),
                  'errors': number_of_errors,
                  'simulations': number_of_simulations}
        return status, 200


class TotalErrorCheck(Resource):
    """
    Resource to monitor the number of errors that did happen since the server started.
    """

    @swagger.operation(
        notes='Get an Inciga2 status (OK, WARNING or ERROR) regarding the number of'
              ' errors that did happen since the server has been started',
        responseClass=string.__name__,
        responseMessages=[
            {
                "code": 200,
                "message": "Success"
            }
        ]
    )
    @RestSyncMiddleware.threadsafe
    def get(self):
        """
        Get a nagios status regarding the number of errors that happened since the server started.
        """
        number_of_errors = sum(simulation.errors for simulation in simulations)
        number_of_simulation = len(simulations)
        status = {'state': _get_level(number_of_errors, number_of_simulation),
                  'errors': number_of_errors,
                  'simulations': number_of_simulation}
        return status, 200
