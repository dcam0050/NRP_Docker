'''client for working with the MIMEType service'''
import urllib
from datetime import datetime, timedelta
from urlparse import urljoin
from collections import namedtuple

import requests

import bbp_client.mimetype_service.models as models


class MimetypeLookupCache(object):
    '''cache for mimetype find operation'''
    CachedMimetype = namedtuple('CachedMimetype', ['mimetype', 'expire'])

    def __init__(self, max_age=timedelta(hours=1)):
        self._mimetype_cache = {}
        self._query_cache = {}
        self.max_age = max_age

    def add(self, query, mimetypes):
        '''cache list of mimetypes for given query'''
        exp = datetime.now() + self.max_age
        self._mimetype_cache.update(dict((m.id, self.CachedMimetype(m, exp)) for m in mimetypes))
        self._query_cache[query] = [m.id for m in mimetypes]

    def _remove_expired(self):
        '''remove expired items from cache'''
        now = datetime.now()
        expired_ids = set([idx for (idx, item) in self._mimetype_cache.items()
                           if item.expire < now])
        expired_queries = [query for (query, ids) in self._query_cache.items()
                           if set(ids) & expired_ids]
        for idx in expired_ids:
            del self._mimetype_cache[idx]
        for idx in expired_queries:
            del self._query_cache[idx]

    def get(self, query):
        '''check cache for given query'''
        self._remove_expired()
        cached_result = self._query_cache.get(query)
        if cached_result:
            return [self._mimetype_cache[idx].mimetype for idx in cached_result]
        return None

    def reset(self):
        '''reset cache'''
        self._mimetype_cache = {}
        self._query_cache = {}


