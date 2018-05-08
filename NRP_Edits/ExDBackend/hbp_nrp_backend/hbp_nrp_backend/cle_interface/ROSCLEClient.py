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
Takes care of making the appropriate ROS call(s) to control a simulation.
On the other side of ROS, the calls are handled by ROSCLEServer.py
"""
import sys
python3 = True if sys.hexversion > 0x03000000 else False

import logging
import rospy
# This package comes from the catkin package ROSCLEServicesDefinitions
# in the GazeboRosPackages repository.
from cle_ros_msgs import srv
from hbp_nrp_backend.cle_interface import SERVICE_SIM_RESET_ID, \
    SERVICE_GET_TRANSFER_FUNCTIONS, SERVICE_EDIT_TRANSFER_FUNCTION, \
    SERVICE_ACTIVATE_TRANSFER_FUNCTION, SERVICE_ADD_TRANSFER_FUNCTION, \
    SERVICE_DELETE_TRANSFER_FUNCTION, SERVICE_SET_BRAIN, SERVICE_GET_BRAIN, \
    SERVICE_GET_POPULATIONS, SERVICE_GET_CSV_RECORDERS_FILES, SERVICE_SIM_EXTEND_TIMEOUT_ID, \
    SERVICE_GET_STRUCTURED_TRANSFER_FUNCTIONS, SERVICE_SET_STRUCTURED_TRANSFER_FUNCTION, \
    SERVICE_SIMULATION_RECORDER

__author__ = "Lorenzo Vannucci, Daniel Peppicelli, Georg Hinkel"
logger = logging.getLogger(__name__)


def fallback_retval(val):
    """
    This function is intended to be used as a decorator for the methods calling CLE services.
    It intercepts a ROSCLEClientException during the execution of a ROSServiceWrapper and returns
    the desired value instead.
    :param val: the fallback return value for the decorated method
    """
    def decorator(func):
        """
        The decorator function returned once the wanted fallback return value is set
        :param func: the function to decorate.
        """
        def f(*args, **kwargs):
            """
            The function actually executed instead of the decorated one.
            """
            try:
                return func(*args, **kwargs)
            except ROSCLEClientException:
                return val
        return f
    return decorator


class ROSCLEClientException(Exception):
    """
    Exception within the CLE client
    """
    pass


class ROSCLEServiceWrapper(object):
    """
    Wraps the behaviour of a standard ROS service, throwing a detailed ROSCLEClientException
    in case of invalid client or ROS exceptions.
    """
    ROS_SERVICE_TIMEOUT = 180

    def __init__(self, service_name, service_class, ros_cle_client, invalidate_on_failure=False):
        """
        :param service_name: the name of the ROS service.
        :param service_class: the class of the ROS service parameter.
        :param ros_cle_client: the ROSCLEClient instance creating the wrapper.
        :param invalidate_on_failure (default=False): a boolean value deciding whether the
            ROSCLEClient should be invalidated in case of failure (True) or not (False).
        """
        self.__handler = None
        self.__ros_cle_client = ros_cle_client
        self.__invalidate_on_failure = invalidate_on_failure
        try:
            logger.info("Connecting to ROS service " + service_name)
            self.__handler = rospy.ServiceProxy(service_name, service_class)
            self.__handler.wait_for_service(timeout=self.ROS_SERVICE_TIMEOUT)
        except rospy.ROSException:
            # According to the documentation, only a timeout will raise a generic
            # 'ROSException'.
            # http://docs.ros.org/api/rospy/html/rospy-module.html#wait_for_service
            message = "Timeout while connecting to the CLE (waiting on %s)." % \
                      (service_name, )
            logger.error(message)
            raise ROSCLEClientException(message)

    def __call__(self, *args, **kwargs):
        try:
            return self.__handler(*args, **kwargs)
        except (rospy.ServiceException, rospy.exceptions.ROSInterruptException) as e:
            if self.invalidate_on_failure:
                self.__ros_cle_client.valid = False
                self.__ros_cle_client.invalid_reason = "a previous communication error"
            message = "Error executing service \"%s\", unable to communicate with the CLE.\n" \
                "Error: %s" % (self.__handler.resolved_name, str(e), )
            logger.error(message)
            raise ROSCLEClientException(message)

    @property
    def handler(self):
        """
        Property getter for the __handler attribute
        """

        return self.__handler

    @property
    def ros_cle_client(self):
        """
        Property getter for the __ros_cle_client attribute
        """

        return self.__ros_cle_client

    @property
    def invalidate_on_failure(self):
        """
        Property getter for the __invalidate_on_failure attribute
        """

        return self.__invalidate_on_failure


class ROSCLEClient(object):
    """
    Client around the ROS controlled Closed Loop Engine.
    """

    def __init__(self, sim_id):
        """
        Create the wrapper client

        :param sim_id: The simulation id
        """
        self.__cle_reset = ROSCLEServiceWrapper(
            SERVICE_SIM_RESET_ID(sim_id), srv.ResetSimulation, self)

        self.__cle_extend_timeout = ROSCLEServiceWrapper(
            SERVICE_SIM_EXTEND_TIMEOUT_ID(sim_id), srv.ExtendTimeout, self)

        self.__cle_get_transfer_functions = ROSCLEServiceWrapper(
            SERVICE_GET_TRANSFER_FUNCTIONS(sim_id), srv.GetTransferFunctions, self)

        self.__cle_add_transfer_function = ROSCLEServiceWrapper(
            SERVICE_ADD_TRANSFER_FUNCTION(sim_id), srv.AddTransferFunction, self)

        self.__cle_activate_transfer_function = ROSCLEServiceWrapper(
            SERVICE_ACTIVATE_TRANSFER_FUNCTION(sim_id), srv.ActivateTransferFunction, self)

        self.__cle_edit_transfer_function = ROSCLEServiceWrapper(
            SERVICE_EDIT_TRANSFER_FUNCTION(sim_id), srv.EditTransferFunction, self)

        self.__cle_get_structured_transfer_functions = ROSCLEServiceWrapper(
            SERVICE_GET_STRUCTURED_TRANSFER_FUNCTIONS(sim_id),
            srv.GetStructuredTransferFunctions, self)

        self.__cle_set_structured_transfer_function = ROSCLEServiceWrapper(
            SERVICE_SET_STRUCTURED_TRANSFER_FUNCTION(sim_id),
            srv.SetStructuredTransferFunction, self)

        self.__cle_delete_transfer_function = ROSCLEServiceWrapper(
            SERVICE_DELETE_TRANSFER_FUNCTION(sim_id), srv.DeleteTransferFunction, self)

        self.__cle_get_brain = ROSCLEServiceWrapper(SERVICE_GET_BRAIN(sim_id), srv.GetBrain, self)
        self.__cle_set_brain = ROSCLEServiceWrapper(SERVICE_SET_BRAIN(sim_id), srv.SetBrain, self)
        self.__cle_get_populations = ROSCLEServiceWrapper(SERVICE_GET_POPULATIONS(sim_id),
                                                          srv.GetPopulations, self)
        self.__cle_get_CSV_recorders_files = ROSCLEServiceWrapper(
            SERVICE_GET_CSV_RECORDERS_FILES(sim_id), srv.GetCSVRecordersFiles, self)

        self.__simulation_recorder = ROSCLEServiceWrapper(
            SERVICE_SIMULATION_RECORDER(sim_id), srv.SimulationRecorder, self)

        self.__stop_reason = None

    def stop_communication(self, reason):
        """
        Tells the client to stop all communication to the simulation server because of the given
        reason

        :param reason: The reason why no more communication should be performed
        """
        self.__stop_reason = reason

    def reset(self, reset_type, world_sdf=None, brain_path=None, populations=None):
        """
        Reset the simulation.

        :param populations: To populations for the reset
        :param brain_path: The brain path for the reset
        :param world_sdf: The world sdf
        :param reset_type: Denotes the kind of reset the user wants to perform, details about
        reset types and details are given in the ResetSimulation service request message.
        """
        if self.__stop_reason is not None:
            raise ROSCLEClientException(self.__stop_reason)
        # TODO: Uniform response from ROS CLE services so that this could be done directly
        # in the wrapper class

        # cancel any simulation recording in progress, discard all if this is a full reset
        # since the recorders/playback will break with simulator time reset
        self.__simulation_recorder(srv.SimulationRecorderRequest.CANCEL)
        if reset_type == srv.ResetSimulationRequest.RESET_FULL:
            self.__simulation_recorder(srv.SimulationRecorderRequest.RESET)

        if populations is not None:
            for pop in populations:
                _x = pop.name
                if python3 or type(_x) == unicode:
                    _x = _x.encode('utf-8')
                else:
                    _x = str(_x)
                pop.name = _x
                if pop.step <= 0:
                    pop.step = 1

        resp = self.__cle_reset(reset_type=reset_type,
                                world_sdf=world_sdf if world_sdf is not None else "",
                                brain_path=brain_path if brain_path is not None else "",
                                populations=populations if populations is not None else [])
        if not resp.success:
            raise ROSCLEClientException(resp.error_message)

    def get_simulation_brain(self):
        """
        Get the brain of the running simulation

        :return: dict with brain_data, brain_type, brain_populations and data_type
        """
        if self.__stop_reason is not None:
            raise ROSCLEClientException(self.__stop_reason)
        return self.__cle_get_brain()

    def set_simulation_brain(self, brain_type, data, data_type, brain_populations,
                             change_population):
        """
        Set the brain of the running simulation (will pause the simulation)

        :param brain_type: Type of the brain file ('h5' or 'py')
        :param data: Contents of the brain file. Encoding given in field data_type
        :param data_type: Type of the data field ('text' or 'base64')
        :param brain_populations: A dictionary indexed by population names and containing neuron
                                  indices. Neuron indices could be defined by individual integers,
                                  lists of integers or python slices. Python slices are defined by a
                                  dictionary containing the 'from', 'to' and 'step' values.
        :param change_population: a flag to select an action on population name change, currently
                                  possible values are: 0 ask user for permission to replace;
                                  1 (permission granted) replace old name with a new one;
                                  2 proceed with no replace action

        :return: response of the cle
        """
        if self.__stop_reason is not None:
            raise ROSCLEClientException(self.__stop_reason)
        return self.__cle_set_brain(brain_type, data, data_type, brain_populations,
                                    change_population)

    @fallback_retval(([], []))
    def get_simulation_transfer_functions(self):
        """
        Get the simulation transfer functions and their activation status

        :returns:  A tuple of parallel arrays of:
        - strings containing the source code of the transfer functions
        - their activation status
        """
        if self.__stop_reason is not None:
            raise ROSCLEClientException(self.__stop_reason)

        response = self.__cle_get_transfer_functions()
        return response.transfer_functions, response.active

    @fallback_retval(False)
    def delete_simulation_transfer_function(self, transfer_function_name):
        """
        Delete the given transfer function

        :param transfer_function_name: Name of the transfer function to delete
        :return: True if the call to ROS is successful, False otherwise
        """
        if self.__stop_reason is not None:
            raise ROSCLEClientException(self.__stop_reason)
        return self.__cle_delete_transfer_function(transfer_function_name).success

    def edit_simulation_transfer_function(self, transfer_function_name, transfer_function_source):
        """
        Edit the simulation transfer function's source code.

        :param transfer_function_name: Name of the transfer function to modify
        :param transfer_function_source: Source code of the transfer function
        :returns: "" if the call to ROS is successful,
                     a string containing an error message otherwise
        """
        if self.__stop_reason is not None:
            raise ROSCLEClientException(self.__stop_reason)
        return self.__cle_edit_transfer_function(transfer_function_name, transfer_function_source) \
                   .error_message

    def add_simulation_transfer_function(self, transfer_function_source):
        """
        Add a new simulation transfer function source code.

        :param transfer_function_source: Source code of the transfer function
        :returns: "" if the call to ROS is successful,
                     a string containing an error message otherwise
        """
        if self.__stop_reason is not None:
            raise ROSCLEClientException(self.__stop_reason)
        return self.__cle_add_transfer_function(transfer_function_source).error_message

    def activate_simulation_transfer_function(self, transfer_function_name,
                                              activate_transfer_function):
        """
        Set the activation status of a transfer function
        :param transfer_function_name: the name of the tf to be set
        :param activate_transfer_function: the desired new activation status
        :return:
        """
        if self.__stop_reason is not None:
            raise ROSCLEClientException(self.__stop_reason)
        return self.__cle_activate_transfer_function(transfer_function_name,
                                                     activate_transfer_function).error_message

    def get_structured_transfer_functions(self):
        """
        Gets the transfer functions in a structured format
        """
        if self.__stop_reason is not None:
            raise ROSCLEClientException(self.__stop_reason)
        return self.__cle_get_structured_transfer_functions().transfer_functions

    def set_structured_transfer_function(self, transfer_function):
        """
        Sets the given structured transfer function

        :param transfer_function: The new transfer function in a structured format
        :returns: "" if the call to ROS is successful,
                     a string containing an error message otherwise
        """
        if self.__stop_reason is not None:
            raise ROSCLEClientException(self.__stop_reason)
        return self.__cle_set_structured_transfer_function(transfer_function).error_message

    def get_populations(self):
        """
        Gets the neurons of the brain in the simulation

        :return: populations as dict
        """
        populations = self.__cle_get_populations()
        result = {
            'populations': [
                {
                    'name': p.name,
                    'neuron_model': p.neuron_model,
                    'parameters': ROSCLEClient.__convert_parameter_list(p.parameters),
                    'gids': p.gids,
                    'indices': p.indices
                } for p in populations.neurons
            ]
        }
        return result

    @staticmethod
    def __convert_parameter_list(parameters):
        """
        Gets the specified parameter list as dictionary

        :param parameters: A list of NeuronParameters
        :return: neuron parameters as list
        """
        return [
            {
                'parameterName': p.parameterName,
                'value': p.value
            } for p in parameters
        ]

    @fallback_retval([])
    def get_simulation_CSV_recorders_files(self):
        """
        Get the file paths of simulation's CSV recorders

        :returns: An array of dictionaries
        {name: 'my_recorder_file.csv', temporary_path: 'my_recorder_file_path'}
        """
        return self.__cle_get_CSV_recorders_files().files

    def extend_simulation_timeout(self, timeout):
        """
        Extend the simulation timeout

        :param timeout: new new simulation timeout
        :returns: "" if the call to ROS is successful
        """
        return self.__cle_extend_timeout(str(timeout)).success

    def command_simulation_recorder(self, command):
        """
        Issue a request/command to the simulation recorder

        :param command: the command to issue, see SimulationRecorder.srv definition for types
        :return: boolean value/success and message if provided
        """
        if self.__stop_reason is not None:
            raise ROSCLEClientException(self.__stop_reason)
        return self.__simulation_recorder(command)
