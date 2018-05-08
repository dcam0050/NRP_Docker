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
This module contains the REST implementation for the control of the simulation state
"""

__author__ = 'Georg Hinkel'

from flask import request
from flask_restful import Resource, fields
from flask_restful_swagger import swagger

from transitions import MachineError

from hbp_nrp_backend.rest_server import NRPServicesStateException, NRPServicesWrongUserException, \
    ErrorMessages
from hbp_nrp_backend.rest_server.__SimulationControl import _get_simulation_or_abort
from hbp_nrp_backend.__UserAuthentication import UserAuthentication

from hbp_nrp_commons.bibi_functions import docstring_parameter

# pylint: disable=R0201


class SimulationState(Resource):
    """
    The resource to control the state of the simulation.
    Allowed state values are: created, initialized, started, paused, stopped
    """

    @swagger.model
    class _State(object):
        """
        State of a simulation. Allowed values are: created, initialized, started,
        paused, stopped.
        Only used for swagger documentation
        """

        resource_fields = {
            'state': fields.String()
        }
        required = ['state']

    @swagger.operation(
        notes='Gets the state of the given simulation.'
        ' Possible values are: created, initialized, started, paused, stopped',
        responseClass=_State.__name__,
        parameters=[
            {
                "name": "sim_id",
                "description": "The ID of the simulation whose state shall be retrieved",
                "required": True,
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
                "code": 200,
                "message": "Success. The state of the simulation with the given ID is retrieved"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404)
    def get(self, sim_id):
        """
        Gets the state of the simulation with the specified simulation id. Possible values are:
        created, initialized, started, paused, stopped

        :param sim_id: The simulation id

        :> json string state: The state of the simulation

        :status 404: {0}
        :status 200: The state of the simulation with the given ID was successfully retrieved
        """
        simulation = _get_simulation_or_abort(sim_id)
        return {'state': str(simulation.state)}, 200

    @swagger.operation(
        notes='Sets the state of the given simulation.'
        ' Allowed values are: created, initialized, started, paused, stopped',
        responseClass=_State.__name__,
        parameters=[
            {
                "name": "sim_id",
                "required": True,
                "description": "The ID of the simulation whose state shall be set",
                "paramType": "path",
                "dataType": int.__name__
            },
            {
                "name": "state",
                "description": "The new state of the simulation",
                "required": True,
                "paramType": "body",
                "dataType": _State.__name__
            }
        ],
        responseMessages=[
            {
                "code": 404,
                "message": ErrorMessages.SIMULATION_NOT_FOUND_404
            },
            {
                "code": 401,
                "message": ErrorMessages.SIMULATION_PERMISSION_401
            },
            {
                "code": 400,
                "message": "The state transition is invalid"
            },
            {
                "code": 200,
                "message": "Success. The new state has been correctly applied"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401)
    def put(self, sim_id):
        """
        Sets the simulation with the given name into a new state. Allowed values are:
        created, initialized, started, paused, stopped

        :param sim_id: The simulation id

        :< json string state: The state of the simulation to set

        :> json string state: The state of the simulation

        :status 404: {0}
        :status 401: {1}
        :status 400: The state transition is invalid
        :status 200: The state of the simulation with the given ID was successfully set
        """
        simulation = _get_simulation_or_abort(sim_id)

        if not UserAuthentication.matches_x_user_name_header(request, simulation.owner):
            raise NRPServicesWrongUserException()

        body = request.get_json(force=True)
        try:
            simulation.state = body['state']
        except MachineError:
            raise NRPServicesStateException(
                "Invalid transition (" + simulation.state + "->" + body['state'] + ")")
        return {'state': str(simulation.state)}, 200
