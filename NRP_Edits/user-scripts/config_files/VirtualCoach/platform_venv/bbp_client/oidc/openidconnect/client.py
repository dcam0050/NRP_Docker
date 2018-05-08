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

""" OpenID Connect Client """

import logging
import urllib
import urlparse
import datetime

from error import FlowUserInfoError
from error import FlowTokenInfoError
from tokeninfo import TokenInfo
from userinfo import UserInfo

import httplib2
from bbp_client.oidc.oauth2client.client import OAuth2WebServerFlow, OAuth2Credentials, FlowExchangeError
from bbp_client.oidc.oauth2client.client import flow_from_clientsecrets
from bbp_client.oidc.oauth2client.client import _extract_id_token

try: # pragma: no cover
  import simplejson
except ImportError: # pragma: no cover
  try:
    # Try to import from django, should work on App Engine
    from django.utils import simplejson
  except ImportError:
    # Should work for Python2.6 and higher.
    import json as simplejson

try:
      from urlparse import parse_qsl
except ImportError:
      from cgi import parse_qsl

__author__ = "Maciej Machulak"
__maintainer__ = "Maciej Machulak"
__email__ = "mmachulak@google.com"

__copyright__ = "Copyright 2012 Google Inc. All Rights Reserved."
__license__ = "Apache License 2.0"
__version__ = "0.1"
__status__ = "Prototype"


GOOGLE_OPENIDCONNECT_SCOPE = "https://www.googleapis.com/auth/userinfo.profile"
GOOGLE_TOKENINFO_URI = "https://www.googleapis.com/oauth2/v1/tokeninfo"
GOOGLE_USERINFO_URI = "https://www.googleapis.com/oauth2/v1/userinfo"


def openidconnect_flow_from_clientsecrets(filename, scope = GOOGLE_OPENIDCONNECT_SCOPE, message=None):
  """Create OpenID Connect Flow from a clientsecrets file.

  Will create the right kind of Flow based on the contents of the clientsecrets
  file or will raise InvalidClientSecretsError for unknown types of Flows.

  Args:
    filename: string, File name of client secrets.
    scope: string or list of strings, scope(s) to request.
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. If message is provided then
      sys.exit will be called in the case of an error. If message in not
      provided then clientsecrets.InvalidClientSecretsError will be raised.

  Returns:
    A Flow object.

  Raises:
    UnknownClientSecretsFlowError if the file describes an unknown kind of Flow.
    clientsecrets.InvalidClientSecretsError if the clientsecrets file is
      invalid.
  """

  # Check if submitted scope contains the Ope
  oauth_flow = flow_from_clientsecrets(filename,scope,message)
  return OpenIDConnectFlow(client_id = oauth_flow.client_id,
      client_secret = oauth_flow.client_secret,
      scope = oauth_flow.scope,
      user_agent = oauth_flow.user_agent,
      auth_uri = oauth_flow.auth_uri,
      token_uri = oauth_flow.token_uri)


class VerifiedTokenCredentials(OAuth2Credentials):
    """Credentials verified with the TokenInfo endpoint."""

    def __init__(self, oauth_credentials, tokeninfo):
        OAuth2Credentials.__init__(self,
            oauth_credentials.access_token,
            oauth_credentials.client_id,
            oauth_credentials.client_secret,
            oauth_credentials.refresh_token,
            oauth_credentials.token_expiry,
            oauth_credentials.token_uri,
            oauth_credentials.user_agent,
            oauth_credentials.id_token)

        self.tokeninfo = tokeninfo

class OpenIDConnectCredentials(VerifiedTokenCredentials):
    """OpenID Connect Credentials received from the UserInfo endpoint."""

    def __init__(self, verified_token_credentials, userinfo):
        VerifiedTokenCredentials.__init__(self,
            verified_token_credentials,
            verified_token_credentials.tokeninfo)

        self.userinfo = userinfo


