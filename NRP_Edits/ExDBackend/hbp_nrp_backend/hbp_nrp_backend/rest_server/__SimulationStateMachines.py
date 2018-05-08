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
This module contains the REST implementation for setting and getting the experiment control State
Machines in a running simulation.
"""

__author__ = 'Bernd Eckstein'

import logging
from flask import request
from flask_restful_swagger import swagger
from flask_restful import Resource, fields

from hbp_nrp_backend.rest_server import NRPServicesGeneralException, \
    NRPServicesStateMachineException, NRPServicesWrongUserException, ErrorMessages
from hbp_nrp_backend.rest_server.__SimulationControl import _get_simulation_or_abort
from hbp_nrp_backend.__UserAuthentication import UserAuthentication

from hbp_nrp_backend.simulation_control.__Simulation import Simulation

from hbp_nrp_commons.bibi_functions import docstring_parameter
from sys import exc_info

# pylint: disable=no-self-use

logger = logging.getLogger(__name__)


def pause_simulation_or_raise(simulation):
    """
    Pauses the simulation and raise an exception in case of failure.
    This is needed before an update of a state machine code

    :param simulation: The simulation to be reset
    """
    state = simulation.state
    if state == 'paused' or state == 'started':
        state = simulation.state = 'paused'

    if state != 'paused':
        raise NRPServicesGeneralException(
            "Simulation in state {0}. Can't update the state machine".format(state),
            "Server error", error_code=403
        )


@swagger.model
class StateMachineDictionary(object):
    """
    Swagger documentation object
    StateMachineDict ... tried to make it look like a dictionary for the swagger doc
    """
    resource_fields = {
        'sm_id_1': str.__name__,
        'sm_id_2': str.__name__,
        'sm_id_n': str.__name__
    }


@swagger.model
@swagger.nested(data=StateMachineDictionary.__name__)
class StateMachineData(object):
    """
    Swagger documentation object
    Main Data Attribute for parsing convenience on the frontend side.
    """

    resource_fields = {
        'data': fields.Nested(StateMachineDictionary.resource_fields)
    }
    required = ['data']


class SimulationStateMachines(Resource):
    """
    REST service for getting the code of all state machines
    """

    def __init__(self):
        Resource.__init__(self)

    @swagger.operation(
        notes='Get code of all state machines',
        responseClass=StateMachineData.__name__,
        parameters=[
            {
                "name": "sim_id",
                "required": True,
                "description": "The ID of the simulation whose state machines will be retrieved",
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
                "message": "Success. The state machines were returned"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404)
    def get(self, sim_id):
        """
        Get code of all state machines. This works in all simulation states except 'created', where
        it will deliver an empty dictionary.

        :param sim_id: The simulation ID

        :> json dict data: Dictionary containing all state machines ('name': 'source')

        :status 404: {0}
        :status 200: Success. The state machines were returned
        """
        simulation = _get_simulation_or_abort(sim_id)
        state_machines = dict()
        for sm in simulation.state_machines:
            state_machines[sm.sm_id] = simulation.get_state_machine_code(sm.sm_id)

        return dict(data=state_machines), 200


class SimulationStateMachine(Resource):
    """
    REST service for patching control state machine source code.
    """

    @swagger.operation(
        notes='Applies user changes to state machine code.',
        responseClass=int.__name__,
        parameters=[
            {
                "name": "sim_id",
                "required": True,
                "description": "The ID of the simulation whose state machine will be modified",
                "paramType": "path",
                "dataType": int.__name__
            },
            {
                "name": "state_machine_name",
                "description": "The name of the state machine to be modified",
                "required": True,
                "paramType": "path",
                "dataType": str.__name__
            },
            {
                "name": "data",
                "description": "The state machine source code to patch",
                "required": True,
                "paramType": "body",
                "dataType": str.__name__
            }
        ],
        responseMessages=[
            {
                "code": 404,
                "message": ErrorMessages.SIMULATION_NOT_FOUND_404
            },
            {
                "code": 403,
                "message": ErrorMessages.OPERATION_INVALID_IN_CURRENT_STATE_403
            },
            {
                "code": 401,
                "message": ErrorMessages.SIMULATION_PERMISSION_401
            },
            {
                "code": 400,
                "message": ErrorMessages.SOURCE_CODE_ERROR_400
            },
            {
                "code": 200,
                "message": "Success. The code was successfully patched"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401,
                         ErrorMessages.SOURCE_CODE_ERROR_400)
    def put(self, sim_id, state_machine_name):
        """
        Applies user changes to state machine code.
        If the simulation is paused or started, it will be paused.
        A stopped, created or failed simulation will fail the request with error code 403

        :param sim_id: The simulation ID
        :param state_machine_name: The name of the state machine to be modified

        :< json string data: The source code of the state machine

        :status 404: {0}
        :status 401: {1}
        :status 400: {2}
        :status 200: Success. The code was successfully patched
        """
        simulation = _get_simulation_or_abort(sim_id)
        assert simulation, Simulation
        if not UserAuthentication.matches_x_user_name_header(request, simulation.owner):
            raise NRPServicesWrongUserException()

        state_machine_source = request.data
        try:
            simulation.set_state_machine_code(
                state_machine_name,
                state_machine_source
            )
            return "Success. The code was successfully patched.", 200
        except (AttributeError, NameError) as e:
            info = exc_info()
            raise NRPServicesStateMachineException(e.message, 400), None, info[2]

        except SyntaxError as e:
            info = exc_info()
            args_txt = ""
            for text in e.args:
                args_txt += " {0}".format(text)
            raise NRPServicesStateMachineException(
                "The source code is invalid: "
                "SyntaxError in line {0}{1}.".format(e.lineno, args_txt),
                400
            ), None, info[2]

        except Exception as e:
            info = exc_info()
            raise NRPServicesGeneralException(
                "Update of state machine code failed. "
                "{0}: {1}".format(
                    e.__class__.__name__,
                    e.message
                ), "State machine error"
            ), None, info[2]

    @swagger.operation(
        notes='Delete a state machine.',
        responseClass=int.__name__,
        parameters=[
            {
                "name": "sim_id",
                "required": True,
                "description": "The ID of the simulation whose state machine will be deleted",
                "paramType": "path",
                "dataType": int.__name__
            },
            {
                "name": "state_machine_name",
                "description": "The name of the state machine to be deleted",
                "required": True,
                "paramType": "path",
                "dataType": str.__name__
            },
        ],
        responseMessages=[
            {
                "code": 500,
                "message": ErrorMessages.SERVER_ERROR_500
            },
            {
                "code": 404,
                "message": ErrorMessages.SIMULATION_NOT_FOUND_404
            },
            {
                "code": 401,
                "message": ErrorMessages.SIMULATION_PERMISSION_401
            },
            {
                "code": 200,
                "message": "Success. The delete operation was successfully called. This "
                           "does not imply that the state machine function was correctly "
                           "deleted though."
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SERVER_ERROR_500,
                         ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401)
    def delete(self, sim_id, state_machine_name):
        """
        Delete a state machine

        :param sim_id: The simulation ID
        :param state_machine_name: The name of the state machine to be deleted

        :status 500: {0}
        :status 404: {1}
        :status 401: {2}
        :status 200: The delete operation was successfully called. This does not imply that the
                     state machine function was correctly deleted though.
        """
        simulation = _get_simulation_or_abort(sim_id)
        if not UserAuthentication.matches_x_user_name_header(request, simulation.owner):
            raise NRPServicesWrongUserException()

        failure_message = "State machine destruction failed: "
        try:
            ok, response_message = simulation.delete_state_machine(state_machine_name)
            if ok:
                return "Success. The state machine was successfully deleted.", 200
        except Exception as e:
            info = exc_info()
            raise NRPServicesGeneralException(
                failure_message +
                " {0}: {1}".format(e.__class__.__name__, e.message),
                "State machine error",
            ), None, info[2]
        raise NRPServicesStateMachineException(failure_message + "\n" + response_message, 404)
