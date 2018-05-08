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
from RestrictedPython import compile_restricted
from hbp_nrp_cleserver.server.ROSCLEServer import extract_line_number
from unittest import TestCase
import sys

__author__ = "Georg Hinkel"

class TestErrorLineExtraction(TestCase):

    ret_none = lambda: None

    def test_line_number_of_type_error(self):
        code = "# Here are some comments\n" \
               "def test():\n" \
               "    foo = None\n" \
               "    # the next line will crash\n" \
               "    foo.bar\n"
        line_no = self.__get_line_number_of_error(code)
        self.assertEqual(5, line_no)

    def __get_line_number_of_error(self, code):
        test = TestErrorLineExtraction.ret_none
        restricted = compile_restricted(code, '<string>', 'exec')
        exec restricted
        try:
            return test()
        except Exception:
            tb = sys.exc_info()[2]
            return extract_line_number(tb)