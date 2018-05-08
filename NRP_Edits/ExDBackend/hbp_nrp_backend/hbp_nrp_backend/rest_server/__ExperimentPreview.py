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
for loading (and someday writing) experiment preview images
"""

__author__ = 'Bernd Eckstein'

from flask_restful import Resource, fields
from flask_restful_swagger import swagger

from hbp_nrp_backend.rest_server import NRPServicesClientErrorException, ErrorMessages
from hbp_nrp_backend.rest_server.RestSyncMiddleware import RestSyncMiddleware
from hbp_nrp_backend.rest_server.__ExperimentService import get_experiment_rel, \
    get_experiment_basepath

from hbp_nrp_commons.generated import exp_conf_api_gen
from hbp_nrp_commons.bibi_functions import docstring_parameter

from pyxb import ValidationError

import mimetypes
import base64
import os

# pylint: disable=R0201


class ExperimentPreview(Resource):
    """
    Get Experiment preview PNG file as octet-stream
    """

    @swagger.model
    class _Image(object):
        """
        Get and Set Experiment Configuration
        Only used for swagger documentation
        """

        resource_fields = {
            'image_as_base64': fields.String()
        }
        required = ['image_as_base64']

    @swagger.operation(
        notes='Get the preview image of a given experiment',
        responseClass=_Image.__name__,
        parameters=[
            {
                "name": "exp_id",
                "description": "The ID of the experiment",
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
                "message": ErrorMessages.EXPERIMENT_NOT_FOUND_404
            },
            {
                "code": 404,
                "message": ErrorMessages.EXPERIMENT_PREVIEW_NOT_FOUND_404
            },
            {
                "code": 200,
                "message": "Success. The preview image was sent."
            }
        ]
    )
    @docstring_parameter(ErrorMessages.MODEXP_VARIABLE_ERROR,
                         ErrorMessages.EXPERIMENT_NOT_FOUND_404,
                         ErrorMessages.EXPERIMENT_PREVIEW_NOT_FOUND_404)
    @RestSyncMiddleware.threadsafe
    def get(self, exp_id):
        """
        Get preview image of the experiment specified with experiment ID.

        :param exp_id: The experiment ID

        :> json image_as_base64: The PNG image as base64

        :status 500: {0}
        :status 404: {1} or {2}
        :status 200: Success. The preview image is returned
        """

        # Check experiment
        experiment_file_path = os.path.join(get_experiment_basepath(),
                                            get_experiment_rel(exp_id))
        if not os.path.isfile(experiment_file_path):
            raise NRPServicesClientErrorException(ErrorMessages.EXPERIMENT_CONF_FILE_NOT_FOUND_404,
                                                  error_code=404)

        experiment_dir = os.path.split(experiment_file_path)[0]
        # Parse the experiment XML and get the thumbnail path
        with open(experiment_file_path) as exd_file:
            try:
                experiment_file = exp_conf_api_gen.CreateFromDocument(exd_file.read())
                preview_file = os.path.join(experiment_dir, experiment_file.thumbnail)
            except ValidationError:
                raise NRPServicesClientErrorException(
                                                    ErrorMessages.EXPERIMENT_CONF_FILE_INVALID_500,
                                                    error_code=500)

        # Check thumbnail
        if not os.path.isfile(preview_file):
            raise NRPServicesClientErrorException(ErrorMessages.EXPERIMENT_PREVIEW_NOT_FOUND_404,
                                                  error_code=404)
        mime_type = mimetypes.guess_type(preview_file)[0] # returns tuple (type, encoding)
        if not mime_type or not mime_type.startswith('image'):
            raise NRPServicesClientErrorException(ErrorMessages.EXPERIMENT_PREVIEW_INVALID_500,
                                                  error_code=500)

        with open(preview_file, "rb") as _file:
            data = _file.read()

        # Base64
        return dict(image_as_base64=base64.b64encode(data))
