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
Wrapper around the storage API
"""

import os
import logging
import tempfile
import requests
import shutil
from hbp_nrp_backend.config import Config
from pyxb import ValidationError
from xml.sax import SAXParseException
from hbp_nrp_backend.rest_server import NRPServicesGeneralException
from hbp_nrp_commons.generated import exp_conf_api_gen

__author__ = "Manos Angelidis"
logger = logging.getLogger(__name__)


class StorageClient(object):
    """
    Wrapper around the storage server API. Users of this class should first
    call the authentication function to retrieve a token, before making the
    requests to the storage server
    """

    def __init__(self):
        """
        Creates the storage client
        """

        def make_temp_directory():
            """
            Returns a temp directory where all the simulation related files are
            stored. This directory starts with nrpTemp

            :return the path to the temporary directory
            """
            for entry in os.listdir(tempfile.gettempdir()):
                if entry.startswith('nrpTemp'):
                    return os.path.join(tempfile.gettempdir(), entry)
            return None
        self.__proxy_url = Config.LOCAL_STORAGE_URI['storage_uri']
        if not make_temp_directory():
            self.__temp_directory = tempfile.mkdtemp(
                prefix="nrpTemp", suffix="")
        else:
            self.__temp_directory = make_temp_directory()

    def get_temp_directory(self):
        """
        Returns the temporary directory where all the simulation based files are stored
        """
        return self.__temp_directory

    # Wrappers around the storage API
    def authenticate(self, user, password):
        """
        Authenticates the user based on the user name and password
        :param user: the username of the user
        :param password: the password of the user
        :return: the token
        """
        try:
            res = requests.post(self.__proxy_url +
                                '/authentication/authenticate',
                                json={"user": user, "password": password})
            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(
                    'Failed to communicate with the storage server, status code ' +
                    str(res.status_code))
            else:
                return res.json()
        except requests.exceptions.ConnectionError, err:
            logger.exception(err)
            raise err

    def list_experiments(self, token, context_id, get_all=False, name=None):
        """
        Lists the experiments the user has access to depending on his token
        :param token: a valid token to be used for the request
        :param context_id: the context_id if we are using collab storage
        :param get_all: a parameter to return all the available experiments,
                        not only the ones available to a specific user
        :param name: if we want to get a specific folder i.e. the robots
        :return: an array of all the available to the user experiments
        """
        headers = {'Authorization': 'Bearer ' +
                   token, 'context-id': context_id}

        try:
            url = self.__proxy_url + '/storage/experiments'
            if get_all and name:
                url += '?all=true&filter=' + name
            elif name:
                url += '?filter=' + name
            elif get_all:
                url += '?all=true'
            res = requests.get(url, headers=headers)

            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(
                    'Failed to communicate with the storage server, status code ' +
                    str(res.status_code))
            else:
                return res.json()
        except requests.exceptions.ConnectionError, err:
            logger.exception(err)
            raise err

    def get_file(self, token, experiment, filename, byname=False, zipped=False):
        """
        Gets a file under an experiment based on the filename
        :param token: a valid token to be used for the request
        :param experiment: the name of the experiment
        :param filename: the name of the file to return
        :return: if successful, the content of the file
        """
        try:
            headers = {'Authorization': 'Bearer ' + token}
            if not byname:
                res = requests.get(self.__proxy_url +
                                   '/storage/{0}/{1}'.format(
                                       experiment, filename), headers=headers)
            else:
                res = requests.get(self.__proxy_url +
                                   '/storage/{0}/{1}?byname=true'.format(
                                       experiment, filename), headers=headers)
            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(
                    'Failed to communicate with the storage server, status code '
                    + str(res.status_code))
            if zipped:
                return res.content
            else:
                return res.text
        except requests.exceptions.ConnectionError, err:
            logger.exception(err)
            raise err

    def delete_file(self, token, experiment, filename):
        """
        Deletes a file under under an experiment based on the
        experiment name and the filename. Needs the user token
        :param token: a valid token to be used for the request
        :param experiment: the name of the experiment
        :param filename: the name of the file to delee
        :return: if successful, the name of the deleted file
        """
        headers = {'Authorization': 'Bearer ' + token}
        try:
            res = requests.delete(self.__proxy_url +
                                  '/storage/{0}/{1}'.format(
                                      experiment, filename), headers=headers)
            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(
                    'Failed to communicate with the storage server, status code '
                    + str(res.status_code))
            else:
                return "Success"
        except requests.exceptions.ConnectionError, err:
            logger.exception(err)
            raise err

    def create_or_update(self, token, experiment, filename, content, content_type):
        """
        Creates or updates a file under an experiment
        :param token: a valid token to be used for the request
        :param experiment: the name of the experiment
        :param filename: the name of the file to update/create
        :param content: the content of the file
        :param content_type: the content type of the file i.e. text/plain or
        aplication/octet-stream
        """
        try:
            headers = {'content-type': content_type,
                       'Authorization': 'Bearer ' + token}
            res = requests.post(self.__proxy_url +
                                '/storage/{0}/{1}'.format(
                                    experiment, filename),
                                headers=headers, data=content)
            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(
                    'Failed to communicate with the storage server, status code '
                    + str(res.status_code))
            else:
                return res.status_code
        except requests.exceptions.ConnectionError, err:
            logger.exception(err)
            raise err

    def create_folder(self, token, experiment, name):
        """
        Creates a folder under an experiment. If the folder exists we reuse it
        :param token: a valid token to be used for the request
        :param experiment: the name of the experiment
        :param name: the name of the folder to create
        """
        try:
            headers = {'Authorization': 'Bearer ' + token}
            res = requests.post(self.__proxy_url +
                                '/storage/{0}/{1}{2}'.format(
                                    experiment, name, '?type=folder'),
                                headers=headers)
            if res.status_code == 400:
                logger.info('The folder with the name {0} already exists in the storage, \
                reusing'.format(name))
                return 200
            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(
                    'Failed to communicate with the storage server, status code '
                    + str(res.status_code))
            else:
                return res.json()
        except requests.exceptions.ConnectionError, err:
            logger.exception(err)
            raise err

    def list_files(self, token, experiment):
        """
        Lists all the files under an experiment based on the
        experiment name and the user token
        :param token: a valid token to be used for the request
        :param experiment: the name of the experiment
        :return: if successful, the files under the experiment
        """
        try:
            headers = {
                'Authorization': 'Bearer ' + token,
            }
            res = requests.get(self.__proxy_url +
                               '/storage/{0}'.format(
                                   experiment), headers=headers)
            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(
                    'Failed to communicate with the storage server, status code '
                    + str(res.status_code))
            else:
                results = []
                # we have to filter out the folders
                for entry in res.json():
                    if entry['type'] == 'file':
                        results.append(entry)
                return results
        except requests.exceptions.ConnectionError, err:
            logger.exception(err)
            raise err

    def get_custom_models(self, token, context_id, folder_name):
        """
        Returns the contents of a custom models folder provided its name
        :param token: a valid token to be used for the request
        :param context_id: the context_id of the collab
        :param folder_name: the name of the folder
        :return: if found, the uuid of the named folder
        """
        try:
            headers = {
                'Authorization': 'Bearer ' + token,
                'context-id': context_id
            }
            res = requests.get(self.__proxy_url +
                               '/storage/custommodels/{0}'.format(
                                   folder_name), headers=headers)
            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(
                    'Failed to communicate with the storage server, status code '
                    + str(res.status_code))
            else:
                return res.json()
        except requests.exceptions.ConnectionError, err:
            logger.exception(err)
            raise err

    def get_custom_model(self, token, context_id, model_path):
        """
        Returns a custom model provided its path
        :param token: a valid token to be used for the request
        :param context_id: the context_id of the collab
        :param folder_name: the name of the folder
        :return: if found, the uuid of the named folder
        """
        try:
            headers = {
                'Authorization': 'Bearer ' + token,
                'context-id': context_id
            }
            res = requests.get(self.__proxy_url +
                               '/storage/custommodel/{0}'.format(
                                   model_path), headers=headers)
            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(
                    'Failed to communicate with the storage server, status code '
                    + str(res.status_code))
            else:
                return res.content
        except requests.exceptions.ConnectionError, err:
            logger.exception(err)
            raise err

    # HELPER FUNCTIONS
    def clone_file(self, filename, token, experiment):
        """
        Clones a file according to a given filename to a temporary folder.
        The caller has then the responsibility of managing this folder.

        :param filename: The filename of the file to clone
        :param token: The token of the request
        :param filename: The experiment which contains the file
        :return: The local path of the cloned file,
        """
        found = False
        for folder_entry in self.list_files(token, experiment):
            if filename in folder_entry['name']:
                found = True
        if found:
            clone_destination = os.path.join(self.__temp_directory, filename)
            with open(clone_destination, "w") as f:
                f.write(self.get_file(
                    token, experiment, filename, byname=True))
            return clone_destination
        else:
            return None

    def clone_all_experiment_files(self, token, experiment, new_folder=False):
        """
        Clones all the experiment files to a temporary folder.
        The caller has then the responsibility of managing this folder.

        :param token: The token of the request
        :param experiment: The experiment to clone
        :param new_folder: specifies whether we want to clone the files again
        or use the existing temporary nrpTemp folder. Used in reset
        :return: A dictionary containing the paths to the experiment files
        as well as the path to the temporary folder
        """
        experiment_paths = dict()
        list_files_to_clone = self.list_files(token, experiment)
        if new_folder:
            destination_directory = tempfile.mkdtemp()
        else:
            destination_directory = self.get_temp_directory()
        for file_under_experiment in list_files_to_clone:
            file_clone_destination = os.path.join(
                destination_directory, file_under_experiment['name'])
            with open(file_clone_destination, "w") as f:
                zipped = os.path.splitext(file_under_experiment['name'])[
                    1].lower() == '.zip'
                file_contents = self.get_file(
                    token, experiment, file_under_experiment['name'], byname=True, zipped=zipped)
                # in order to return the environment and experiment path we have
                # to read the .exc
                if 'experiment_configuration.exc' in str(file_clone_destination):
                    experiment_paths[
                        'experiment_conf'] = file_clone_destination
                    env_filename = exp_conf_api_gen.CreateFromDocument(
                        file_contents).environmentModel.src
                    experiment_paths['environment_conf'] = os.path.join(
                        destination_directory, env_filename)
                f.write(file_contents)
        return destination_directory, experiment_paths

    @staticmethod
    def parse_and_check_file_is_valid(filepath, create_obj_function, instance_type):
        """
        Parses a file and checks if it corresponds to its instance type and
        can be created into its object
        :param filepath: The path of the file
        :param create_obj_function: The function to create the object
        :param instance_type: The required instance type of the file
        :return: An object containing the file content
        """
        with open(filepath) as file_content:
            try:
                file_obj = create_obj_function(file_content.read())
                if not isinstance(file_obj, instance_type):
                    raise NRPServicesGeneralException(
                        "%s configuration file content is not valid." % (
                            filepath),
                        "File not valid"
                    )
            except (ValidationError, SAXParseException) as ve:
                raise NRPServicesGeneralException(
                    "Could not parse file %s due to validation error: %s" % (
                        filepath, str(ve)),
                    "File not valid"
                )
        return file_obj

    def get_folder_uuid_by_name(self, token, context_id, folder_name):
        """
        Returns the uuid of a folder provided its name
        :param token: a valid token to be used for the request
        :param context_id: the context_id of the collab
        :param folder_name: the name of the folder
        :return: if found, the uuid of the named folder
        """
        folders = self.list_experiments(
            token, context_id, get_all=True, name=folder_name)
        for folder in folders:
            if folder["name"] == folder_name:
                return folder["uuid"]

    # pylint: disable=no-self-use
    def remove_temp_directory(self):
        """
        Removes the temporary directory where all the simulation based files are stored
        """
        for entry in os.listdir(tempfile.gettempdir()):
            if entry.startswith('nrpTemp'):
                nrp_temp = os.path.join(tempfile.gettempdir(), entry)
                logger.debug(
                    "removing the temporary configuration folder %s",
                    nrp_temp
                )
                shutil.rmtree(nrp_temp)


def get_model_basepath():
    """
    :return: path given in the environment variable 'NRP_MODELS_DIRECTORY'
    """

    path = os.environ.get('NRP_MODELS_DIRECTORY')
    if path is None:
        raise Exception("Server Error. NRP_MODELS_DIRECTORY not defined.")

    return path
