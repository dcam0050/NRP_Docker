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
for loading and saving experiment state machine files
"""


__author__ = 'Bernd Eckstein'
import os
import logging
from threading import Thread
from flask import request
from flask_restful import Resource, fields
from flask_restful_swagger import swagger

from hbp_nrp_backend.rest_server import NRPServicesClientErrorException, ErrorMessages
from hbp_nrp_backend.__UserAuthentication import UserAuthentication
from hbp_nrp_backend.rest_server.__ExperimentService import save_file, \
    get_control_state_machine_files, get_evaluation_state_machine_files

from hbp_nrp_commons.generated import exp_conf_api_gen
from hbp_nrp_commons.bibi_functions import docstring_parameter

logger = logging.getLogger(__name__)

# pylint: disable=no-self-use


@swagger.model
class StateMachines(object):
    """
    Get and Set Experiment State Machine
    Only used for swagger documentation
    """

    resource_fields = {
        'StateMachine_1': fields.String(),
        'StateMachine_2': fields.String()
    }


@swagger.model
@swagger.nested(control=StateMachines.__name__,
                evaluation=StateMachines.__name__)
class ReturnObject(object):
    """
    Get and Set Experiment State Machine
    Only used for swagger documentation
    """

    resource_fields = {
        'control': fields.Nested(StateMachines.resource_fields),
        'evaluation': fields.Nested(StateMachines.resource_fields)
    }
    required = ['control', 'evaluation']


class ExperimentGetStateMachines(Resource):
    """
    The resource to load experiment state machine files
    """

    @swagger.operation(
        notes='Get the state machine files of a given experiment.',
        responseClass=ReturnObject.__name__,
        parameters=[
            {
                "name": "exp_id",
                "description": "The ID of the experiment state machine files to be retrieved",
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
                "message": "State machine file not found: [filename]"
            },
            {
                "code": 200,
                "message": "Success. The experiment state machine files where retrieved"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.MODEXP_VARIABLE_ERROR,
                         ErrorMessages.EXPERIMENT_NOT_FOUND_404)
    def get(self, exp_id):
        """
        Gets state machine files of the experiment specified with experiment ID.

        :param exp_id: The experiment ID

        :> json dict control: Contains control state machines as dictionary ('name': 'source_code')
        :> json dict evaluation: Contains evaluation state machines as dictionary
                                ('name': 'source_code')

        :status 500: {0}
        :status 404: State machine file not found: [filename]
        :status 404: {1}
        :status 200: Success. The experiment state machine files where retrieved
        """
        # Get ID, absolute path of state machine files
        ctrl_file_names = get_control_state_machine_files(exp_id)
        eval_file_names = get_evaluation_state_machine_files(exp_id)

        # Crete return dictionaries
        ctrl_ret = dict()
        eval_ret = dict()

        # So we can iterate over it and don't have to copy-paste the for-loop
        # below: create Arrays
        file_names = [ctrl_file_names, eval_file_names]
        ret = [ctrl_ret, eval_ret]

        for i in 0, 1:
            for sm in file_names[i]:
                filename = file_names[i][sm]
                if not os.path.isfile(filename):
                    raise NRPServicesClientErrorException(
                        "State machine file not found: " + filename,
                        error_code=404
                    )
                with open(filename, "r") as _file:
                    data = _file.read()
                    ret[i][sm] = data

        return {'control': ctrl_ret, 'evaluation': eval_ret}, 200


class ExperimentPutStateMachine(Resource):
    """
    The resource to save experiment state machine files
    """

    @swagger.operation(
        notes='Sends a state machine file of an experiment to the server',
        parameters=[
            {
                "name": "exp_id",
                "required": True,
                "description": "The ID of the experiment, whose BIBI file will be written.",
                "paramType": "path",
                "dataType": basestring.__name__
            },
            {
                "name": "state_machine_name",
                "required": True,
                "description": "The name of the state machine to be written",
                "paramType": "path",
                "dataType": basestring.__name__
            },
            {
                "name": "source_code",
                "description": "The source code of the state machine",
                "required": True,
                "paramType": "body",
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
                "code": 200,
                "message": "Success. File written: '[file_name]'"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.MODEXP_VARIABLE_ERROR,
                         ErrorMessages.EXPERIMENT_NOT_FOUND_404)
    def put(self, exp_id, state_machine_name):
        """
        Send a state machine of an experiment to the server
        (currently, the file will be written with the ending "_new")

        :param exp_id: The experiment ID
        :param state_machine_name: The name of the state machine to be written

        :< json string source: Source code of the state machine

        :status 500: {0}
        :status 404: {1}
        :status 200: Success. File written.
        """

        state_machine_source = request.data

        ctrl_file_names = get_control_state_machine_files(exp_id)
        eval_file_names = get_evaluation_state_machine_files(exp_id)

        if state_machine_name not in ctrl_file_names and state_machine_name not in eval_file_names:
            raise NRPServicesClientErrorException("State machine not found: "
                                                  "{0}".format(state_machine_name), error_code=404)

        if state_machine_name in ctrl_file_names:
            filename = ctrl_file_names[state_machine_name]
        else:
            filename = eval_file_names[state_machine_name]

        filename = save_file(None, filename, state_machine_source)
        return {'message': "Success. File written: {0}".format(filename)}, 200


class ExperimentStorageStateMachine(Resource):
    """
    The resource to save experiment state machine files
    """
    @swagger.operation(
        notes='Saves state machines of an experiment to the storage',
        parameters=[
            {
                "name": "experiment_id",
                "required": True,
                "description": "The experiment_id of the experiment.",
                "paramType": "path",
                "dataType": basestring.__name__
            },
            {
                "name": "state_machines",
                "required": True,
                "description": "The state machine code",
                "paramType": "body",
                "dataType": basestring.__name__
            }
        ],
        responseMessages=[
            {
                "code": 500,
                "message": ErrorMessages.ERROR_SAVING_FILE_500
            },
            {
                "code": 400,
                "message": "State machine code should be sent in the body under the"
                           "'state_machines' key"
            },
            {
                "code": 200,
                "message": "Success. File written."
            }
        ]
    )
    def put(self, experiment_id):
        """
        Save state machines to the storage

        :param path experiment_id: The experiment_id id of the experiment
        :param body source_code: Source code of the state machine as string.
        :status 500: The experiment xml either could not be found or read
        :status 200: Success. File written.
        """
        # Done here in order to avoid circular dependencies introduced by the
        # way we __init__ the rest_server module.
        body = request.get_json(force=True)
        if 'state_machines' not in body:
            raise NRPServicesClientErrorException(
                "State machine code should be sent in "
                "the body under the 'state_machines' key"
            )

        from hbp_nrp_backend.storage_client_api.StorageClient \
            import StorageClient

        client = StorageClient()

        exp_xml_file_path = client.clone_file('experiment_configuration.exc',
                                              UserAuthentication.get_header_token(
                                                  request),
                                              experiment_id)

        if not exp_xml_file_path:
            return {"message": "Failed to clone experiment configuration file"}, 500

        experiment = client.parse_and_check_file_is_valid(
            exp_xml_file_path,
            exp_conf_api_gen.CreateFromDocument,
            exp_conf_api_gen.ExD_
        )

        if not experiment:
            return {"message": "Failed to parse experiment configuration file"}, 500

        threads = []
        for sm_name in body['state_machines']:
            sm_node = exp_conf_api_gen.SMACHStateMachine()
            sm_node.id = os.path.splitext(sm_name)[0]
            sm_node.src = sm_name if sm_name.endswith(
                ".exd") else sm_name + ".exd"
            exp_control = exp_conf_api_gen.ExperimentControl()
            exp_control.stateMachine.append(sm_node)
            experiment.experimentControl = exp_control
            t = Thread(target=client.create_or_update, kwargs={
                'token': UserAuthentication.get_header_token(request),
                'experiment': experiment_id,
                'filename': sm_node.src,
                'content': body['state_machines'][sm_name],
                'content_type': "application/hbp-neurorobotics.sm+python"})
            t.start()
            threads.append(t)

        t = Thread(target=client.create_or_update,
                   kwargs={
                       'token': UserAuthentication.get_header_token(request),
                       'experiment': experiment_id,
                       'filename': 'experiment_configuration.exc',
                       'content': experiment.toxml("utf-8"),
                       'content_type': "application/hbp-neurorobotics+xml"})
        t.start()
        threads.append(t)
        for thread in threads:
            thread.join()
        return {"message": "Success. Files written to the storage"}, 200
