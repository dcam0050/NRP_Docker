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
This module tests the simulate routine of the ROSCLESimulationFactory class
"""

__author__ = 'Bernd Eckstein'


import unittest
import os
from datetime import datetime, timedelta
import pytz
from hbp_nrp_cleserver.server.ROSCLESimulationFactory import ROSCLESimulationFactory
from mock import Mock, patch
from hbp_nrp_cle.mocks.robotsim import MockRobotControlAdapter, MockRobotCommunicationAdapter
from hbp_nrp_cleserver.server.LocalGazebo import LocalGazeboServerInstance
MODELS_PATH = os.path.split(__file__)[0]
EXPERIMENTS_PATH = os.path.join(MODELS_PATH, 'experiment_data')
tz = pytz.timezone("Europe/Zurich")



class MockedServiceRequest(object):
    environment_file = "environment_file.sdf"
    exd_config_file = os.path.join(EXPERIMENTS_PATH, "ExDXMLExample.exc")
    gzserver_host = "local"
    brain_processes = 1
    sim_id = 0
    timeout = str(datetime.now(tz) + timedelta(minutes=5))
    reservation = 'user_workshop'
    playback_path = None
    token = None
    ctx_id = None


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


class MockOs(object):
    environ = os.environ
    system = Mock()


@patch("hbp_nrp_cleserver.server.LocalGazebo.os", new=MockOs())
@patch('hbp_nrp_cleserver.server.LocalGazebo.Watchdog', new=Mock())
@patch("hbp_nrp_cleserver.server.SimulationAssembly.ROSNotificator", new=Mock())
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.ROSCLEServer", new=Mock())
@patch("hbp_nrp_cle.robotsim.RosControlAdapter.RosControlAdapter", new=MockRobotControlAdapter)
@patch("hbp_nrp_cle.robotsim.RosCommunicationAdapter.RosCommunicationAdapter", new=MockRobotCommunicationAdapter)
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.nrp.config.active_node", new=Mock())
@patch("hbp_nrp_cleserver.server.ROSCLESimulationFactory.get_experiment_basepath",
    new=Mock(return_value=EXPERIMENTS_PATH)
)
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.models_path", EXPERIMENTS_PATH)
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.LuganoVizClusterGazebo",
       new=lambda x, y: LocalGazeboServerInstance())
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.LocalGazeboBridgeInstance", new=Mock())
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.GazeboHelper", new=MockedGazeboHelper)
@patch("hbp_nrp_cle.cle.DeterministicClosedLoopEngine.GazeboHelper", new=MockedGazeboHelper)
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.ClosedLoopEngine", new=MockedClosedLoopEngine())
@patch("hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly.nrp", new=Mock())
class SimulationTestCase(unittest.TestCase):

    def test_simulation_local(self):

        factory = ROSCLESimulationFactory()
        factory.create_new_simulation(MockedServiceRequest())

        factory.simulation_terminate_event.wait()

    def test_simulation_lugano(self):

        MockedServiceRequest.gzserver_host = 'lugano'

        factory = ROSCLESimulationFactory()
        factory.create_new_simulation(MockedServiceRequest())

        factory.simulation_terminate_event.wait()


if __name__ == '__main__':
    unittest.main()
