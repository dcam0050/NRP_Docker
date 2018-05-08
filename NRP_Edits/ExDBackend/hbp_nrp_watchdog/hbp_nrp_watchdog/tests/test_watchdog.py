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
This module tests the watchdog implementation
"""

import unittest
from hbp_nrp_watchdog.Watchdog import Watchdog
from mock import patch, Mock

__author__ = "Georg Hinkel"


class TestWatchdog(unittest.TestCase):

    def callback(self):
        self.__callback_called = True

    @patch("hbp_nrp_watchdog.Watchdog.Timer")
    def setUp(self, timer_mock):
        self.__callback_called = False
        self.watchdog = Watchdog("foo", self.callback)
        self.timer_callback = timer_mock.call_args[0][1]
        self.timer_mock = timer_mock()

    def test_callback_called_when_process_died(self):
        with patch("hbp_nrp_watchdog.Watchdog.Watchdog._is_alive", return_value=False):
            self.timer_callback()
            self.assertTrue(self.__callback_called)

    def test_callback_not_called_when_process_still_alive(self):
        with patch("hbp_nrp_watchdog.Watchdog.Watchdog._is_alive", return_value=True):
            self.timer_callback()
            self.assertFalse(self.__callback_called)

    @patch("hbp_nrp_watchdog.Watchdog.psutil")
    def test_sanity_check_pids(self, ps_util_mock):
        p = Mock()
        p.name.return_value = "foobar"
        p.pid = 23
        ps_util_mock.Process.return_value = p
        ps_util_mock.NoSuchProcess = Exception
        with patch("hbp_nrp_watchdog.Watchdog.Timer"):
            self.assertEqual(23, Watchdog("foo", self.callback, 23).pid)
            self.assertIsNone(Watchdog("gzserver", self.callback, 23).pid)
            ps_util_mock.Process.side_effect = Exception
            self.assertIsNone(Watchdog("foo", self.callback, 23).pid)


    @patch("hbp_nrp_watchdog.Watchdog.psutil")
    def test_is_alive_suceeds_process_found(self, ps_util_mock):
        p1 = Mock()
        p1.name.return_value = "gzserver"
        p1.pid = 8
        p2 = Mock()
        p2.name.return_value = "foobar"
        p2.pid = 42
        ps_util_mock.process_iter.return_value = [p1, p2]
        self.timer_callback()
        self.assertFalse(self.__callback_called)
        self.assertEqual(42, self.watchdog.pid)

    @patch("hbp_nrp_watchdog.Watchdog.psutil")
    def test_is_alive_fails_if_process_dead(self, ps_util_mock):
        p1 = Mock()
        p1.name.return_value = "gzserver"
        p1.pid = 8
        ps_util_mock.process_iter.return_value = [p1]
        self.timer_callback()
        self.assertTrue(self.__callback_called)
        self.assertIsNone(self.watchdog.pid)

    @patch("hbp_nrp_watchdog.Watchdog.psutil")
    def test_is_alive_does_not_reiterate_if_pid_known(self, ps_util_mock):
        p1 = Mock()
        p1.name.return_value = "gzserver"
        p1.pid = 8
        p2 = Mock()
        p2.name.return_value = "foobar"
        p2.pid = 42
        ps_util_mock.process_iter.return_value = [p1, p2]
        self.timer_callback()
        self.assertFalse(self.__callback_called)
        ps_util_mock.process_iter.return_value = []
        ps_util_mock.pid_exists.return_value = True
        self.timer_callback()
        self.assertFalse(self.__callback_called)
        ps_util_mock.pid_exists.return_value = False
        self.timer_callback()
        self.assertTrue(self.__callback_called)

    @patch("hbp_nrp_watchdog.Watchdog.psutil")
    def test_reset_forgets_pid(self, ps_util_mock):
        p1 = Mock()
        p1.name.return_value = "gzserver"
        p1.pid = 8
        p2 = Mock()
        p2.name.return_value = "foobar"
        p2.pid = 42
        ps_util_mock.process_iter.return_value = [p1, p2]
        self.timer_callback()
        self.assertFalse(self.__callback_called)
        ps_util_mock.process_iter.return_value = []
        ps_util_mock.pid_exists.return_value = True
        self.watchdog.reset()
        self.timer_callback()
        self.assertTrue(self.__callback_called)

    def test_start_starts_timer(self):
        self.watchdog.start()
        self.timer_mock.start.assert_called_once_with()

    def test_stop_stops_timer(self):
        self.watchdog.stop()
        self.timer_mock.cancel_all.assert_called_once_with()
