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
This module contains REST services for handling simulations reset,
Using the storage
"""

__author__ = "Alessandro Ambrosano, Ugo Albanese, Georg Hinkel, Manos Angelidis"

import os
import tempfile
import shutil
import logging
import json

from cle_ros_msgs import srv, msg
from flask import request
from flask_restful import Resource, fields
from flask_restful_swagger import swagger

from hbp_nrp_backend.cle_interface.ROSCLEClient import ROSCLEClientException

from hbp_nrp_backend.rest_server import NRPServicesGeneralException, \
    NRPServicesWrongUserException, NRPServicesClientErrorException, \
    NRPServicesTransferFunctionException, ErrorMessages
from hbp_nrp_backend.rest_server.__SimulationControl import _get_simulation_or_abort
from hbp_nrp_backend.__UserAuthentication import UserAuthentication
from hbp_nrp_cleserver.bibi_config.bibi_configuration_script import generate_tf, \
    import_referenced_python_tfs, correct_indentation, get_tf_name, get_all_neurons_as_dict

from hbp_nrp_cleserver.server.ROSCLESimulationFactory import get_experiment_data
from hbp_nrp_commons.bibi_functions import docstring_parameter
from hbp_nrp_commons.generated import exp_conf_api_gen, bibi_api_gen
from distutils.dir_util import copy_tree  # pylint: disable=F0401,E0611

logger = logging.getLogger(__name__)

# pylint: disable=no-self-use


class SimulationResetStorage(Resource):
    """
    This resource handles the reset of a simulation, forwarding all the reset requests to the
    respective CLE instance.
    """

    @swagger.model
    class ResetRequest(object):
        """
        Represents a request for the API implemented by SimulationResetStorage
        """

        resource_fields = {'resetType': fields.Integer,
                           'contextId': fields.String()}
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
                "message": "Invalid request, the JSON parameters are incorrect"
            },
            {
                "code": 200,
                "message": "Success. The reset type requested was performed on the given "
                           "simulation"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SERVER_ERROR_500,
                         ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401)
    def put(self, sim_id, experiment_id):
        """
        Calls the CLE for resetting a given simulation to the last saved state in the storage.

        :param sim_id: The simulation ID.
        :param experiment_id: The experiment ID

        :> json resetType: the reset type the user wants to be performed, details about possible
                          values are given in
                          GazeboRosPackages/src/cle_ros_msgs/srv/ResetSimulation.srv

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
        context_id = body.get('contextId', None)

        for par in SimulationResetStorage.ResetRequest.required:
            if par not in body:
                raise NRPServicesClientErrorException(
                    'Missing parameter %s' % (par, ))

        for par in body:
            if par not in SimulationResetStorage.ResetRequest.resource_fields:
                raise NRPServicesClientErrorException(
                    'Invalid parameter %s' % (par, ))

        reset_type = body.get('resetType')

        world_sdf, brain_file, populations = SimulationResetStorage\
            ._compute_payload(reset_type, experiment_id, context_id)

        try:
            rsr = srv.ResetSimulationRequest
            if reset_type == rsr.RESET_FULL:
                SimulationResetStorage.resetFromStorageAll(
                    sim, experiment_id, context_id)
                sim.cle.reset(reset_type, world_sdf=world_sdf, brain_path=brain_file,
                              populations=populations)
            elif reset_type == rsr.RESET_BRAIN:
                SimulationResetStorage.resetBrain(
                    sim, experiment_id, context_id)
            else:
                sim.cle.reset(reset_type, world_sdf=world_sdf, brain_path=brain_file,
                              populations=populations)

        except ROSCLEClientException as e:
            raise NRPServicesGeneralException(str(e), 'CLE error', 500)

        return {}, 200

    @staticmethod
    def resetFromStorageAll(simulation, experiment_id, context_id):
        """
        Reset states machines and transfer functions

        :param: the simulation id
        :param: the experiment id
        :param: the context_id for collab based simulations
        """

        from hbp_nrp_backend.storage_client_api.StorageClient \
            import StorageClient

        client = StorageClient()

        _, experiment_file_paths = client.clone_all_experiment_files(
            UserAuthentication.get_header_token(request),
            experiment_id, new_folder=True)
        cloned_base_path = os.path.dirname(
            experiment_file_paths['experiment_conf'])

        current_experiment_path = simulation.lifecycle.experiment_path
        current_base_path = os.path.dirname(current_experiment_path)

        copy_tree(cloned_base_path, current_base_path)
        if tempfile.gettempdir() in cloned_base_path:
            shutil.rmtree(cloned_base_path)

        exp_conf, bibi_conf = get_experiment_data(current_experiment_path)

        SimulationResetStorage.resetBrain(
            simulation, experiment_id, context_id)

        SimulationResetStorage.resetTransferFunctions(simulation,
                                                      bibi_conf,
                                                      current_base_path)
        SimulationResetStorage.resetStateMachines(
            simulation, exp_conf, current_base_path)

    @staticmethod
    def resetBrain(simulation, experiment_id, context_id):
        """
        Reset brain

        :param simulation: simulation object
        :param experiment_id: the related experiment id
        :param context_id: the context ID for collab based simulations
        """
        brain_path, _, neurons_config = \
            SimulationResetStorage._get_brain_info_from_storage(
                experiment_id, context_id)

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

        with open(brain_path, 'r') as myfile:
            data = myfile.read()
            DO_CHANGE_POPULATION = 1
            result = simulation.cle.set_simulation_brain('py', data, "text", neurons_config,
                                                         DO_CHANGE_POPULATION)
            if result.error_message is not "":
                # Error in given brain
                raise ROSCLEClientException('{}, line:{}, column:{}, population_change:{}'
                                            .format(result.error_message, result.error_line,
                                                    result.error_column,
                                                    result.handle_population_change))

    @staticmethod
    def resetStateMachines(sim, experiment, sm_base_path):
        """
        Reset states machines

        :param sim:
        :param experiment: experiment conf
        :param sm_base_path: base path of the experiment
        """

        sim.delete_all_state_machines()

        state_machine_paths = {}
        if experiment.experimentControl is not None:
            state_machine_paths.update({sm.id: os.path.join(sm_base_path, sm.src)
                                        for sm in
                                        experiment.experimentControl.stateMachine
                                        if isinstance(sm, exp_conf_api_gen.SMACHStateMachine)})

        if experiment.experimentEvaluation is not None:
            state_machine_paths.update({sm.id: os.path.join(sm_base_path, sm.src)
                                        for sm in
                                        experiment.experimentEvaluation.stateMachine
                                        if isinstance(sm, exp_conf_api_gen.SMACHStateMachine)})

        sim.state_machine_manager.add_all(state_machine_paths, sim.sim_id)
        sim.state_machine_manager.initialize_all()

    @staticmethod
    def resetTransferFunctions(simulation, bibi_conf, base_path):
        """
        Reset transfer functions

        :param simulation: simulation object
        :param bibi_conf: BIBI conf
        :param base_path: base path of the experiment
        """
        old_tfs, _ = simulation.cle.get_simulation_transfer_functions()
        for tf in old_tfs:
            simulation.cle.delete_simulation_transfer_function(get_tf_name(tf))

        import_referenced_python_tfs(bibi_conf, base_path)

        for tf in bibi_conf.transferFunction:
            tf_code = generate_tf(tf, bibi_conf)
            tf_code = correct_indentation(tf_code, 0)
            tf_code = tf_code.strip() + "\n"
            logger.info(" RESET TF: " + tf.name + "\n" + tf_code + '\n')

            error_message = simulation.cle.add_simulation_transfer_function(
                str(tf_code)
            )
            if error_message:
                raise NRPServicesTransferFunctionException(
                    "Transfer function patch failed: "
                    + str(error_message) + "\n"
                    + "Updated source:\n"
                    + str(tf_code)
                )

    @staticmethod
    def _compute_payload(reset_type, experiment_id, context_id):
        """
        Compute the payload corresponding to a certain reset type

        :param reset_type:
        :param experiment_id: the experiment needed by RESET_WORLD
        :param context_id: the context ID for collab based simulations
        :return: the payload for the reset request: a tuple of (world_sdf, brain_path, populations)
        """

        rsr = srv.ResetSimulationRequest

        if reset_type == rsr.RESET_WORLD:
            return \
                SimulationResetStorage._get_sdf_world_from_storage(
                    experiment_id, context_id), None, None
        elif reset_type == rsr.RESET_BRAIN:
            brain, populations, _ = SimulationResetStorage._get_brain_info_from_storage(
                experiment_id, context_id)
            return None, brain, populations
        elif reset_type == rsr.RESET_FULL:
            world_sdf = SimulationResetStorage._get_sdf_world_from_storage(
                experiment_id, context_id)
            brain, populations, _ = SimulationResetStorage._get_brain_info_from_storage(
                experiment_id, context_id)
            return world_sdf, brain, populations
        else:
            return None, None, None

    @staticmethod
    def _get_brain_info_from_storage(experiment_id, context_id):
        """
        Gathers from the storage the brain script and the populations by getting the BIBI
        configuration file.

        :param experiment_id: the id of the experiment in which to look for the brain information
        :param context_id: the context ID for collab based simulations
        :return: A tuple with the path to the brain file and a list of populations
        """

        from hbp_nrp_backend.storage_client_api.StorageClient \
            import StorageClient

        client = StorageClient()

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
        brain_filename = os.path.split(bibi_file_obj.brainModel.file)[-1]
        brain_file_path = os.path.join(
            client.get_temp_directory(), brain_filename)

        if 'storage://' in bibi_file_obj.brainModel.file:
            with open(brain_file_path, "w") as f:
                f.write(client.get_file(
                    UserAuthentication.get_header_token(request),
                    client.get_folder_uuid_by_name(UserAuthentication.get_header_token(request),
                                                   context_id,
                                                   'brains'),
                    brain_filename,
                    byname=True))

        else:
            brain_file_path = client.clone_file(
                brain_filename,
                UserAuthentication.get_header_token(request),
                experiment_id
            )

        neurons_config = get_all_neurons_as_dict(
            bibi_file_obj.brainModel.populations)

        neurons_config_clean = [
            SimulationResetStorage._get_experiment_population(name, v)
            for (name, v) in neurons_config.iteritems()
        ]
        return brain_file_path, neurons_config_clean, neurons_config

    @staticmethod
    def _get_experiment_population(name, value):
        """
        Gets an ExperimentPopulation object for the given population

        :param name: The population name
        :param value: The value describing the population
        :return:
        """
        if value is None:
            return msg.ExperimentPopulationInfo(name=name, type=0, ids=[], start=0, stop=0, step=0)
        elif isinstance(value, slice):
            return msg.ExperimentPopulationInfo(name=name, type=1, ids=[], start=value.start,
                                                stop=value.stop, step=value.step)
        elif isinstance(value, list):
            return msg.ExperimentPopulationInfo(name=name, type=2, ids=value, start=0,
                                                stop=0, step=0)

    @staticmethod
    def _get_sdf_world_from_storage(experiment_id, context_id):
        """
        Download from the storage an sdf world file as a string.
        The file belongs to the experiment identified by experiment_id

        :param experiment_id: the ID of the experiment in which to look for the world sdf
        :param context_id: the context ID for collab based simulations
        :return: The content of the world sdf file
        """

        # Done here in order to avoid circular dependencies introduced by the
        # way we __init__ the rest_server module.
        from hbp_nrp_backend.storage_client_api.StorageClient \
            import StorageClient

        client = StorageClient()

        # find the sdf filename from the .exc
        experiment_file = client.get_file(
            UserAuthentication.get_header_token(request),
            experiment_id,
            'experiment_configuration.exc',
            byname=True)

        world_file_name = exp_conf_api_gen.CreateFromDocument(
            experiment_file).environmentModel.src

        if 'storage://' in world_file_name:
            return client.get_file(
                UserAuthentication.get_header_token(request),
                client.get_folder_uuid_by_name(UserAuthentication.get_header_token(request),
                                               context_id,
                                               'environments'),
                os.path.basename(world_file_name),
                byname=True)
        else:
            return client.get_file(
                UserAuthentication.get_header_token(request),
                experiment_id,
                world_file_name,
                byname=True)
