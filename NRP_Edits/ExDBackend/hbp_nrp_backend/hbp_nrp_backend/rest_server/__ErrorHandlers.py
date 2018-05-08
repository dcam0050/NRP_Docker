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
This module contains the error handlers for the REST server.
For 500 errors, a json object understandable by the HBP
frontend libraries is returned.
"""

__author__ = 'GeorgHinkel'

from hbp_nrp_backend.rest_server import NRPServicesGeneralException, \
    NRPServicesClientErrorException, app
from hbp_nrp_backend.cle_interface.ROSCLEClient import ROSCLEClientException
import json
import logging
# pylint: disable=unused-argument
logger = logging.getLogger(__name__)


@app.errorhandler(404)
def not_found(error):
    """
    Handles cases where the command was not found on the server
    :param error: The error object
    """
    return "The command you requested was not found on this server", 404


@app.errorhandler(500)
def internal_error(error):
    """
    Handles internal server errors
    :param error: The error object
    """
    logger.exception(error)
    message = "Internal server error: " + str(error)
    return json.dumps({'message': message,
                       'type': 'General error'}), 500


@app.errorhandler(ROSCLEClientException)
# pylint does not understand the way Flask let
# users redefine handlers for Exceptions.
# pylint: disable=function-redefined
def internal_error(error):
    """
    Handles ROSCLEClientException errors

    :param error: The error object
    """
    logger.exception(error)
    message = "Error while communicating with the CLE"
    message += " (" + str(error) + ")."
    return json.dumps({'message': message, 'type': 'CLE error'}), 500


@app.errorhandler(NRPServicesGeneralException)
@app.errorhandler(NRPServicesClientErrorException)
# pylint: disable=function-redefined
def error2json(error):
    """
    Handles NRPServicesGeneralException errors

    :param error: The error object
    """
    logger.exception(error)
    return json.dumps({'message': error.message,
                       'type': error.error_type,
                       'data': error.data}), error.error_code
