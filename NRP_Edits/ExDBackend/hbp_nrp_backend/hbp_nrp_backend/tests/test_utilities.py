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
This class tests the common tools of the main module.
"""
__author__ = 'LucGuyot'

from hbp_nrp_backend import get_date_and_time_string
import unittest


class TestUtilities(unittest.TestCase):

    def test_get_date_and_time_string(self):
        # Create a string that can be used to generate a file or a folder name
        # e.g., 2016-03-10_12-11-36, used in csv-recorders-2016-03-10_12-11-36
        time = get_date_and_time_string()
        # Some special characters should not be used in file or folder names
        self.assertNotIn(' ', time)
        self.assertNotIn('/', time)
        self.assertNotIn('\"', time)
        self.assertNotIn('\'', time)
        # The later the file or the folder is created, the lower it appears in a sorted list
        later_time = get_date_and_time_string()
        time_list = [time, later_time]
        time_list.sort()
        self.assertEqual(time_list[0], time)


if __name__ == '__main__':
    unittest.main()
