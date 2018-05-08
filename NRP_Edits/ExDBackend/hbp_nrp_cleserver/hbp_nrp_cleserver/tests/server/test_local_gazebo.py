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
from hbp_nrp_cleserver.server.LocalGazebo import LocalGazeboServerInstance, LocalGazeboBridgeInstance
from hbp_nrp_cle import config
import unittest
from mock import patch, MagicMock

__author__ = 'Alessandro Ambrosano, Georg Hinkel'


class TestLocalGazeboServerInstance(unittest.TestCase):

    def setUp(self):
        self.instance = LocalGazeboServerInstance()
        self.has_died = False
        self.die_error = None

    def died_callback(self):
        self.has_died = True

    @patch('hbp_nrp_cleserver.server.LocalGazebo.os')
    @patch('hbp_nrp_cleserver.server.LocalGazebo.Watchdog')
    def test_start(self, mocked_watchdog, mocked_os):
        self.instance.start('')
        mocked_os.system.assert_any_call(config.config.get('gazebo', 'restart-cmd'))
        self.assertTrue(mocked_watchdog.called)
        self.assertTrue(mocked_watchdog().start.called)

    @patch('hbp_nrp_cleserver.server.LocalGazebo.os')
    @patch('hbp_nrp_cleserver.server.LocalGazebo.Watchdog')
    def test_start_models(self, mocked_watchdog, mocked_os):
        self.instance.start('', '/somewhere/over/the/rainbow')
        print(mocked_os.system.call_args_list)
        mocked_os.system.assert_any_call('export GAZEBO_MODELS_PATH=/somewhere/over/the/rainbow:'
                                         '$GAZEBO_MODELS_PATH && ' +
                                         config.config.get('gazebo', 'restart-cmd'))
        self.assertTrue(mocked_watchdog.called)
        self.assertTrue(mocked_watchdog().start.called)

    @patch('hbp_nrp_cleserver.server.LocalGazebo.os')
    @patch('hbp_nrp_cleserver.server.LocalGazebo.Watchdog')
    def test_start_gzserver_args(self, mocked_watchdog, mocked_os):
        self.instance.start('', None, '--seed 123456')
        print(mocked_os.system.call_args_list)
        mocked_os.system.assert_any_call('export GZSERVER_ARGS="--seed 123456" && ' +
                                         config.config.get('gazebo', 'restart-cmd'))
        self.assertTrue(mocked_watchdog.called)
        self.assertTrue(mocked_watchdog().start.called)

    @patch('hbp_nrp_cleserver.server.LocalGazebo.os')
    @patch('hbp_nrp_cleserver.server.LocalGazebo.Watchdog')
    def test_stop(self, mocked_watchdog, mocked_os):
        self.instance.start('')
        self.instance.stop()
        mocked_os.system.assert_any_call(config.config.get('gazebo', 'stop-cmd'))
        self.assertTrue(mocked_watchdog().stop.called)

    @patch('hbp_nrp_cleserver.server.LocalGazebo.os')
    @patch('hbp_nrp_cleserver.server.LocalGazebo.Watchdog')
    def test_restart(self, mocked_watchdog, mocked_os):
        self.instance.restart('')
        mocked_os.system.assert_any_call(config.config.get('gazebo', 'restart-cmd'))
        self.assertTrue(mocked_watchdog.called)
        self.assertTrue(mocked_watchdog().start.called)

    @patch('hbp_nrp_cleserver.server.LocalGazebo.os')
    def test_gazebo_master_uri(self, mocked_os):
        mocked_os.environ.get = MagicMock(return_value=None)
        self.assertIsInstance(self.instance.gazebo_master_uri, str)
        self.assertNotEqual(self.instance.gazebo_master_uri, "")
        mock_gazebo_master_uri = "http://localhost:12345"
        mocked_os.environ.get = MagicMock(return_value=mock_gazebo_master_uri)
        self.assertIsInstance(self.instance.gazebo_master_uri, str)
        self.assertEquals(self.instance.gazebo_master_uri, mock_gazebo_master_uri)

    @patch('hbp_nrp_cleserver.server.LocalGazebo.os')
    @patch('hbp_nrp_cleserver.server.LocalGazebo.Watchdog')
    def test_raises_callback(self, mocked_watchdog, mocked_os):
        self.instance.start('')
        self.instance.gazebo_died_callback = self.died_callback
        callback = mocked_watchdog.call_args[0][1]
        callback()
        self.assertTrue(self.has_died)

    def test_can_extend(self):
        self.assertTrue(self.instance.try_extend("does not matter"))


class TestLocalGazeboBridgeInstance(unittest.TestCase):
    @patch('hbp_nrp_cleserver.server.LocalGazebo.os')
    @patch('hbp_nrp_cleserver.server.LocalGazebo.config')
    def test_start_performs_command(self, mocked_config, mocked_os):
        mocked_config.config.get.return_value = "foo"
        bridge = LocalGazeboBridgeInstance()
        bridge.start()
        mocked_os.system.assert_called_once_with("foo")
        mocked_config.config.get.assert_called_once_with('gzbridge', 'start-cmd')

    @patch('hbp_nrp_cleserver.server.LocalGazebo.os')
    @patch('hbp_nrp_cleserver.server.LocalGazebo.config')
    def test_stop_performs_command(self, mocked_config, mocked_os):
        mocked_config.config.get.return_value = "bar"
        bridge = LocalGazeboBridgeInstance()
        bridge.stop()
        mocked_os.system.assert_called_once_with("bar")
        mocked_config.config.get.assert_called_once_with('gzbridge', 'stop-cmd')


    @patch('hbp_nrp_cleserver.server.LocalGazebo.os')
    @patch('hbp_nrp_cleserver.server.LocalGazebo.config')
    def test_restart_performs_command(self, mocked_config, mocked_os):
        mocked_config.config.get.return_value = "foobar"
        bridge = LocalGazeboBridgeInstance()
        bridge.restart()
        mocked_os.system.assert_called_once_with("foobar")
        mocked_config.config.get.assert_called_once_with('gzbridge', 'restart-cmd')


if __name__ == '__main__':
    unittest.main()
