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

""" Token Info class. """

from error import DataError
from pouch import _Pouch

__author__ = "Maciej Machulak"
__maintainer__ = "Maciej Machulak"
__email__ = "mmachulak@google.com"

__copyright__ = "Copyright 2012, Google Inc."
__license__ = "Apache License 2.0"
__version__ = "0.1"
__status__ = "Prototype"


class TokenInfo(_Pouch):
    """ Represents the OpenID Connect Token Info object."""

    def __init__(self, token_dict):
        if isinstance(token_dict, dict):
            super(TokenInfo, self).__init__()
            self.issued_to = token_dict.get('issued_to', None)
            self.scope = token_dict.get('scope', None)
            self.audience = token_dict.get('audience', None)
            self.user_id = token_dict.get('user_id', None)
            self.expires_in = token_dict.get('expires_in', None)
            self.email = token_dict.get('email', None)
            self.verified_email = token_dict.get('verified_email', None)
        else:
            raise DataError('could not parse token info response')

    def __repr__(self):
        user_info = ''
        user_info += 'issued_to: ' + (self.issued_to or '')
        user_info += '\nscope: ' + (self.scope or '')
        user_info += '\naudience: ' + (self.audience or '')
        user_info += '\nuser_id: ' + (self.user_id or '')
        user_info += '\nexpires_in: ' + (str(self.expires_in) or '')
        user_info += '\nemail: ' + (str(self.email) or '')
        user_info += '\nverified_email: ' + (str(self.verified_email) or '')
        return user_info
