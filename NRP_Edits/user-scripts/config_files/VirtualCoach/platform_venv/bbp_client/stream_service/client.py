'''Collab service client'''
import logging

from os.path import join as joinp
from datetime import datetime

import requests

from bbp_services.client import get_services
from bbp_client.oidc.client import BBPOIDCClient


L = logging.getLogger(__name__)


class Client(object):
    '''Stream service client'''

    def __init__(self, host, oidc, environment='prod'):
        '''
        Args:
           host: host to connnect to, ie: http://localhost:8888
           oauth_client: instance of the bbp_client.oidc.client
        '''
        services = get_services()
        if services['collab_service'].get(host):
            self._host = services['collab_service'][environment]['url']
        else:
            self._host = host
        self._oidc = oidc
        self.environment = environment

    @classmethod
    def new(cls, environment='prod', user=None, password=None, token=None):
        '''create new collab service client'''
        services = get_services()
        oauth_url = services['oidc_service'][environment]['url']
        service_url = services['stream_service'][environment]['url']
        if token:
            oauth_client = BBPOIDCClient.bearer_auth(oauth_url, token)
        else:
            oauth_client = BBPOIDCClient.implicit_auth(user, password, oauth_url)
        return cls(service_url, oauth_client, environment)

    def _get_headers(self):
        '''return the headers, necessary for authentication'''
        return {'Authorization': self._oidc.get_auth_header(),
                'Accept': 'application/json'}

    def register_activity(self, activity):
        '''Post Activity'''
        if not activity.get('time'):
            activity['time'] = str(datetime.now())

        url = joinp(self._host, 'activity/')
        resp = requests.post(url, json=activity, headers=self._get_headers())
        resp.raise_for_status()
