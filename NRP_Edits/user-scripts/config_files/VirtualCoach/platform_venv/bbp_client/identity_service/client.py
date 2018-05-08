'''client class to send requests to User and Group APIs'''
import logging
import requests

from bbp_services.client import get_services
from bbp_client.oidc.client import BBPOIDCClient
from bbp_client.identity_service.userinfo import UserInfo


L = logging.getLogger(__name__)


HBP_MEMBER_GROUP = 'hbp-member'


class Client(object):
    '''Interface to the identity service via python'''

    def __init__(self, host, oauth_client=None, headers=None):
        '''
        Args:
           host: host to connnect to, ie: http://localhost:8888 (can be dev or prod as well)
           oauth_client: instance of the bbp_client.oidc.client
           headers: HTTP headers passed to server
        '''
        services = get_services()
        if services['idm_service'].get(host):
            self.base_url = services['idm_service'][host]['url']
        else:
            self.base_url = host
        self.oauth_client = oauth_client
        self.session = requests.Session()
        self.session.headers.update({'Authorization': self.oauth_client.get_auth_header()})
        if headers:
            self.session.headers.update(headers)

    @classmethod
    def new(cls, environment='prod', user=None, password=None, token=None):
        '''create new documentservice client'''
        services = get_services()
        oauth_url = services['oidc_service'][environment]['url']
        idm_url = services['idm_service'][environment]['url']
        if token:
            oauth_client = BBPOIDCClient.bearer_auth(oauth_url, token)
        else:
            oauth_client = BBPOIDCClient.implicit_auth(user, password, oauth_url)
        return cls(idm_url, oauth_client)

    @classmethod
    def _build_query_string(cls, query_params):
        '''returns query string

        Default rule is to add query param like key=value for every key
        But in case value is list it will be key=value1&..&key=valueN for each value

        Example:
            >>> _build_query_string({'key1': 'val1', 'key2': ['val21', 'val22']})
            ?key1=val1&key2=val21&key2=val22

        Args:
            query_params (dict): Query Params
                Values either strings or list of strings

        Returns:
            str: Empty string in case of empty query params. Otherwise string like
                ?key1=value1&key2=value21&key2=value22
        '''
        if not query_params:
            return ''

        jf = lambda k, v: '%s=%s' % (k, v)
        func = lambda k, v: '&'.join([jf(k, vv) for vv in v]) if isinstance(v, list) else jf(k, v)

        res = '&'.join([func(k, v) for k, v in query_params.items() if v])
        return '?' + res if res else res

    def _get(self, resource=None, url=None, query_params=None):
        '''wrapper for GET request

        Builds url based on base url and query string
        '''
        if not url:
            _url = '%s%s%s' % (self.base_url, resource, self._build_query_string(query_params))
        else:
            _url = url
        L.debug('Sending GET request to %s', _url)
        resp = self.session.get(_url)
        resp.raise_for_status()
        return resp.json()

    def me(self):
        '''return current user info'''
        return self._get('/user/me')

    def get_groups(self, user_id, name=None, page=None, page_size=50, sort=None):
        '''return groups of given user

        Args:
            user_id (str): user id
            name (str or list): If provided, result will contain only the groups having those names
            page: page number, if provided only one page returned
            page_size (int):  number of items present in the page
            sort (str or list): example 'name,desc' or ['name,asc', 'description,desc']

        Returns:
            list: of group names

        Raises:
            HTTPError: in case non 200 response from API
        '''
        query_params = {'name': name, 'page': page, 'pageSize': page_size, 'sort': sort}
        res = self._get('/user/%s/member-groups' % user_id, query_params=query_params)
        if not res.get('_embedded'):
            return []
        groups = [group['name'] for group in res['_embedded']['groups']]

        while not page and res['_links'].get('next'):
            res = self._get(url=res['_links']['next']['href'])
            groups.extend([group['name'] for group in res['_embedded']['groups']])

        return groups

    def is_member_of(self, user_id, group):
        '''check whether user is member of given group

        Args:
            user_id (str): user id
            group (str or list): name of group(s)

        Returns:
            bool: True if user is member of all groups from group, False otherwise
        '''
        return not self.get_groups(user_id, name=group) == []

    def is_hbp_member(self, user_id):
        '''check that user is HBP member

        Args:
            user_id (str): user id

        Returns:
            bool: True if user is HBP member, False if it is Community User
        '''
        return self.is_member_of(user_id, HBP_MEMBER_GROUP)

    def userinfo(self, user_ids):
        '''return userinfo for list of users

        Args:
            user_ids (list): list of user ids (str)

        Returns:
            dict: dict of (userid, userinfo) items
        '''
        res = self._get('/user/search', query_params={'id': user_ids, 'pageSize': 1000})
        if not res.get('_embedded'):
            return []
        users = dict((user['id'], UserInfo(user)) for user in res['_embedded']['users'])

        while res['_links'].get('next'):
            res = self._get(url=res['_links']['next']['href']).json()
            users.update(dict((user['id'], UserInfo(user)) for user in res['_embedded']['users']))
        return users

    def members(self, group, recursive=False, page=None, page_size=50, sort=None):
        '''return list of members of given group

        Args:
            group(str): name of the group
            recursive(bool): including members of subgroups or not
            page: page number, if provided only one page returned
            page_size (int):  number of items present in the page
            sort (str or list): example 'name,desc' or ['name,asc', 'description,desc']

        Returns:
            list(UserInfo): list of UserInfo
        '''
        query_params = {'page': page, 'pageSize': page_size, 'sort': sort}
        url = '/group/%s/members' % group
        if recursive:
            url = '/user/searchByGroups'
            query_params['include'] = group
        res = self._get(url, query_params=query_params)
        users = [UserInfo(user) for user in res['_embedded']['users']]

        while not page and res['_links'].get('next'):
            res = self._get(url=res['_links']['next']['href'])
            users.extend([UserInfo(user) for user in res['_embedded']['users']])

        return users

    def subgroups(self, group, page=None, page_size=50, sort=None):
        '''return list of subgroups of given group

        Args:
            group(str): group name
            page: page number, if provided only one page returned
            page_size (int):  number of items present in the page
            sort (str or list): example 'name,desc' or ['name,asc', 'description,desc']

        Returns:
            list(str): list of group names
        '''
        query_params = {'page': page, 'pageSize': page_size, 'sort': sort}
        res = self._get('/group/%s/member-groups' % group, query_params=query_params)
        groups = [group['name'] for group in res['_embedded']['groups']]

        while not page and res['_links'].get('next'):
            res = self._get(url=res['_links']['next']['href'])
            groups.extend([group['name'] for group in res['_embedded']['groups']])

        return groups
