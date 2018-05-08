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
for retrieving Experiment names and IDs, as well as some functions used by other
classes that retrieve experiment related files.
"""

__author__ = "Bernd Eckstein"

import os
import base64
import logging

from flask_restful import Resource, fields
from flask_restful_swagger import swagger

from hbp_nrp_backend.rest_server import NRPServicesClientErrorException, \
    NRPServicesGeneralException, ErrorMessages
from hbp_nrp_backend.__UserAuthentication import UserAuthentication
from hbp_nrp_backend.rest_server.RestSyncMiddleware import RestSyncMiddleware

from hbp_nrp_commons.generated import exp_conf_api_gen, bibi_api_gen
from hbp_nrp_commons.bibi_functions import docstring_parameter

from flask import request
from pyxb import ValidationError


# pylint: disable=no-self-use
# because pylint detects experiment.get_bibiConf() as no member:
# pylint: disable=maybe-no-member


LOG = logging.getLogger(__name__)


@swagger.model
class ExperimentObject(object):
    """
    Swagger documentation object
    Experiment definition
    """
    resource_fields = {
        "name": fields.String(),
        "experimentConfiguration": fields.String(),
        "description": fields.String(),
        "tags": fields.List(fields.String),
        "timeout": fields.Integer(),
        "maturity": fields.String(),
        "cameraPose": fields.List(fields.Float),
        "visualModel": fields.String(),
        "visualModelParams": fields.List(fields.Float),
        "brainProcesses": fields.Integer()
    }
    required = ['name', 'experimentConfiguration', 'description', 'tags', 'timeout', 'maturity',
                'cameraPose', 'visualModel', 'visualModelParams', 'brainProcesses']


@swagger.model
@swagger.nested(exp_id=ExperimentObject.__name__)
class ExperimentDictionary(object):
    """
    Swagger documentation object
    ExperimentDictionary ... tried to make it look like a dictionary for the swagger doc
    """
    resource_fields = {
        'exp_id': fields.Nested(ExperimentObject.resource_fields)
    }
    required = ['exp_id']


@swagger.model
@swagger.nested(data=ExperimentDictionary.__name__)
class ExperimentData(object):
    """
    Swagger documentation object
    Main Data Attribute for parsing convenience on the frontend side.
    """
    resource_fields = {
        'data': fields.Nested(ExperimentDictionary.resource_fields)
    }
    required = ['data']


class Experiment(Resource):
    """
    Implements the REST service for retrieving all stored experiments
    as a dictionary
    """

    @swagger.operation(
        notes="Gets dictionary of experiments",
        responseClass=ExperimentData.__name__,
        responseMessages=[
            {
                "code": 500,
                "message": ErrorMessages.MOD_VARIABLE_ERROR
            },
            {
                "code": 200,
                "message": "Success. The experiment list was sent."
            }
        ]
    )
    @RestSyncMiddleware.threadsafe
    @docstring_parameter(ErrorMessages.MOD_VARIABLE_ERROR)
    def get(self):
        """
        Gets dictionary of experiments stored on the server.

        :return: Dictionary with experiments

        :status 500: {0}
        :status 200: Success. The experiment list was sent
        """
        experiments = dict(data=get_experiments())
        return experiments, 200


class StorageExperiment(Resource):
    """
    Implements the REST service for retrieving a storage experiment
    as a dictionary
    """
    @swagger.operation(
        notes="Gets dictionary of experiment",
        responseClass=ExperimentData.__name__,
        responseMessages=[
            {
                "code": 500,
                "message": "Error on server: storage experiment not found."
            },
            {
                "code": 200,
                "message": "Success. The experiment list was sent."
            }
        ]
    )
    def get(self, experiment_id):
        """
        Gets dictionary of the experiment stored on the storage
        :param: experiment_id the id of the storage experiment
        :return: Dictionary with experiment
        :status 500: Error on server: storage experiment file not found
        :status 200: Success. The dictionary was returned
        """
        return dict(data=get_storage_experiment(experiment_id)), 200


def get_experiments(empty_experiment=False):
    """
    Read all available Experiments from disk, and add to dictionary

    :return dictionary: with string: ID, string: ExDConfig File
    """
    experiment_names = os.listdir(get_experiment_basepath())
    if empty_experiment:
        filtered_experiment_names = [
            x for x in experiment_names if x.startswith('.')]
    else:
        filtered_experiment_names = [
            x for x in experiment_names if not x.startswith('.')]
    experiment_dict = {}

    for current_dir in filtered_experiment_names:
        current_path = os.path.join(get_experiment_basepath(), current_dir)
        if not os.path.isdir(current_path):
            continue
        for current in os.listdir(current_path):
            if current.lower().endswith('.exc'):
                # Parse Experiment
                experiment_conf = os.path.join(current_path, current)
                ex = parse_exp(experiment_conf)
                if isinstance(ex, exp_conf_api_gen.ExD_):
                    current_exp = _make_experiment(ex, current, current_path)
                    experiment_dict[os.path.splitext(current)[0]] = current_exp
    return experiment_dict


def parse_exp(experiment_conf):
    """
    Parse an experiment xml file.

    :param experiment_conf: the experiment configuration file to parse
    :return the parsed xml
    """
    with open(experiment_conf) as exd_file:
        try:
            return exp_conf_api_gen.CreateFromDocument(exd_file.read())
        except ValidationError, ve:
            LOG.warn("Could not parse experiment configuration %s due to validation "
                     "error: %s", experiment_conf, str(ve))


def get_storage_experiment(experiment_id):
    """
    Retrieve the storage experiment from the storage, and add to dictionary
    :param experiment_id: The experiment id
    :return dictionary: with string: ID, string: ExDConfig File
    """
    from hbp_nrp_backend.storage_client_api.StorageClient \
        import StorageClient

    client = StorageClient()

    exp_xml_file_path = client.clone_file('experiment_configuration.exc',
                                          UserAuthentication.get_header_token(
                                              request),
                                          experiment_id)
    experiment = client.parse_and_check_file_is_valid(
        exp_xml_file_path,
        exp_conf_api_gen.CreateFromDocument,
        exp_conf_api_gen.ExD_
    )
    current_exp = _make_experiment(experiment)
    result = {os.path.splitext(os.path.split(
        exp_xml_file_path)[-1])[0]: current_exp}
    return result


def _make_experiment(experiment, experiment_file='', experiment_dir=''):
    """
    Creates and returns an dictionary with the experiment data

    :param experiment_file: filename of the XML containing the experiment
    :param experiment: the parsed experiment
    :param experiment_dir: the directory containing the XML file of the experiment
    :return dictionary with the experiment data
    """

    _timeout = experiment.timeout
    _name = experiment.name
    _description = experiment.description
    _maturity = experiment.maturity
    _cameraPoseObj = experiment.cameraPose
    _cameraPose = None
    _visualModelObj = experiment.visualModel
    _visualModel = None
    _visualModelParams = None
    _brainProcesses = experiment.bibiConf.processes

    if _timeout is None:
        _timeout = 600
    if _name is None:
        _name = os.path.splitext(experiment_file)[0]
    if _description is None:
        _description = "No description available for this experiment."
    # Axel: maturity can be "development" or "production"
    if _maturity is None or (_maturity != "development" and _maturity != "production"):
        _maturity = "development"
    if _cameraPoseObj:
        _cameraPose = [_cameraPoseObj.cameraPosition.x, _cameraPoseObj.cameraPosition.y,
                       _cameraPoseObj.cameraPosition.z, _cameraPoseObj.cameraLookAt.x,
                       _cameraPoseObj.cameraLookAt.y, _cameraPoseObj.cameraLookAt.z]
    if _visualModelObj:
        _visualModel = _visualModelObj.src
        _visualModelParams = [_visualModelObj.visualPose.x, _visualModelObj.visualPose.y,
                              _visualModelObj.visualPose.z, _visualModelObj.visualPose.ux,
                              _visualModelObj.visualPose.uy, _visualModelObj.visualPose.uz,
                              _visualModelObj.scale if _visualModelObj.scale else 1.0]

    current_exp = dict(name=_name,
                       description=_description,
                       tags=experiment.tags if experiment.tags else [],
                       experimentConfiguration=os.path.join(
                           experiment_dir, experiment_file),
                       timeout=_timeout,
                       maturity=_maturity,
                       cameraPose=_cameraPose,
                       visualModel=_visualModel,
                       visualModelParams=_visualModelParams,
                       brainProcesses=_brainProcesses)
    return current_exp


def save_file(base64_data, filename_abs, data=None):
    """
    Save a file, encoded as base64_data to specified filename_abs

    :param base64_data:  base64 encoded data
    :param filename_abs: the absolute filename
    :param data: use instead of base64_data, when you wand to write a string as-is to the disk
    :return filename (string), when file is saved
    :exception NRPServicesClientErrorException, errorNo: 401: Error in base64
    """

    if data is None:
        try:
            data = base64.decodestring(base64_data)
        except Exception as _ex:
            raise NRPServicesClientErrorException(
                ErrorMessages.ERROR_IN_BASE64_400.format(_ex.message)
            )

    base_path = os.path.abspath(filename_abs)
    allowed_path = get_experiment_basepath()

    if base_path.startswith(allowed_path):
        pass
    else:
        LOG.error("Path not accepted: '{0}' is not a subdirectory of allowed path: '{1}'."
                  .format(base_path, allowed_path))
        raise NRPServicesGeneralException(ErrorMessages.ERROR_SAVING_FILE_500,
                                          "Server Error: {0}, {1}".format(base_path,
                                                                          allowed_path), 500)

    filename = "{0}_new".format(filename_abs)
    with open(filename, 'wb') as _file:
        _file.write(data)
        return filename


def get_experiment_basepath():
    """
    :return: path given in the environment variable 'NRP_EXPERIMENTS_DIRECTORY'
    """

    path = os.environ.get('NRP_EXPERIMENTS_DIRECTORY')
    if path is None:
        raise NRPServicesGeneralException(
            ErrorMessages.EXP_VARIABLE_ERROR, "Server Error", 500)

    return path


def get_model_basepath():
    """
    :return: path given in the environment variable 'NRP_MODELS_DIRECTORY'
    """

    path = os.environ.get('NRP_MODELS_DIRECTORY')
    if path is None:
        raise NRPServicesGeneralException(
            ErrorMessages.MOD_VARIABLE_ERROR, "Server Error", 500)

    return path


def get_experiment_rel(exp_id):
    """
    Given an experiment id it returns the experiment dictionary containing the experiment files'
    paths and returns the experiment configuration relative path.
    In case we are launching a new experiment we are returning the path to the empty template
    experiment.

    :return: relative name of the experiment xml
    """
    if exp_id == 'newExperiment':
        empty_experiment_dict = get_experiments(empty_experiment=True)
        empty_experiment_file_path = \
            empty_experiment_dict['TemplateEmpty']['experimentConfiguration']
        return empty_experiment_file_path

    experiment_dict = get_experiments()
    if exp_id not in experiment_dict:
        raise NRPServicesClientErrorException(
            ErrorMessages.EXPERIMENT_NOT_FOUND_404,
            error_code=404
        )

    # Gets Experiments relative filename
    experiment_file = experiment_dict[exp_id]['experimentConfiguration']
    return experiment_file


def get_experiment_conf(exp_id):
    """
    Gets the filename of the conf file

    :param exp_id: id of the experiment
    :return Absolute path to experiment xml file
    """
    experiment_file = get_experiment_rel(exp_id)
    experiment_conf = os.path.join(get_experiment_basepath(), experiment_file)
    return experiment_conf


def get_bibi_file(exp_id, experiment_file=None):
    """
    Gets the filename of the bibi file

    :param exp_id: id of the experiment
    :param experiment_file: The experiment file path
    :return Absolute path to experiment bibi file
    """
    if experiment_file is None:
        experiment_file = get_experiment_conf(exp_id)

    # parse experiment configuration
    with open(experiment_file) as exd_file:
        experiment = exp_conf_api_gen.CreateFromDocument(exd_file.read())
    assert isinstance(experiment, exp_conf_api_gen.ExD_)
    bibi_file = experiment.bibiConf.src
    bibi_conf = os.path.join(os.path.dirname(experiment_file), bibi_file)
    return bibi_conf


def get_brain_file(exp_id):
    """
    Gets the brain filename

    :param exp_id: id of the experiment
    :return: Absolute path to experiment brain file
    """
    experiment_file = get_experiment_conf(exp_id)
    bibi_file_name = get_bibi_file(exp_id, experiment_file)
    with open(bibi_file_name) as bibi_file:
        bibi = bibi_api_gen.CreateFromDocument(bibi_file.read())
        assert isinstance(bibi, bibi_api_gen.BIBIConfiguration)
        brain_file_name = bibi.brainModel.file
        return os.path.join(os.path.dirname(experiment_file), brain_file_name)


def get_control_state_machine_files(exp_id):
    """
    Gets the control state machine file names

    :param exp_id: id of the experiment
    :return Dict with name, Absolute path to state machine files
    """
    return _get_state_machine_files(exp_id, 'control')


def get_evaluation_state_machine_files(exp_id):
    """
    Gets the evaluation state machine file names

    :param exp_id: id of the experiment
    :return Dict with name, Absolute path to state machine files
    """
    return _get_state_machine_files(exp_id, 'evaluation')


def _get_state_machine_files(exp_id, which):
    """
    Gets the state machine file names

    :param exp_id: id of the experiment
    :param string which: 'control' or 'evaluation'
    :return: Dict with name, Absolute path to state machine files
    """
    ret = dict()
    experiment_file = get_experiment_conf(exp_id)
    # parse experiment configuration
    with open(experiment_file) as exd_file:
        experiment = exp_conf_api_gen.CreateFromDocument(exd_file.read())

    assert isinstance(experiment, exp_conf_api_gen.ExD_)

    if which is 'control':
        files = experiment.experimentControl
    elif which is 'evaluation':
        files = experiment.experimentEvaluation

    if files:
        exp_dir = os.path.dirname(experiment_file)
        for sm in files.stateMachine:
            if isinstance(sm, exp_conf_api_gen.SMACHStateMachine):
                ret[sm.id] = os.path.join(exp_dir, sm.src)

    return ret
