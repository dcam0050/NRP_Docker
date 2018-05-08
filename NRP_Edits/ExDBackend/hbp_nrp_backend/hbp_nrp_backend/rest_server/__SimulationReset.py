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
This module contains REST services for handling simulations reset.
"""

__author__ = "Alessandro Ambrosano"

import os
import logging
import json
import tempfile

from flask import request
from flask_restful import Resource, fields
from flask_restful_swagger import swagger

from hbp_nrp_backend.cle_interface.ROSCLEClient import ROSCLEClientException

from hbp_nrp_backend.rest_server import NRPServicesGeneralException, \
    NRPServicesWrongUserException, NRPServicesClientErrorException, \
    NRPServicesTransferFunctionException, ErrorMessages
from hbp_nrp_backend.rest_server.__SimulationControl import _get_simulation_or_abort
from hbp_nrp_backend.__UserAuthentication import UserAuthentication

from cle_ros_msgs.srv import ResetSimulationRequest
from hbp_nrp_backend.rest_server.__ExperimentService import get_experiment_basepath
from hbp_nrp_backend.rest_server.__ExperimentService import get_model_basepath
from hbp_nrp_cleserver.server.ROSCLESimulationFactory import get_experiment_data
from hbp_nrp_cleserver.bibi_config.bibi_configuration_script import get_all_neurons_as_dict

from hbp_nrp_cleserver.bibi_config.bibi_configuration_script import generate_tf, \
    import_referenced_python_tfs, correct_indentation, get_tf_name

from hbp_nrp_commons.generated import exp_conf_api_gen
from hbp_nrp_commons.bibi_functions import docstring_parameter

logger = logging.getLogger(__name__)

# pylint: disable=no-self-use


class SimulationReset(Resource):
    """
    This resource handles the reset of a simulation, forwarding all the reset requests to the
    respective CLE instance.
    """

    @swagger.model
    class ResetRequest(object):
        """
        Represents a request for the API implemented by SimulationReset
        """

        resource_fields = {'resetType': fields.Integer}
        required = ['resetType']

    @swagger.operation(
        notes='Handles the reset of a given simulation.',
        parameters=[
            {
                "name": "sim_id",
                "description": "The ID of the simulation whose state shall be retrieved",
                "required": True,
                "paramType": "path",
                "dataType": int.__name__
            },
            {
                "name": "body",
                "paramType": "body",
                "dataType": ResetRequest.__name__,
                "required": True
            }
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
                "code": 400,
                "message": "Invalid request, the JSON parameters are incorrect."
            },
            {
                "code": 200,
                "message": "Success. The reset type requested was performed on the given simulation"
            },
        ]
    )
    @docstring_parameter(ErrorMessages.SERVER_ERROR_500,
                         ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401)
    def put(self, sim_id):
        """
        Calls the CLE for resetting a given simulation.

        :param sim_id: The simulation ID.

        :> json resetType: the reset type the user wants to be performed, details about possible
            values are given in GazeboRosPackages/src/cle_ros_msgs/srv/ResetSimulation.srv

        :status 500: {0}
        :status 404: {1}
        :status 401: {2}
        :status 400: Invalid request, the JSON parameters are incorrect
        :status 200: The requested reset was performed successfully
        """

        sim = _get_simulation_or_abort(sim_id)

        if not UserAuthentication.matches_x_user_name_header(request, sim.owner):
            raise NRPServicesWrongUserException()

        body = request.get_json(force=True)

        for par in SimulationReset.ResetRequest.required:
            if par not in body:
                raise NRPServicesClientErrorException(
                    'Missing parameter %s' % (par, ))

        for par in body:
            if par not in SimulationReset.ResetRequest.resource_fields:
                raise NRPServicesClientErrorException(
                    'Invalid parameter %s' % (par, ))

        try:
            reset_type = body.get('resetType')
            if reset_type == ResetSimulationRequest.RESET_FULL:
                SimulationReset.reset_brain(sim)
                SimulationReset.reset_transfer_functions(sim)
                SimulationReset.reset_state_machines(sim)
                sim.cle.reset(reset_type)
            elif reset_type == ResetSimulationRequest.RESET_BRAIN:
                SimulationReset.reset_brain(sim)
            else:
                sim.cle.reset(reset_type)

        except ROSCLEClientException as e:
            raise NRPServicesGeneralException(str(e), 'CLE error', 500)

        return {}, 200

    @staticmethod
    def reset_state_machines(sim):
        """
        Reset states machines
        """

        sim.delete_all_state_machines()

        sm_base_path = get_experiment_basepath()
        experiment_basepath = os.path.join(sm_base_path, sim.experiment_conf)
        experiment, _ = get_experiment_data(str(experiment_basepath))
        if experiment is None:
            return

        state_machine_paths = {}
        if experiment.experimentControl is not None:
            state_machine_paths.update({
                sm.id: os.path.join(os.path.dirname(experiment_basepath), sm.src)
                for sm in experiment.experimentControl.stateMachine
                if isinstance(sm, exp_conf_api_gen.SMACHStateMachine)})

        if experiment.experimentEvaluation is not None:
            state_machine_paths.update({
                sm.id: os.path.join(os.path.dirname(experiment_basepath), sm.src)
                for sm in experiment.experimentEvaluation.stateMachine
                if isinstance(sm, exp_conf_api_gen.SMACHStateMachine)})

        sim.state_machine_manager.add_all(state_machine_paths, sim.sim_id)
        sim.state_machine_manager.initialize_all()

    @staticmethod
    def reset_brain(sim):
        """
        Reset populations

        :param sim:
        """

        experiments_base_path = os.path.join(
            get_experiment_basepath(), sim.experiment_conf)
        models_base_path = get_model_basepath()
        _, bibi_conf = get_experiment_data(str(experiments_base_path))
        if bibi_conf is None:
            return

        neurons_config = get_all_neurons_as_dict(
            bibi_conf.brainModel.populations)

        # Convert the populations to a JSON dictionary
        for (name, s) in neurons_config.iteritems():
            v = dict()
            v['from'] = s.start
            v['to'] = s.stop
            if s.step <= 0:
                v['step'] = 1
            else:
                v['step'] = s.step

            neurons_config[name] = v

        neurons_config = json.dumps(neurons_config)
        if 'storage://' in bibi_conf.brainModel.file:
            for entry in os.listdir(tempfile.gettempdir()):
                if entry.startswith('nrpTemp'):
                    brain_path = os.path.join(tempfile.gettempdir(),
                                              entry,
                                              os.path.basename(bibi_conf.brainModel.file))
        else:
            brain_path = os.path.join(
                models_base_path, bibi_conf.brainModel.file)

        with open(brain_path, 'r') as myfile:
            data = myfile.read()
            DO_CHANGE_POPULATION = 1
            result = sim.cle.set_simulation_brain('py', data, "text", neurons_config,
                                                  DO_CHANGE_POPULATION)
            if result.error_message is not "":
                # Error in given brain
                raise ROSCLEClientException('{}, line:{}, column:{}, population_change:{}'
                                            .format(result.error_message, result.error_line,
                                                    result.error_column,
                                                    result.handle_population_change))

    @staticmethod
    def reset_transfer_functions(sim):
        """
        Reset transfer functions
        """
        # Delete all TFs
        old_tfs, _ = sim.cle.get_simulation_transfer_functions()
        for tf in old_tfs:
            sim.cle.delete_simulation_transfer_function(get_tf_name(tf))

        experiment_basepath = os.path.join(
            get_experiment_basepath(), sim.experiment_conf)
        _, bibi_conf = get_experiment_data(str(experiment_basepath))
        if bibi_conf is None:
            return

        # Reset Transfer functions
        import_referenced_python_tfs(
            bibi_conf, os.path.dirname(experiment_basepath))

        for tf in bibi_conf.transferFunction:
            tf_code = generate_tf(tf, bibi_conf)
            tf_code = correct_indentation(tf_code, 0)
            tf_code = tf_code.strip() + "\n"

            error_message = sim.cle.add_simulation_transfer_function(
                str(tf_code)
            )
            if error_message:
                raise NRPServicesTransferFunctionException(
                    "Transfer function patch failed: "
                    + str(error_message) + "\n"
                    + "Updated source:\n"
                    + str(tf_code)
                )