class OpenIDConnectFlow(OAuth2WebServerFlow):
    """Does the OpenID Connect flow."""

    def __init__(self,
                 scope=GOOGLE_OPENIDCONNECT_SCOPE,
                 tokeninfo_uri=GOOGLE_TOKENINFO_URI,
                 userinfo_uri=GOOGLE_USERINFO_URI,
                 **kwargs):
        """Constructor for OpenIDConnectFlow.

        Args:
          tokeninfo_uri: string, URI for TokenInfo endpoint. For convenience
            defaults to Google's endpoints but any OAuth 2.0 provider can be
            used.
          userinfo_uri: string, URI for UserInfo endpoint. For convenience
            defaults to Google's endpoints but any OAuth 2.0 provider can be
            used.
          **kwargs: dict, The keyword arguments require the following parameters
                          - client_id: string, client identifier.
                          - client_secret: string client secret.
                          - scope: string or list of strings, scope(s) of the
                          credentials being requested.
                          - user_agent: string, HTTP User-Agent to provide for
                          this application.
                          - auth_uri: string, URI for authorization endpoint.
                          For convenience defaults to Google's endpoints but
                          any OAuth 2.0 provider can be used.
                          - token_uri: string, URI for token endpoint. For
                          conveniencedefaults to Google's endpoints but
                          any OAuth 2.0 provider can be used
                          - any other optional parameters for OAuth 2.0
        """

        super(OpenIDConnectFlow, self).__init__(scope = scope, **kwargs)

        self.tokeninfo_uri = tokeninfo_uri
        self.userinfo_uri = userinfo_uri

    def step3_verify_access_token(self, credentials, http=None, verify_id=True):
        """Verifies access token at the TokenInfo endpoint.

        Args:
            credentials

        Returns:
            VerifiedTokenCredentials

        Raises:
            FlowTokenInfoError
        """

        if http is None:
            http = httplib2.Http()

        resp, content = http.request(self.tokeninfo_uri,
            method="POST",
            body=urllib.urlencode({'access_token': credentials.access_token}),
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if resp.status == 200:
            # Process the response
            d = simplejson.loads(content)
            if 'valid' in d and not d['valid']:
                raise FlowTokenInfoError('invalid token')

            tokeninfo = TokenInfo(d)
            logging.debug('Successfully retrieved token info: %s' % tokeninfo)
            verified_token_credentials = VerifiedTokenCredentials(credentials, tokeninfo)

            if verify_id:
                # Perform checks on the token info
                if verified_token_credentials.tokeninfo.audience != credentials.client_id:
                    logging.error('token issued for a different client - issued to %s, '
                                  'expected %s.' %
                                  (verified_token_credentials.tokeninfo.audience,
                                   credentials.client_id))
                    raise FlowTokenInfoError('invalid token')

            if int(verified_token_credentials.tokeninfo.expires_in) < 1:
                logging.error('token expired')
                raise FlowTokenInfoError('token expired')

            return verified_token_credentials
        else:
            logging.error('Failed to retrieve token info: %s' % content)
            error_msg = 'Invalid token info response %s.' % resp['status']
            try:
                data = simplejson.loads(content)
                if 'error' in data:
                    error_msg = data['error']
            except Exception:
                pass

            raise FlowTokenInfoError(error_msg)

    def step4_userinfo(self, credentials, http=None):
        """Obtains UserInfo from the UserInfo endpoint.

        Args:
            credentials

        Returns:
            OpenIDConnectCredentials

        Raises:
            FlowUserInfoError
        """

        if http is None:
            http = httplib2.Http()

        http = credentials.authorize(http)
        resp, content = http.request(self.userinfo_uri)

        if resp.status == 200:
            d = simplejson.loads(content)
            userinfo = UserInfo(d)
            logging.debug('Successfully retrieved user info: %s' % userinfo)
            return OpenIDConnectCredentials(credentials, userinfo)
        else:
            logging.error('Failed to retrieve user info: %s' % content)
            error_msg = 'Invalid user info response %s.' % resp['status']
            try:
                data = simplejson.loads(content)
                if 'error' in data:
                    error_msg = data['error']
            except Exception:
                pass

            raise FlowUserInfoError(error_msg)

    def step234_exchange_and_tokeninfo_and_userinfo(self, code, http=None):
        """Exchanges authorization for token, then validates the token and
        obtains UserInfo.

        Args:
            code

        Returns:
            OpenIDConnectCredentials

        Raises:
            FlowUserInfoError
        """

        if http is None:
            http = httplib2.Http()

        logging.debug('exchanging code for access token')
        credentials = self.step2_exchange(code, http)
        logging.debug('verifing access token received from the IDP')
        credentials = self.step3_verify_access_token(credentials, http)
        logging.debug('using access token to access user info from the IDP')
        return self.step4_userinfo(credentials, http)

    def step1_get_authorize_implicit_url(self, redirect_uri, http=None):
        if http is None:
            http = httplib2.Http()

        self.redirect_uri = redirect_uri
        query = {
                'response_type': 'token',
                'client_id': self.client_id,
                'redirect_uri': redirect_uri,
                'prompt': 'consent',
                }
        if self.scope:
            query['scope'] = self.scope

        parts = list(urlparse.urlparse(self.auth_uri))
        query.update(dict(parse_qsl(parts[4]))) # 4 is the index of the query part
        parts[4] = urllib.urlencode(query)
        return urlparse.urlunparse(parts)

    def step2_get_credentials_from_url_fragment(self, url_post_auth):
        o = urlparse.urlparse(url_post_auth)
        frag = urlparse.parse_qs(o.fragment)

        return OAuth2Credentials(frag['access_token'][0], self.client_id,
                                 self.client_secret, None, frag['expires_in'][0],
                                 self.token_uri, self.user_agent,
                                 id_token=_extract_id_token( frag['id_token'][0]))

    def step12_get_token_from_client_credentials(self, http=None):

        body = urllib.urlencode({
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'response_type': 'token',
            'scope': self.scope,
            })
        headers = {
            'content-type': 'application/x-www-form-urlencoded',
        }

        if self.user_agent is not None:
          headers['user-agent'] = self.user_agent

        if http is None:
          http = httplib2.Http()

        resp, content = http.request(self.token_uri, method='POST', body=body, headers=headers)

        if resp.status == 200:
          # TODO(jcgregorio) Raise an error if simplejson.loads fails?
          d = simplejson.loads(content)
          access_token = d['access_token']
          refresh_token = d.get('refresh_token', None)
          token_expiry = None
          if 'expires_in' in d:
            token_expiry = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=int(d['expires_in']))

          if 'id_token' in d:
            d['id_token'] = _extract_id_token(d['id_token'])

          return OAuth2Credentials(access_token, self.client_id,
                                   self.client_secret, refresh_token, token_expiry,
                                   self.token_uri, self.user_agent,
                                   id_token=d.get('id_token', None))
        else:
          logging.error('Failed to retrieve access token: %s' % content)
          error_msg = 'Invalid response %s.' % resp['status']
          try:
            d = simplejson.loads(content)
            if 'error' in d:
              error_msg = d['error']
          except:
            pass

          raise FlowExchangeError(error_msg)
