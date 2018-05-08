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
Tests for RestSyncMiddleware.py
"""

import unittest
from mock import patch, MagicMock
from hbp_nrp_backend.rest_server.RestSyncMiddleware import RestSyncMiddleware


class TestRestSyncMiddleWare(unittest.TestCase):

    def create_mocks(self, test_method_result=""):
        self.env_list = ["path_info", "test_method"]
        self.mock_wsgi = MagicMock()
        self.mock_app = MagicMock()
        viewfunction ="viewfunction"
        self.mock_map_adapter = MagicMock()
        self.mock_map_adapter.match = MagicMock(return_value=(viewfunction,None))
        self.mock_app.url_map.bind = MagicMock(return_value=self.mock_map_adapter)

        mock_view = MagicMock()
        x = MagicMock()
        x.test_method = test_method_result
        mock_view.view_class = x
        self.mock_app.view_functions = {viewfunction: mock_view}


        self.mock_env = MagicMock()
        self.mock_env.get = MagicMock(side_effect=self.env_list)
        self.mock_response = MagicMock()

    def test_threadsafe_decorator(self):
        rest = RestSyncMiddleware(MagicMock(), MagicMock())
        new_func = rest.threadsafe(MagicMock())

        self.assertTrue(new_func.is_threadsafe)

    @patch('hbp_nrp_backend.rest_server.RestSyncMiddleware.Lock')
    def test_call_works_correctly(self, patch_lock):
        self.create_mocks()
        # call the class
        rest = RestSyncMiddleware(self.mock_wsgi, self.mock_app)
        rest(self.mock_env, self.mock_response)

        self.mock_app.url_map.bind.assert_called_with('localhost', default_method=self.env_list[1])
        self.mock_map_adapter.match.assert_called_with(self.env_list[0])
        self.assertTrue(rest.threadLock.acquire.called)
        self.mock_wsgi.assert_called_with(self.mock_env, self.mock_response)
        self.assertTrue(rest.threadLock.release.called)

    @patch('hbp_nrp_backend.rest_server.RestSyncMiddleware.Lock')
    def test_call_is_threadsafe(self, patch_lock):
        mock_function = MagicMock()
        mock_function.is_threadsafe = True
        self.create_mocks(mock_function)
        # call the class
        rest = RestSyncMiddleware(self.mock_wsgi, self.mock_app)
        rest(self.mock_env, self.mock_response)

        self.mock_app.url_map.bind.assert_called_with('localhost', default_method=self.env_list[1])
        self.mock_map_adapter.match.assert_called_with(self.env_list[0])
        self.assertFalse(rest.threadLock.acquire.called)
        self.mock_wsgi.assert_called_with(self.mock_env, self.mock_response)
        self.assertFalse(rest.threadLock.release.called)


    @patch('hbp_nrp_backend.rest_server.RestSyncMiddleware.Lock')
    def test_call_works_with_exception(self, patch_lock):
        mock_wsgi = MagicMock(side_effect=KeyError)
        self.create_mocks()
        # call the class
        rest = RestSyncMiddleware(mock_wsgi, self.mock_app)
        rest(self.mock_env, self.mock_response)

        self.mock_app.url_map.bind.assert_called_with('localhost', default_method=self.env_list[1])
        self.mock_map_adapter.match.assert_called_with(self.env_list[0])
        self.assertTrue(rest.threadLock.acquire.called)
        mock_wsgi.assert_called_with(self.mock_env, self.mock_response)
        self.assertTrue(rest.threadLock.release.called)


if __name__ == '__main__':
    unittest.main()
