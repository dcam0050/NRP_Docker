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
for loading and saving experiment transfer functions
"""


__author__ = 'Bernd Eckstein'

import logging
import xml.dom.minidom
from threading import Thread
from flask_restful import Resource, request, fields
from flask_restful_swagger import swagger

from hbp_nrp_backend.rest_server import NRPServicesClientErrorException, ErrorMessages
from hbp_nrp_backend.__UserAuthentication import UserAuthentication
from hbp_nrp_backend.rest_server.__SimulationTransferFunctions import get_tf_name
from hbp_nrp_commons.generated import bibi_api_gen, exp_conf_api_gen

logger = logging.getLogger(__name__)
# pylint: disable=no-self-use


class ExperimentTransferfunctions(Resource):
    """
    The resource to load and save experiment transfer function files
    """

    @swagger.model
    class _TransferFunction(object):
        """
        The source code of a transfer function in a simple string.
        """
        resource_fields = {
            'transfer_functions': fields.List(fields.String)
        }
        required = ['transfer_functions']

    @swagger.model
    class _Bibi(object):
        """
        Get and Set Experiment BIBI
        Only used for swagger documentation
        """

        resource_fields = {
            'filename': fields.String(),
            'base64': fields.String()
        }
        required = ['base64']

    @swagger.operation(
        notes='Save transfer functions of an experiment to the storage',
        parameters=[
            {
                "name": "transfer_functions",
                "required": True,
                "description": "List of Transfer functions in Python (list of strings)",
                "paramType": "body",
                "dataType": _TransferFunction.__name__
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
                "message": "Transfer functions code should be sent in "
                           "the body under the 'transfer_functions' key"
            },
            {
                "code": 200,
                "message": "Success. File written"
            }
        ]
    )
    def put(self, experiment_id):
        """
        Save transfer functions of an experiment to the storage.

        :param path experiment_id: The experiment_id of the experiment where the transfer functions
         will be saved
        :<json body json array of string transfer_functions: the transfer functions as python
        :status 500: BIBI configuration file not found
        :status 500: Error saving file
        :status 404: The experiment_id with the given expreiment ID was not found
        :status 404: The request body is malformed
        :status 200: Success. File written.
        """
        # pylint: disable=too-many-locals
        # Done here in order to avoid circular dependencies introduced by the
        # way we __init__ the rest_server module
        from hbp_nrp_backend.storage_client_api.StorageClient \
            import StorageClient

        body = request.get_json(force=True)
        if 'transfer_functions' not in body:
            raise NRPServicesClientErrorException(
                "Transfer functions code should be sent in "
                "the body under the 'transfer_functions' key"
            )

        client = StorageClient()

        experiment_file = client.get_file(
            UserAuthentication.get_header_token(request),
            experiment_id,
            'experiment_configuration.exc',
            byname=True)

        bibi_filename = exp_conf_api_gen.CreateFromDocument(
            experiment_file).bibiConf.src

        bibi_file_path = client.clone_file(bibi_filename,
                                           UserAuthentication.get_header_token(
                                               request),
                                           experiment_id)

        bibi = client.parse_and_check_file_is_valid(
            bibi_file_path,
            bibi_api_gen.CreateFromDocument,
            bibi_api_gen.BIBIConfiguration
        )
        # Remove all transfer functions from BIBI. Then we save them in a
        # separate python file.
        del bibi.transferFunction[:]
        threads = []
        for transfer_function in body['transfer_functions']:
            transfer_function_name = get_tf_name(transfer_function)
            if transfer_function_name is not None:
                transfer_function_node = bibi_api_gen.PythonTransferFunction()
                transfer_function_node.src = transfer_function_name + ".py"
                bibi.transferFunction.append(transfer_function_node)

                t = Thread(target=client.create_or_update,
                           kwargs={
                               'token': UserAuthentication.get_header_token(request),
                               'experiment': experiment_id,
                               'filename': transfer_function_name + ".py",
                               'content': transfer_function,
                               'content_type': 'text/plain'})
                t.start()
                threads.append(t)

        # we need to prettify the parsed bibi
        pretty_bibi = xml.dom.minidom.parseString(
            bibi.toxml("utf-8")).toprettyxml()
        t = Thread(target=client.create_or_update,
                   kwargs={
                       'token': UserAuthentication.get_header_token(request),
                       'experiment': experiment_id,
                       'filename': bibi_filename,
                       'content': pretty_bibi,
                       'content_type': 'text/plain'})
        t.start()
        threads.append(t)
        for x in threads:
            x.join()
        return 200
