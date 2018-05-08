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
PlaybackServerLifecycle unit test
"""

from hbp_nrp_cleserver.server.PlaybackServerLifecycle import PlaybackServerLifecycle
import logging
from testfixtures import log_capture
import unittest
from mock import patch, MagicMock, Mock
from hbp_nrp_cle.tf_framework import TFException


class TestPlaybackServerLifecycle(unittest.TestCase):

    LOGGER_NAME = 'hbp_nrp_cleserver.server.PlaybackServerLifecycle'

    def setUp(self):
        self.mock_cle = MagicMock()
        self.mock_server = MagicMock()
        self.mock_double_timer_instance = MagicMock()
        self.mock_double_timer = \
            patch('hbp_nrp_cleserver.server.PlaybackServerLifecycle.DoubleTimer',
            MagicMock(return_value=self.mock_double_timer_instance))

        self.mock_event_instance = MagicMock()
        self.mock_thread_instance = MagicMock()
        self.mock_threading = \
            patch('hbp_nrp_cleserver.server.PlaybackServerLifecycle.threading').start()
        self.mock_threading.Event.return_value = self.mock_event_instance
        self.mock_threading.Thread.return_value = self.mock_thread_instance

        self.pbl = PlaybackServerLifecycle(0, self.mock_server)

    def test_init(self):
        self.mock_double_timer_instance.start.assert_called()
        self.mock_double_timer_instance.enable_second_callback.assert_called()
        self.mock_threading.Event.assert_called()

    def test_shutdown(self):
        # Testing shutdown
        self.pbl.shutdown('not relevant')
        self.mock_event_instance.set.assert_called()

    def test_fail(self):
        # Testing fail
        self.pbl.fail('not relevant')
        self.mock_server.publish_state_update.assert_called()

    def test_start(self):
        self.pbl.start('not relevant')
        self.mock_server.process_lifecycle_command.assert_called_with('start')

    def test_stop(self):
        self.pbl.stop('not relevant')
        self.mock_server.process_lifecycle_command.assert_called_with('stop')

    def test_pause(self):
        self.pbl.pause('not relevant')
        self.mock_server.process_lifecycle_command.assert_called_with('pause')

    def test_done_event(self):
        self.assertEquals(self.pbl.done_event, self.mock_event_instance)

    def test_unused(self):
        # not really tests, for code coverage / interface requirements
        self.pbl.initialize('not relevant')
        self.pbl.reset('not relevant')

if __name__ == '__main__':
    unittest.main()
