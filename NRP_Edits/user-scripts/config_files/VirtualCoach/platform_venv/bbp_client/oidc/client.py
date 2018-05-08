'''client for handling OAUTH authentication for python clients

Generally, this is used to create an oidc client object, used for other services

To create a client, use one of the static methods:
    implicit_auth(user=None, password=None, oauth_url=None, use_cache=True)
    bearer_auth(oauth_url, token)
    secret_auth(oauth_url, oidcconfig=None)
    file_auth(yaml_path, oauth_url=None)

Read their docstrings for further information
'''

import urllib
import httplib2
import logging
import os
import pickle
import stat
import json

from urlparse import urlparse, urljoin
from os.path import join as joinp

from bbp_services.client import get_services
from bbp_client.oidc.openidconnect.client import OpenIDConnectFlow
from bbp_client.oidc.oauth2client.client import OAuth2Credentials
from urllib2 import HTTPError


DEFAULT_OIDC_CONFIG = {
    'client_id': 'kamaji-python-client',
    'user_agent': 'OpenID Connect - Python client',
    'scope': '',
}

L = logging.getLogger(__name__)


class BBPOIDCException(Exception):
    '''Local exception'''
    pass


class BBPOIDCClient(OpenIDConnectFlow):
    '''Client to use OpenID Connect through Python
    '''

    @staticmethod
    def implicit_auth(user=None, password=None, oauth_url=None, use_cache=True):
        '''perform implicit authentication using either supplied user/password
            or ask for them

        Args:
            user(str): the username, if none, the environment is queried for
                       the current logged in user, and the user is queried if that's
                       what they want to use, interactively
            password(str): the password, if none, it's asked for interactively
            oauth_url(str): the 'Authorization Server' url, either the full url,
                            or the human form of 'dev', 'staging' or 'production
            use_cache(bool): Whether the cache should be used

        Returns:
            BBPOIDCClient instance

        Example:
            >>> from bbp_client.oidc.client import BBPOIDCClient
            >>> user = 'gevaert'
            >>> client = BBPOIDCClient.implicit_auth(user)
            # will now prompt for password, unless a successful
            # authentication has already taken place, and the token is valid

        Warning: if a cache is not used, it's possible to create many tokens.  This
                 will result in the openid connect server slowing down significantly
                 until the tokens expire.  If you are creating many tokens, please
                 revoke_token() when they are not needed.
        '''
        import getpass

        L.debug('Obtaining credentials using implicit_auth')
        c = BBPOIDCClient(oauth_url)
        if use_cache:
            if not user:
                env_user = getpass.getuser()
                user = raw_input('Username (%s): ' % env_user)
                if user == '':
                    user = env_user
            L.debug('Obtaining credentials from cache')
            c.credentials = c._cache_load_token(user, c.oauth_url)  # pylint: disable=W0212

        #cache didn't work, or we're using no-cache
        if not c.credentials:
            if not password:
                password = getpass.getpass()
            L.debug('obtaining credentials from manual authentication')
            c.credentials = c.manual_implicit_auth(user, password, use_cache)
        c.http = c.credentials.authorize(c.http)
        return c

    @staticmethod
    def bearer_auth(oauth_url, token):
        ''' If a bearer token exists, it is used to for authentication

        Args:
            oauth_url(str): the 'Authorization Server' url, either the full url,
                            or the human form of 'dev', 'staging' or 'production
            token: Token to be used for authentication

        Returns:
            BBPOIDCClient instance

        Note:
            - the cache is not used, since we don't know anything about the
              token

        Example:
            >>> from bbp_client.oidc.client import BBPOIDCClient
            >>> token = 'very long string....'
            >>> client = BBPOIDCClient.bearer_auth(token)
            # will now prompt for password, unless a successful
            # authentication has already taken place, and the token is valid
        '''
        L.debug('Obtaining credentials using bearer_auth')
        c = BBPOIDCClient(oauth_url)
        conf = c.oidcconfig
        access_token = token if not token.lower().startswith('bearer') else token[7:]
        cred = OAuth2Credentials(
            access_token=access_token, client_id=conf['client_id'],
            client_secret=conf.get('client_secret', None),
            refresh_token=None, token_expiry=None,
            token_uri=c.oauth_url + 'token', user_agent=None)
        c.credentials = c.step3_verify_access_token(cred, c.http, verify_id=False)
        c.http = c.credentials.authorize(c.http)
        return c

    @staticmethod
    def secret_auth(oauth_url, oidcconfig=None):
        ''' Authenticate using a preshared secret

        Args:
            oauth_url(str): the 'Authorization Server' url, either the full url,
                            or the human form of 'dev', 'staging' or 'production

            oidcconfig(dict): configuration that overrides the default config:
                {
                    'client_id': 'kamaji-python-client',
                    'client_secret': 'long string of characters',
                    'user_agent': 'OpenID Connect - Python client',
                    'scope': 'openid email',
                }

            With meaning:
                client_id(str): client ID as specified on OIDC server
                client_secret(str): client secret as specified on OIDC server
                user_agent(str): user agent to use
                scope(str): scope requested from OIDC server

        Returns:
            BBPOIDCClient instance

        Note: This doesn't use the cache

        Example:
            >>> from bbp_client.oidc.client import BBPOIDCClient
            >>> oidcconf = {...}
            >>> client = BBPOIDCClient.secret_auth(oauth_url='dev', oidcconf)
        '''
        L.debug('Obtaining credentials using client_secret')
        if oidcconfig and not oidcconfig.get('scope'):
            oidcconfig['scope'] = DEFAULT_OIDC_CONFIG['scope']
        if oidcconfig and not oidcconfig.get('user_agent'):
            oidcconfig['user_agent'] = DEFAULT_OIDC_CONFIG['user_agent']

        c = BBPOIDCClient(oauth_url, oidcconfig)
        c.credentials = c.step12_get_token_from_client_credentials(c.http)
        c.credentials = c.step3_verify_access_token(c.credentials, c.http)
        # no userinfo request (no user involved)
        c.http = c.credentials.authorize(c.http)
        return c

    @staticmethod
    def file_auth(yaml_path, oauth_url=None):
        '''load the oidc config

        Args:
            yaml_file(str path): path to yaml file to load

        Example yaml files:
            This example implies implicit auth:
                user: gevaert
                password: a password
                oauth_url: dev  #this is optional
            --- or ---
            This example implies secret auth:
                client_id: kamaji-python-client
                client_secret: axoidfuasfgdhadsmnfgjkqawhermxandf
                user_agent: OpenID Connect - Python client
                scope: openid email
                oauth_url: dev  #this is required

            Note: These are mutually exclusive.

        Example:
            >>> from bbp_client.oidc.client import BBPOIDCClient
            >>> client = BBPOIDCClient.file_auth('path_to_yaml')
        '''
        import yaml

        yaml_path = os.path.expanduser(yaml_path)
        if not os.path.exists(yaml_path):
            raise BBPOIDCException('Missing path: %s' % yaml_path)

        # init configuration from json file
        with open(yaml_path, 'r') as config:
            conf = yaml.safe_load(config.read())

        oauth_url = conf.get('oauth_url', oauth_url)

        if 'user' in conf and 'password' in conf:
            client = BBPOIDCClient.implicit_auth(user=conf['user'],
                                                 password=conf['password'],
                                                 oauth_url=oauth_url)
        else:
            assert 'client_id' in conf and 'client_secret' in conf
            secret_conf = dict(DEFAULT_OIDC_CONFIG)
            secret_conf.update(conf)
            if oauth_url is None:
                raise BBPOIDCException('missing oauth_url in yaml file')
            client = BBPOIDCClient.secret_auth(oauth_url, secret_conf)

        return client

    def __init__(self, oauth_url=None, oidcconfig=None):
        '''this is generally not used, as the staticmethod's are better:

            bearer_auth(oauth_url, token)
            implicit_auth(user=None, password=None, oauth_url=None, use_cache=True)
            secret_auth(oauth_url, oidcconfig=None)
            file_auth(yaml_path, oauth_url=None)
        '''
        service = get_services()['oidc_service']
        if oauth_url in service:
            self.oauth_url = service[oauth_url]['url']
        else:
            self.oauth_url = oauth_url or service['prod']['url']
        L.debug('Using url: %s', self.oauth_url)

        self.oidcconfig = oidcconfig or DEFAULT_OIDC_CONFIG

        super(BBPOIDCClient, self).__init__(
            client_id=self.oidcconfig['client_id'],
            client_secret=self.oidcconfig.get('client_secret', None),
            user_agent=self.oidcconfig['user_agent'],
            scope=self.oidcconfig['scope'],
            auth_uri=self.oauth_url + 'authorize',
            token_uri=self.oauth_url + 'token',
            tokeninfo_uri=self.oauth_url + 'tokeninfo',
            userinfo_uri=self.oauth_url + 'userinfo'
        )

        self.redirect_uri = urljoin(self.oauth_url, 'resources/oauth_code.html')

        # bundle of X.509 certificates of public Certificate Authorities
        cacerts_path = joinp(os.path.dirname(__file__), 'cacert/cacert.pem')
        self.http = httplib2.Http(ca_certs=cacerts_path)

        self.credentials = None

    def manual_implicit_auth(self, user, passwd, use_cache):
        '''performs authentication if we can't load from cache, or don't already
           have a working token

            then we take the user/password and emulate a browser
        '''
        authorize_url = self.step1_get_authorize_implicit_url(self.redirect_uri)
        L.debug('authorize_url: %s', authorize_url)

        url_with_fragment = self._authenticate_user(authorize_url, user, passwd)

        credentials = self.step2_get_credentials_from_url_fragment(url_with_fragment)
        credentials = self.step3_verify_access_token(credentials, self.http)
        credentials = self.step4_userinfo(credentials, self.http)

        if use_cache:
            self._cache_save_token(user, credentials, self.oauth_url)

        return credentials

    @staticmethod
    def _authenticate_user(authorize_url, user, passwd):
        '''Authenticate the user by emulating browser interaction
            Args:
                authorize_url: URL to get a valid token
                user(string): username
                password(string): password for above username
            Return: the url (String) provided by the AS containing as fragment access_token & co
                    to be parsed by method 'step2_get_credentials_from_url_fragment'
        '''
        #maximum number of times to try and authenticate against the OIDC webserver
        MAX_TRY = 3

        # mechanize isn't parsed well by pylint, and thus select_form and
        # submit are marked non-callable
        # pylint: disable=E1102
        import mechanize
        br = mechanize.Browser()
        br.set_handle_robots(False)
        for _ in range(MAX_TRY):
            br.open(authorize_url)
            br.select_form(name='j_spring_security_check')

            # fill form
            br['j_username'] = user
            br['j_password'] = passwd

            res = br.submit()
            L.debug('post authentication URL: %s', res.geturl())
            if 'error=' not in res.geturl():
                break
            else:
                L.debug('Permission denied, please try again')
        else:
            raise BBPOIDCException('Permission denied')

        L.debug('pre approve URL: %s', res.geturl())
        # the user is forwarded to the approve page if not approved yet
        if 'access_token' not in (urlparse(res.geturl()).fragment.lower()):
            br.select_form(name='confirmationForm')
            res = br.submit()

        L.debug('return URL: %s', res.geturl())

        # return url with access_token as uri fragment
        return res.geturl()

    @staticmethod
    def _cache_token_path(user, oauth_url):
        '''returns the expected token path based on user

           ex. /home/user/.credentials/py_oidc_user_authserv
        '''
        url = urlparse(oauth_url)
        token_folder = joinp(os.path.expanduser('~'), '.credentials')
        token_file = joinp(token_folder, 'py_oidc_%s_%s' % (user, url.hostname))
        L.debug('token_file: %s', token_file)
        return token_file

    def _cache_load_token(self, user, oauth_url, token_file=None):
        '''check if there's a token stored in the token_file

            returns the credentials if they verify, None otherwise
        '''
        token_file = token_file or self._cache_token_path(user, oauth_url)

        if not os.path.exists(token_file):
            return None

        L.debug('Loading access_token from cache')
        with open(token_file, 'r') as token_cache:
            credentials = pickle.load(token_cache)
            try:
                # verifying token
                credentials = self.step3_verify_access_token(credentials, self.http)
                # get userinfo
                credentials = self.step4_userinfo(credentials, self.http)
            except Exception:  # pylint: disable=W0703
                L.info('token found but is not valid, authenticate again...')
                credentials = None

        return credentials

    @staticmethod
    def _cache_save_token(user, credentials, oauth_url, token_file=None):
        '''dump it to file'''
        token_file = token_file or BBPOIDCClient._cache_token_path(user, oauth_url)
        #L.debug('Saving token to: %s', token_file)
        token_file_dir = os.path.dirname(token_file)
        try:
            if not os.path.exists(token_file_dir):
                os.makedirs(token_file_dir)
            with open(token_file, 'wb') as output:
                pickle.dump(credentials, output, pickle.HIGHEST_PROTOCOL)
            # set permissions: read/write for owner
            os.chmod(token_file, stat.S_IRUSR | stat.S_IWUSR)
        except Exception as e:
            raise BBPOIDCException('Error storing credentials in %s, SKIP' % token_file, e)

    def refresh(self):
        '''try and refresh the OAUTH token'''
        #need to use a 'private' method to refresh the token
        #this won't work for any auth type except for secret_auth at the moment
        self.credentials._refresh(self.http.request)  # pylint: disable=W0212

    def get_auth_header(self):
        '''get the authentication header text used in header

            ie: Authorization=*this return*
        '''
        return 'Bearer ' + self.credentials.access_token

    def request(self, uri, method='GET', body=None, headers=None, params=None):
        ''' http2lib.request wrapper
        '''
        if isinstance(params, dict):
            params = urllib.urlencode(params)

        if params:
            uri += '?' + params

        resp, content = self.http.request(uri, method, body, headers)
        _verify_request(uri, resp.status, content)
        return resp, content

    @property
    def introspect_uri(self):
        '''the uri where introspect requests can be sent to'''
        return os.path.join(self.oauth_url, 'introspect')

    def introspect_token(self, token):
        '''request up to date information about the given token

        only supported on clients that have a secret in their config'''
        _, content = self.request(
            self.introspect_uri,
            params=dict(client_id=self.client_id, client_secret=self.client_secret,
                        token=token))

        return json.loads(content)

    @property
    def chain_token_uri(self):
        '''the uri where chain requests can be sent to'''
        return os.path.join(self.oauth_url, 'token')

    def chain_token(self, token):
        '''create a new token from a given one

        only supported on clients that have a secret in their config'''
        _, content = self.request(
            self.chain_token_uri,
            params=dict(client_id=self.client_id, client_secret=self.client_secret,
                        grant_type='urn:ietf:params:oauth:grant_type:redelegate',
                        token=token))

        return json.loads(content)

    @property
    def revoke_token_uri(self):
        '''the uri where chain requests can be sent to'''
        return os.path.join(self.oauth_url, 'revoke')

    def revoke_token(self, token=None):
        '''mark the given token as invalid, if no token is given, the one in this client is used
        '''
        if token is None:
            token = self.credentials.access_token

        self.request(
            self.revoke_token_uri,
            params=dict(client_id=self.client_id, client_secret=self.client_secret, token=token))


def _verify_request(uri, status, content):
    '''convenience method to consistently deal with and log request results.

    raises HTTPError if the status was not OK'''
    if status >= 200 and status < 300:
        L.debug('Successfully retrieved data')
    else:
        L.error('Failed to retrieve data: %s', content)
        error_msg = 'Invalid response %s.' % status
        raise HTTPError(uri, status, error_msg, None, None)
