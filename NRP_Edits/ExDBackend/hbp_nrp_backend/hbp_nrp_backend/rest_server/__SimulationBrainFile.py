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
for loading and saving experiment brain files
"""

__author__ = 'Bernd Eckstein'

from flask_restful import Resource, fields
from flask_restful_swagger import swagger
from flask import request

from hbp_nrp_backend.rest_server import NRPServicesWrongUserException, ErrorMessages
from hbp_nrp_backend.rest_server.__SimulationControl import _get_simulation_or_abort
from hbp_nrp_backend.__UserAuthentication import UserAuthentication

from hbp_nrp_commons.bibi_functions import docstring_parameter

import json

# pylint: disable=no-self-use
# because it seems to be buggy:
# pylint: disable=pointless-string-statement


@swagger.model
class PopulationIndices(object):
    """
    Swagger documentation object
    """
    resource_fields = {
        'to': fields.Integer,
        'step': fields.Integer,
        'from': fields.Integer
    }
    required = ['to', 'step', 'from']


@swagger.model
@swagger.nested(population_name=PopulationIndices.__name__)
class PopulationDictionary(object):
    """
    Swagger documentation object
    Population dictionary
    """
    resource_fields = {
        'population_name': fields.Nested(PopulationIndices.resource_fields)
    }
    required = ['population_name']


class SimulationBrainFile(Resource):
    """
    The resource to get and set brain files in the running simulation
    """

    @swagger.model
    @swagger.nested(additional_populations=PopulationDictionary.__name__)
    class GetBrain(object):
        """
        Get Experiment Brain
        Only used for swagger documentation
        """

        resource_fields = {
            'brain_type': fields.String(),
            'data_type': fields.String(),
            'data': fields.String(),
            'additional_populations': fields.Nested(PopulationDictionary.resource_fields)
        }
        required = ['brain_type', 'data_type', 'data', 'additional_populations']

    @swagger.model
    @swagger.nested(additional_populations=PopulationDictionary.__name__)
    class SetBrain(object):
        """
        Set Experiment Brain
        Only used for swagger documentation
        """
        resource_fields = {
            'brain_type': fields.String(),
            'data_type': fields.String(),
            'data': fields.String(),
            'additional_populations': fields.Nested(PopulationDictionary.resource_fields),
            'change_population': fields.Integer
        }
        required = ['brain_type', 'data_type', 'data', 'additional_populations',
                    'change_population']

    @swagger.model
    class BrainError(object):
        """
        Set Experiment Brain
        Only used for swagger documentation
        """

        resource_fields = {
            'error_message': fields.String(),
            'error_line': fields.String(),
            'error_column': fields.String(),
            'handle_population_change': fields.Boolean
        }
        required = []

    @swagger.operation(
        notes='Get the brain file of the given simulation.',
        responseClass=GetBrain.__name__,
        parameters=[
            {
                "name": "sim_id",
                "description": "The ID of the simulation",
                "required": True,
                "paramType": "path",
                "dataType": basestring.__name__
            }
        ],
        responseMessages=[
            {
                "code": 500,
                "message": ErrorMessages.MODEXP_VARIABLE_ERROR
            },
            {
                "code": 404,
                "message": ErrorMessages.SIMULATION_NOT_FOUND_404
            },
            {
                "code": 200,
                "message": "Success. The brain file was retrieved"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.MODEXP_VARIABLE_ERROR,
                         ErrorMessages.SIMULATION_NOT_FOUND_404)
    def get(self, sim_id):
        """
        Get brain data of the simulation specified with simulation ID.

        :param sim_id: The simulation ID

        :> json string brain_type: Type of the brain file ('h5' or 'py')
        :> json string data_type: type of the data field ('text' or 'base64')
        :> json string data: Contents of the brain file. Encoding given in field data_type
        :> json dict additional_populations: A dictionary indexed by population names and containing
                                             neuron indices.

        :status 500: {0}
        :status 404: {1}
        :status 200: Success. The experiment brain file was retrieved
        """

        simulation = _get_simulation_or_abort(sim_id)

        result = simulation.cle.get_simulation_brain()

        return {
            'data': result.brain_data,
            'brain_type': result.brain_type,
            'data_type': result.data_type,
            'additional_populations': json.loads(result.brain_populations),
        }, 200

    @swagger.operation(
        notes='Get the brain file of the given simulation.',
        responseClass=BrainError.__name__,
        parameters=[
            {
                "name": "sim_id",
                "description": "The ID of the simulation",
                "required": True,
                "paramType": "path",
                "dataType": basestring.__name__
            },
            {
                "name": "data",
                "description": "The brain data",
                "required": True,
                "paramType": "body",
                "dataType": SetBrain.__name__
            }
        ],
        responseMessages=[
            {
                "code": 500,
                "message": ErrorMessages.MODEXP_VARIABLE_ERROR
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
                "message": "Success. The brain file was replaced"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.MODEXP_VARIABLE_ERROR,
                         ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401,
                         ErrorMessages.SOURCE_CODE_ERROR_400)
    def put(self, sim_id):
        """
        Set brain file of the simulation specified with simulation ID.
        Depending on the type of brain file, it has to be transmitted as text or
        as base64 (given in the field data_type)

        :param sim_id: The simulation ID

        :< json string brain_type: Type of the brain file ('h5' or 'py')
        :< json string data_type: type of the data field ('text' or 'base64')
        :< json string data: Contents of the brain file. Encoding given in field data_type
        :< json dict additional_populations: A dictionary indexed by population names and containing
                                             neuron indices
        :< json int change_population: A flag to select an action on population name change

        :> json string error_message: Error Message if there is a syntax error in the code
        :> json int error_line: Line of code, where error occurred
        :> json int error_column: Column, where error occurred (if available)
        :> json bool handle_population_change: a flag indicating if user wants to change transfer
                                               functions according to population changes.

        :status 500: {0}
        :status 404: {1}
        :status 401: {2}
        :status 400: {3}
        :status 200: Success. The experiment brain file was replaced
        """

        simulation = _get_simulation_or_abort(sim_id)
        if not UserAuthentication.matches_x_user_name_header(request, simulation.owner):
            raise NRPServicesWrongUserException()

        body = request.get_json(force=True)
        result = simulation.cle.set_simulation_brain(body['brain_type'],
                                                     body['data'],
                                                     body['data_type'],
                                                     json.dumps(body['additional_populations']),
                                                     body['change_population'])

        if result.error_message is not "":
            # Error in given brain
            return {'error_message': result.error_message,
                    'error_line': result.error_line,
                    'error_column': result.error_column,
                    'handle_population_change': result.handle_population_change}, 400

        # Success
        return {'message': "Success"}, 200
