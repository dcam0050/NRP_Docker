'''the access module of the document service client'''
import copy
import json
import os

from os.path import join as joinp
from urllib2 import HTTPError

import requests

from bbp_client import swagger_helpers as sh
from bbp_client.document_service.swagger import swagger, ProjectApi, FolderApi, FileApi, EntityApi
from bbp_client.document_service.swagger.models import ProjectPostJson, FolderPostJson, \
    FilePostJson, EntityReturn
from bbp_client.document_service.exceptions import DocException
from bbp_services.client import get_services

#W0212: the document service standard attributes start with _
# pylint: disable=W0212

import logging
L = logging.getLogger(__name__)


class DocAccess(object):
    '''Access to the doc. server'''
    class RootEntity(object):
        '''make the root entity have properies like a normal entity'''
        ROOT_SENTINEL = Ellipsis
        _entityType = 'root'
        _name = '/'
        _uuid = ROOT_SENTINEL
        swaggerTypes = {'_entityType': 'str',
                        '_name': 'str',
                        '_uuid': 'str',
                        }

    def __init__(self, host, oauth_client=None, headers=None):
        service = get_services()['document_service']
        if host in service:
            self.host = service[host]['url']
        else:
            self.host = host or service['prod']['url']
        L.debug('Using document_service url: %s', self.host)

        self._api = swagger.ApiClient('api_key', self.host)

        #save the oauth_client in case we need to refresh the token (not implemented yet)
        self.oauth_client = oauth_client
        self.headers = headers or {}

        sh.patch_swagger_callapi(self._api, self._get_headers)

        if self.oauth_client:
            self.headers['Authorization'] = self.oauth_client.get_auth_header()
        self.headers['User-Agent'] = 'py_document_service_client'

        #api accessors
        self._project = ProjectApi.ProjectApi(self._api)
        self._project.update = ProjectApi.ProjectApi.update_project
        self._folder = FolderApi.FolderApi(self._api)
        self._folder.update = FolderApi.FolderApi.update_folder
        self._file = FileApi.FileApi(self._api)
        self._file.update = FileApi.FileApi.update_file
        self._entity = EntityApi.EntityApi(self._api)

    def _get_headers(self):
        '''return the headers required for the http call'''
        #TODO, when to do oauth_client refresh?
        #self.oauth_client.refresh()
        return self.headers

    @staticmethod
    def _get_full_list(operation, args):
        '''helper to get list of entities if there are more then one page
            Args:
                operation: API operation which returns EntityReturnList
                args: dict with arguments for operation call
        '''
        ret = operation(**args)
        lst = ret.result
        while ret.hasMore:
            args['from'] = lst[-1]._uuid
            ret = operation(**args)
            if len(ret.result) > 1:
                lst.extend(ret.result[1:])
        return lst

    def reset_cache(self):
        '''hook method to reset the cache'''
        pass

    def _add_to_cache(self, base, entities):
        '''hook method for cache'''
        pass

    def _remove_from_cache(self, base):
        '''hook method for cache'''
        pass

    def _get_children(self, entity):
        '''get the contents of a folder/project from the server'''
        if self.isroot(entity):
            children = DocAccess._get_full_list(self._project.get_all_projects, {})
        elif self.isproject(entity):
            children = DocAccess._get_full_list(self._project.get_entity_children,
                                                {'uuid': entity._uuid})
        elif self.isfolder(entity):
            children = DocAccess._get_full_list(self._folder.get_entity_children,
                                                {'uuid': entity._uuid})
        elif self.isfile(entity):
            raise DocException('file has no children')
        else:
            raise DocException('Received unknown type from server: %s' %
                               entity._entityType)

        self._add_to_cache(entity, children)

        return children

    def _get_entity_accessor(self, entity):
        '''given an entity, return self._{entity_type} obj'''
        if self.isproject(entity):
            obj = self._project
        elif self.isfolder(entity):
            obj = self._folder
        else:
            assert self.isfile(entity)
            obj = self._file
        return obj

    def _get_entity_by_path(self, path):
        '''returns the entity from the server, based on its path

        Returns:
            Entity, if found, None otherwise
        '''
        assert path.startswith('/')

        if path is '/':
            return DocAccess.RootEntity()

        LOOKUP_URI = 'entity/'
        headers = copy.copy(self._get_headers())

        resp = requests.get(joinp(self.host, LOOKUP_URI), headers=headers,
                            params={'path': path})
        if 200 != resp.status_code:
            return None

        response_obj = json.loads(resp.text)
        entity = self._api.deserialize(response_obj, EntityReturn.EntityReturn)
        return entity

    def _get_parent(self, path):
        '''gets the parent entity of path

        _get_parent('/foo/bar/bin') would return the entity for '/foo/bar'
        '''
        parent_path = os.path.dirname(path)
        parent = self._get_entity_by_path(parent_path)
        if parent is None:
            raise OSError('Path does not exist: %s' % path)
        L.debug('parent of %s: (%s:%s)', path, parent._name, parent._uuid)
        return parent

    def exists(self, path):
        '''check if path exists, can be a project/directory or file
        '''
        #root path always exists
        if '/' == path:
            return True

        return bool(self._get_entity_by_path(path))

    def listdir(self, path):
        '''list contents of a path, analagous to os.listdir'''
        entity = self._get_entity_by_path(path)
        if entity is None:
            raise OSError('Path does not exist: %s' % path)

        if self.isfile(entity):
            raise OSError('Not a directory: %s' % path)

        children = self._get_children(entity)

        return [c._name for c in children]

    def rmdir(self, path, force=False):
        '''rmdir, analagous to os.rmdir'''
        entity = self._get_entity_by_path(path)
        if entity is None:
            raise OSError('Path does not exist: %s' % path)

        if not self.iscontainer(entity):
            raise OSError('can only remove directories and projects')
        if not force:
            if self._get_children(entity):
                raise OSError('directory must be empty before deletion')

        if self.isproject(entity):
            self._project.delete_project(entity._uuid)
        elif self.isfolder(entity):
            self._folder.delete_folder(entity._uuid)

    def mkdir(self, path, ignore_error=False):
        '''mkdir, analagous to os.mkdir'''
        parent = self._get_parent(path)
        if self.isfile(parent):
            raise TypeError('file with this name already exists')

        name = os.path.basename(path)
        try:
            if self.isroot(parent):
                body = sh.swagger_create_type(ProjectPostJson.ProjectPostJson, {'_name': name})
                entity = self._project.create_project(body)
            elif self.iscontainer(parent):
                body = sh.swagger_create_type(FolderPostJson.FolderPostJson,
                                              {'_name': name,
                                               '_parent': parent._uuid,
                                               })
                entity = self._folder.create_folder(body)
        except HTTPError:
            if ignore_error:
                return None
            else:
                raise OSError('directory already exists')

        self._add_to_cache(parent, (entity, ))

        return entity._uuid

    def create_external_link(self, external_path, dst, st_attr, mimetype=None):
        '''creates external link to file

            Args:
                external_path(string): path to file like /gpfs/bbp.epfl.ch/...
                dst(string path): on the server, including the
                    /project/folder/...folders/file
                st_attr(dict): standard attributes
                mimetype(str): target mimetype

            Returns: uuid of created entity
        '''
        parent, entity = self._create_placeholder(dst, mimetype, st_attr,
                                                  extra_attr={'_contentUri': external_path})

        #add entity to cache, since everything was succesful
        self._add_to_cache(parent, (entity, ))

        return entity._uuid

    def rename(self, src, dst):
        '''rename project/dir/file, analagous to os.rename'''
        if src.rsplit('/', 1)[0] != dst.rsplit('/', 1)[0]:
            raise DocException('can only rename the last level of the path')

        entity = self._get_entity_by_path(src)
        if entity is None:
            raise OSError('Path does not exist: %s' % src)
        _uuid = entity._uuid

        body = copy.copy(entity)

        name = dst.rsplit('/', 1)[1]
        body._name = name
        parent = body._parent

        del body._createdOn
        del body._uuid
        del body._entityType
        del body._createdBy
        del body._contentUri
        del body._contentType
        del body._description

        if self.isproject(entity):
            del body._parent
            body._name = body._name.lstrip('/')
            self._project.update_project(_uuid, body)
        elif self.isfolder(entity):
            self._folder.update_folder(_uuid, body)
        elif self.isfile(entity):
            self._file.update_file(_uuid, body)
        else:
            raise DocException('Cannot rename %s' % entity._entityType)

        entity._name = name
        self._remove_from_cache(entity)
        self._add_to_cache(parent, (entity, ))

    def remove(self, path):
        '''remove file, analagous to os.remove'''
        entity = self._get_entity_by_path(path)
        if entity is None:
            raise OSError('Path does not exist: %s' % path)

        if not self.isfile(entity):
            raise OSError('can only delete files')

        self._file.delete_file(entity._uuid)
        self._remove_from_cache(entity)

    def walk(self, path='/'):
        '''walk the filesystem, analagous to os.walk'''
        entity = self._get_entity_by_path(path)
        if entity is None:
            raise OSError('Path does not exist: %s' % path)
        if not entity or self.isfile(entity):
            yield []
        elif self.iscontainer(entity) or self.isroot(entity):
            dirs, nondirs = [], []
            children = self._get_children(entity)
            for entity in children:
                if self.iscontainer(entity):
                    dirs.append(entity._name)
                else:
                    nondirs.append(entity._name)
            yield (path, dirs, nondirs)
            for name in dirs:
                new_path = joinp(path, name)
                for x in self.walk(new_path):
                    yield x

    def download_file(self, src_path, dst_path=None):
        '''download a file from the server

            Args:
                path: the path to the file entity
                dst_path: the path to store the downloaded contents

            Returns:
                path to the file if dst_path was provided
                contents of the file as a string otherwise
        '''
        entity = self._get_entity_by_path(src_path)
        if entity is None:
            raise OSError('Path does not exist: %s' % src_path)
        return self.download_file_by_id(entity._uuid, dst_path)

    def download_file_by_id(self, _id, dst_path=None):
        '''download a file from the server

            Args:
                id(string): the id of the file entity
                dst_path: the path to store the downloaded contents

            Returns:
                path to the file if dst_path was provided
                contents of the file as a string otherwise
        '''
        content_url = joinp(self.host, 'file', _id, 'content/download')
        resp = requests.get(content_url, headers=self._get_headers())
        if 200 != resp.status_code:
            raise DocException('Could not download file (%s): %s' % (resp.status_code, resp.text))

        if dst_path:
            CHUNK_SIZE = 10 * 1024
            with open(dst_path, 'wb') as f:
                for chunk in resp.iter_content(CHUNK_SIZE):
                    f.write(chunk)
            return dst_path
        else:
            return resp.text

    def upload_file(self, src, dst, mimetype, st_attr):
        '''upload a file to the server'''
        with open(src) as fd:
            return self._upload_content(fd, dst, mimetype, st_attr)

    def upload_string(self, _str, dst, mimetype, st_attr):
        '''upload a string to the server'''
        return self._upload_content(_str, dst, mimetype, st_attr)

    def _create_placeholder(self, dst, mimetype, st_attr, extra_attr=None):
        '''creates a placeholder'''
        #TODO: Do we allow overwriting of files?
        #if self._get_entity_by_path(dst) is not None:
        #    raise OSError('Cannot overwrite a directory that already exists')

        parent = self._get_parent(dst)
        dst_name = os.path.basename(dst)

        # create placeholder
        props = st_attr if st_attr else {}
        props.update({'_name': dst_name,
                      '_parent': parent._uuid,
                      })
        if extra_attr:
            props.update(extra_attr)

        if mimetype is not None:
            props['_contentType'] = str(mimetype)

        body = sh.swagger_create_type(FilePostJson.FilePostJson, props)
        entity = self._file.create_file(body)
        return parent, entity

    def _upload_content(self, content, dst, mimetype, st_attr):
        '''upload the content

            Args:
                content(string or open file): follows the same conventions
                    as HTTPConnection.request
                dst(string path): on the server, including the
                    /project/folder/...folders/file
                mimetype(str): set the _contentType property to this mimetype
                st_attr(dict): standard attributes

            Returns: uuid of created entity
        '''
        parent, entity = self._create_placeholder(dst, mimetype, st_attr)

        content_url = joinp(self.host, 'file', entity._uuid, 'content/upload')
        headers = copy.copy(self._get_headers())

        resp = requests.post(content_url, headers=headers, data=content)
        if 201 != resp.status_code:
            raise DocException('Could not upload file (%s): %s' % (resp.status_code, resp.text))

        response_obj = json.loads(resp.text)
        entity = self._api.deserialize(response_obj, EntityReturn.EntityReturn)

        #add entity to cache, since everything was succesful
        self._add_to_cache(parent, (entity, ))

        return entity._uuid

    def get_standard_attr(self, path):
        '''get the standard attributes for a path'''
        entity = self._get_entity_by_path(path)
        if entity is None:
            raise DocException('Path does not exist: %s' % path)
        return dict((n, getattr(entity, n)) for n in
                    entity.swaggerTypes.keys())

    def get_standard_attr_by_id(self, _id):
        '''get the standard attributes for a id
        '''
        return self._entity.get_entity(_id)

    def set_standard_attr(self, path, attr_dict):
        '''set the standard attributes on path'''
        entity = self._get_entity_by_path(path)
        if entity is None:
            raise DocException('Path does not exist: %s' % path)

        return self._set_standard_attr(entity, attr_dict)

    def set_standard_attr_by_id(self, _id, attr_dict):
        '''set the standard attributes by id

        Args:
            ent(EntityReturn): the entity where the lookup happens
        '''
        ent = self.get_standard_attr_by_id(_id)
        return self._set_standard_attr(ent, attr_dict)

    def _set_standard_attr(self, ent, attr_dict):
        '''helper to actually set the standard attributes'''
        if not isinstance(attr_dict, dict):
            raise ValueError('attr_dict must be a dictionary')
        # ensure all values are strings
        attr = dict([(k, str(v)) for k, v in attr_dict.items()])
        obj = self._get_entity_accessor(ent)
        return obj.update(obj, ent._uuid, attr)

    def get_metadata(self, path):
        '''get the metadata for a path'''
        entity = self._get_entity_by_path(path)
        if entity is None:
            raise DocException('Path does not exist: %s' % path)
        return self._get_metadata(entity)

    def get_metadata_by_id(self, _id):
        '''get the metadata by id'''
        ent = self.get_standard_attr_by_id(_id)
        return self._get_metadata(ent)

    def _get_metadata(self, ent):
        '''helper to actually get the metadata

        Args:
            ent(EntityReturn): the entity where the lookup happens
        '''
        obj = self._get_entity_accessor(ent)
        json_meta = obj.get_metadata(ent._uuid)
        return json_meta or dict() # json_meta may be None, always give a dict back

    def set_metadata(self, path, metadata_dict):
        '''set the metadata on path'''
        entity = self._get_entity_by_path(path)
        if entity is None:
            raise DocException('Path does not exist: %s' % path)

        return self._set_metadata(entity, metadata_dict)

    def set_metadata_by_id(self, _id, metadata_dict):
        '''set the metadata by id

        Args:
            ent(EntityReturn): the entity where the lookup happens
        '''
        ent = self.get_standard_attr_by_id(_id)
        return self._set_metadata(ent, metadata_dict)

    def _set_metadata(self, ent, metadata_dict):
        '''helper to actually set the metadata'''
        if not isinstance(metadata_dict, dict):
            raise ValueError('metadata_dict must be a dictionary')
        # ensure all values are strings
        metadata = dict([(k, str(v)) for k, v in metadata_dict.items()])
        obj = self._get_entity_accessor(ent)
        json_meta = obj.add_metadata(ent._uuid, metadata)
        return json_meta

    @staticmethod
    def isfile(entity):
        '''is file'''
        return 'file' == entity._entityType

    @staticmethod
    def isproject(entity):
        '''is project'''
        return 'project' == entity._entityType

    @staticmethod
    def isfolder(entity):
        '''is folder'''
        return 'folder' == entity._entityType

    @staticmethod
    def iscontainer(entity):
        '''is project or is folder'''
        return entity._entityType in ('project', 'folder')

    @staticmethod
    def isroot(entity):
        '''is it the root entity'''
        return 'root' == entity._entityType

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
        # TODO: apply swagger bindings to server endpoint so this can be auto genegerated
        parent = self.get_standard_attr(dst_folder)['_uuid']

        post_data = [dict(
            _parent=parent,
            _contentType=f['content_type'],
            _description='',
            _entityType='file',
            _contentUri=f['external_path'],
            _name=name) for name, f in files.items()]

        ret = self._file.apiClient.callAPI(
            '/bulkfile/', 'POST', [],
            post_data,
            self._get_headers())

        return ret

    def filter_projects(self, filter_expr):
        '''return filtered list of projects

            Args:
                filter_expr: filter expression like _name=my_project

            Returns: list of EntityReturn
        '''
        return self._project.get_all_projects(filter=filter_expr).result
