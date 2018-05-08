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
ROSCLEClient unit test
"""

import rospy
from hbp_nrp_backend.cle_interface.ROSCLEState import ROSCLEState
from hbp_nrp_backend.cle_interface import ROSCLEClient, \
    SERVICE_SIM_START_ID, SERVICE_SIM_PAUSE_ID, \
    SERVICE_SIM_STOP_ID, SERVICE_SIM_RESET_ID, SERVICE_SIM_STATE_ID, \
    SERVICE_GET_TRANSFER_FUNCTIONS, SERVICE_EDIT_TRANSFER_FUNCTION, SERVICE_ADD_TRANSFER_FUNCTION, \
    SERVICE_DELETE_TRANSFER_FUNCTION, SERVICE_SET_BRAIN, SERVICE_GET_BRAIN, \
    SERVICE_GET_POPULATIONS, SERVICE_GET_CSV_RECORDERS_FILES, \
    SERVICE_CLEAN_CSV_RECORDERS_FILES, SERVICE_SIMULATION_RECORDER
from cle_ros_msgs.srv import ResetSimulationRequest, \
    SimulationRecorderRequest
from std_srvs.srv import Empty
from cle_ros_msgs.srv import GetTransferFunctions, EditTransferFunction, \
    AddTransferFunction, DeleteTransferFunction, ActivateTransferFunction, GetBrain, SetBrain
from hbp_nrp_backend.cle_interface.ROSCLEClient import ROSCLEClientException
from mock import patch, MagicMock, Mock, call
from cle_ros_msgs.msg import PopulationInfo, NeuronParameter, CSVRecordedFile
import unittest

from cle_ros_msgs import srv

__author__ = 'Lorenzo Vannucci, Daniel peppicelli, Georg Hinkel'


class TestROSCLEClient(unittest.TestCase):

    LOGGER_NAME = ROSCLEClient.__name__
    NUMBER_OF_SERVICE_PROXIES = 14  # Update when adding a new service to ROSCLEClient!

    def setUp(self):
        patcher = patch('rospy.ServiceProxy')
        self.addCleanup(patcher.stop)
        self.serviceProxyMock = patcher.start()
        self.serviceProxyMocks = [MagicMock() for _ in range(self.NUMBER_OF_SERVICE_PROXIES)]
        self.serviceProxyMock.side_effect = self.serviceProxyMocks

    @patch('hbp_nrp_backend.cle_interface.ROSCLEClient.ROSCLEServiceWrapper')
    def test_roscleclient_constructor(self, service_wrapper_mock):
        client = ROSCLEClient.ROSCLEClient(0)
        listened_services = [x[0][0] for x in service_wrapper_mock.call_args_list]
        expected_services = [
            SERVICE_SIM_RESET_ID(0), SERVICE_GET_TRANSFER_FUNCTIONS(0),
            SERVICE_EDIT_TRANSFER_FUNCTION(0), SERVICE_ADD_TRANSFER_FUNCTION(0),
            SERVICE_DELETE_TRANSFER_FUNCTION(0), SERVICE_GET_BRAIN(0), SERVICE_SET_BRAIN(0),
            SERVICE_GET_POPULATIONS(0), SERVICE_GET_CSV_RECORDERS_FILES(0),
            SERVICE_SIMULATION_RECORDER(0)
        ]
        self.assertNotIn(False, [x in listened_services for x in expected_services])

    @patch('hbp_nrp_backend.cle_interface.ROSCLEClient.rospy.ServiceProxy')
    def test_rosservicewrapper_constructor(self, service_proxy_mock):
        # Case when the service is correctly subscribed
        service_wrapper = ROSCLEClient.ROSCLEServiceWrapper('service_name', Empty, None)
        self.assertEquals('service_name', service_proxy_mock.call_args[0][0])
        self.assertIsInstance(service_proxy_mock.call_args[0][1], type(Empty))
        args, kwargs = service_wrapper.handler.wait_for_service.call_args_list[0]
        self.assertEquals(kwargs['timeout'], ROSCLEClient.ROSCLEServiceWrapper.ROS_SERVICE_TIMEOUT)

        # Case when the service timeouts
        service_proxy_mock.side_effect = rospy.ROSException()
        self.assertRaises(ROSCLEClient.ROSCLEClientException,
            ROSCLEClient.ROSCLEServiceWrapper, 'service_name', Empty, None)

    @patch('hbp_nrp_backend.cle_interface.ROSCLEClient.rospy.ServiceProxy')
    def test_rosservicewrapper_call(self, service_proxy_mock):
        client = ROSCLEClient.ROSCLEClient(0)

        # When everything is fine, the service should just be called
        service_wrapper = ROSCLEClient.ROSCLEServiceWrapper('service_name', Empty, client)
        self.assertEqual(client, service_wrapper.ros_cle_client)
        service_wrapper()
        self.assertEquals(service_wrapper.handler.call_count, 1)

        # When something's wrong during the service call it should throw ROSCLEClientException
        service_wrapper = ROSCLEClient.ROSCLEServiceWrapper('service_name', Empty, client,
                                                            invalidate_on_failure=False)
        service_wrapper.handler.side_effect = rospy.ServiceException()

        self.assertRaises(ROSCLEClient.ROSCLEClientException, service_wrapper)

        service_wrapper.handler.side_effect = rospy.exceptions.ROSInterruptException()

        self.assertRaises(ROSCLEClient.ROSCLEClientException, service_wrapper)

        # and invalidate the ROSCLEClient if asked to
        service_wrapper = ROSCLEClient.ROSCLEServiceWrapper('service_name', Empty, client,
                                                            invalidate_on_failure=True)
        self.assertRaises(ROSCLEClient.ROSCLEClientException, service_wrapper)

    def test_get_simulation_transfer_functions(self):
        msg = GetTransferFunctions()
        msg.transfer_functions = ['some', 'source', 'code']
        msg.active = [True, False, True]

        client = ROSCLEClient.ROSCLEClient(0)

        client._ROSCLEClient__cle_get_transfer_functions = MagicMock(return_value=msg)

        response = client.get_simulation_transfer_functions()
        self.assertEqual(response, (msg.transfer_functions, msg.active))

        client.stop_communication("Test stop")
        response = client.get_simulation_transfer_functions()
        self.assertEqual(response, ([], []))

    def test_add_simulation_transfer_function(self):
        msg = AddTransferFunction()
        resp = msg._response_class(error_message="Some error message")

        client = ROSCLEClient.ROSCLEClient(0)

        client._ROSCLEClient__cle_add_transfer_function = MagicMock(return_value=resp)
        self.assertEqual(
            client.add_simulation_transfer_function("def tf_1(): \n  return 1"),
            resp.error_message
        )

        client.stop_communication("Test stop")
        with self.assertRaises(ROSCLEClientException):
            client.add_simulation_transfer_function("def tf_1(): \n return 1")

    def test_edit_simulation_transfer_function(self):
        msg = EditTransferFunction()
        resp = msg._response_class(error_message="Some error message")

        client = ROSCLEClient.ROSCLEClient(0)

        client._ROSCLEClient__cle_edit_transfer_function = MagicMock(return_value=resp)
        self.assertEquals(
            client.edit_simulation_transfer_function("tf_1", "def tf_1(): \n return 1"),
            resp.error_message)

        client.stop_communication("Test stop")
        with self.assertRaises(ROSCLEClientException):
            client.edit_simulation_transfer_function("tf_1", "def tf_1(): \n return 1")

    def test_delete_simulation_transfer_function(self):
        msg = DeleteTransferFunction()
        resp = msg._response_class(success=True)

        client = ROSCLEClient.ROSCLEClient(0)

        client._ROSCLEClient__cle_delete_transfer_function = MagicMock(return_value=resp)
        self.assertEquals(client.delete_simulation_transfer_function("tf_1"), resp.success)

        client.stop_communication("Test stop")
        self.assertFalse(client.delete_simulation_transfer_function("tf_1"))

    def test_activate_transfer_function(self):

        msg = ActivateTransferFunction()
        resp = msg._response_class(error_message="")

        client = ROSCLEClient.ROSCLEClient(0)

        client._ROSCLEClient__cle_activate_transfer_function = MagicMock(return_value=resp)
        self.assertEquals(client.activate_simulation_transfer_function("tf_1", True), resp.error_message)

        client.stop_communication("Test stop")
        with self.assertRaises(ROSCLEClientException):
            client.activate_simulation_transfer_function("tf_1", True)

    def test_get_brain(self):
        msg = GetBrain()
        resp = msg._response_class(brain_data='the brain data', brain_type='the brain type',
                                   data_type='the data type')

        client = ROSCLEClient.ROSCLEClient(0)

        client._ROSCLEClient__cle_get_brain = MagicMock(return_value=resp)
        self.assertEquals(client.get_simulation_brain(), resp)

        client.stop_communication("Test stop")
        with self.assertRaises(ROSCLEClientException):
            client.get_simulation_brain()

    def test_set_brain(self):
        msg = SetBrain()
        resp = msg._response_class(error_message='error message', error_line=-1, error_column=-1)

        client = ROSCLEClient.ROSCLEClient(0)

        change_population = srv.SetBrainRequest.DO_RENAME_POPULATION

        client._ROSCLEClient__cle_set_brain = MagicMock(return_value=resp)
        self.assertEquals(client.set_simulation_brain(
            'data', 'py', 'text', '{"population_1": 2}', change_population), resp)
        client._ROSCLEClient__cle_set_brain.assert_called_once_with(
            'data', 'py', 'text', '{"population_1": 2}', change_population)

        client.stop_communication("Test stop")
        with self.assertRaises(ROSCLEClientException):
            client.set_simulation_brain('data', 'py', 'text', '{"population_1": 2}', change_population)

    def test_get_populations(self):
        client = ROSCLEClient.ROSCLEClient(0)

        populations = Mock()
        populations.neurons = [
            PopulationInfo("foo", "bar", [ NeuronParameter("p", 42.0) ], [0, 8, 15], range(0, 3))
        ]

        client._ROSCLEClient__cle_get_populations = Mock(return_value=populations)
        self.assertEqual(client.get_populations(), {
            'populations': [
                {
                    'name': 'foo',
                    'neuron_model': 'bar',
                    'parameters': [{ 'parameterName': 'p', 'value': 42.0}],
                    'gids': [0,8,15],
                    'indices': range(0, 3)
                }
            ]
        })

    def test_reset(self):
        client = ROSCLEClient.ROSCLEClient(0)

        simulation_recorder = Mock()
        reset_resp = Mock()
        reset_resp.success = True
        reset = Mock(return_value=reset_resp)
        client._ROSCLEClient__simulation_recorder = simulation_recorder
        client._ROSCLEClient__cle_reset = reset

        pop1 = Mock()
        pop2 = Mock()

        pop1.name = u'foo'
        pop1.step = 1
        pop2.name = 'bar'
        pop2.step = 0
        client.reset(ResetSimulationRequest.RESET_FULL, populations=[pop1, pop2])

        simulation_recorder.assert_has_calls(call(SimulationRecorderRequest.CANCEL))
        simulation_recorder.assert_has_calls(call(SimulationRecorderRequest.RESET))
        self.assertEqual(pop1.name, 'foo')
        self.assertEqual(pop2.name, 'bar')
        self.assertEqual(pop1.step, 1)
        self.assertEqual(pop2.step, 1)
        self.assertTrue(reset.called)

        reset_resp.success = False
        reset_resp.error_message = "Foobar"
        self.assertRaises(ROSCLEClientException, client.reset, ResetSimulationRequest.RESET_FULL)

        client.stop_communication("Test stop")
        self.assertRaises(ROSCLEClientException, client.reset, ResetSimulationRequest.RESET_FULL)

    def test_get_csv_files(self):
        client = ROSCLEClient.ROSCLEClient(0)

        files = Mock()
        files.files = [
            CSVRecordedFile("foo", "foo.csv"), CSVRecordedFile("bar", "bar.csv")
        ]

        client._ROSCLEClient__cle_get_CSV_recorders_files = Mock(return_value=files)
        self.assertEqual(client.get_simulation_CSV_recorders_files(), files.files)

        client.stop_communication("Test stop")
        self.assertEqual(client.get_simulation_CSV_recorders_files(), files.files)

    def test_command_simulation_recorder(self):
        client = ROSCLEClient.ROSCLEClient(0)

        client._ROSCLEClient__simulation_recorder = Mock(return_value=['foo', 'bar'])
        self.assertEqual(client.command_simulation_recorder(0), ['foo', 'bar'])
        client._ROSCLEClient__simulation_recorder.assert_called_once_with(0)

        client.stop_communication("Test stop")
        with self.assertRaises(ROSCLEClientException):
            client.command_simulation_recorder(0)

if __name__ == '__main__':
    unittest.main()
