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
This module contains the REST implementation
for extending the simulation timeout
"""

from flask import request
from flask_restful import Resource
from flask_restful_swagger import swagger

from hbp_nrp_backend.rest_server import NRPServicesWrongUserException, ErrorMessages
from hbp_nrp_backend.rest_server.__SimulationControl import _get_simulation_or_abort
from hbp_nrp_backend.__UserAuthentication import UserAuthentication

from hbp_nrp_commons.bibi_functions import docstring_parameter

import datetime
# pylint: disable=R0201


SIMULATION_TIMEOUT_EXTEND = 10  # minutes


class SimulationTimeout(Resource):

    """
    REST service for extending the simulation timeout
    """

    @swagger.operation(
        notes='Extends the simulation timeout',
        parameters=[
            {
                "name": "sim_id",
                "required": True,
                "description": "The ID of the simulation whose timeout shall be extended",
                "paramType": "path",
                "dataType": int.__name__
            }
        ],
        responseMessages=[
            {
                "code": 404,
                "message": ErrorMessages.SIMULATION_NOT_FOUND_404
            },
            {
                "code": 402,
                "message": "Failed to extend the timeout"
            },
            {
                "code": 401,
                "message": ErrorMessages.SIMULATION_PERMISSION_401
            },
            {
                "code": 200,
                "message": "Success. The simulation timeout has been extended"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401)
    def post(self, sim_id):
        """
        Extends the simulation timeout

        :param sim_id: The simulation id

        :status 404: {0}
        :status 402: Failed to extend the timeout
        :status 401: {1}
        :status 200: Success. The simulation timeout has been extended
        """
        simulation = _get_simulation_or_abort(sim_id)

        if not UserAuthentication.matches_x_user_name_header(request, simulation.owner):
            raise NRPServicesWrongUserException()

        new_timeout = simulation.kill_datetime + \
            datetime.timedelta(minutes=SIMULATION_TIMEOUT_EXTEND)

        if not simulation.cle.extend_simulation_timeout(new_timeout):
            return {}, 402

        simulation.kill_datetime = new_timeout

        return {}, 200
