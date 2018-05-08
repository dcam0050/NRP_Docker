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
Tests for cleanup.py
"""

import unittest
from mock import patch, MagicMock
import hbp_nrp_backend.rest_server.cleanup as cleanup
from datetime import datetime, timedelta
import pytz


class TestCleanup(unittest.TestCase):
    @patch('hbp_nrp_backend.rest_server.cleanup.simulations')
    def test_remove_old_simulations(self, simulations):
        timezone = pytz.timezone('Europe/Zurich')

        sim = MagicMock()
        sim.kill_datetime = datetime.now(timezone) - timedelta(days=2)
        sim.sim_id = 5
        sim.state = 'running'

        sim2 = MagicMock()
        sim2.kill_datetime = datetime.now(timezone) + timedelta(days=2)
        sim2.sim_id = 5
        sim2.state = 'running'

        simulations.__iter__.return_value = [sim, sim2]
        cleanup.remove_old_simulations()
        assert sim.state == 'stopped'
        assert sim2.state == 'running'


if __name__ == '__main__':
    unittest.main()
