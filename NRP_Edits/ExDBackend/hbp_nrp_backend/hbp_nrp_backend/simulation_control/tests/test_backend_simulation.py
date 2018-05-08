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
This module tests the backend implementation of the simulation lifecycle
"""

from mock import Mock, patch
import unittest
import os
from hbp_nrp_backend.simulation_control.__BackendSimulationLifecycle import BackendSimulationLifecycle
from hbp_nrp_backend import NRPServicesGeneralException
from hbp_nrp_commons.generated import exp_conf_api_gen
import datetime
import rospy

PATH = os.path.split(__file__)[0]

__author__ = 'Georg Hinkel'


class TestBackendSimulationLifecycle(unittest.TestCase):

    def setUp(self):
        self.simulation = Mock()

        self.simulation.sim_id = 42
        self.simulation.experiment_conf = "ExDXMLExample.xml"
        self.simulation.environment_conf = None
        self.simulation.experiment_id = None
        self.simulation.state_machines = []
        self.simulation.playback_path = None
        self.simulation.private = None

        caller_id = patch(
            "hbp_nrp_commons.simulation_lifecycle.get_caller_id", return_value="test_client")
        caller_id.start()
        self.addCleanup(caller_id.stop)

        factory_client = patch(
            "hbp_nrp_backend.simulation_control.__BackendSimulationLifecycle.ROSCLESimulationFactoryClient")
        self.factory_mock = factory_client.start()
        self.addCleanup(factory_client.stop)

        cle_factory_client = patch(
            "hbp_nrp_backend.simulation_control.__BackendSimulationLifecycle.ROSCLEClient")
        self.cle_factory_mock = cle_factory_client.start()
        self.addCleanup(cle_factory_client.stop)

        playback_client = patch(
            "hbp_nrp_backend.cle_interface.PlaybackClient.PlaybackClient")
        self.playback_mock = playback_client.start()
        self.addCleanup(playback_client.stop)

        rospy_patch = patch(
            "hbp_nrp_backend.simulation_control.__BackendSimulationLifecycle.rospy")
        self.rospy_mock = rospy_patch.start()
        self.addCleanup(rospy_patch.stop)

        with patch("hbp_nrp_commons.simulation_lifecycle.Publisher"):
            with patch("hbp_nrp_commons.simulation_lifecycle.Subscriber"):
                self.lifecycle = BackendSimulationLifecycle(self.simulation)

        self.lifecycle.models_path = PATH
        self.lifecycle.experiment_path = PATH
        self.assertEqual("", self.lifecycle.simulation_root_folder)

    def test_init_playback(self):
        self.simulation.playback_path = 'foo'
        lifecycle = BackendSimulationLifecycle(self.simulation)
        self.playback_mock.assert_callled_once_with(42)

    def test_backend_initialize_non_storage(self):
        with patch("hbp_nrp_backend.simulation_control.__BackendSimulationLifecycle.UserAuthentication.get_header_token"):
            self.lifecycle.initialize(Mock())

            # Assert state machines have been initialized
            self.assertTrue(
                self.simulation.state_machine_manager.add_all.called)
            self.assertTrue(
                self.simulation.state_machine_manager.initialize_all.called)

            # Assert Simulation server has been called
            self.assertTrue(self.factory_mock.called)

            # Assert the simulation will be killed eventually
            self.assertIsInstance(
                self.simulation.kill_datetime, datetime.datetime)

            self.assertEqual(self.lifecycle.simulation_root_folder,
                             self.lifecycle.models_path)
            self.assertIsNotNone(self.lifecycle.experiment_path)

    def test_backend_initialize_state_machines(self):
        with patch("hbp_nrp_backend.simulation_control.__BackendSimulationLifecycle.UserAuthentication.get_header_token"):
            self.simulation.experiment_conf = "ExDXMLExampleWithStateMachines.xml"

            self.lifecycle.initialize(Mock())

            state_machines = self.simulation.state_machine_manager.add_all.call_args[0][0]

            self.assertEqual(2, len(state_machines))
            directory = PATH
            self.assertEqual(os.path.join(directory, "SM1.py"),
                             state_machines["SM1"])
            self.assertEqual(os.path.join(directory, "SM2.py"),
                             state_machines["SM2"])

    def test_backend_initialize_storage(self):
        self.simulation.experiment_id = "Foobar"
        self.simulation.experiment_conf = "ExDXMLExampleWithStateMachines.xml"
        directory = PATH
        with patch("hbp_nrp_backend.storage_client_api.StorageClient.StorageClient") as storage_client:
            with patch("hbp_nrp_backend.simulation_control.__BackendSimulationLifecycle.UserAuthentication.get_header_token") as user_auth:

                storage_paths = {
                    'experiment_conf': os.path.join(directory, "ExDXMLExampleWithStateMachines.xml"),
                    'environment_conf': "Neverland.sdf"
                }

                storage_client.clone_all_experiment_files.return_value = directory, storage_paths

                self.lifecycle.initialize(Mock())

                self.assertTrue(storage_client.clone_all_experiment_files)

        # Assert that the state machine experiment has been called
        state_machines = self.simulation.state_machine_manager.add_all.call_args[0][0]
        self.assertEqual(2, len(state_machines))

        self.assertIsNotNone(self.lifecycle.experiment_path)
        self.assertIsNotNone(self.lifecycle.simulation_root_folder)

    def test_backend_initialize_nonexisting_experiment(self):
        self.simulation.experiment_conf = "DoesNotExist.xml"
        self.assertRaises(NRPServicesGeneralException,
                          self.lifecycle.initialize, Mock())

    def test_backend_initialize_noclecommunication(self):
        self.rospy_mock.ROSException = rospy.ROSException
        self.factory_mock.side_effect = rospy.ROSException
        self.assertRaises(NRPServicesGeneralException,
                          self.lifecycle.initialize, Mock())

    def test_backend_initialize_service_problem(self):
        self.rospy_mock.ServiceException = rospy.ServiceException
        self.factory_mock.side_effect = rospy.ServiceException
        self.assertRaises(NRPServicesGeneralException,
                          self.lifecycle.initialize, Mock())

    def test_backend_start(self):
        self.lifecycle.start(Mock())

        # Assert state machines have been started
        self.assertTrue(self.simulation.state_machine_manager.start_all.called)

    def test_backend_start_state_machines_failed(self):
        self.simulation.state_machine_manager.start_all.side_effect = IOError
        self.lifecycle.start(Mock())

        # Assert no exception, but state machine manager was still called
        self.assertTrue(self.simulation.state_machine_manager.start_all.called)

    def test_backend_stop(self):
        self.simulation.context_id = "Foobar"

        with patch('tempfile.gettempdir', return_value='foo') as mock_tempfile,\
                patch('os.path.split', return_value=['foo', 'bar']) as mock_split, \
                patch('shutil.rmtree') as mock_rmtree, \
                patch('os.listdir') as mock_list_dir, \
                patch('tempfile.mkdtemp') as mock_mkdir:

            self.lifecycle.stop(Mock())
            mock_tempfile.assert_called_once()
            mock_split.assert_called_once()
            mock_rmtree.assert_called_once()
            mock_list_dir.assert_called_once()
            mock_mkdir.assert_called_once()

        # Assert State Machines have been terminated
        self.assertTrue(self.simulation.state_machine_manager.shutdown.called)

        self.assertIsNone(self.simulation.kill_datetime)

    def test_backend_pause(self):
        self.lifecycle.pause(Mock())
        # The method does nothing currently, so we have nothing to test

    def test_backend_fail(self):
        self.lifecycle.fail(Mock())

        # Assert state machines have been terminated
        self.assertTrue(
            self.simulation.state_machine_manager.terminate_all.called)

        self.assertIsNone(self.simulation.kill_datetime)

    def test_backend_reset(self):
        self.lifecycle.reset(Mock())

        # Assert state machines have been terminated
        self.assertTrue(
            self.simulation.state_machine_manager.terminate_all.called)

    def test_parse_env_path_template(self):
        exp_path = os.path.join(PATH, self.simulation.experiment_conf)
        with open(exp_path, 'r') as exp_file:
            exp = exp_conf_api_gen.CreateFromDocument(exp_file.read())
        env_path = self.lifecycle._parse_env_path(
            exp.environmentModel.src, exp, False)
        self.assertEqual(env_path, os.path.join(
            PATH, 'virtual_room/virtual_room.sdf'))

    @patch("hbp_nrp_backend.storage_client_api.StorageClient.StorageClient")
    def test_parse_env_path_custom_environment_throws(self, mock_storage):
        with patch("hbp_nrp_backend.simulation_control.__BackendSimulationLifecycle.UserAuthentication.get_header_token") as user_auth:
            mock_storage().get_custom_models.return_value = [
                {'path': 'fakePath'}]
            exp_path = os.path.join(PATH, 'ExDXMLExampleZipped.exc')
            with open(exp_path, 'r') as exp_file:
                exp = exp_conf_api_gen.CreateFromDocument(exp_file.read())
            with self.assertRaises(NRPServicesGeneralException) as context:
                self.lifecycle._parse_env_path(
                    exp.environmentModel.src, exp, True)
            self.assertEqual(
                NRPServicesGeneralException, context.expected)

    @patch("hbp_nrp_backend.storage_client_api.StorageClient.StorageClient")
    @patch("hbp_nrp_backend.simulation_control.__BackendSimulationLifecycle.zipfile")
    def test_parse_env_path_custom_environment_ok(self, mock_zip, mock_storage):
        with patch("hbp_nrp_backend.simulation_control.__BackendSimulationLifecycle.UserAuthentication.get_header_token") as user_auth:
            mock_storage().get_custom_models.return_value = [
                {'path': 'virtual_room.zip'}]
            mock_storage().get_custom_model.return_value = 'test'
            mock_storage().get_temp_directory.return_value = os.path.join(os.path.dirname(
                os.path.realpath(__file__)), 'zipped_data')
            import zipfile
            mock_zip.ZipFile.return_value = zipfile.ZipFile(os.path.join(
                os.path.dirname(os.path.realpath(__file__)), 'zipped_data', 'mouse_ymaze_world.zip'), 'r')
            exp_path = os.path.join(PATH, 'ExDXMLExampleZipped.exc')
            with open(exp_path, 'r') as exp_file:
                exp = exp_conf_api_gen.CreateFromDocument(exp_file.read())
            self.lifecycle._parse_env_path(
                exp.environmentModel.src, exp, True)
            self.assertEqual(exp.environmentModel.src, 'virtual_room.sdf')
            self.assertEqual(
                exp.environmentModel.customModelPath, 'virtual_room.zip')

    @patch("hbp_nrp_backend.storage_client_api.StorageClient.StorageClient")
    def test_parse_env_path_template_storage(self, mock_storage):
        exp_path = os.path.join(PATH, 'ExDXMLExample_2.xml')
        with open(exp_path, 'r') as exp_file:
            exp = exp_conf_api_gen.CreateFromDocument(exp_file.read())
        mock_storage().get_temp_directory.return_value = PATH
        mock_storage().get_file.return_value = '<sdf></sdf>'
        mock_storage().get_folder_uuid_by_name.return_value = 'environments'
        with patch("hbp_nrp_backend.simulation_control.__BackendSimulationLifecycle.UserAuthentication.get_header_token"):
            env_path = self.lifecycle._parse_env_path(
                None, exp, False)
            self.assertEqual(env_path, os.path.join(
                PATH, 'virtual_room.sdf'))

    @patch("hbp_nrp_backend.storage_client_api.StorageClient.StorageClient")
    def test_parse_env_path_template_storage_user_env(self, mock_storage):
        exp_path = os.path.join(PATH, 'ExDXMLExample_2.xml')
        with open(exp_path, 'r') as exp_file:
            exp = exp_conf_api_gen.CreateFromDocument(exp_file.read())

        mock_storage().get_temp_directory.return_value = PATH
        mock_storage().get_file.return_value = '<sdf></sdf>'
        mock_storage().get_folder_uuid_by_name.return_value = 'environments'
        with patch("hbp_nrp_backend.simulation_control.__BackendSimulationLifecycle.UserAuthentication.get_header_token"):
            env_path = self.lifecycle._parse_env_path(
                exp.environmentModel.src, exp, True)
            self.assertEqual(env_path, os.path.join(
                PATH, 'virtual_room.sdf'))
