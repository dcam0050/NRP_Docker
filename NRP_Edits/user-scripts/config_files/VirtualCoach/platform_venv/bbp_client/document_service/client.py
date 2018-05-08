'''client for interacting with the documentation service, implements many
of the os.* functions
'''
import logging
import os
from os.path import join as joinp
from bbp_client import swagger_helpers as sh
from bbp_services.client import get_services

from bbp_client.oidc.client import BBPOIDCClient
from bbp_client.document_service.access import DocAccess
from bbp_client.document_service.exceptions import DocException


L = logging.getLogger(__name__)

# pylint: disable=W0212


class Client(object):
    '''Interface to the document service via python

        Example:
            >>> #you'll likely need a user for authentication
            >>> user = 'gevaert'
            >>> server = 'http://localhost:8888'
            >>> from bbp_client.oidc.client import BBPOIDCClient
            >>> client = BBPOIDCClient.implicit_auth(user)
            >>> from bbp_client.document_service.client import Client
            >>> handler = Client(server, client)
            >>> handler.walk()
    '''

    def __init__(self, host, oauth_client=None, headers=None):
        '''
        Args:
           host: host to connnect to, ie: http://localhost:8888
           oauth_client: instance of the bbp_client.oidc.client
           headers: HTTP headers passed to server
        '''
        self._cwd = '/'  # means that we're at the top level
        self._access = DocAccess(host, oauth_client, headers)

    @classmethod
    def new(cls, environment='prod', user=None, password=None, token=None):
        '''create new documentservice client'''
        services = get_services()
        oauth_url = services['oidc_service'][environment]['url']
        ds_url = services['document_service'][environment]['url']
        if token:
            oauth_client = BBPOIDCClient.bearer_auth(oauth_url, token)
        else:
            oauth_client = BBPOIDCClient.implicit_auth(user, password, oauth_url)
        return cls(ds_url, oauth_client)

    @sh.swagger_error
    def exists(self, path):
        '''check if path exists, can be a project/directory or file
        '''
        return self._access.exists(path)

    def _norm_path(self, path=None):
        '''returns a normalized path'''
        path = str(path)  # convert from unicode, potentially
        if path:
            ret = os.path.normpath(joinp(self._cwd, path))
        else:
            ret = self._cwd
        return ret

    ######### os.* like functions ##########
    @sh.swagger_error
    def getcwd(self):
        '''Return a string representing the current working directory'''
        return self._cwd

    @sh.swagger_error
    def chdir(self, path):
        '''Change the current working directory to path

           raises DocException if the path doesn't exist
        '''
        path = self._norm_path(path)
        while path.startswith('..'):
            self._cwd = self._cwd.rsplit('/', 1)[0]
            if not self._cwd:  # trying to traverse past root
                self._cwd = '/'
            head, path = os.path.split(path)
            #print 'head "%s" path "%s' % (head, path)
            if not head:
                break

        #print 'path after: "%s", cwd: "%s"' % (path, self._cwd)

        if not path or '..' == path:
            return

        norm_path = self._norm_path(path)
        L.debug("chdir: %s, normalized: %s", path, norm_path)
        try:
            if self._access.exists(norm_path):
                self._cwd = norm_path
            else:
                raise DocException('directory does not exist')
        except KeyError:
            raise DocException('directory does not exist')

    @sh.swagger_error
    def listdir(self, path=None):
        '''Return a list containing the names of the entries in the
           directory given by path. The list is in arbitrary order.

           if no path is given, starts at root (ie: all projects)
        '''
        path = path or '/'
        norm_path = self._norm_path(path)
        return self._access.listdir(norm_path)

    @sh.swagger_error
    def mkdir(self, path=None, ignore_error=False):
        '''Create a directory named path'''
        norm_path = self._norm_path(path)
        return self._access.mkdir(norm_path, ignore_error)

    @sh.swagger_error
    def makedirs(self, path):
        '''Recursive directory creation function'''
        norm_path = self._norm_path(path)
        L.debug('makedirs %s', path)
        split_path = norm_path.split('/')
        assert(not split_path[0])
        prev = joinp('/', split_path[1])
        self.mkdir(prev, ignore_error=True)
        for p in split_path[2:]:
            prev = joinp(prev, p)
            self.mkdir(prev, ignore_error=True)

    @sh.swagger_error
    def remove(self, path):
        '''Remove (delete) the file path'''
        norm_path = self._norm_path(path)
        self._access.remove(norm_path)

    @sh.swagger_error
    def rename(self, src, dst):
        '''Rename the file or directory src to dst'''
        norm_src = self._norm_path(src)
        norm_dst = self._norm_path(dst)
        return self._access.rename(norm_src, norm_dst)

    @sh.swagger_error
    def rmdir(self, path, force=False):
        '''Remove (delete) the directory path'''
        norm_path = self._norm_path(path)
        self._access.rmdir(norm_path, force)

    @sh.swagger_error
    def walk(self, path=None):
        '''For each directory in the tree rooted at cwd (including top itself),
           it yields a 3-tuple (dirpath, dirnames, filenames).
        '''
        norm_path = self._norm_path(path or self._cwd)
        return self._access.walk(norm_path)

    ######### specialized functions ##########
    @sh.swagger_error
    def upload_file(self, src_path, dst_path, mimetype=None, st_attr=None):
        '''upload a file from the local file system to a directory

            Returns: uuid of created entity
        '''
        if not os.path.isfile(src_path):
            raise OSError('Source path does not exist: %s' % src_path)
        dst_path = self._norm_path(dst_path)
        return self._access.upload_file(src_path, dst_path, mimetype, st_attr)

    @sh.swagger_error
    def upload_string(self, _str, dst, mimetype=None, st_attr=None):
        '''upload a string supplied string to document service

            Returns: uuid of created entity
        '''
        return self._access.upload_string(_str, str(dst), mimetype, st_attr)

    @sh.swagger_error
    def download_file(self, path, dst_path=None):
        '''download file

            Args:
                path: the path to the file entity
                dst_path: the path to store the downloaded contents

            Returns:
                path to the file if dst_path was provided
                contents of the file as a string otherwise
        '''
        norm_path = self._norm_path(path)
        return self._access.download_file(norm_path, dst_path)

    @sh.swagger_error
    def download_file_by_id(self, _id, dst_path=None):
        '''download file

            Args:
                id(string): the id of the file entity
                dst_path: the path to store the downloaded contents

            Returns:
                path to the file if dst_path was provided
                contents of the file as a string otherwise
        '''
        return self._access.download_file_by_id(_id, dst_path)

    @sh.swagger_error
    def create_external_link(self, external_path, dst_path, st_attr=None):
        '''create external link to the file

            Args:
                external_path: path like /gpfs/bbp.epfl.ch/...
                dst_path: the path in document server
                st_attr: optional standard attributes

            Returns: uuid of created entity
        '''
        dst = self._norm_path(dst_path)
        return self._access.create_external_link(external_path, dst, st_attr)

    @sh.swagger_error
    def bulk_create_external_links(self, files, dst_folder):
        '''creates external link to file

            Args:
                files(dict): a dictionary of dst_name -> properties
                    where properties must be a dictionary containing content_type and external_path
                    example:
                    {'txt1': {'content_type': 'text/plain', 'external_path': '/gpfs/txt1'},
                     'txt2': ...
                    }
                dst_folder(string): on the server

            Returns: dictionary of dst_name -> uuid
        '''
        dst = self._norm_path(dst_folder)
        return self._access.bulk_create_external_links(files, dst)

    @sh.swagger_error
    def get_external_link_path_by_id(self, uuid):
        '''get the path to an external link.

        Args:
            uuid: The UUID of the ducument service entity.
        Returns:

            A path to the external link.
        '''
        doc_attrs = self.get_standard_attr_by_id(uuid)
        return doc_attrs._contentUri

    @sh.swagger_error
    def get_standard_attr(self, path):
        '''get the standard attributes of the path
           https://bbpteam.epfl.ch/project/spaces/display/BBPWFA/Document+Service+REST+API+Draft+3#DocumentServiceRESTAPIDraft3-StandardAttributesandMetadata # pylint: disable=C0301 # nopep8

            Args:
                path: the path to the entity

            Returns:
                Dictionary with all standard attributes
        '''
        norm_path = self._norm_path(path)
        return self._access.get_standard_attr(norm_path)

    @sh.swagger_error
    def set_standard_attr(self, path, attr_dict):
        '''set the standard attributes of the path'''
        norm_path = self._norm_path(path)
        return self._access.set_standard_attr(norm_path, attr_dict)

    @sh.swagger_error
    def get_standard_attr_by_id(self, _id):
        '''get the standard attributes of the entity'''
        return self._access.get_standard_attr_by_id(_id)

    @sh.swagger_error
    def set_standard_attr_by_id(self, _id, attr_dict):
        '''set the standard attributes of the entity'''
        return self._access.set_standard_attr_by_id(_id, attr_dict)

    @sh.swagger_error
    def get_metadata(self, path):
        '''get the metadata of the path

            Args:
                path: the path to the entity

            Returns:
                Dictionary with all meta attributes
        '''
        norm_path = self._norm_path(path)
        return self._access.get_metadata(norm_path)

    @sh.swagger_error
    def get_metadata_by_id(self, _id):
        '''get the metadata of the id

            Args:
                id: the id of the entity

            Returns:
                Dictionary with all meta attributes
        '''
        return self._access.get_metadata_by_id(_id)

    @sh.swagger_error
    def set_metadata(self, path, metadata_dict):
        '''set the metadata of the path

            Args:
                path: the path to the entity
                metadata_dict: dictionary of key/values to set
        '''
        norm_path = self._norm_path(path)
        return self._access.set_metadata(norm_path, metadata_dict)

    @sh.swagger_error
    def set_metadata_by_id(self, _id, metadata_dict):
        '''set the metadata of an id

            Args:
                id: the uuid of the entity
                metadata_dict: dictionary of key/values to set
        '''
        return self._access.set_metadata_by_id(_id, metadata_dict)

    @sh.swagger_error
    def reset_cache(self):
        '''reset the directory cache'''
        self._access.reset_cache()

    @sh.swagger_error
    def __repr__(self):
        return repr(self._access)

    def get_path_by_id(self, _id):
        '''returns a path on the DS from the uuid of an existing object'''
        attr = self.get_standard_attr_by_id(_id)
        if attr._parent == 'None':
            return '/' + attr._name
        else:
            return joinp(self.get_path_by_id(attr._parent), attr._name)

    @sh.swagger_error
    def get_project_by_collab_id(self, collab_id):
        '''return project managed by collab'''
        projects = self._access.filter_projects('managed_by_collab=%s' % collab_id)
        if len(projects) > 1:
            raise DocException('More than one project exists for collab %s' % collab_id)
        if projects:
            return dict((n, getattr(projects[0], n)) for n in
                        projects[0].swaggerTypes.keys())
        return None
