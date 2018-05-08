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
SimulationServerLifecycle unit test
"""

from hbp_nrp_cleserver.server.SimulationServerLifecycle import SimulationServerLifecycle
import logging
from testfixtures import log_capture
import unittest
from concurrent.futures import Future
from mock import patch, MagicMock, Mock
from hbp_nrp_cle.tf_framework import TFException


class TestSimulationServerLifecycle(unittest.TestCase):

    LOGGER_NAME = 'hbp_nrp_cleserver.server.SimulationServerLifecycle'

    def setUp(self):
        self.mock_cle = MagicMock()
        self.mock_server = MagicMock()

        self.mock_event_instance = MagicMock()
        self.mock_thread_instance = MagicMock()
        self.mock_threading = \
            patch('hbp_nrp_cleserver.server.SimulationServerLifecycle.threading').start()
        self.mock_threading.Event.return_value = self.mock_event_instance
        self.mock_threading.Thread.return_value = self.mock_thread_instance
        self.mock_except_hook = Mock()

        self.ssl = SimulationServerLifecycle(0, self.mock_cle, self.mock_server, self.mock_except_hook)

    def test_init(self):
        self.mock_threading.Event.assert_called()

    def test_initialize(self):
        # Trying to initialize with initialized CLE
        self.mock_cle.is_initialized = True
        self.ssl.initialize('not relevant')
        self.assertFalse(self.mock_cle.initialize.called)
        # Trying to initialize with uninitialized CLE
        self.mock_cle.is_initialized = False
        self.ssl.initialize('not relevant')
        self.mock_cle.initialize.assert_called()

    def test_start(self):
        self.ssl.start('not relevant')
        self.mock_cle.start.assert_called()

        crash_cb = self.mock_cle.start_cb
        f1 = Future()
        crash_cb(f1)
        f1.set_running_or_notify_cancel()
        f1.set_exception(TFException(None, None, None))
        self.assertEquals(self.mock_server.publish_error.call_args_list[-1][0][0],
                          "Transfer Function")

        f2 = Future()
        crash_cb(f2)
        f2.set_running_or_notify_cancel()
        f2.set_exception(Exception())
        self.assertEquals(self.mock_server.publish_error.call_args_list[-1][0][0], "CLE")

    def test_stop(self):
        # Stop transition with everything all right
        self.ssl.stop('not relevant')
        self.mock_cle.stop.assert_called_once_with(forced=True)

        # Stop transition with a thread unwilling to stop
        e = Exception()
        self.mock_cle.stop.side_effect = e
        self.ssl.stop('not relevant')
        self.mock_except_hook.assert_called_once_with(e)

    def test_shutdown(self):
        # Testing shutdown
        self.ssl.shutdown('not relevant')
        self.mock_event_instance.set.assert_called()

    def test_fail(self):
        # Testing fail
        self.ssl.fail('not relevant')
        self.mock_cle.stop.assert_called()

    def test_pause(self):
        self.ssl.pause('not relevant')
        self.mock_cle.stop.assert_called()

    def test_reset(self):
        self.ssl.reset('not relevant')
        self.mock_server.start_fetching_gazebo_logs.assert_called()
        self.mock_cle.stop.assert_called()
        self.mock_cle.reset.assert_called()
        self.mock_server.stop_fetching_gazebo_logs.assert_called()

    def test_done_event(self):
        self.assertEquals(self.ssl.done_event, self.mock_event_instance)


if __name__ == '__main__':
    unittest.main()
