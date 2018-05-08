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
This module contains the REST implementation for getting and setting the source code of Transfer
Functions used in an experiment.
"""
import re
import logging
from flask import request
from flask_restful_swagger import swagger
from flask_restful import Resource, fields

from hbp_nrp_backend.rest_server import NRPServicesTransferFunctionException, \
    NRPServicesWrongUserException, NRPServicesDuplicateNameException, ErrorMessages
from hbp_nrp_backend.rest_server.__SimulationControl import _get_simulation_or_abort
from hbp_nrp_backend.__UserAuthentication import UserAuthentication

from hbp_nrp_commons.bibi_functions import docstring_parameter

__author__ = 'LucGuyot, DanielPeppicelli'

# pylint: disable=no-self-use
# We need to define the methods like "get", "put", "post", ... in
# the class even though they could be static. This is because of the
# Swagger framework.

logger = logging.getLogger(__name__)


def get_tf_name(source):
    """
    Get the transfer function def name from its python source code.

    :param source: The source code of the transfer function
    :return: transfer function name
    """
    matches = re.findall(r"def\s+(\w+)\s*\(", source)
    return matches[0] if matches else None


@swagger.model
class TransferFunctionDictionary(object):
    """
    Swagger documentation object
    """
    resource_fields = {
        'tf_name': fields.String()
    }


@swagger.model
class ActiveTransferFunctionDictionary(object):
    """
    Swagger documentation object
    """
    resource_fields = {
        'tf_name': fields.Boolean
    }


@swagger.model
@swagger.nested(data=TransferFunctionDictionary.__name__,
                active=ActiveTransferFunctionDictionary.__name__)
class TransferFunctionData(object):
    """
    Swagger documentation object
    Main Data Attribute for parsing convenience on the front-end side.
    """
    resource_fields = {
        'data': fields.Nested(TransferFunctionDictionary.resource_fields),
        'active': fields.Nested(ActiveTransferFunctionDictionary.resource_fields),
    }
    required = ['data', 'active']


class SimulationTransferFunctions(Resource):
    """
    Expose the source code of the CLE transfer functions as a REST service.
    """

    def __init__(self):
        Resource.__init__(self)

    @swagger.operation(
        notes='Gets all transfer functions',
        responseClass=TransferFunctionData.__name__,
        parameters=[
            {
                "name": "sim_id",
                "required": True,
                "description":
                    "The ID of the simulation whose transfer function will be retrieved",
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
                "message": "Success. Transfer functions retrieved successfully"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404)
    def get(self, sim_id):
        """
        Gets all transfer functions (robot to neuron and neuron to robot) in a dictionary with
        string values.

        :param sim_id: The simulation ID

        :> json dict data: Dictionary containing all transfer functions ('name': 'source')
        :> json dict active: Dictionary containing a mask for active TFs ('name': 'isActive')

        :status 404: {0}
        :status 200: Transfer functions retrieved successfully
        """

        simulation = _get_simulation_or_abort(sim_id)

        transfer_functions = dict()
        active_tfs_mask = dict()

        transfer_functions_list, active_tfs_mask_list = \
            simulation.cle.get_simulation_transfer_functions()

        for tf, tf_active in zip(transfer_functions_list, active_tfs_mask_list):
            name = get_tf_name(tf)
            transfer_functions[name] = tf
            active_tfs_mask[name] = tf_active

        return dict(data=transfer_functions, active=active_tfs_mask), 200

    @swagger.operation(
        notes='Adds a new transfer function.',
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
                "name": "data",
                "description": "The transfer function source code to patch",
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
                "message": ErrorMessages.DUPLICATE_NAME_403
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
                         ErrorMessages.DUPLICATE_NAME_403,
                         ErrorMessages.SIMULATION_PERMISSION_401,
                         ErrorMessages.SOURCE_CODE_ERROR_400)
    def post(self, sim_id):
        """
        Adds a new transfer function

        :param sim_id: The simulation ID

        :< string data: The source code of the transfer function

        :status 404: {0}
        :status 403: {1}
        :status 401: {2}
        :status 400: {3}
        :status 200: Success. The transfer function was successfully patched
        """
        simulation = _get_simulation_or_abort(sim_id)
        if not UserAuthentication.matches_x_user_name_header(request, simulation.owner):
            raise NRPServicesWrongUserException()

        transfer_function_source = request.data

        error_message = simulation.cle.add_simulation_transfer_function(transfer_function_source)
        if error_message and "duplicate" in error_message:
            raise NRPServicesDuplicateNameException(
                "Transfer function patch failed: "
                + error_message + "\n"
                + "Updated source:\n"
                + str(transfer_function_source)
            )
        elif error_message:
            raise NRPServicesTransferFunctionException(
                "Adding a new Transfer Function failed: "
                + error_message + "\n"
                + "Updated source:\n"
                + str(transfer_function_source)
            )
        return 200


class SimulationTransferFunction(Resource):
    """
    REST service for patching transfer function source code.
    """

    def __init__(self):
        Resource.__init__(self)

    @swagger.operation(
        notes='Applies user changes to transfer function code.',
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
                "name": "transfer_function_name",
                "description": "The name of the transfer function to be modified",
                "required": True,
                "paramType": "path",
                "dataType": str.__name__
            },
            {
                "name": "data",
                "description": "The transfer function source code to patch",
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
                "message": ErrorMessages.DUPLICATE_NAME_403
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
                         ErrorMessages.DUPLICATE_NAME_403,
                         ErrorMessages.SIMULATION_PERMISSION_401,
                         ErrorMessages.SOURCE_CODE_ERROR_400)
    def put(self, sim_id, transfer_function_name):
        """
        Applies user changes to transfer function code

        :param sim_id: The simulation ID
        :param transfer_function_name: The name of the transfer function to be modified

        :< string data: The source code of the transfer function

        :status 404: {0}
        :status 403: {1}
        :status 401: {2}
        :status 400: {3}
        :status 200: Success. The transfer function was successfully patched
        """
        simulation = _get_simulation_or_abort(sim_id)
        if not UserAuthentication.matches_x_user_name_header(request, simulation.owner):
            raise NRPServicesWrongUserException()

        transfer_function_source = request.data
        error_message = simulation.cle.edit_simulation_transfer_function(
            transfer_function_name, transfer_function_source)

        if error_message and "duplicate" in error_message:
            raise NRPServicesDuplicateNameException(
                "Transfer function patch failed: "
                + error_message + "\n"
                + "Updated source:\n"
                + str(transfer_function_source)
            )
        elif error_message:
            raise NRPServicesTransferFunctionException(
                "Transfer function patch failed: "
                + error_message + "\n"
                + "Updated source:\n"
                + str(transfer_function_source)
            )
        return 200

    @swagger.operation(
        notes='Delete a transfer function.',
        responseClass=int.__name__,
        parameters=[
            {
                "name": "sim_id",
                "required": True,
                "description": "The ID of the simulation whose transfer function will be deleted",
                "paramType": "path",
                "dataType": int.__name__
            },
            {
                "name": "transfer_function_name",
                "description": "The name of the transfer function to be deleted",
                "required": True,
                "paramType": "path",
                "dataType": str.__name__
            },
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
                "code": 200,
                "message": "Success. The delete operation was successfully called. This "
                           "does not imply that the transfer function was correctly "
                           "deleted though."
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401)
    def delete(self, sim_id, transfer_function_name):
        """
        Delete a transfer function

        :param sim_id: The simulation ID
        :param transfer_function_name: The name of the transfer function to be deleted

        :status 404: {0}
        :status 401: {1}
        :status 200: Success. The code was successfully patched
        """
        simulation = _get_simulation_or_abort(sim_id)
        if not UserAuthentication.matches_x_user_name_header(request, simulation.owner):
            raise NRPServicesWrongUserException()

        response = simulation.cle.delete_simulation_transfer_function(transfer_function_name)

        if response is False:
            raise NRPServicesTransferFunctionException(
                "Transfer function delete failed: " + str(transfer_function_name))
        return 200


class SimulationTransferFunctionActivation(Resource):
    """
    REST service for setting the activation state of a transfer function
    """

    def __init__(self):
        Resource.__init__(self)

    @swagger.operation(
        notes='Set the activation state of a transfer function.',
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
                "name": "transfer_function_name",
                "description": "The name of the transfer function to be modified",
                "required": True,
                "paramType": "path",
                "dataType": str.__name__
            },
            {
               "name": "activate",
               "description": "Desired new activation state of the transfer function",
               "required": True,
               "paramType": "path",
               "dataType": bool.__name__
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
                "message": ErrorMessages.ACTIVATION_ERROR_400
            },
            {
                "code": 200,
                "message": "Success. The activation state of the TF has been successfully changed"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401,
                         ErrorMessages.ACTIVATION_ERROR_400)
    def put(self, sim_id, transfer_function_name, activate):
        """

        Sets the activation state of the transfer function

        :param sim_id: The simulation ID
        :param transfer_function_name: The name of the transfer function to be modified
        :param activate A boolean denoting the new desired activation status

        :status 404: {0}
        :status 401: {1}
        :status 400: {2}
        :status 200: Success. The activation state of the TF has been successfully changed

        """

        simulation = _get_simulation_or_abort(sim_id)
        if not UserAuthentication.matches_x_user_name_header(request, simulation.owner):
            raise NRPServicesWrongUserException()

        activate_bool = activate.lower() == "true"  # convert unicode to boolean

        error_message = simulation.cle.activate_simulation_transfer_function(
            transfer_function_name, activate_bool)

        if error_message:
            raise NRPServicesTransferFunctionException(
                "Transfer function (de-)activation failed: "
                + error_message + "\n"
            )

        return 200
