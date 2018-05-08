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
from hbp_nrp_cleserver.server.LuganoVizClusterGazebo import LuganoVizClusterGazebo

import unittest
from mock import patch, Mock, MagicMock
import os

__author__ = 'Alessandro Ambrosano'


class TestLuganoVizClusterGazebo(unittest.TestCase):

    def setUp(self):
        self.instance = LuganoVizClusterGazebo()

    @patch('pexpect.spawn')
    def test_start_fake_x(self, mock_spawn):
        mock_spawn().expect = Mock(return_value=1)
        mock_spawn.call_count = 0

        self.instance._start_fake_X()
        self.assertEqual(mock_spawn.call_count, 1)
        self.assertNotEqual(mock_spawn().expect.call_count, 0)

        mock_spawn().expect = Mock(return_value = 3)
        self.assertRaises(Exception, self.instance._start_fake_X)

    @patch('pexpect.spawn')
    def test_spawn_vglconnect(self, mock_spawn):
        # failure: __node is None
        self.instance._node = None
        self.assertRaises(Exception, self.instance._spawn_vglconnect)

        # failure: __allocation_process is None
        self.instance = LuganoVizClusterGazebo()
        self.instance._allocation_process = None
        self.assertRaises(Exception, self.instance._spawn_vglconnect)

        self.instance._node = 'something that won\'t be used'
        self.instance._allocation_process = mock_spawn()

        mock_spawn().sendline = Mock()
        mock_spawn().expect = Mock(return_value=0)
        mock_spawn.call_count = 0

        # successful call
        self.instance._spawn_vglconnect()
        self.assertEqual(mock_spawn.call_count, 1)
        self.assertNotEqual(mock_spawn().sendline.call_count, 0)

        # password missing
        mock_spawn().expect = Mock(return_value=1)
        self.assertRaises(Exception, self.instance._spawn_vglconnect)

        # generic error
        mock_spawn().expect = Mock(return_value=2)
        self.assertRaises(Exception, self.instance._spawn_vglconnect)

        self.instance = LuganoVizClusterGazebo()

    @patch('pexpect.spawn')
    def test_start_xvnc(self, mock_spawn):
        self.instance._spawn_vglconnect = mock_spawn
        mock_spawn().sendline = Mock()

        # failure: __node is None
        self.instance._node = None
        self.assertRaises(Exception, self.instance._start_xvnc)

        # failure: __allocation_process is None
        self.instance = LuganoVizClusterGazebo()
        self.instance._allocation_process = None
        self.assertRaises(Exception, self.instance._start_xvnc)

        self.instance._node = 'something that won\'t be used'
        self.instance._allocation_process = mock_spawn()

        mock_spawn().sendline = Mock()

        # error creating vnc
        mock_spawn().expect = Mock(return_value=1)
        self.assertRaises(Exception, self.instance._start_xvnc)

        # successful call
        mock_spawn().expect = Mock(return_value=0)
        mock_spawn.call_count = 0
        self.instance._start_xvnc()
        self.assertEqual(mock_spawn.call_count, 1)
        self.assertNotEqual(mock_spawn().sendline.call_count, 0)
        self.assertNotEqual(mock_spawn().expect.call_count, 0)

        self.instance = LuganoVizClusterGazebo()

    @patch('pexpect.spawn')
    @patch('hbp_nrp_cleserver.server.LuganoVizClusterGazebo.os.environ')
    def test_start_gazebo(self, mock_os_environ, mock_spawn):
        # failure: __node is None
        self.instance = LuganoVizClusterGazebo()
        self.instance._node = None
        self.assertRaises(Exception, self.instance._start_gazebo, 'random_master_uri')

        # failure: __allocation_process is None
        self.instance = LuganoVizClusterGazebo()
        self.instance._allocation_process = None
        self.assertRaises(Exception, self.instance._start_gazebo, 'random_master_uri')

        # failure: __remote_display_port is -1
        self.instance = LuganoVizClusterGazebo()
        self.instance._remote_display_port = -1
        self.assertRaises(Exception, self.instance._start_gazebo, 'random_master_uri')

        self.instance = LuganoVizClusterGazebo()
        self.instance._node = 'not none'
        self.instance._allocation_process = 'this neither'
        self.instance._remote_display_port = 1
        self.instance._spawn_vglconnect = mock_spawn

        mock_spawn().sendline = Mock()
        mock_spawn().expect = Mock(return_value=1)
        self.assertRaises(Exception, self.instance._start_gazebo, 'random_master_uri')

        self.instance = LuganoVizClusterGazebo()

    def test_start(self):
        self.instance._allocate_job = Mock()
        self.instance._start_fake_X = Mock()
        self.instance._start_xvnc = Mock()
        self.instance._start_gazebo = Mock()

        self.instance.start('random_master_uri')
        self.assertEqual(self.instance._allocate_job.call_count, 1)
        self.assertEqual(self.instance._start_fake_X.call_count, 1)
        self.assertEqual(self.instance._start_xvnc.call_count, 1)
        self.assertEqual(self.instance._start_gazebo.call_count, 1)
        self.instance = LuganoVizClusterGazebo()

    @patch('pexpect.spawn')
    def test_stop(self, mock_spawn):
        self.instance._clean_remote_files = Mock()
        self.instance._deallocate_job = Mock()

        self.instance._remote_xvnc_process = Mock()
        self.instance._gazebo_remote_process = Mock()
        self.instance._x_server_process = Mock()

        self.instance._allocation_process = mock_spawn()
        mock_spawn().sendline = Mock()

        self.instance.stop()
        self.assertEqual(self.instance._clean_remote_files.call_count, 1)
        self.assertEqual(self.instance._deallocate_job.call_count, 1)

        self.instance = LuganoVizClusterGazebo()

    def test_restart(self):
        with patch("hbp_nrp_cleserver.server.LuganoVizClusterGazebo.LuganoVizClusterGazebo.start"):
            with patch("hbp_nrp_cleserver.server.LuganoVizClusterGazebo.LuganoVizClusterGazebo.stop"):
                self.instance.restart('')
                self.assertEqual(self.instance.start.call_count, 1)
                self.assertEqual(self.instance.stop.call_count, 1)

if __name__ == '__main__':
    unittest.main()
