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
This module contains a resource to query the BIBI transfer functions
"""

__author__ = 'Georg Hinkel'

from flask_restful import Resource, fields
from flask_restful_swagger import swagger
from hbp_nrp_commons.generated import bibi_api_gen
from hbp_nrp_commons.bibi_functions import print_expression, print_neurons, get_default_property, \
    docstring_parameter

from hbp_nrp_backend.rest_server import NRPServicesClientErrorException, ErrorMessages
from hbp_nrp_backend.rest_server.__ExperimentService import get_bibi_file

import os

# pylint: disable=R0201
# because it seems to be buggy:
# pylint: disable=W0105


@swagger.model
class Device(object):
    """
    Gets a device configuration
    Only used for swagger documentation
    """

    resource_fields = {
        'parameterName': fields.String,
        'type': fields.String,
        'target': fields.String,
        'neurons': fields.String
    }

    required = ['parameterName', 'type', 'neurons']


@swagger.model
class Topic(object):
    """
    Gets a topic configuration
    Only used for swagger documentation
    """

    resource_fields = {
        'parameterName': fields.String,
        'type': fields.String,
        'topic': fields.String,
        'topicType': fields.String
    }

    required = ['parameterName', 'type', 'topic']


@swagger.model
@swagger.nested(devices=Device.__name__, topics=Topic.__name__)
class TransferFunction(object):
    """
    Gets a transfer function
    Only used for swagger documentation
    """

    resource_fields = {
        'name': fields.String,
        'devices': fields.List(fields.Nested(Device.resource_fields)),
        'topics': fields.List(fields.Nested(Topic.resource_fields)),
        'body': fields.String
    }


class ExperimentBibiTransferFunctions(Resource):
    """
    The resource to load transfer functions consumable by the graphical editor
    """

    @swagger.model
    @swagger.nested(transferFunctions=TransferFunction.__name__)
    class _BibiTransferFunctions(object):
        """
        Get BIBI Transfer Functions
        Only used for swagger documentation
        """

        resource_fields = {
            'transferFunctions': fields.List(fields.Nested(TransferFunction.resource_fields))
        }

        required = ['transferFunctions']

    @swagger.operation(
        notes='Get the bibi transfer functions of a given experiment.',
        responseClass=_BibiTransferFunctions.__name__,
        parameters=[
            {
                "name": "exp_id",
                "description": "The ID of the experiment BIBI file to be retrieved",
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
                "message": "The experiment with the given ID was not found or the experiment BIBI "
                           "file was not found"
            },
            {
                "code": 200,
                "message": "Success. The experiment BIBI file was retrieved"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.MODEXP_VARIABLE_ERROR)
    def get(self, exp_id):
        """
        Gets bibi file of the experiment specified with experiment ID.

        :param exp_id: The experiment ID

        :> json string filename: Name of the experiment file
        :> json string base64: Contents of the BIBI file encoded as base64

        :status 500: {0}
        :status 404: The experiment with the given ID was not found or the experiment BIBI file was
                     not found
        :status 200: Success. The experiment BIBI file was retrieved
        """
        # pylint: disable=too-many-locals
        filename = get_bibi_file(exp_id)

        if not os.path.isfile(filename):
            raise NRPServicesClientErrorException(ErrorMessages.EXPERIMENT_BIBI_FILE_NOT_FOUND_404,
                                                  error_code=404)
        with open(filename) as bibi_file:
            bibi = bibi_api_gen.CreateFromDocument(bibi_file.read())
            assert isinstance(bibi, bibi_api_gen.BIBIConfiguration)

            tfs = []
            for tf in bibi.transferFunction:
                if isinstance(tf, bibi_api_gen.BIBITransferFunction):

                    if len(tf.deviceGroup) > 0 or isinstance(tf, bibi_api_gen.Neuron2Monitor):
                        continue

                    devices = []
                    topics = []
                    impl = ""
                    for local in tf.local:
                        assert isinstance(local, bibi_api_gen.Local)
                        impl += local.name + " = " + print_expression(local.body) + "\n"
                    for dev in tf.device:
                        assert isinstance(dev, bibi_api_gen.DeviceChannel)
                        dev_e = {
                            'parameterName': dev.name,
                            'type': dev.type,
                            'neurons': print_neurons(dev.neurons)
                        }
                        if dev.target is not None:
                            dev_e['target'] = dev.target
                        devices.append(dev_e)
                        if dev.body is not None:
                            impl += dev.name + "." + get_default_property(dev.type) + " = " + \
                                    print_expression(dev.body) + "\n"
                    for top in tf.topic:
                        assert isinstance(top, bibi_api_gen.TopicChannel)
                        topic_e = {
                            'parameterName': top.name,
                            'type': 'publisher' if top.body is not None else 'subscriber',
                            'topic': top.topic,
                            'topicType': top.type
                        }
                        topics.append(topic_e)
                        if top.body is not None:
                            impl += top.name + ".send_message(" + print_expression(top.body) + \
                                    ")\n"
                    if isinstance(tf, bibi_api_gen.Neuron2Robot):
                        ret = tf.returnValue
                        assert isinstance(ret, bibi_api_gen.TopicChannel)
                        topic_e = {
                            'parameterName': '__return__',
                            'type': 'publisher',
                            'topic': ret.topic,
                            'topicType': ret.type
                        }
                        topics.append(topic_e)
                        impl += "return " + print_expression(ret.body)
                    tf_e = {
                        'name': tf.name,
                        'devices': devices,
                        'topics': topics,
                        'body': impl
                    }
                    tfs.append(tf_e)
            return {'transferFunctions': tfs}, 200