class Client(object):
    '''Interface to the platform MIMEType service via python

        Example:
            >>> server = 'http://localhost:8000'
            >>> from bbp_client.mimetype_service.client import Client
            >>> ms = Client(server)
            >>> ms.find_mimetype(mimetype='image/png')
    '''
    MIMETYPE_PATH = 'mimetype/'
    VIEWER_PATH = 'viewer/'
    KEY_PATH = 'key/'

    REQUIRED_HEADERS = {'Content-Type': 'application/json',
                        }

    def __init__(self, host, headers={}, cache_enabled=False): # pylint: disable=W0102
        '''
        Args:
            host: the protocol and name, 'http://localhost:port
            headers: HTTP headers passed to server
        '''
        self.host = host
        self.headers = dict(Client.REQUIRED_HEADERS)
        self.headers.update(headers)
        if cache_enabled:
            self.cache = MimetypeLookupCache()
        else:
            self.cache = None

    def __repr__(self):
        return 'mimetype.service.client.Client("%s")' % self.host

    __str__ = __repr__

    @property
    def url_mimetype(self):
        '''get the route to the mimetype endpoint'''
        return urljoin(self.host, Client.MIMETYPE_PATH)

    @property
    def url_viewer(self):
        '''get the route to the viewer endpoint'''
        return urljoin(self.host, Client.VIEWER_PATH)

    @property
    def url_key(self):
        '''get the route to the viewer endpoint'''
        return urljoin(self.host, Client.KEY_PATH)

    @staticmethod
    def _get_models_by_url(base_url, params):
        '''get and deserialize many mimetype/viewer/key based on a url

        Args:
            base_url(str): url on which to perform query
            params(dict): key/value pairs to search for
        '''
        url = base_url

        filt = urllib.urlencode([(k, v) for k, v in params.items() if v])
        if filt:
            url = urljoin(url, '?' + filt)

        ret = []
        while url:
            r = requests.get(url)
            r.raise_for_status()
            response = r.json()
            ret.extend(models.JSONModel.deserialize(json_obj=d) for d in response['results'])
            url = response.get('next', None)

        return ret

    @staticmethod
    def _get_model_by_url(url):
        '''get and deserialize a mimetype/viewer/key based on a url'''
        r = requests.get(url)
        r.raise_for_status()
        return models.JSONModel.deserialize(json_obj=r.json())

    def _update_keys(self, old_mimetype, new_mimetype):
        '''update the keys of a mimetype'''
        old_keys = dict((k.id, k) for k in old_mimetype.keys)
        new_keys = dict((k.id, k) for k in new_mimetype.keys)

        old_id = set(old_keys.keys())
        new_id = set(new_keys.keys())

        #delete keys that no longer exist
        for k in old_id - new_id:
            self.delete_key(old_keys[k])

        #add keys that are new
        for k in new_id - old_id:
            new_keys[k].mimetype = new_mimetype.id
            self.register_key(new_keys[k])

        #check for modifications of other keys, and update them
        for k in old_id & new_id:
            if old_keys[k] != new_keys[k]:
                self.update_key(new_keys[k])

        return new_mimetype.keys

    def _add_to_cache(self, query, mimetypes):
        '''cache list of mimetypes'''
        if self.cache:
            self.cache.add(query, mimetypes)

    def _get_from_cache(self, query):
        '''check cache for given query'''
        if self.cache and self.cache.get(query):
            return self.cache.get(query)
        return None

    def _reset_cache(self):
        '''reset cache'''
        if self.cache:
            self.cache.reset()

    def get_mimetype(self, mimetype_id):
        '''get the value of a MIMEType by id

        Args:
            mimetype_id(int): get the mimetype by its primary key/id

        Returns:
            MimeType that has the id, or None if it does not exist

        Example:
            >>> server = 'http://localhost:8000'
            >>> from bbp_client.mimetype_service.client import Client
            >>> ms = Client(server)
            >>> mt = ms.get_mimetype(1)
        '''
        url = urljoin(self.url_mimetype, '%d/' % int(mimetype_id))
        return self._get_model_by_url(url)

    def find_mimetype(self, mimetype=None, description=None):
        '''get the value of a MIMEType by name, or description

        Args:
            mimetype(str): name of the MIMEType to filter for, optional
            description(str): description of MIMEType to filter for, optional

        Returns:
            List of MimeType that match the query, where the match is case
                insensitive, and the union of mimetypes that match the above filters
        '''
        search_terms = {'mimetype': mimetype,
                        'description': description,
                        }
        query = (mimetype, description)
        res = self._get_from_cache(query)
        if not res:
            res = self._get_models_by_url(self.url_mimetype, search_terms)
            self._add_to_cache(query, res)
        return res

    def register_mimetype(self, mimetype):
        '''register a new mimetype with the server

            >>> server = 'http://localhost:8000'
            >>> from bbp_client.mimetype_service.client import Client
            >>> from bbp_client.mimetype_service import models
            >>> new_mt = models.MimeTypeFactory(mimetype='test/mimetype', description='test mt')
            >>> ms = Client(server)
            >>> mt = ms.register_mimetype(new_mt)
            >>> print mt
        '''

        url = self.url_mimetype
        r = requests.post(url, data=mimetype.serialize(skip_fields=set(['keys'])),
                          headers=self.headers)
        r.raise_for_status()
        ret = models.JSONModel.deserialize(json_obj=r.json())
        ret.__dict__['keys'] = self._update_keys(ret, mimetype)

        self._reset_cache()

        return ret

    def update_mimetype(self, mimetype):
        ''''put' any changes that have been done to the mimetype

        This is expected to be used like so:

        Example:
            >>> server = 'http://localhost:8000'
            >>> from bbp_client.mimetype_service.client import Client
            >>> ms = Client(server)
            >>> mt = ms.get_mimetype(mimetype='test/mimetype')[0]
            >>> mt.description = 'a new description'
            >>> mt = ms.update_mimetype(mt)
            >>> print mt

        '''
        url = urljoin(self.url_mimetype, '%d/' % int(mimetype.id))
        r = requests.put(url, data=mimetype.serialize(skip_fields=set(['keys'])),
                         headers=self.headers)
        r.raise_for_status()
        ret = models.JSONModel.deserialize(json_obj=r.json())
        ret.__dict__['keys'] = self._update_keys(ret, mimetype)

        self._reset_cache()

        return ret

    def delete_mimetype(self, mimetype):
        '''delete the mimetype on the mimetype service

        Example:
            >>> server = 'http://localhost:8000'
            >>> from bbp_client.mimetype_service.client import Client
            >>> ms = Client(server)
            >>> mt = ms.get_mimetype(mimetype='image/png')
            >>> ms.delete_mimetype(mt)
        '''
        url = urljoin(self.url_mimetype, '%d/' % int(mimetype.id))
        r = requests.delete(url, headers=self.headers)
        r.raise_for_status()

        self._reset_cache()

        return r

    def get_viewer(self, viewer_id):
        '''get the value of a viewer by id

        Args:
            id_(int): get the viewer by its primary key/id

        Returns:
            viewer that has the secified id

        Example:
            >>> server = 'http://localhost:8000'
            >>> from bbp_client.mimetype_service.client import Client
            >>> ms = Client(server)
            >>> v = ms.get_viewer(viewer='test')
            >>> print v
        '''
        url = urljoin(self.url_viewer, '%d/' % int(viewer_id))
        return self._get_model_by_url(url)

    def find_viewer(self, viewer=None, version=None, deprecated=None):
        '''get the value of a viewer by name, or version, and deprecation value

        Args:
            viewer(str): name of the viewer to filter for, optional
            version(str): version of the viewer to filter for, optional
            deprecated(bool): bool if looking for deprecated viewer, optional

        Returns:
            List of viewers that match the query, where the match is case
                insensitive, and the union of mimetypes that match the above filters
        '''
        search_terms = {'viewer': viewer,
                        'version': version,
                        'deprecated': deprecated,
                        }
        return self._get_models_by_url(self.url_viewer, search_terms)

    def register_viewer(self, viewer_model):
        '''register a new viewer with the server

            >>> server = 'http://localhost:8000'
            >>> from bbp_client.mimetype_service.client import Client
            >>> from bbp_client.mimetype_service import models
            >>> new_viwer = models.ViewerFactory(viewer='test viewer',
            >>>                                  version=1, mimetype=[1, 2, 3])
            >>> ms = Client(server)
            >>> v = ms.register_viewer(new_viewer)
            >>> print v
        '''
        r = requests.post(self.url_viewer, data=viewer_model.serialize(), headers=self.headers)
        r.raise_for_status()
        return models.JSONModel.deserialize(json_obj=r.json())

    def update_viewer(self, viewer):
        '''put any changes that have been done to the viewer parameter

        This is expected to be used like so:

        Example:
            >>> server = 'http://localhost:8000'
            >>> from bbp_client.mimetype_service.client import Client
            >>> ms = Client(server)
            >>> v = ms.get_viewer(1)
            >>> v.version = 2
            >>> v = ms.update_viewer(v)
            >>> print v

        Which will only update the description of the viewer, since no other fields were changed
        '''
        url = urljoin(self.url_viewer, '%d/' % int(viewer.id))
        r = requests.put(url, data=viewer.serialize(), headers=self.headers)
        r.raise_for_status()
        return models.JSONModel.deserialize(json_obj=r.json())

    def delete_viewer(self, viewer):
        '''delete the viewer on the viewer service

        Example:
            >>> server = 'http://localhost:8000'
            >>> from bbp_client.mimetype_service.client import Client
            >>> ms = Client(server)
            >>> v = ms.get_viewer(1)
            >>> ms.delete_viewer(v)
        '''
        url = urljoin(self.url_viewer, '%d/' % int(viewer.id))
        r = requests.delete(url, headers=self.headers)
        r.raise_for_status()
        return r

    def register_key(self, key):
        '''register a key'''
        r = requests.post(self.url_key, data=key.serialize(), headers=self.headers)
        r.raise_for_status()
        return models.JSONModel.deserialize(json_obj=r.json())

    def update_key(self, key):
        '''update a key'''
        url = urljoin(self.url_key, '%d/' % int(key.id))
        r = requests.put(url, data=key.serialize(), headers=self.headers)
        r.raise_for_status()
        return models.JSONModel.deserialize(json_obj=r.json())

    def delete_key(self, key):
        '''delete a key'''
        url = urljoin(self.url_key, '%d/' % int(key.id))
        r = requests.delete(url, headers=self.headers)
        r.raise_for_status()
        return r
