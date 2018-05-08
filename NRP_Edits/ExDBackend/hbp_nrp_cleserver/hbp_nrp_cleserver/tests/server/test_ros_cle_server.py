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
ROSCLEServer unit test
"""

from cle_ros_msgs.srv import ResetSimulation, ResetSimulationRequest
from cle_ros_msgs.msg import CSVRecordedFile, ExperimentPopulationInfo
from hbp_nrp_cle.tf_framework import BrainParameterException, TFLoadingException
from hbp_nrp_cleserver.server import ROSCLEServer
import logging
from mock import patch, MagicMock, Mock, PropertyMock, mock_open
from testfixtures import log_capture
from os import path
import base64
import unittest
import json
from functools import wraps
from multiprocessing import Process

from cle_ros_msgs import srv

__author__ = 'HBP NRP software team'


# Code for timeout decorator from
# http://stackoverflow.com/questions/14366761/
class TimeoutError(Exception):
    pass


def timeout(seconds=5, error_message="Timeout"):
    def decorator(func):
        def wrapper(*args, **kwargs):
            process = Process(None, func, None, args, kwargs)
            process.start()
            process.join(seconds)
            if process.is_alive():
                process.terminate()
                raise TimeoutError(error_message)

        return wraps(func)(wrapper)
    return decorator


class TestROSCLEServer(unittest.TestCase):

    LOGGER_NAME = ROSCLEServer.__name__

    @patch("hbp_nrp_cleserver.server.ROSCLEServer.SimulationServerLifecycle")
    @patch("hbp_nrp_cleserver.server.SimulationServer.Timer")
    def setUp(self, mocked_timer, mocked_lifecycle):
        unittest.TestCase.setUp(self)

        # Mock the respective objects and make them available for all tests.
        # Also have a look at the following link:
        # https://docs.python.org/3.5/library/unittest.mock-examples.html#applying-the-same-patch-to-every-test-method
        cle_patcher = patch('hbp_nrp_cle.cle.CLEInterface.IClosedLoopControl')
        rospy_patcher = patch('hbp_nrp_cleserver.server.ROSCLEServer.rospy')
        base_rospy_patcher = patch('hbp_nrp_cleserver.server.SimulationServer.rospy')

        # Ensure that the patchers are cleaned up correctly even in exceptional cases
        # e.g. when an exception was thrown.
        self.addCleanup(cle_patcher.stop)
        self.addCleanup(rospy_patcher.stop)
        self.addCleanup(base_rospy_patcher.stop)

        self.__mocked_cle = cle_patcher.start()
        self.__mocked_cle.simulation_time = 0
        self.__mocked_cle.real_time = 0
        self.__mocked_cle.tf_elapsed_time = Mock(return_value=0)
        self.__mocked_cle.brainsim_elapsed_time = Mock(return_value=0)
        self.__mocked_cle.robotsim_elapsed_time = Mock(return_value=0)
        self.__mocked_rospy = rospy_patcher.start()
        self.__mock_base_rospy = base_rospy_patcher.start()
        self.__mocked_notificator = Mock()
        self.__mocked_notificator.task_notifier = mock_open()

        self.__ros_cle_server = ROSCLEServer.ROSCLEServer(0, None, None, self.__mocked_notificator)
        self.assertEqual(mocked_timer.Timer.call_count, 1)
        self.__ros_cle_server._ROSCLEServer__done_flag = Mock()
        self.__ros_cle_server.cle = self.__mocked_cle
        self.__ros_cle_server.prepare_simulation(None)
        self.__mock_lifecycle = mocked_lifecycle()

    def tearDown(self):
        # remove all handlers after each test!
        logging.getLogger(self.LOGGER_NAME).handlers = []

    def test_ros_node_initialized_with_right_name(self):
        self.__mock_base_rospy.init_node.assert_called_with('ros_cle_simulation', anonymous=True)

    def test_prepare_initialization(self):
        self.__mocked_cle.is_initialized = False
        self.assertEqual(12, self.__mocked_rospy.Service.call_count)
        self.assertEqual(2, self.__mock_base_rospy.Service.call_count)

    def test_reset_simulation(self):
        self.__mocked_cle.is_initialized = False
        self.__mock_lifecycle.state = 'paused'

        # Reset robot pose without Collab
        msg = ResetSimulationRequest()
        msg.reset_type = ResetSimulationRequest.RESET_ROBOT_POSE
        response, message = self.__ros_cle_server.reset_simulation(msg)
        self.assertEqual("", message)
        self.assertTrue(response)
        self.assertEqual(1, self.__mocked_cle.reset_robot_pose.call_count)
        self.__mocked_cle.reset_mock()

        # Reset Brain without Collab
        msg.reset_type = ResetSimulationRequest.RESET_BRAIN
        response, message = self.__ros_cle_server.reset_simulation(msg)
        self.assertEqual("", message)
        self.assertTrue(response)
        self.assertEqual(1, self.__mocked_cle.reset_brain.call_count)
        self.__mocked_cle.reset_mock()

        # Reset World without Collab
        msg.reset_type = ResetSimulationRequest.RESET_WORLD
        response, message = self.__ros_cle_server.reset_simulation(msg)
        self.assertEqual("", message)
        self.assertTrue(response)
        self.assertEqual(1, self.__mocked_cle.reset_world.call_count)
        self.__mocked_cle.reset_mock()

        # Reset Brain within Collab
        msg.reset_type = ResetSimulationRequest.RESET_BRAIN
        msg.brain_path = "/random/tmp/file.brain"
        msg.populations = [ExperimentPopulationInfo(name="population1", type=ExperimentPopulationInfo.TYPE_POPULATION_SLICE,
                                                    ids=[], start=0, stop=5, step=1),
                           ExperimentPopulationInfo(name="population2", type=ExperimentPopulationInfo.TYPE_POPULATION_SLICE,
                                                    ids=[], start=5, stop=10, step=1)]
        response, message = self.__ros_cle_server.reset_simulation(msg)
        self.assertEqual("", message)
        self.assertTrue(response)
        self.assertEqual(1, self.__mocked_cle.reset_brain.call_count)
        self.assertEqual(self.__mocked_cle.reset_brain.call_args_list[0][0][0],
                         "/random/tmp/file.brain")
        self.assertEqual(self.__mocked_cle.reset_brain.call_args_list[0][0][1],
                         {'population1': slice(0, 5, 1), 'population2': slice(5, 10, 1)})
        self.__mocked_cle.reset_mock()

        # Reset World within Collab
        msg.reset_type = ResetSimulationRequest.RESET_WORLD
        msg.world_sdf = "<a valid sdf string>"
        response, message = self.__ros_cle_server.reset_simulation(msg)
        self.assertEqual("", message)
        self.assertTrue(response)
        self.assertEqual(1, self.__mocked_cle.reset_world.call_count)
        self.assertEqual(self.__mocked_cle.reset_world.call_args_list[0][0][0], msg.world_sdf)
        self.__mocked_cle.reset_mock()

        # Reset Full
        msg.reset_type = ResetSimulationRequest.RESET_FULL
        msg.world_sdf = "<a valid sdf string>"
        msg.brain_path = "/random/tmp/file.brain"
        msg.populations = [ExperimentPopulationInfo(name="population1", type=ExperimentPopulationInfo.TYPE_POPULATION_SLICE,
                                                    ids=[], start=0, stop=5, step=1),
                           ExperimentPopulationInfo(name="population2", type=ExperimentPopulationInfo.TYPE_POPULATION_SLICE,
                                                    ids=[], start=5, stop=10, step=1)]
        response, message = self.__ros_cle_server.reset_simulation(msg)

    def __get_handlers_for_testing_main(self):
        self.__mocked_cle.is_initialized = True
        self.__ros_cle_server.prepare_simulation(None)

        # Get the ROS Service handlers; this will always be the third argument.
        arguments = {
            k.split('/')[-1]: v
            for (k, _, v) in
            [x[0] for x in self.__mocked_rospy.Service.call_args_list]
        }

        return arguments

    def test_get_brain(self):
        with patch("hbp_nrp_cleserver.server.ROSCLEServer.tf_framework") as mocked_tf_framework:
            mocked_tf_framework.get_brain_source.return_value = "Some python code"
            slice1 = { 'from': 1, 'to': 2, 'step': 3}
            slice2 = { 'from': 1, 'to': 2}
            populations_json_slice = {
              'population_1': 1, 'population_2': 2,
              'slice_1': slice1, 'slice_2': slice2,
              'list_1': [1, 2, 3]
            }
            mocked_tf_framework.get_brain_populations.return_value = populations_json_slice
            ros_callbacks = self.__get_handlers_for_testing_main()
            directory = path.split(__file__)[0]
            get_brain_implementation = ros_callbacks['get_brain']
            brain = get_brain_implementation(Mock())
            self.assertEqual("py", brain[0])
            self.assertEqual("Some python code", brain[1])
            self.assertEqual("text", brain[2])
            self.assertEqual(json.dumps(populations_json_slice), brain[3])
            mocked_tf_framework.get_brain_source.return_value = None
            brain = get_brain_implementation(Mock())
            self.assertEqual("h5", brain[0])
            self.assertEqual("base64", brain[2])

    @patch('hbp_nrp_cleserver.server.ROSCLEServer.NamedTemporaryFile')
    @patch('hbp_nrp_cleserver.server.ROSCLEServer.SimulationServerLifecycle')
    def test_set_brain(self, mock_tempfile, mock_lifecycle):

        mock_tempfile.name = 'random_name_tempfile'

        with patch("hbp_nrp_cleserver.server.ROSCLEServer.tf_framework") as mocked_tf_framework:
            slice1 = { 'from': 1, 'to': 2, 'step': 1}
            populations_json_slice = {
              'index1': 1,
              'slice_1': slice1,
              'list1': [1, 2, 3]
            }
            mocked_tf_framework.get_brain_populations.return_value = populations_json_slice

            ros_callbacks = self.__get_handlers_for_testing_main()
            self.__mock_lifecycle.state = 'started'
            self.__mocked_cle.network_file = PropertyMock()
            set_brain_implementation = ros_callbacks['set_brain']
            populations_erroneous = json.dumps({
                'index1': 1,
                'list1': [1, 2, 3],
                'slice1 new': {'from': 1, 'to': 2, 'step': 1}
            })
            request = Mock()
            request.data_type = "text"
            request.brain_type = "py"
            request.brain_data = "Dummy = None"
            request.brain_populations = populations_erroneous
            request.change_population = srv.SetBrainRequest.ASK_RENAME_POPULATION
            response = set_brain_implementation(request)
            self.assertNotEqual(response[0], "")

            populations_new = json.dumps({
                'index1': 1,
                'list1': [1, 2, 3],
                'slice1_new': {'from': 1, 'to': 2, 'step': 1}
            })
            request.change_population = srv.SetBrainRequest.DO_RENAME_POPULATION
            request.brain_populations = populations_new
            response = set_brain_implementation(request)
            self.assertEqual(response[0], "")

        self.__mock_lifecycle.paused.assert_called()
        expected_populations_arg = json.dumps(
            self.__mocked_cle.load_network_from_file.call_args[1]
        )
        self.assertEqual(populations_new, expected_populations_arg)
        self.__mocked_cle.load_network_from_file.reset_mock()
        request.data_type = "base64"
        request.brain_data = base64.encodestring(request.brain_data)
        response = set_brain_implementation(request)
        self.__mocked_cle.load_network_from_file.assert_called()
        request.data_type = "not_supported"
        response = set_brain_implementation(request)
        self.assertNotEqual("", response[0])

        request.brain_populations = "invalid JSON"
        response = set_brain_implementation(request)
        self.assertNotEqual("", response[0])
        request.brain_populations = populations_new

        def raise_syntax_error(foo):
            exec "Foo Bar"
        with patch("base64.decodestring") as mock_b64:
            request.data_type = "base64"
            mock_b64.side_effect = raise_syntax_error
            response = set_brain_implementation(request)
            self.assertNotEqual("", response[0])
            mock_b64.side_effect = Exception
            response = set_brain_implementation(request)
            self.assertNotEqual("", response[0])

    @patch('hbp_nrp_cleserver.server.ROSCLEServer.NamedTemporaryFile')
    @patch('hbp_nrp_cleserver.server.ROSCLEServer.SimulationServerLifecycle')
    def test_handling_BrainParameterException(self, mock_tempfile, mock_lifecycle):

        # any caught BrainParameterException exception should return [{msg}, -1, -1, 0]
        mock_tempfile.name = 'random_name_tempfile'

        self.__mocked_cle.load_network_from_file.side_effect = BrainParameterException("BrainParameterException")

        with patch("hbp_nrp_cleserver.server.ROSCLEServer.tf_framework") as mocked_tf_framework:

            slice1 = { 'from': 1, 'to': 2, 'step': 1}
            populations_json_slice = {
              'index1': 1,
              'slice_1': slice1,
              'list1': [1, 2, 3]
            }
            mocked_tf_framework.get_brain_populations = MagicMock(return_value=populations_json_slice)

            ros_callbacks = self.__get_handlers_for_testing_main()
            self.__mocked_cle.network_file = PropertyMock()
            set_brain_implementation = ros_callbacks['set_brain']

            request = Mock()
            request.data_type = "text"
            request.brain_type = "py"
            request.brain_data = "Dummy = None"
            request.brain_populations = json.dumps(populations_json_slice)
            request.change_population = srv.SetBrainRequest.ASK_RENAME_POPULATION
            response = set_brain_implementation(request)

            self.assertEqual(response[0], 'BrainParameterException')
            self.assertEqual(response[1], -1)
            self.assertEqual(response[2], -1)
            self.assertEqual(response[3], 0)

    @patch('hbp_nrp_cleserver.server.ROSCLEServer.tf_framework')
    def test_CSV_recorders_functions(self, mocked_tf_framework):
        ros_callbacks = self.__get_handlers_for_testing_main()
        get_CSV_recorders_files_implementation = ros_callbacks['get_CSV_recorders_files']
        clean_CSV_recorders_files_implementation = ros_callbacks['clean_CSV_recorders_files']
        mocked_tf_framework.dump_csv_recorder_to_files = Mock()
        mocked_tf_framework.dump_csv_recorder_to_files.return_value = [('a', 'b'), ('c', 'd')]
        result_value = get_CSV_recorders_files_implementation(None).files
        self.assertEqual(result_value[0].name, 'a')
        self.assertEqual(result_value[0].temporary_path, 'b')
        self.assertEqual(result_value[1].name, 'c')
        self.assertEqual(result_value[1].temporary_path, 'd')
        mocked_tf_framework.clean_csv_recorders_files = Mock()
        clean_CSV_recorders_files_implementation(None)
        self.assertEqual(1, mocked_tf_framework.clean_csv_recorders_files.call_count)

    def test_get_tf_name(self):
        tf1 = "def tf1  (a,b,c):\n return"
        tf2 = "not a tf"
        tf3 = "def tf1(a,b,c):\ndef tf2(a):\n    return  return"
        self.assertEqual(ROSCLEServer.ROSCLEServer.get_tf_name(tf1), (True, "tf1"))
        self.assertEqual(ROSCLEServer.ROSCLEServer.get_tf_name(tf2), (False, "New Transfer Function has no definition name. Compilation aborted"))
        self.assertEqual(ROSCLEServer.ROSCLEServer.get_tf_name(tf3), (False, "New Transfer Function has multiple definition names. Compilation aborted"))

    @patch('hbp_nrp_cleserver.server.ROSCLEServer.tf_framework')
    def test_get_transfer_functions(self, mocked_tf_framework):
        tf = [MagicMock(), MagicMock()]
        tf[0].source = "tf_0 python code"
        tf[0].active = True
        tf[1].source = "tf_1 python code"
        tf[1].active = False

        mocked_tf_framework.get_transfer_functions = MagicMock(return_value=tf)
        ros_callbacks = self.__get_handlers_for_testing_main()
        transfer_functions_from_service, active_tfs_mask = ros_callbacks['get_transfer_functions'](None)
        self.assertEqual(2, len(transfer_functions_from_service))
        self.assertEqual(2, len(active_tfs_mask))
        self.assertEqual("tf_0 python code", transfer_functions_from_service[0])
        self.assertEqual("tf_1 python code", transfer_functions_from_service[1])
        self.assertEqual(True, active_tfs_mask[0])
        self.assertEqual(False, active_tfs_mask[1])

    @patch('hbp_nrp_cleserver.server.ROSCLEServer.tf_framework')
    def test_activate_transfer_function_ok(self, mocked_tf_framework):

        mocked_tf = MagicMock()
        mocked_tf.configure_mock(name='tf_0', active=True)
        mocked_tf_framework.get_transfer_function = MagicMock(return_value=mocked_tf)
        mocked_tf_framework.activate_transfer_function = MagicMock()

        ros_callbacks = self.__get_handlers_for_testing_main()
        activate_transfer_function_handler = ros_callbacks['activate_transfer_function']

        new_activate = False
        request = MagicMock(transfer_function_name=mocked_tf.name, activate=new_activate)

        response_message = activate_transfer_function_handler(request)

        self.assertEqual(response_message, "")  # no error
        self.assertTrue(mocked_tf_framework.activate_transfer_function.called)

    @patch('hbp_nrp_cleserver.server.ROSCLEServer.tf_framework')
    def test_activate_transfer_function_no_tf(self, mocked_tf_framework):
        mocked_tf_framework.get_transfer_function = MagicMock(return_value=None)

        ros_callbacks = self.__get_handlers_for_testing_main()
        activate_transfer_function_handler = ros_callbacks['activate_transfer_function']

        request = MagicMock(transfer_function_name="tf_foo", activate=False)

        response_message = activate_transfer_function_handler(request)

        self.assertIn("not found", response_message)  # no error
        self.assertEqual(self.__mocked_notificator.publish_error.call_count, 1)  # publish error message

    @patch('hbp_nrp_cleserver.server.ROSCLEServer.StructuredTransferFunction')
    def test_set_structured_transfer_function(self, mocked_structured_tf):

        ros_callbacks = self.__get_handlers_for_testing_main()
        set_structured_transfer_function_handler = ros_callbacks['set_structured_transfer_function']

        mock_tf_name = "tf_0"
        mock_tf_source = "Some python code"
        mocked_structured_tf.generate_code_from_structured_tf = \
            MagicMock(return_value=mock_tf_source)

        mock_request = MagicMock(transfer_function=MagicMock())
        mock_request.transfer_function.name = mock_tf_name

        with patch.object(self.__ros_cle_server,
                          '_ROSCLEServer__set_transfer_function') as set_tf_mock:
            set_structured_transfer_function_handler(mock_request)
            request_arg = set_tf_mock.call_args[0][0]

        self.assertEqual(request_arg.transfer_function_name, mock_tf_name)
        self.assertEqual(request_arg.transfer_function_source, mock_tf_source)

    @patch('hbp_nrp_cleserver.server.ROSCLEServer.tf_framework')
    def test_edit_flawed_transfer_function(self, mocked_tf_framework):
        mocked_tf_framework.delete_flawed_transfer_function = MagicMock()
        mocked_tf_framework.get_flawed_transfer_function.return_value = MagicMock(name='mock_flawed_tf')

        ros_callbacks = self.__get_handlers_for_testing_main()
        add_transfer_function_handler = ros_callbacks['edit_transfer_function']
        request = MagicMock()
        request.transfer_function_name = "tf_0"
        request.transfer_function_source = "def tf0(): \n return 0"

        set_transfer_function_msg = ''
        with patch.object(self.__ros_cle_server,
                          '_ROSCLEServer__set_transfer_function',
                          return_value=set_transfer_function_msg):
            _ = add_transfer_function_handler(request)

        # when a flawed transfer function is patched, it should be deleted
        mocked_tf_framework.delete_flawed_transfer_function.assert_called_once()

    @patch('hbp_nrp_cleserver.server.ROSCLEServer.tf_framework')
    def test_edit_flawed_transfer_function_fail(self, mocked_tf_framework):
        mocked_tf_framework.delete_flawed_transfer_function = MagicMock()
        mocked_tf_framework.get_flawed_transfer_function.return_value = MagicMock(name='mock_flawed_tf')

        ros_callbacks = self.__get_handlers_for_testing_main()
        add_transfer_function_handler = ros_callbacks['edit_transfer_function']
        request = MagicMock()
        request.transfer_function_name = "tf_0"
        request.transfer_function_source = "def tf0(): \n return 0"

        set_transfer_function_message = "SOME ERROR"
        with patch.object(self.__ros_cle_server,
                          '_ROSCLEServer__set_transfer_function',
                          return_value=set_transfer_function_message):
            _ = add_transfer_function_handler(request)

        # when a flawed transfer function is patched, it should be deleted
        mocked_tf_framework.delete_flawed_transfer_function.assert_called_once()

    @patch('hbp_nrp_cleserver.server.ROSCLEServer.tf_framework')
    def test_edit_transfer_function(self, mocked_tf_framework):
        mocked_tf_framework.set_transfer_function = MagicMock(return_value=None)
        mocked_tf_framework.delete_transfer_function = MagicMock()
        ros_callbacks = self.__get_handlers_for_testing_main()
        add_transfer_function_handler = ros_callbacks['add_transfer_function']
        request = MagicMock()
        request.transfer_function_name = "tf_0"
        request.transfer_function_source = "def tf0(): \n return 0"
        response = add_transfer_function_handler(request)
        self.assertEqual("", response)

        mocked_tf_framework.delete_transfer_function.reset_mock()
        request.transfer_function_name = ""
        request.transfer_function_source = "def tf0(): \n return 0"
        response = add_transfer_function_handler(request)
        self.assertEqual(0, mocked_tf_framework.delete_transfer_function.call_count)
        self.assertEqual("", response)

        request.transfer_function_name = "tf_1"
        request.transfer_function_source = "def (): \n return -1"
        response = add_transfer_function_handler(request)
        self.assertIn("no definition name", response)

        # test add duplicate
        tf1_name = "tf_1"
        tf1_source = "def tf_1(): \n return -1"
        mock_tf = MagicMock(source=tf1_source, active=True)
        mocked_tf_framework.get_transfer_functions.return_value = [mock_tf]
        mocked_tf_framework.get_flawed_transfer_function.return_value = False

        request.transfer_function_name = tf1_name
        request.transfer_function_source = tf1_source

        response = add_transfer_function_handler(request)

        self.assertIn("duplicate", response)
        mocked_tf_framework.get_transfer_functions = MagicMock()  # reset return_value
        mocked_tf_framework.get_flawed_transfer_function = MagicMock()

        # test add flawed tf
        request.transfer_function_name = "tf_2"
        request.transfer_function_source = "def tf_2(): \n return -1 undefined"
        response = add_transfer_function_handler(request)
        self.assertEqual(0, mocked_tf_framework.delete_transfer_function.call_count)
        self.assertNotEquals("", response)

        request.transfer_function_name = "tf_3"
        request.transfer_function_source = "def tf_3_a(): \n\treturn -1\ndef tf_3_b(): \n\treturn -2"
        response = add_transfer_function_handler(request)
        self.assertIn("multiple definition names", response)

        # test add faulty tf
        with patch('hbp_nrp_cleserver.server.ROSCLEServer.compile_restricted') as compile_restricted:
            request.transfer_function_name = "tf_4"
            request.transfer_function_source = "def tf_4(): \n return 0"
            compile_restricted.side_effect = Exception("foo")
            response = add_transfer_function_handler(request)
            self.assertNotEquals("", response)

        mocked_tf_framework.set_transfer_function.side_effect = TFLoadingException("bar_name", "bar_message")
        self.__ros_cle_server._SimulationServer__lifecycle = Mock()
        response = add_transfer_function_handler(request)
        self.assertEqual("bar_message", response)

        mocked_tf_framework.set_transfer_function.reset_mock()
        name = "tf_3_a"
        request.transfer_function_name = name
        request.transfer_function_source = "def tf_3_a(): \n\tdef tf_3_b(): \n\t\treturn -2\n\treturn -1"
        response = add_transfer_function_handler(request)
        assert name in mocked_tf_framework.set_transfer_function.call_args[0]
        self.assertNotIn("multiple definition names", response)

    @patch('hbp_nrp_cleserver.server.ROSCLEServer.tf_framework')
    def test_delete_transfer_function(self, mocked_tf_framework):
        mocked_tf_framework.delete_transfer_function = MagicMock(return_value=True)
        ros_callbacks = self.__get_handlers_for_testing_main()
        delete_transfer_function_handler = ros_callbacks['delete_transfer_function']
        request = MagicMock()
        request.transfer_function_name = "tf_0"
        response = delete_transfer_function_handler(request)
        self.assertEqual(True, response)

    def test_change_tf_for_population(self):
        mock_tf = MagicMock()
        mock_tf.params = []
        mock_tf.source = "tf_source node_name"
        tfs = [mock_tf]
        ROSCLEServer.ROSCLEServer.change_transfer_function_for_population(MagicMock(), MagicMock(), MagicMock(), tfs)
        # check nothing has changed
        self.assertEqual(mock_tf.source, "tf_source node_name")

        mock_mapping = MagicMock()
        mock_mapping.name = "node_name"

        mock_spec = MagicMock(spec=["neurons"])
        mock_spec.neurons = mock_mapping

        mock_params = MagicMock(spec=["spec"])
        mock_params.spec = mock_spec
        mock_tf.params = ["t", mock_params]  # for some reason the real data has a t as in the list

        tfs = [mock_tf]
        self.assertEqual(ROSCLEServer.ROSCLEServer.change_transfer_function_for_population(srv.SetBrainRequest.ASK_RENAME_POPULATION, "node_name", MagicMock(), tfs), ["we ask the user if we change TFs", 0, 0, 1])
        self.assertEqual(mock_tf.source, "tf_source node_name")

        mock_mapping.name = ""
        mock_parent = MagicMock()
        mock_parent.name = "node_name"
        mock_mapping.parent = mock_parent

        ROSCLEServer.ROSCLEServer.change_transfer_function_for_population(srv.SetBrainRequest.DO_RENAME_POPULATION, "node_name", "new_node_name", tfs)
        self.assertEqual(mock_parent.name, "new_node_name")
        self.assertEqual(mock_tf.source, "tf_source new_node_name")

    def test_shutdown(self):
        z = self.__ros_cle_server._ROSCLEServer__cle = MagicMock()
        a = self.__ros_cle_server._SimulationServer__service_reset  = MagicMock()
        b = self.__ros_cle_server._ROSCLEServer__current_task = None
        c = self.__ros_cle_server._ROSCLEServer__service_get_transfer_functions = MagicMock()
        d = self.__ros_cle_server._SimulationServer__service_extend_timeout = MagicMock()
        e = self.__ros_cle_server._ROSCLEServer__service_add_transfer_function = MagicMock()
        f = self.__ros_cle_server._ROSCLEServer__service_edit_transfer_function = MagicMock()
        g = self.__ros_cle_server._ROSCLEServer__service_get_brain = MagicMock()
        h = self.__ros_cle_server._ROSCLEServer__service_set_brain = MagicMock()
        i = self.__ros_cle_server._ROSCLEServer__service_get_populations = MagicMock()
        j = self.__ros_cle_server._ROSCLEServer__service_get_CSV_recorders_files = MagicMock()
        k = self.__ros_cle_server._ROSCLEServer__service_clean_CSV_recorders_files = MagicMock()
        l = self.__ros_cle_server._ROSCLEServer__service_get_structured_transfer_functions = MagicMock()
        m = self.__ros_cle_server._ROSCLEServer__service_set_structured_transfer_function = MagicMock()
        n = self.__ros_cle_server._ROSCLEServer__service_delete_transfer_function = MagicMock()

        self.__ros_cle_server.shutdown()
        for x in [a, c, d, e, f, g, h, i, j, k, l, m, n, z]:
            self.assertEquals(x.shutdown.call_count, 1, repr(x) + " not shutdown")


if __name__ == '__main__':
    unittest.main()
