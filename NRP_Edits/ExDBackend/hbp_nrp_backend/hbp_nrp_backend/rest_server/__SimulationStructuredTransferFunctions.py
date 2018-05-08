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
This module contains the Flask resource for structured transfer functions
"""

import re
import json
from flask import request
from flask_restful_swagger import swagger
from flask_restful import Resource, fields

from hbp_nrp_backend.rest_server import NRPServicesTransferFunctionException, \
    NRPServicesWrongUserException, ErrorMessages
from hbp_nrp_backend.rest_server.__SimulationControl import _get_simulation_or_abort
from hbp_nrp_backend.__UserAuthentication import UserAuthentication

from hbp_nrp_commons.bibi_functions import docstring_parameter


__author__ = "Georg Hinkel"


def get_tf_name(source):
    """
    Get the transfer function def name from its python source code.

    :param source: The source code of the transfer function
    :return: transfer function name
    """
    matches = re.findall(r"def\s+(\w+)\s*\(", source)
    return matches[0] if matches else None


class JSONObject(object):
    """
    A helper class
    """

    def __init__(self, d):
        """
        Creates a new JSON object with the given dict

        :param d: The dictionary for the object
        """
        self.__dict__ = d


@swagger.model
class NeuronModel(object):
    """
    Swagger documentation object
    """
    resource_fields = {
        'name': fields.String(),
        'type': fields.Integer(),
        'ids': fields.Nested(int.__name__),
        'start': fields.Integer(),
        'stop': fields.Integer(),
        'step': fields.Integer()
    }
    required = ['name', 'type']


@swagger.model
@swagger.nested(data=NeuronModel.__name__)
class DeviceModel(object):
    """
    Swagger documentation object
    """
    resource_fields = {
        'name': fields.String(),
        'type': int.__name__,
        'neurons': fields.Nested(NeuronModel.__name__)
    }
    required = ['name', 'type', 'neurons']


@swagger.model
class TopicModel(object):
    """
    Swagger documentation object
    """
    resource_fields = {
        'name': fields.String(),
        'topic': fields.String(),
        'type': fields.String(),
        'publishing': fields.Boolean()
    }
    required = ['']


@swagger.model
class VariableModel(object):
    """
    Swagger documentation object
    """
    resource_fields = {
        'name': fields.String(),
        'type': fields.String(),
        'initial value': fields.String()
    }
    required = []


@swagger.model
@swagger.nested(data=DeviceModel.__name__)
class TransferFunctionModel(object):
    """
    Swagger documentation object
    """
    resource_fields = {
        'name': fields.String(),
        'code': fields.String(),
        'type': fields.Integer(),
        'devices': fields.Nested(DeviceModel.__name__),
        'topics': fields.Nested(TopicModel.__name__),
        'variables': fields.Nested(VariableModel.__name__)
    }


@swagger.model
@swagger.nested(data=TransferFunctionModel.__name__)
class TransferFunctionsData(object):
    """
    Swagger documentation object
    """
    resource_fields = {
        'transferFunctions': fields.Nested(TransferFunctionModel.resource_fields)
    }
    required = ['transferFunctions']


# pylint: disable=no-self-use
class SimulationStructuredTransferFunctions(Resource):
    """
    The resource for structured transfer functions
    """

    @swagger.operation(
        notes='Get transfer functions in a structured format',
        responseClass=TransferFunctionsData.__name__,
        parameters=[
            {
                "name": "sim_id",
                "required": True,
                "description": "The ID of the simulation whose transfer functions are obtained",
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
                "message": "Success. The transfer functions were returned"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404)
    def get(self, sim_id):
        """
        Gets the structured transfer functions

        :param sim_id: The simulation id

        :status 404: {0}
        :status 200: Success. The transfer functions were returned
        """
        simulation = _get_simulation_or_abort(sim_id)

        tfs = []
        transfer_functions_list = simulation.cle.get_structured_transfer_functions()
        for tf in transfer_functions_list:
            devices = [{
                'name': dev.name,
                'type': dev.type,
                'neurons': {
                    'name': dev.neurons.name,
                    'type': dev.neurons.type,
                    'ids': [
                        {
                            'id': n_id
                        } for n_id in dev.neurons.ids
                    ],
                    'start': dev.neurons.start,
                    'stop': dev.neurons.stop,
                    'step': dev.neurons.step
                }
            } for dev in tf.devices]

            topics = [{
                'name': top.name,
                'topic': top.topic,
                'type': top.type,
                'publishing': top.publishing
            } for top in tf.topics]

            variables = [{
                'name': var.name,
                'type': var.type,
                'initial_value': var.initial_value
            } for var in tf.variables]

            tf_e = {
                'name': tf.name,
                'code': tf.code,
                'type': tf.type,
                'devices': devices,
                'topics': topics,
                'variables': variables
            }
            tfs.append(tf_e)
        return {'transferFunctions': tfs}, 200

    @swagger.operation(
        notes='Applies user changes to a structured transfer function.',
        responseClass=int.__name__,
        parameters=[
            {
                "name": "sim_id",
                "required": True,
                "description": "The ID of the simulation whose transfer function will be modified",
                "paramType": "path",
                "dataType": int.__name__
            },
            {
                "name": "transfer_function",
                "description": "The structured transfer function",
                "required": True,
                "paramType": "body",
                "dataType": TransferFunctionsData.__name__
            }
        ],
        responseMessages=[
            {
                "code": 500,
                "message": "Simulation in state [STATE]. Can't update transfer function"
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
                "code": 400,
                "message": ErrorMessages.SOURCE_CODE_ERROR_400
            },
            {
                "code": 200,
                "message": "Success. The transfer function was successfully patched"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401,
                         ErrorMessages.SOURCE_CODE_ERROR_400)
    def put(self, sim_id):
        """
        Puts the structured transfer functions

        :param sim_id: The simulation id

        :status 500: Simulation in state [STATE]. Can't update transfer function
        :status 404: {0}
        :status 401: {1}
        :status 400: {2}
        :status 200: Success. The transfer function was successfully patched
        """
        simulation = _get_simulation_or_abort(sim_id)

        if not UserAuthentication.matches_x_user_name_header(request, simulation.owner):
            raise NRPServicesWrongUserException()

        transfer_function = json.loads(request.data, object_hook=JSONObject)
        error_message = simulation.cle.set_structured_transfer_function(transfer_function)
        if error_message:
            raise NRPServicesTransferFunctionException(
                "Transfer function patch failed: "
                + error_message + "\n"
                + "Transfer function:\n"
                + request.data
            )
        return 200
