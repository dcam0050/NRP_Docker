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
This module contains the unit tests for the cle launcher initialization
"""

import unittest
import os
from mock import patch, MagicMock, Mock
from hbp_nrp_cleserver.server import CLEGazeboSimulationAssembly
from hbp_nrp_commons.generated import bibi_api_gen, exp_conf_api_gen
from hbp_nrp_cleserver.server.LuganoVizClusterGazebo import XvfbXvnError
from hbp_nrp_cle.mocks.robotsim import MockRobotControlAdapter, MockRobotCommunicationAdapter
from threading import Thread, Event
import hbp_nrp_cle.tf_framework as nrp

class MockedGazeboHelper(object):

    def load_gazebo_world_file(self, world):
        return {}, {}

    @staticmethod
    def parse_gazebo_world_file(world):
        return {}, {}

    def __getattr__(self, x):
        return Mock()

class MockedClosedLoopEngine(Mock):

    DEFAULT_TIMESTEP = 0.02


MockOs = Mock()
MockOs.environ = {'NRP_MODELS_DIRECTORY': '/somewhere/near/the/rainbow',
                  'ROS_MASTER_URI': "localhost:0815"}
MockOs.path.join.return_value = "/a/really/nice/place"

class SomeWeirdTFException(Exception):
    pass


@patch("hbp_nrp_cleserver.server.SimulationAssembly.os", new=Mock())
@patch("hbp_nrp_cleserver.server.SimulationAssembly.ROSNotificator", new=Mock())
@patch("hbp_nrp_cle.robotsim.RosControlAdapter.RosControlAdapter", new=MockRobotControlAdapter)
@patch("hbp_nrp_cle.robotsim.RosCommunicationAdapter.RosCommunicationAdapter", new=MockRobotCommunicationAdapter)
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.LocalGazeboBridgeInstance", new=Mock())
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.GazeboHelper", new=MockedGazeboHelper)
@patch("hbp_nrp_cle.cle.DeterministicClosedLoopEngine.GazeboHelper", new=MockedGazeboHelper)
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.ClosedLoopEngine", new=MockedClosedLoopEngine())
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.CLEGazeboSimulationAssembly._create_brain_adapters", new=Mock(return_value=(Mock(), Mock())))
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.CLEGazeboSimulationAssembly._create_robot_adapters", new=Mock(return_value=(Mock(), Mock())))
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.os", new=MockOs)
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.CLEGazeboSimulationAssembly._get_robot_abs_path", new=Mock(return_value="/a/robot/under/the/rainbow/model.sdf"))
class TestCLELauncherInit(unittest.TestCase):

    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.LocalGazeboServerInstance")
    def setUp(self, mock_gazebo):
        self.mock_gazebo = mock_gazebo

        dir = os.path.split(__file__)[0]
        with open(os.path.join(dir, "experiment_data/milestone2.bibi")) as bibi_file:
            bibi = bibi_api_gen.CreateFromDocument(bibi_file.read())
        with open(os.path.join(dir, "experiment_data/ExDXMLExample.exc")) as exd_file:
            exd = exp_conf_api_gen.CreateFromDocument(exd_file.read())
        exd.path = "/somewhere/over/the/rainbow/exc"
        exd.dir = "/somewhere/over/the/rainbow"
        bibi.path = "/somewhere/over/the/rainbow/bibi"

        models_path_patch = patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.models_path", "/somewhere/near/the/rainbow")
        models_path_patch.start()
        self.addCleanup(models_path_patch.stop)

        with patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.os", MockOs):
            self.launcher = CLEGazeboSimulationAssembly.CLEGazeboSimulationAssembly(42, exd, bibi, gzserver_host="local")

    def tearDown(self):
        self.launcher.shutdown()

    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.ROSCLEServer")
    def test_gazebo_start_exception_catches_xvfbxvn_error(self, mock_server):
        self.mock_gazebo().start.side_effect = XvfbXvnError
        exception_caught = False
        try:
            self.launcher.initialize("world_file", None)
        except Exception, e:
            self.assertTrue(str(e).startswith("Recoverable error occurred"), msg=e)
            exception_caught = True
        self.assertTrue(exception_caught)

    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.nrp")
    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.ROSCLEServer")
    def test_wrong_transfer_function_aborts_initialization(self, mock_server, mock_nrp):
        mock_nrp.set_transfer_function.side_effect = SomeWeirdTFException

        with self.assertRaises(SomeWeirdTFException):

            self.launcher.initialize("world_file", None)

            # tf should not be set as faulty
            mock_nrp.set_faulty_transfer_function.assert_not_called()

    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.nrp")
    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.ROSCLEServer")
    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.compile_restricted")
    def test_faulty_tf_does_not_aborts_initialization_syntax_error(self, comp_restricted_mock, mock_server, mock_nrp):

        mock_nrp.set_faulty_transfer_function = MagicMock()
        comp_restricted_mock.side_effect = SyntaxError()

        try:
            self.launcher.initialize("world_file", None)
        except SyntaxError:
            self.fail('CLEGazeboSimulationAssembly.initialize should NOT propagate a SyntaxError.')

        mock_nrp.set_faulty_transfer_function.assert_called_once()

    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.nrp")
    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.ROSCLEServer")
    def test_faulty_tf_does_not_aborts_initialization_TFLoading_exception(self, mock_server, mock_nrp):

        mock_nrp.set_faulty_transfer_function = MagicMock()

        mock_nrp.TFLoadingException = nrp.TFLoadingException  # restore TFLoadingException class in the mock
        mock_nrp.set_transfer_function = MagicMock(side_effect=nrp.TFLoadingException('tf_foo', 'foo error'))

        try:
            self.launcher.initialize("world_file", None)
        except nrp.TFLoadingException:
            self.fail('CLEGazeboSimulationAssembly.initialize should NOT propagate a TFLoadingException.')

        mock_nrp.set_faulty_transfer_function.assert_called_once()

    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.nrp")
    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.ROSCLEServer")
    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.compile_restricted")
    def test_faulty_tf_does_not_aborts_initialization_Syntax_exception(self, comp_restricted_mock, mock_server, mock_nrp):

        mock_nrp.set_faulty_transfer_function = MagicMock()
        comp_restricted_mock.side_effect = SyntaxError()

        try:
            self.launcher.initialize("world_file", None)
        except SyntaxError:
            self.fail('CLEGazeboSimulationAssembly.initialize should NOT propagate a SyntaxError.')

        mock_nrp.set_faulty_transfer_function.assert_called_once()

    def __launch_callback(self, *_):
        self.launcher.gzserver.gazebo_died_callback()

    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.nrp")
    @patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.ROSCLEServer")
    def test_gazebo_crash_aborts_initialization(self, mock_server, mock_nrp):
        self.mock_gazebo().start.side_effect = self.__launch_callback
        exception_caught = False
        try:
            self.launcher.initialize("world_file", None)
        except Exception, e:
            self.assertTrue(str(e).startswith("The simulation must abort"), msg=e)
            exception_caught = True
        self.assertTrue(exception_caught)
        mock_server().lifecycle.failed.assert_called_once_with()
        mock_server().lifecycle.stopped.assert_called_once_with()
