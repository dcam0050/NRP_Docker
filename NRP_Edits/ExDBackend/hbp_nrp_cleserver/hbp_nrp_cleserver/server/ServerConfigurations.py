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
This module contains the existing server configuration. Each configuration is represented
by a class that adopts the SimulationAssembly API.
"""

from hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly import CLEGazeboSimulationAssembly


def unused(_):
    """
    Marks an argument as unused
    """
    pass


def robot_gazebo_ros_adapters():
    """
    Creates the adapter components for the robot side, configuration with Gazebo

    :return: A tuple of the communication and control adapter for the robot side
    """
    from hbp_nrp_cle.robotsim.RosControlAdapter import RosControlAdapter
    from hbp_nrp_cle.robotsim.RosCommunicationAdapter import RosCommunicationAdapter
    # control adapter
    robotcontrol = RosControlAdapter()
    # communication adapter
    robotcomm = RosCommunicationAdapter()
    return robotcomm, robotcontrol


def robot_ros_adapters():
    """
    Creates the adapter components for the robot side, configuration with the real robot

    :return: A tuple of the communication and control adapter for the robot side
    """
    from hbp_nrp_cle.robotsim.RosRobotControlAdapter import RosRobotControlAdapter
    from hbp_nrp_cle.robotsim.RosCommunicationAdapter import RosCommunicationAdapter
    # control adapter
    robotcontrol = RosRobotControlAdapter()
    # communication adapter
    robotcomm = RosCommunicationAdapter()
    return robotcomm, robotcontrol


def brain_nest_adapters():
    """
    Creates the adapter components for the neural simulator, configuration with NEST

    :return: A tuple of the communication and control adapter for the neural simulator
    """
    import pyNN.nest as nestsim
    from hbp_nrp_cle.brainsim.pynn.PyNNControlAdapter import PyNNControlAdapter
    from hbp_nrp_cle.brainsim.pynn_nest.PyNNNestCommunicationAdapter import \
        PyNNNestCommunicationAdapter
    braincontrol = PyNNControlAdapter(nestsim)
    braincomm = PyNNNestCommunicationAdapter()
    return braincomm, braincontrol


def brain_spinnaker_adapters():  # pragma: no cover
    """
    Creates the adapter components for the neural simulator, configuration with SpiNNaker

    :return: A tuple of the communication and control adapter for the neural simulator
    """
    # pylint: disable=import-error, no-name-in-module
    try:
        import pyNN.spiNNaker as spinnaker
    except ImportError:
        try:
            import spynnaker8 as spinnaker
        except ImportError:
            raise Exception("Spinnaker does not seem to be installed on this machine. "
                            "Please install Spinnaker in order to use it in the NRP "
                            "or use a different server.")
    from hbp_nrp_cle.brainsim.pynn_spiNNaker.PyNNSpiNNakerCommunicationAdapter import \
        PyNNSpiNNakerCommunicationAdapter
    from hbp_nrp_cle.brainsim.pynn_spiNNaker.PyNNSpiNNakerControlAdapter import \
        PySpiNNakerControlAdapter
    return PyNNSpiNNakerCommunicationAdapter(), PySpiNNakerControlAdapter(spinnaker)


class SynchronousNestSimulation(CLEGazeboSimulationAssembly):
    """
    This class represents a synchronous simulation assembly using Nest as the neural simulator
    synchronous to Gazebo
    """

    def _create_robot_adapters(self):
        """
        Creates the adapter components for the robot side

        :return: A tuple of the communication and control adapter for the robot side
        """
        return robot_gazebo_ros_adapters()

    def _create_brain_adapters(self):
        """
        Creates the adapter components for the neural simulator

        :return: A tuple of the communication and control adapter for the neural simulator
        """
        return brain_nest_adapters()


class SynchronousSpinnakerSimulation(CLEGazeboSimulationAssembly):
    """
    This class represents a synchronous simulation assembly using SpiNNaker as the neural simulator
    """

    def _create_robot_adapters(self):  # pragma: no cover
        """
        Creates the adapter components for the robot side

        :return: A tuple of the communication and control adapter for the robot side
        """
        return robot_gazebo_ros_adapters()

    def _create_brain_adapters(self):  # pragma: no cover
        """
        Creates the adapter components for the neural simulator

        :return: A tuple of the communication and control adapter for the neural simulator
        """
        return brain_spinnaker_adapters()


class SynchronousRobotRosNest(CLEGazeboSimulationAssembly):
    """
    This class represents a synchronous simulation assembly using Nest as the neural simulator
    and a real robotic platform that uses ROS
    """

    def _load_environment(self, world_file, robot_file_abs):
        """
        Loads the environment and robot in Gazebo

        :param world_file Backwards compatibility for world file specified through webpage
        """
        unused(world_file)
        unused(robot_file_abs)
        return None, None, None

    def _create_robot_adapters(self):
        """
        Creates the adapter components for the robot side

        :return: A tuple of the communication and control adapter for the robot side
        """
        return robot_ros_adapters()

    def _create_brain_adapters(self):
        """
        Creates the adapter components for the neural simulator

        :return: A tuple of the communication and control adapter for the neural simulator
        """
        return brain_nest_adapters()
