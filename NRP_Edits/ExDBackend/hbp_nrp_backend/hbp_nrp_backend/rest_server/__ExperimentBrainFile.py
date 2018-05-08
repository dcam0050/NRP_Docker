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

import os
import logging
import xml.dom.minidom

from flask_restful import Resource, fields, request
from flask_restful_swagger import swagger

from hbp_nrp_backend.rest_server import NRPServicesClientErrorException, ErrorMessages
from hbp_nrp_backend.__UserAuthentication import UserAuthentication
from hbp_nrp_commons.generated import bibi_api_gen, exp_conf_api_gen
from hbp_nrp_commons.bibi_functions import docstring_parameter


logger = logging.getLogger(__name__)

# pylint: disable=R0201
# because it seems to be buggy:
# pylint: disable=W0105


class ExperimentBrainFile(Resource):
    """
    The resource to save experiment brain files to the storage
    """

    def parsePopulations(self, brain_populations, bibi):
        """
        Parse a population from the received brain_populations object and add it to bibi.
        """

        if isinstance(brain_populations, list):
            for value in brain_populations:
                if 'list' in value:
                    population_node = bibi_api_gen.List()
                    for index in value['list']:
                        population_node.append(index)
                else:
                    population_node = bibi_api_gen.Range()
                    population_node.from_ = value['from']
                    population_node.to = value['to']
                    population_node.step = value.get('step')
                    if population_node.step <= 0:
                        population_node.step = 1
                population_node.population = value['name']
                bibi.brainModel.populations.append(population_node)
        else:
            for key, value in brain_populations.iteritems():
                population_node = None
                if isinstance(value, list):
                    population_node = bibi_api_gen.List()
                    for index in value:
                        population_node.append(index)
                if isinstance(value, dict):
                    population_node = bibi_api_gen.Range()
                    population_node.from_ = value['from']
                    population_node.to = value['to']
                    population_node.step = value.get('step')
                    if population_node.step <= 0:
                        population_node.step = 1
                population_node.population = key
                bibi.brainModel.populations.append(population_node)

    @swagger.model
    class _Brain(object):
        """
        Set Experiment brain
        Only used for swagger documentation
        """

        resource_fields = {
            'data': fields.String(),
            'additional_populations': fields.Arbitrary()
        }
        required = ['data']

    @swagger.operation(
        notes='Save a brain model PyNN of an experiment to the storage.',
        parameters=[
            {
                "name": "brain_model",
                "required": True,
                "description": "Brain model in the Python language (using PyNN)",
                "paramType": "body",
                "dataType": _Brain.__name__
            },
        ],
        responseMessages=[
            {
                "code": 500,
                "message": ErrorMessages.ERROR_SAVING_FILE_500
            },
            {
                "code": 404,
                "message": ErrorMessages.STORAGE_NOT_FOUND_404
            },
            {
                "code": 400,
                "message": "Neural network python code should be sent in "
                           "the body under the 'data' key"
            },
            {
                "code": 200,
                "message": "Success."
            }
        ]
    )
    @docstring_parameter(ErrorMessages.ERROR_SAVING_FILE_500, ErrorMessages.STORAGE_NOT_FOUND_404)
    def put(self, experiment_id):
        """
        Save a brain model PyNN of an experiment to the storage.
        :param path experiment_id: The experiment id

        :< json body json string data: PyNN script of the model
        :< json body json string brain_populations: neuron populations
        :< json body json string brain_populations: context_id of the sim

        :status 500: {0}
        :status 404: {1}
        :status 400: The request body is malformed
        :status 200: Success. File written.
        """
        from hbp_nrp_backend.storage_client_api.StorageClient \
            import StorageClient
        body = request.get_json(force=True)
        if 'data' not in body:
            raise NRPServicesClientErrorException(
                "Neural network python code should be sent in the body under the 'data' key"
            )
        context_id = body.get('context_id', None)

        # no need to rewrite a get_header function since the user
        # authentication already has one
        # Read the request data
        content_type = UserAuthentication.get_header(
            request,
            'Content-type',
            'text/plain'
        )
        data = body['data']
        brain_populations = body.get('additional_populations')

        # Instantiate the storage client
        client = StorageClient()

        # find the bibi filename from the .exc
        experiment_file = client.get_file(
            UserAuthentication.get_header_token(request),
            experiment_id,
            'experiment_configuration.exc',
            byname=True)

        bibi_filename = exp_conf_api_gen.CreateFromDocument(
            experiment_file).bibiConf.src

        # find the brain filename from the bibi
        bibi_file = client.get_file(
            UserAuthentication.get_header_token(request),
            experiment_id,
            bibi_filename,
            byname=True
        )
        bibi_file_obj = bibi_api_gen.CreateFromDocument(bibi_file)
        brain_filename = bibi_file_obj.brainModel.file

        if 'storage://' in brain_filename:
            client.create_or_update(UserAuthentication.get_header_token(request),
                                    client.get_folder_uuid_by_name(
                                        UserAuthentication.get_header_token(
                                            request),
                                        context_id,
                                        'brains'),
                                    os.path.basename(brain_filename),
                                    data,
                                    content_type)
        else:
            client.create_or_update(UserAuthentication.get_header_token(request),
                                    experiment_id,
                                    os.path.basename(brain_filename),
                                    data,
                                    content_type)

        # remove all the populations
        del bibi_file_obj.brainModel.populations[:]

        if brain_populations is not None:
            self.parsePopulations(brain_populations, bibi_file_obj)

        # replace the bibi contents in the storage to match the new brain
        # definition
        client.create_or_update(
            UserAuthentication.get_header_token(request),
            experiment_id,
            bibi_filename,
            xml.dom.minidom.parseString(
                bibi_file_obj.toxml("utf-8")).toprettyxml(),
            "text/plain"
        )

        return 200
