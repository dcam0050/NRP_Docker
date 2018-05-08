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
This module contains the unit tests for the cle launcher shutdown
"""

import unittest
import os
from mock import patch, Mock
from hbp_nrp_cleserver.server import CLEGazeboSimulationAssembly
from hbp_nrp_commons.generated import bibi_api_gen, exp_conf_api_gen


MockOs = Mock()
MockOs.environ = {'NRP_MODELS_DIRECTORY': '/somewhere/near/the/rainbow',
                  'ROS_MASTER_URI': "localhost:0815"}
MockOs.path.join.return_value = "/a/really/nice/place"


@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.os", new=Mock())
class TestCLELauncherShutdown(unittest.TestCase):
    def setUp(self):
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
        self.launcher.cle_server = Mock()
        self.launcher.gzweb = Mock()
        self.launcher.gzserver = Mock()
        self.launcher.gazebo_recorder = Mock()
        self.launcher.ros_notificator = Mock()
        self.launcher.ros_launcher = Mock()

    def test_shutdown_stops_everything(self):
        self.launcher.shutdown()
        self.__assert_everything_properly_shut_down()

    def __assert_everything_properly_shut_down(self):
        self.launcher.gzweb.stop.assert_called_once_with()
        self.launcher.gzserver.stop.assert_called_once_with()
        self.launcher.cle_server.shutdown.assert_called_once_with()
        self.launcher.gazebo_recorder.shutdown.assert_called_once_with()
        self.launcher.ros_notificator.shutdown.assert_called_once_with()

    def test_notify_throws_but_assets_shut_down(self):
        self.launcher.cle_server.notify_start_task.side_effect = Exception
        self.launcher.shutdown()
        self.__assert_everything_properly_shut_down()

    def test_gzserver_shut_down_if_gzweb_throws(self):
        self.launcher.gzweb.stop.side_effect = Exception
        self.launcher.shutdown()
        self.__assert_everything_properly_shut_down()

    def test_cleserver_shutdown_raises(self):
        self.launcher.cle_server.shutdown.side_effect = Exception
        self.launcher.shutdown()
        self.__assert_everything_properly_shut_down()

    def test_gazebo_recorder_shutdown_raises(self):
        self.launcher.gazebo_recorder.shutdown.side_effect = Exception
        self.launcher.shutdown()
        self.__assert_everything_properly_shut_down()

    def test_gzserver_shutdown_raises(self):
        self.launcher.gzserver.shutdown.side_effect = Exception
        self.launcher.shutdown()
        self.__assert_everything_properly_shut_down()

    def test_notifications_failure(self):
        self.launcher.ros_notificator.start_task.side_effect = Exception
        self.launcher.shutdown()
        self.__assert_everything_properly_shut_down()
        self.assertFalse(self.launcher.ros_notificator.finish_task.called)

    def test_notificator_shutdown_raises(self):
        self.launcher.ros_notificator.shutdown.side_effect = Exception
        self.launcher.shutdown()
        self.__assert_everything_properly_shut_down()

    def __create_roslaunch(self):
        launch = exp_conf_api_gen.RosLaunch()
        launch.src = "some launch file"
        return launch

    def test_roslaunch_shutdown(self):
        self.launcher.exc.rosLaunch = self.__create_roslaunch()
        self.launcher.shutdown()
        self.__assert_everything_properly_shut_down()
        self.launcher.ros_launcher.shutdown.assert_called_once_with()

    def test_roslaunch_raises(self):
        self.launcher.exc.rosLaunch = self.__create_roslaunch()
        self.launcher.ros_launcher.side_effect = Exception
        self.launcher.shutdown()
        self.__assert_everything_properly_shut_down()
        self.launcher.ros_launcher.shutdown.assert_called_once_with()
