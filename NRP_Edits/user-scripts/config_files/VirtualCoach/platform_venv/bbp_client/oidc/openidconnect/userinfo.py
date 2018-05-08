#!/usr/bin/env python

# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" User Info class """

from error import DataError
from pouch import _Pouch

__author__ = "Maciej Machulak"
__maintainer__ = "Maciej Machulak"
__email__ = "mmachulak@google.com"

__copyright__ = "Copyright 2012 Google Inc. All Rights Reserved."
__license__ = "Apache License 2.0"
__version__ = "0.1"
__status__ = "Prototype"


class Address(_Pouch):
    """ Represents the address returned by OpenID Connect """

    def __init__(self, address_dict):
        if isinstance(address_dict, dict):
            super(Address, self).__init__()
            self.formatted = address_dict.get('formatted', None)
            self.street_address = address_dict.get('street_address', None)
            self.locality = address_dict.get('locality', None)
            self.postal_code = address_dict.get('postal_code', None)
            self.region = address_dict.get('region', None)
            self.country = address_dict.get('country', None)
        else:
            raise DataError

    def __repr__(self):
        address = ''
        address += 'formatted: ' + (self.formatted or '')
        address += '\nstreet_address: ' + (self.street_address or '')
        address += '\nlocality: ' + (self.locality or '')
        address += '\npostal code: ' + (self.postal_code or '')
        address += '\nregion: ' + (self.region or '')
        address += '\ncountry: ' + (self.country or '')
        return address

    def __str__(self):
        return self.__repr__()


class UserInfo(_Pouch):
    """ Represents the OpenID Connect User Info object. """

    def __init__(self, user_dict):
        if isinstance(user_dict, dict):
            super(UserInfo, self).__init__()
            self.sub = user_dict.get('sub', None)
            self.name = user_dict.get('name', None)
            self.given_name = user_dict.get('given_name', None)
            self.middle_name = user_dict.get('middle_name', None)
            self.family_name = user_dict.get('family_name', None)
            self.preferred_username = user_dict.get('preferred_username', None)
            self.email = user_dict.get('email', None)
            self.email_verified = user_dict.get('email_verified', None)
            self.profile = user_dict.get('profile', None)
            self.picture = user_dict.get('picture', None)
            self.website = user_dict.get('website', None)
            self.gender = user_dict.get('gender', None)
            self.birthday = user_dict.get('birthday', None)
            self.zoneinfo = user_dict.get('zoneinfo', None)
            self.locale = user_dict.get('locale', None)
            self.phone_number = user_dict.get('phone_number', None)
            self.updated_at = user_dict.get('updated_at', None)
            self.address = None
            address = user_dict.get('address', None)
            if address and isinstance(address, dict):
                self.address = Address(address)
            groups = user_dict.get('groups', None)
            if groups and isinstance(groups, basestring):
                self.groups = groups.split(',')
            else:
                self.groups = groups
        else:
            raise DataError

    def __repr__(self):
        user_info = ''
        user_info += 'sub: ' + (self.sub or '')
        user_info += '\nname: ' + (self.name or '')
        user_info += '\ngiven_name: ' + (self.given_name or '')
        user_info += '\nmiddle_name: ' + (self.middle_name or '')
        user_info += '\nfamily_name: ' + (self.family_name or '')
        user_info += '\npreferred_username: ' + (self.preferred_username or '')
        user_info += '\nemail: ' + (self.email or '')
        user_info += '\nemail_verified: ' + (str(self.email_verified) or '')
        user_info += '\nprofile: ' + (self.profile or '')
        user_info += '\npicture: ' + (self.picture or '')
        user_info += '\nwebsite: ' + (self.website or '')
        user_info += '\ngender: ' + (self.gender or '')
        user_info += '\nbirthday: ' + (self.birthday or '')
        user_info += '\nzoneinfo: ' + (self.zoneinfo or '')
        user_info += '\nlocale: ' + (self.locale or '')
        user_info += '\nphone_number: ' + (self.phone_number or '')
        user_info += '\nupdated_at: ' + (str(self.updated_at) or '')
        user_info += '\naddress: ' + (self.address or '')
        user_info += '\ngroups: ' + (str(self.groups) or '')
        return user_info

    def __str__(self):
        return self.__repr__()
