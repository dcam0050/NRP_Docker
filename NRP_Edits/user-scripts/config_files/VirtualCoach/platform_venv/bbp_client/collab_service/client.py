'''Collab service client'''
import logging
import uuid

from os.path import join as joinp

import requests

from bbp_services.client import get_services
from bbp_client.oidc.client import BBPOIDCClient
from bbp_client.collab_service.exceptions import CollabException, NoAccessException
import bbp_client.collab_service.extension as ext


L = logging.getLogger(__name__)


class Client(object):
    '''Collab service client'''
    ITEM_TYPES = {'item': 'item', 'it': 'item', 'folder': 'folder', 'fo': 'folder',
                  'ex': 'ex', 'external': 'ex',
                  }

    def __init__(self, host, oidc, collab_id, environment='prod'):
        '''simple wrapper around the collab concept:
        gives it auth, which server and what collab_id

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
        self.collab_id = int(collab_id)
        self.environment = environment

    @classmethod
    def new(cls, collab_id, environment='prod', user=None, password=None, token=None):
        '''create new collab service client'''
        services = get_services()
        oauth_url = services['oidc_service'][environment]['url']
        service_url = services['collab_service'][environment]['url']
        if token:
            oauth_client = BBPOIDCClient.bearer_auth(oauth_url, token)
        else:
            oauth_client = BBPOIDCClient.implicit_auth(user, password, oauth_url)
        return cls(service_url, oauth_client, collab_id, environment)

    def set_collab_id_by_context(self, context):
        '''lookup collab by context'''
        url = joinp(self._host, 'collab/context/%s/' % context)
        resp = requests.get(url, headers=self._get_headers())
        if resp.status_code != 200:
            raise CollabException('Failed to get collab by context %s, "%s"' %
                                  (resp.status_code, resp.text))
        self.collab_id = resp.json()['collab']['id']
        return self.collab_id

    def get_extension(self, app_id):
        '''Returns a configured instance of the extension referred to by app_id

        Args:
            app_id(int or str): if it's an int, it's used as the app_id, if it's a string, it is
                looked up to find the correct extension
        '''
        try:
            app_id = int(app_id)
            extension = ext.Extension.get_extension_by_id(self._host, self._oidc, app_id)
        except ValueError:
            extension = ext.Extension.get_ext_title_2_backend(app_id)
        return extension(self._host, self._oidc)

    @staticmethod
    def _get_uuid4():
        '''get a string version of a uuid4'''
        return str(uuid.uuid4())

    def _get_headers(self):
        '''return the headers, necessary for authentication'''
        return {'Authorization': self._oidc.get_auth_header(),
                'Accept': 'application/json'}

    def permissions(self):
        '''return collab permissions for current user'''
        url = joinp(self._host, 'collab/%s/permissions/' % self.collab_id)
        resp = requests.get(url, headers=self._get_headers())
        if resp.status_code != 200:
            raise CollabException('Failed to get collab permissions %s, "%s"' %
                                  (resp.status_code, resp.text))
        return resp.json()

    def permissions_by_context(self, context):
        '''return permissions by context'''
        url = joinp(self._host, 'collab/context/%s/permissions/' % context)
        resp = requests.get(url, headers=self._get_headers())
        if resp.status_code == 403:
            raise NoAccessException(resp.text)
        elif resp.status_code != 200:
            raise CollabException('Failed to get collab context permissions %s, "%s"' %
                                  (resp.status_code, resp.text))

        return resp.json()

    def is_contributor(self):
        '''check if current user is a contributor for particular collab'''
        return self.permissions().get('UPDATE', False)

    def _fetch_list(self, url, page_size_arg='page_size', page_size=50):
        '''retrieves list page by page'''
        results = []
        headers = self._get_headers()
        page_url = '%s?%s=%s' % (url, page_size_arg, page_size)

        while True:
            resp = requests.get(page_url, headers=headers)
            if resp.status_code != 200:
                raise CollabException('Failed to GET %s %s, "%s"' %
                                      (url, resp.status_code, resp.text))
            jsn = resp.json()
            results.extend(jsn['results'])
            if jsn.get('next'):
                page_url = jsn['next']
            else:
                break

        return results

    def collabs(self):
        '''return all collabs which user can read'''
        return self._fetch_list(joinp(self._host, 'collab/'))

    def my_collabs(self):
        '''return collabs which user is member of'''
        return self._fetch_list(joinp(self._host, 'mycollabs/'))

    def team(self):
        '''return collab members

        Returns:
            list(str): list of userids
        '''
        if not self.collab_id:
            return []
        resp = requests.get(joinp(self._host, 'collab/%s/team/' % self.collab_id))
        resp.raise_for_status()
        return [str(item['user_id']) for item in resp.json()]

    def get_app_id(self, _id):
        '''if _id is numeric, will return it, if it's a name, will try and look it up
           on the collab server
        '''
        try:
            return int(_id)
        except ValueError:
            pass
        return ext.lookup_extension_by_name(self._host, self._oidc, _id)

    def add_item(self, parent_id, prop, _type='Item'):
        '''post an item to the nav tree, returns the id'''
        name = prop['name']
        L.info('Adding %s to parent_id: %d (type: %s)', name, parent_id, _type)

        _type = Client.ITEM_TYPES[_type.lower()]
        url = joinp(self._host, 'collab/%d/nav/' % self.collab_id)
        if 'folder' == _type:
            data = {
                'name': name,
                'collab': self.collab_id,
                'type': 'FO',
                'parent': str(parent_id),
                'order_index': '-1',
            }
        else:
            app_id = self.get_app_id(prop['app_id'])
            data = {
                'name': name,
                'collab': self.collab_id,
                'type': 'IT',
                'parent': str(parent_id),
                'app_id': app_id,
                'context': prop.get('context', self._get_uuid4()),
                'order_index': prop.get('order_index', '-1'),
            }
        resp = requests.post(url, headers=self._get_headers(), json=data)
        if resp.status_code != 201:
            raise CollabException('Failed to get add_item to collab %s, "%s"' %
                                  (resp.status_code, resp.text))
        return resp.json()

    def get_current_tree(self):
        '''return the current tree in the collab'''
        url = joinp(self._host, 'collab/%d/nav/all/' % self.collab_id)
        resp = requests.get(url, headers=self._get_headers())
        if resp.status_code != 200:
            raise CollabException('Failed to get collab current_tree %s, "%s"' %
                                  (resp.status_code, resp.text))
        return self._create_tree(resp.json())

    @staticmethod
    def _create_tree(flat_tree):
        '''create actual recursive tree structure

        Args:
            flat_tree(list of dicts): json returned from /nav/all/ endpoint

        Note: This doesn't copy the tree elements, so any changes are propagated
        '''
        root = None

        ind_map = dict([(el['id'], el) for el in flat_tree])

        for el in ind_map.values():
            if el['type'] == 'FO':
                el['children'] = []

        #find parents, and fill out children property
        for el in flat_tree:
            if el['parent'] is None:
                assert(root is None)
                root = el
            else:
                parent = ind_map[el['parent']]
                parent['children'].append(el)

        return root

    def context_url(self, context):
        '''return url to navitem by context'''
        url = joinp(self._host, 'collab/context/%s/' % context)
        resp = requests.get(url, headers=self._get_headers())
        resp.raise_for_status()
        return joinp(get_services()['collaboratory'][self.environment]['url'],
                     '#/collab/%s/nav/%s' % (resp.json()['collab']['id'], resp.json()['id']))


def sync_nav_tree(collab, tree, tree_additions):
    '''
    Args:
        collab(Collab): which collab to sync tree
        tree(dict): current representation of the tree at the same level as tree_additions
            each FO type has a 'children' list containing the element underneath it
        tree_additions(list): list of items to be created
            Ex:
                [{'0Path':
                    [{'1Path': [{'Name0': {'app_id': Content Page}}]},
                     {'Name1': {'app_id': Content Page}}]},
                 {'Name1': {'app_id': Content Page}}]
        Note: This doesn't copy the tree elements, so any changes are propagated
    '''
    _id = tree['id']
    children = tree['children']

    children_names = dict([(t['name'], t) for t in children])
    for item in tree_additions:
        for name, prop in item.items():
            if isinstance(prop, dict):  # item
                if name not in children_names:
                    prop['name'] = name
                    new_item = collab.add_item(_id, prop, _type='Item')
                    if 'config' in prop:
                        context = new_item['context']
                        config = prop['config']
                        config['context'] = context
                        extension_backend = collab.get_extension(prop['app_id'])
                        extension_backend.post(context, config)
                    children.append(new_item)
            else:  # Folder
                if name not in children_names:
                    sub_tree = collab.add_item(_id, {'name': name}, _type='Folder')
                    children.append(sub_tree)
                    children_names[name] = sub_tree
                    sub_tree['children'] = []
                else:
                    sub_tree = children_names[name]
                if prop is not None:  # might have an empty folder, then prop is None
                    sync_nav_tree(collab, sub_tree, prop)
    return tree
