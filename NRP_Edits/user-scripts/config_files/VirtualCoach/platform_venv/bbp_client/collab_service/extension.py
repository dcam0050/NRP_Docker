'''base for all extensions'''

import logging
import uuid

from os.path import join as joinp

import requests


L = logging.getLogger(__name__)


def get_uuid4():
    '''get a string version of a uuid4'''
    return str(uuid.uuid4())


def get_headers(oidc):
    '''return the headers, necessary for authentication'''
    return {'Authorization': oidc.get_auth_header(),
            }


def lookup_extension_by_name(server, oidc, name):
    '''returns the app_id associated with a extension

    Args:
        name(str): case-insensitive name to search for
    '''
    headers = get_headers(oidc)
    url = joinp(server, 'extension/')
    resp = requests.get(url, headers=headers, params={'search': name})
    if resp.status_code != 200:
        raise Exception('Failed to get retrieve data %s, "%s"' %
                        (resp.status_code, resp.text))
    data = resp.json()
    if 1 != len(data['results']):
        raise Exception("Could not find '%s' extension" % name)
    return int(data['results'][0]['id'])


class Extension(object):
    '''base for all extensions, should be used for communicating with the extension endpoint'''
    # endpoint relative to the collab endpoint, ie 'config/' for
    # https://services.humanbrainproject.eu/collab/v0/config/
    BASE_ENDPOINT = None

    # fields that must be posted to the above endpoint
    REQUIRED_FIELDS = None

    #List of 'title's of extensions that use the particular specialization
    EXTENSION_TITLES = None

    def __init__(self, host, oidc):
        self._host = host
        self._oidc = oidc

    def get(self, context):
        '''get data associated with the context'''
        assert(self.BASE_ENDPOINT)
        L.debug('Getting context %s', context)
        url = joinp(self._host, self.BASE_ENDPOINT, context + '/')
        L.debug('Getting data from %s', url)
        headers = get_headers(self._oidc)
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            raise Exception('Failed to get extension info for %s, "%s"' %
                            (resp.status_code, resp.text))

        return resp.json()

    @classmethod
    def _verify_fields(cls, data):
        '''check that all required fields exist'''
        if set(data.keys()) - set(cls.REQUIRED_FIELDS):
            raise Exception('Mismatch of required fields: %s != %s', (set(data.keys()),
                                                                      set(cls.REQUIRED_FIELDS)))

    def put(self, context, data):
        '''Put (ie: update) data to context

        Args:
            context(str): Usually a uuid, identifying the content to be posted
            data(dict): fields to be posted to service
        '''
        data['context'] = context
        self._verify_fields(data)

        url = joinp(self._host, self.BASE_ENDPOINT, context + '/')
        headers = get_headers(self._oidc)
        resp = requests.put(url, headers=headers, data=data)
        if resp.status_code not in (200, 201, ):
            raise Exception('Failed to PUT data %s, "%s"' %
                            (resp.status_code, resp.text))

        return resp.json()

    def post(self, context=None, data=None):
        '''post data to extension

        Args:
            data(dict): fields to be 'put-ed' to service
        '''
        context = context or get_uuid4()
        data['context'] = context
        self._verify_fields(data)

        url = joinp(self._host, self.BASE_ENDPOINT)
        headers = get_headers(self._oidc)
        resp = requests.post(url, headers=headers, data=data)
        if resp.status_code not in (200, 201, ):
            raise Exception('Failed to POST data %s, "%s"' %
                            (resp.status_code, resp.text))

        return resp.json()

    def __repr__(self):
        return '<Extension(%s)>' % self.__class__.__name__

    @staticmethod
    def get_ext_title_2_backend(title):
        '''returns the extension object that matches the 'title' as saved in the collab db'''
        title = title.lower()
        for c in Extension.__subclasses__():  # pylint: disable=E1101
            if title in c.EXTENSION_TITLES:
                return c
        raise Exception('Unknown title: %s' % title)

    @staticmethod
    def get_extension_by_id(server, oidc, _id):
        '''returns the extension details based on a lookup of id'''
        headers = get_headers(oidc)
        url = joinp(server, 'extension/%s/' % _id)
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            raise Exception('Failed to get retrieve data %s, "%s"' %
                            (resp.status_code, resp.text))
        data = resp.json()
        return Extension.get_ext_title_2_backend(data['title'])


class Notes(Extension):
    '''Deal with notes extension in collab'''
    BASE_ENDPOINT = 'note/'
    REQUIRED_FIELDS = ('context', 'type', 'sourceMimeType', 'url', 'source',
                       )
    EXTENSION_TITLES = ('content page',
                        )

    TYPE_URL = 'URL'
    TYPE_SOURCE = 'SOURCE'

    @staticmethod
    def create_note_markdown(_uuid, content):
        '''markdown content helper'''
        return {'context': _uuid,
                'type': Notes.TYPE_SOURCE,
                'sourceMimeType': 'text/markdown',
                'url': '',
                'source': content,
                }

    @staticmethod
    def create_note_url(_uuid, url):
        '''url content helper'''
        return {'context': _uuid,
                'type': Notes.TYPE_URL,
                'sourceMimeType': '',
                'url': url,
                'source': '',
                }


class Config(Extension):
    '''Deal with config extension in collab'''
    BASE_ENDPOINT = 'config/'
    REQUIRED_FIELDS = ('context', 'content',
                       )
    EXTENSION_TITLES = ('config', 'software page',
                        )
