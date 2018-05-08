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
from hbp_nrp_commons.cluster.LuganoVizCluster import LuganoVizCluster

import unittest
from mock import patch, Mock, MagicMock
import os

__author__ = 'Alessandro Ambrosano'


class TestLuganoVizCluster(unittest.TestCase):

    def setUp(self):
        self.instance = LuganoVizCluster(processes=4, gpus=1)

    @patch('pexpect.spawn')
    def test_spawn_ssh(self, mock_spawn):
        mock_spawn().sendline = Mock()

        # Successful call
        mock_spawn().expect = Mock(return_value=0)
        mock_spawn.call_count = 0
        self.instance._spawn_ssh('foo')
        self.assertEqual(mock_spawn.call_count, 1)
        self.assertNotEqual(mock_spawn().sendline, 0)

        # Missing password
        mock_spawn().expect = Mock(return_value=1)
        self.assertRaises(Exception, self.instance._spawn_ssh, 'foo')

        # Timeout
        mock_spawn().expect = Mock(return_value=2)
        self.assertRaises(Exception, self.instance._spawn_ssh, 'foo')

    def test_spawn_ssh_slurm_frontend(self):
        with patch.object(self.instance, '_spawn_ssh', Mock()) as mock_spawn:
            self.instance._spawn_ssh_SLURM_frontend()
            mock_spawn.assert_called_with('bbpviz1')

    def test_spawn_ssh_node(self):
        self.instance._node = 'fake_node'
        with patch.object(self.instance, '_spawn_ssh', Mock()) as mock_spawn:
            self.instance._spawn_ssh_node()
            mock_spawn.assert_called_with('fake_node')

    @patch('pexpect.spawn')
    def test_allocate_job(self, mock_spawn):
        self.instance._spawn_ssh_SLURM_frontend = mock_spawn
        mock_spawn().sendline = Mock()

        # Successful call
        mock_spawn().expect = Mock(return_value=1)
        mock_spawn().after = 'JobState=RUNNING'
        mock_spawn.call_count = 0
        self.instance._allocate_job(False)
        self.assertEqual(mock_spawn.call_count, 1)
        self.assertNotEqual(mock_spawn().sendline.call_count, 0)

        # Job not running
        mock_spawn().expect = Mock(return_value=1)
        mock_spawn().after = 'JobState=WRONG'
        self.assertRaises(Exception, self.instance._allocate_job)

        # Kerberos authentication missing
        mock_spawn().expect = Mock(return_value=2)
        self.assertRaises(Exception, self.instance._allocate_job)

        # General error
        mock_spawn().expect = Mock(return_value=3)
        self.assertRaises(Exception, self.instance._allocate_job)

        self.instance = LuganoVizCluster(processes=4, gpus=1)

    @patch('pexpect.spawn')
    def test_deallocate_job(self, mock_spawn):
        self.instance._allocation_process = mock_spawn()
        mock_spawn().sendline = Mock()

        self.instance._deallocate_job()
        self.assertTrue(True in ['exit' in x for x in [str(y) for y in mock_spawn().sendline.mock_calls]])
        self.assertEqual('UNDEFINED', self.instance._state)
        self.assertIsNone(self.instance._allocation_process)

        self.instance = LuganoVizCluster(processes=4, gpus=1)

    @patch('pexpect.spawn')
    def test_clean_remote_files(self, mock_spawn):
        self.instance._spawn_ssh_node = mock_spawn
        mock_spawn().sendline = Mock()

        # successful call
        self.instance._node = 'something that won\'t be used'
        self.instance._tmp_dir = 'foo'
        self.instance._allocation_process = mock_spawn()

        mock_spawn.call_count = 0
        self.instance._clean_remote_files()
        self.assertEqual(mock_spawn.call_count, 1)
        self.assertNotEqual(mock_spawn().sendline.call_count, 0)

        self.instance = LuganoVizCluster(processes=4, gpus=1)

    @patch('subprocess.call')
    @patch('pexpect.spawn')
    def test_models_path(self, mock_spawn, mock_system):
        mock_system.return_value = 0
        self.instance = LuganoVizCluster(processes=4, gpus=1)
        self.instance._node = 'not none'
        self.instance._allocation_process = 'this neither'

        mock_spawn().expect.return_value = 0
        mock_spawn().readline.return_value = '/somewhere/under/the/rainbow'
        mock_spawn.call_count = 0

        self.instance._copy_to_remote('/somewhere/over/the/rainbow')
        self.assertEqual(mock_spawn.call_count, 1)
        self.assertNotEqual(mock_spawn().sendline.call_count, 0)
        self.assertNotEqual(mock_spawn().expect.call_count, 0)
        self.assertEqual(mock_spawn().readline.call_count, 2)

        mock_system.assert_any_call('scp -r /somewhere/over/the/rainbow bbpnrsoa@not none.cscs.ch:/somewhere/under/the/rainbow'.split())

        # check error cases
        with self.assertRaises(Exception):
            mock_system.return_value = 9
            self.instance._copy_to_remote('/somewhere/over/the/rainbow')

        with self.assertRaises(Exception):
            mock_system.return_value = 10
            self.instance._copy_to_remote('/somewhere/over/the/rainbow')

        with self.assertRaises(Exception):
            mock_system.return_value = 65
            self.instance._copy_to_remote('/somewhere/over/the/rainbow')

        with self.assertRaises(Exception):
            mock_system.return_value = 66
            self.instance._copy_to_remote('/somewhere/over/the/rainbow')

        with self.assertRaises(Exception):
            mock_system.return_value = 42
            self.instance._copy_to_remote('/somewhere/over/the/rainbow')

        self.instance = LuganoVizCluster(processes=4, gpus=1)

    @patch('hbp_nrp_commons.cluster.LuganoVizCluster.os.environ')
    def test_configure_environment(self, mock_os_environ):

        nrp_variables_path = os.path.join(os.path.dirname(__file__), 'nrp-variables')
        mock_os_environ.get = Mock(side_effect=['staging', nrp_variables_path])

        mock_process = Mock()
        mock_process.sendline = Mock()

        self.instance._configure_environment(mock_process) 
        self.assertEqual(mock_os_environ.get.call_count, 2)
        mock_process.sendline.assert_any_call('export ENVIRONMENT=staging')
        mock_process.sendline.assert_any_call('ADDITIONAL_PACKAGE_VERSION=1.1.0')
        mock_process.sendline.assert_any_call('SMALL_PACKAGE_VERSION=2.5.5')
        self.assertEqual(mock_process.sendline.call_count, 3)
        self.assertNotEqual(mock_process.expect, 0)

        self.instance = LuganoVizCluster(processes=4, gpus=1)

    @patch('pexpect.spawn')
    def test_stop(self, mock_spawn):
        self.instance._clean_remote_files = Mock()
        self.instance._deallocate_job = Mock()

        self.instance._allocation_process = mock_spawn()
        mock_spawn().sendline = Mock()

        self.instance.stop()
        self.assertEqual(self.instance._clean_remote_files.call_count, 1)
        self.assertEqual(self.instance._deallocate_job.call_count, 1)

        self.instance = LuganoVizCluster(processes=4, gpus=1)

    @patch('pexpect.spawn')
    def test_stop_except(self, mock_spawn):
        self.instance._clean_remote_files = Mock()
        self.instance._clean_remote_files.side_effect = Exception('foo')
        self.instance._deallocate_job = Mock()

        self.instance._allocation_process = mock_spawn()
        mock_spawn().sendline = Mock()

        self.instance.stop()
        self.assertEqual(self.instance._clean_remote_files.call_count, 1)
        self.assertEqual(self.instance._deallocate_job.call_count, 1)

        self.instance = LuganoVizCluster(processes=4, gpus=1)

if __name__ == '__main__':
    unittest.main()
