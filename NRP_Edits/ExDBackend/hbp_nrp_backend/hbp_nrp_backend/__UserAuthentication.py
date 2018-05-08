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
This module contains a helper class for the REST services to identify and check the user
calling the service.
"""

__author__ = 'Oliver Denninger'

from flask_restful import reqparse
import logging

logger = logging.getLogger("__main__")


class UserAuthentication(object):
    """
    Helper class to get the user, authenticated at the HBP Unified Portal, from a HTTP request.
    This is done by reading the value of the 'X-User-Name' header. If this header is not present,
    the user name 'default-owner' ist used to allow testing outside the portal, etc.
    """

    HTTP_HEADER_USER_NAME = "X-User-Name"
    HEADER_TOKEN = "Authorization"

    @staticmethod
    def get_header(request, header_name, default_value):
        """
        Gets the value of the headername header from the given HTTP request
        :param request: The request
        :param header_name: The name of the header
        :param default_value: If nothing is found, this will be returned
        :return: The value of the headername header or if not found default_value
        """
        request_parser = reqparse.RequestParser()
        request_parser.add_argument(header_name,
                                    type=str, location='headers')
        header_value = request_parser.parse_args(request)[header_name]
        if header_value is None:
            header_value = default_value

        return header_value

    @staticmethod
    def get_x_user_name_header(request):
        """
        Gets the value of the 'X-User-Name' header from the given HTTP request
        :param request: The request
        :return: The value of the 'X-User-Name' header or if not found 'default-owner'
        """
        return UserAuthentication.get_header(request,
                                               UserAuthentication.HTTP_HEADER_USER_NAME,
                                               "default-owner")

    @staticmethod
    def get_header_token(request):
        """
        Gets the value of the 'Authorization' header from the given HTTP request
        :param request: The request
        :return: The value of the 'Authorization' header or if not found 'no-token'
        """
        token_field = UserAuthentication.get_header(request,
                                                      UserAuthentication.HEADER_TOKEN,
                                                      "no_token")
        if (token_field != "no_token"):
            return token_field.split()[1]
        else:
            return token_field

    @staticmethod
    def matches_x_user_name_header(request, user):
        """
        Checks if the value of the 'X-User-Name' header from the given HTTP request matches
        the given user name
        :param request: The request
        :param user: The user name to check
        :return: True if value of the 'X-User-Name' header and user name match, False otherwise
        """
        request_user = UserAuthentication.get_x_user_name_header(request)
        if user == request_user:
            return True
        else:
            logger.warn("Request from user '" + request_user + "' but simulation owned by '"
                        + user + "'")
            return False
