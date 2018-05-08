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
This module contains the unit tests for the ros launcher
"""

import unittest
from mock import patch, Mock

from hbp_nrp_cleserver.server.ROSLaunch import ROSLaunch

import time
import inspect


class MockValue(object):

    def __init__(self, value):
        self.value = value


class TestROSLaunch(unittest.TestCase):

    def test_launch_successful(self):

        def mock_launch(that, launch_file, running, error):
            running.value = True
            time.sleep(1)

        with patch.object(ROSLaunch, '_ROSLaunch__launch', mock_launch):
            foo = ROSLaunch('foo.launch')
            self.assertEquals(foo._running.value, True)
            self.assertEquals(foo._error.value, None)

    def test_launch_error(self):

        def mock_launch(that, launch_file, running, error):
            running.value = False
            error.value = 'launch error'
            time.sleep(1)

        with patch.object(ROSLaunch, '_ROSLaunch__launch', mock_launch):
            self.assertRaises(Exception, ROSLaunch, 'foo.launch')

    def test_launch_timeout(self):

        def mock_launch(that, launch_file, running, error):
            time.sleep(30)

        real_time = time.time
        times = [1000000.0, 0.0]
        def mock_time():
            # introspect the stack to see if we are called by ROSLaunch
            # known position in stack (frame 4 below nosetests, name of calling file)
            if 'ROSLaunch.py' in inspect.stack()[3][1]:
                return times.pop() # pop starts at the end of the list

            # otherwise return a real time value
            return real_time()

        with patch.object(ROSLaunch, '_ROSLaunch__launch', mock_launch),\
             patch('hbp_nrp_cleserver.server.ROSLaunch.time.time', side_effect=mock_time):
            self.assertRaises(Exception, ROSLaunch, 'foo.launch')

    def test_file_missing(self):

        mock_running = MockValue(False)
        mock_error = MockValue(None)

        ROSLaunch._ROSLaunch__launch('foo.launch', mock_running, mock_error)
        self.assertEquals(mock_error.value, 'ROS launch file does not exist: foo.launch')
        self.assertEquals(mock_running.value, False)

    @patch('os.path.isfile', return_value=True)
    def test_file_unreadable(self, mock_isfile):

        mock_running = MockValue(False)
        mock_error = MockValue(None)

        ROSLaunch._ROSLaunch__launch('foo.launch', mock_running, mock_error)
        self.assertEquals(mock_error.value, 'ROS launch file is not readable: foo.launch')
        self.assertEquals(mock_running.value, False)

    @patch('os.path.isfile', return_value=True)
    @patch('os.access', return_value=True)
    @patch('hbp_nrp_cleserver.server.ROSLaunch.roslaunch')
    def test_launch_logic(self, mock_roslaunch, mock_access, mock_isfile):

        mock_running = MockValue(False)
        mock_error = MockValue(None)

        def mock_sleep(time):
            mock_running.value = False

        with patch('time.sleep', side_effect=mock_sleep):
            ROSLaunch._ROSLaunch__launch('foo.launch', mock_running, mock_error)
            self.assertEquals(mock_error.value, None)
            self.assertEquals(mock_running.value, False)

    def test_shutdown(self):

        mock_process = Mock()

        def mock_launch(that, launch_file, running, error):
            running.value = True
            time.sleep(1)

        def mock_sleep(time):
            mock_process.is_alive = Mock(return_value=False)

        with patch.object(ROSLaunch, '_ROSLaunch__launch', mock_launch),\
             patch('time.sleep', side_effect=mock_sleep) as mock_time:
            foo = ROSLaunch('foo.launch')

            # should abort if already shut down
            foo._process = mock_process
            foo._process.is_alive = Mock(return_value=False)
            foo.shutdown()
            mock_time.assert_not_called()

            # clean shutdown
            foo._process.is_alive = Mock(return_value=True)
            foo.shutdown()
            self.assertEquals(foo._running.value, False)

            # failed shutdown
            foo._process.is_alive = Mock(return_value=True)
            foo._running.value = True

            def mock_sleep_fail(time):
                foo._error.value = 'shutdown fail'
            mock_time.side_effect = mock_sleep_fail

            self.assertRaises(Exception, foo.shutdown)

if __name__ == '__main__':
    unittest.main()
