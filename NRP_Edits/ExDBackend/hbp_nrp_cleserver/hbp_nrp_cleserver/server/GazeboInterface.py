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
Interface for gzserver and gzbridge spawning classes.
"""

__author__ = 'Alessandro Ambrosano'


class IGazeboServerInstance(object):
    """
    Takes care of starting a gzserver process somewhere, connect it to the given roscore.
    Each implementation has to take care of providing the methods start, stop and restart as
    well as a property containing the gzserver master URI.
    """

    def __init__(self):
        self.__gazebo_died_callback = None

    @property
    def gazebo_died_callback(self):  # pragma: no cover
        """
        Gets the callback when gazebo dies
        """
        return self.__gazebo_died_callback

    @gazebo_died_callback.setter
    def gazebo_died_callback(self, callback):
        """
        Sets the callback when gazebo dies

        :param callback: The new callback
        """
        self.__gazebo_died_callback = callback

    def _raise_gazebo_died(self):
        """
        Informs clients that Gazebo has died
        """
        if self.__gazebo_died_callback is not None:
            self.__gazebo_died_callback()

    def start(self, ros_master_uri, models_path=None, gzserver_args=None):   # pragma: no cover
        """
        Starts a gzserver instance connected to the local roscore (provided by
        ros_master_uri)

        :param ros_master_uri: The ros master uri where to connect gzserver.
        :param models_path: An additional path where Gazebo may find models
        :param gzserver_args: Additional formatted string of command line arguments to pass to
                              gzserver (e.g. --seed 123456 -e simbody)
        """
        raise NotImplementedError("This method was not implemented in the concrete implementation")

    def stop(self):   # pragma: no cover
        """
        Stops the gzserver instance.
        """
        raise NotImplementedError("This method was not implemented in the concrete implementation")

    def try_extend(self, new_timeout):  # pragma: no cover
        """"
        Verifies that the gazebo can accept the new simulation timeout
        """
        raise NotImplementedError("This method was not implemented in the concrete implementation")

    @property
    def gazebo_master_uri(self):   # pragma: no cover
        """
        Returns a string containing the gazebo master
        URI (like:'http://bbpviz001.cscs.ch:11345')
        """
        raise NotImplementedError("This method was not implemented in the concrete implementation")

    def restart(self, ros_master_uri):   # pragma: no cover
        """
        Restarts the gzserver instance.

        :param ros_master_uri The ros master uri where to connect gzserver.
        """
        raise NotImplementedError("This method was not implemented in the concrete implementation")


class IGazeboBridgeInstance(object):   # pragma: no cover
    """
    Takes care of starting a gzserver instance somewhere.
    """

    def start(self):
        """
        Starts the gzbridge instance represented by the object.
        """
        raise NotImplementedError("This method was not implemented in the concrete implementation")

    def stop(self):
        """
        Stops the gzbridge instance represented by the object.
        """
        raise NotImplementedError("This method was not implemented in the concrete implementation")

    def restart(self):
        """
        Restarts the gzbridge instance represented by the object.
        """
        raise NotImplementedError("This method was not implemented in the concrete implementation")
