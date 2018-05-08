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
Wrapper for roslaunch functionality, which must be run on a "main" thread.
"""

# nosetests has issues importing roslaunch since it includes some "from . import ..."
# statements that seem to break the strict PYTHONPATH set by ContinuousIntegration.
# There's no mechanism to exclude this file during test discovery (we can mock it in tests),
# detect if an ImportError occurs when being run by nosetests discovery and pass.
try:
    import roslaunch
except ImportError:
    import sys
    if 'nose' not in sys.modules.keys():
        raise
    from mock import Mock
    roslaunch = Mock()

from multiprocessing import Process, Manager

import ctypes
import os
import time


class ROSLaunch(object):
    """
    Use the roslaunch API within its own process to prevent threading issues and minimize
    re-implementation within the NRP. Provides clean startup/shutdown/exception handling.
    """

    def __init__(self, launch_file):
        """
        Launches the specified ROS .launch file in a separate subprocess.

        :param launch_file: The ROS .launch file to spawn.
        """

        # shared multi-process variables for running state and errors, use a Manager since we are
        # sharing strings and the underlying pointers will not be handled properly otherwise
        # our pylint version has issues introspecting multiprocessing, disable member checks
        # pylint: disable=no-member
        self._manager = Manager()
        self._running = self._manager.Value(ctypes.c_bool, False)
        self._error = self._manager.Value(ctypes.c_char_p, None)

        # launch the process
        self._process = Process(target=self.__launch,
                                args=(launch_file, self._running, self._error))
        self._process.start()

        # wait until the subprocess marks itself as started, dies, or we timeout waiting
        start = time.time()
        while not self._running.value and self._process.is_alive() and not self._error.value:
            time.sleep(0.1)
            if (time.time() - start) > 10.0:
                self._error.value = 'roslaunch failed, timed out waiting for launch.'

        # handle failure results, either graceful where we set the reason or unexpected
        if self._error.value:
            self._process.terminate() # should already be the case, but no harm
            raise Exception(self._error.value)
        elif not self._process.is_alive:
            raise Exception('roslaunch failed, unexpected termination.')

    def shutdown(self):
        """
        Terminate the roslaunch process and any child nodes.
        """

        # make sure we're actually running
        if not self._running.value or not self._process.is_alive():
            return

        # notify the subprocess to shutdown
        self._running.value = False

        # wait for termination of the subprocess
        while not self._error.value and self._process.is_alive():
            time.sleep(0.1)

        # check to see if we had a shutdown error/failure and propagate it
        if self._error.value:
            self._process.terminate() # should already be the case, but no harm
            raise Exception(self._error.value)

    @staticmethod
    def __launch(launch_file, running, error):
        """
        Perform the actual validation, launch, and shutdown tasks. Runs and locks until
        notified to shutdown through a shared multi-process variable.

        :param launch_file: The ROS .launch file to spawn.
        :param running: Shared multi-process variable to indicate running state.
        :param error: Shared multi-process variable to propagate error message.
        """
        try:

            # abort if the specified launch file does not exist / is inaccessible
            if not os.path.isfile(launch_file):
                raise Exception('ROS launch file does not exist: %s' % launch_file)
            elif not os.access(launch_file, os.R_OK):
                raise Exception('ROS launch file is not readable: %s' % launch_file)

            # configure roslaunch, force all output to stdout for our logger
            # based on example: http://wiki.ros.org/roslaunch/API%20Usage
            uuid = roslaunch.rlutil.get_or_generate_uuid(None, False)
            roslaunch.configure_logging(uuid)
            launch = roslaunch.parent.ROSLaunchParent(uuid, [launch_file], force_screen=True)

            # start the nodes and notify the waiting launch process
            launch.start()
            running.value = True

            # wait until notified to shutdown
            while running.value:
                time.sleep(0.1)

            # shutdown the launched nodes
            launch.shutdown()

        # pylint: disable=broad-except
        except Exception as e:
            error.value = str(e)
