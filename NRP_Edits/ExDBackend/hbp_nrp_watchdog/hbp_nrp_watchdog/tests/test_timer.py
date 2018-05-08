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
Unit tests for the double timer used for the state publishing and the timeout
"""

__author__ = 'Lorenzo Vannucci, Alessandro Ambrosano'

from hbp_nrp_watchdog.Timer import Timer
import time
import threading

import unittest
import mock


class TestTimer(unittest.TestCase):

    def setUp(self):
        self.timer_return = False

    def test_timer(self):

        f = mock.Mock()

        # Testing ticks
        dt = Timer(0.1, f)
        dt.start()
        time.sleep(0.5)
        dt.cancel_all()
        self.assertGreaterEqual(f.call_count, 4)
        time.sleep(0.2)
        self.assertFalse(dt.isAlive())

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTimer)
    unittest.TextTestRunner(verbosity=2).run(suite)
