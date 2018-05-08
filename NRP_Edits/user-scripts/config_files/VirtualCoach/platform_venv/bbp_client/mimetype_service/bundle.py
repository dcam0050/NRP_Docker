'''Bundles are groups of files as specified in:
https://bbpteam.epfl.ch/project/spaces/display/BBPWFA/Bundle+Specification

This package helps in creation, manipulation, and checking correctness of bundles
'''

import copy
import fnmatch
import json
import os


def get_bundle_spec(client, bundle_spec_name):
    '''get the bundle spec from the MIMEType Service

    Args:
        client(bbp_client.mimetype_service.client): client to connect to
        bundle_spec_name(str): name of the MimeType that is a bundle

    Returns:
        dict that is a bundle specification, conforming to the meta-specification

    Example:
        >>> server = 'http://localhost:8888'
        >>> from bbp_client.mimetype_service.client import Client
        >>> ms = Client(server, client)
        >>> bundle_type = 'application/vnd.bbp.bundle.demo'
        >>> spec = get_bundle_spec(ms, bundle_type)

    '''
    mimetype = client.find_mimetype(mimetype=bundle_spec_name)
    spec = mimetype.get_key('bundleTypeSpec')
    spec = json.loads(spec.value)
    spec = _norm_bundle_spec_structure(bundle_spec=spec, client=client)
    return spec


def _check_mimetype(client, mimetype):
    '''check if the mimetype is valid, if no client is specified returns True'''
    if client:
        mimetype_results = client.find_mimetype(mimetype)
        if not mimetype_results:
            raise ValueError('Cannot find "%s" mimetype on server, is it registered?' % mimetype)

    return True


def _validate_bundle_structure(bundle):
    '''validate that a bundle is correctly structured

    Args:
        bundle(dict): dictionary matching bundle specification

    Returns:
        copy of bundle that can be modified
    '''
    for k in ('type', 'bundleType', 'content'):
        if k not in bundle:
            raise ValueError('Invalid bundle spec, missing "%s" key' % k)

    if 'bundle' != bundle['type']:
        raise ValueError('Invalid bundle, type is "%s" instead of "bundle"' % bundle['type'])

    ret = copy.deepcopy(bundle)

    content = ret['content']
    for path, ids in content.items():
        if path.endswith('/') and not isinstance(ids, list):
            raise ValueError('Invalid bundle, path %s is a directory its ids are not a list' % path)
        elif not path.endswith('/') and isinstance(ids, list):
            raise ValueError('Invalid bundle, path %s is a file and its ids are a list' % path)

    return ret


def _norm_bundle_spec_structure(bundle_spec, client=None): # pylint: disable=R0912
    '''normalize a bundle specification, also does some validation of the structure

    Args:
        bundle_spec(str): string of json containing the bundle specification
        client(bbp_client.mimetype_service.client): client to connect to,
            if not specified, MimeTypes are not check for validity with the MimeType Service

    Returns:
        True if valid bundle

    Raises:
        ValueError if invalid bundle

    Notes:
        'Normalized' means that
        * each content value has an associated dict, ie:
            '/gul/baz':  'application/json' -> '/gul/baz': {'type': application/json,
                                                            'count': range(1)
                                                            }
        * count is converted to an array describing a half-open range.  'Inf' is
          used to distinguish Infity.  Note that this is using the fact that python
          orders integers below strings: 10**100 < 'Inf' == True
    '''
    for k in ('type', 'bundleType', 'content'):
        if k not in bundle_spec:
            raise ValueError('Invalid bundle spec, missing "%s" key' % k)

    if 'bundleTypeSpec' != bundle_spec['type']:
        raise ValueError('Invalid bundle spec, type is "%s" instead of "bundleTypeSpec"' %
                         bundle_spec['type'])

    #bundle_spec gets modified, so don't want to change the caller's version
    ret = copy.deepcopy(bundle_spec)
    content = ret['content']
    for path, meta in content.items():
        if isinstance(meta, dict):
            for expected_prop in ('type', 'count'):
                if expected_prop not in meta:
                    raise ValueError(
                        'Invalid bundle spec, content type "%s" is missing property %s' %
                        (meta, expected_prop))

            _check_mimetype(client, meta['type'])

            # make sure count is valid
            count = meta['count']
            err = None
            if isinstance(count, list):
                if 2 != len(count):
                    err = 'Invalid bundle spec, range must have two numbers: %s' % count
                elif count[0] > count[1]:
                    err = 'Invalid bundle spec, range must start low and end high: %s' % count
            elif isinstance(count, basestring):
                if '*' == count:
                    content[path]['count'] = [0, 'Inf']
                elif '+' == count:
                    content[path]['count'] = [1, 'Inf']
                else:
                    err = 'Invalid bundle spec, count must be either * or +'
            elif isinstance(count, (int, long)):
                content[path]['count'] = [count, count + 1]
            else:
                err = ('Invalid bundle spec, count is not a valid type: %s (%s)' %
                       (type(count), count))

            if err:
                raise ValueError(err)
        else:
            _check_mimetype(client, meta)

            content[path] = {
                'type': meta,
                'count': [1, 2]
            }

    return ret


def validate_bundle_from_spec(bundle, bundle_spec):
    '''make sure bundle contents match bundle metadata

    Args:
        bundle(dict): contents of a bundle file, already deserialized
        bundle_spec(spec): a valid bundle spec, if None, client will attempt to get
            it from the MIMEType Service specified by client

    Returns:
        True if bundle is valid

    Raises:
        ValueError if the bundle isn't valid JSON, or if bundle isn't a bundle, or
                   bundle_spec isn't a bundle_spec

    '''
    bundle = _validate_bundle_structure(bundle)
    norm_bundle_spec = _norm_bundle_spec_structure(bundle_spec)

    content = norm_bundle_spec['content']

    for path, ids in bundle['content'].items():
        #remove the non-glob paths, this is the simple case
        if path in content:
            if path.endswith('/'):
                id_count = len(ids)
            else:
                id_count = 1

            if content[path]['count'][0] <= id_count < content[path]['count'][1]:
                del content[path]
                del bundle['content'][path]

    paths_left = set(bundle['content'].keys())
    #norm_bundle_spec should now only contain paths that contain globs, now we have
    #to find the best matches in the bundle
    for path, meta in content.items():
        if not path.endswith('*'):
            raise ValueError('Path: %s does not contain the correct amount of files: [%d-%d)' %
                             (path, meta['count'][0], meta['count'][1]))
        matches = set(fnmatch.filter(paths_left, path))
        if content[path]['count'][0] <= len(matches) < content[path]['count'][1]:
            del content[path]
            paths_left -= matches

    if content:
        raise ValueError('These bundle paths were not satisfied: \n%s' %
                         '\t\n'.join(['%s: [%s-%s)' % (k, v['count'][0], v['count'][1])
                                      for k, v in content.items()]))

    return True


def validate_bundle(bundle, client):
    '''make sure bundle contents match bundle metadata

    Args:
        bundle(dict): contents of a bundle file, already deserialized
        client(bbp_client.mimetype_service.client): client to connect to


    Returns:
        True if bundle is valid

    Raises:
        ValueError if the bundle isn't valid JSON, or if bundle isn't a bundle, or
                   bundle_spec isn't a bundle_spec

    Example:
        >>> server = 'http://localhost:8888'
        >>> from bbp_client.mimetype_service.client import Client
        >>> ms = Client(server, client)
        ... # create bundle
        >>> validate_bundle(bundle, ms)
    '''
    bundle_spec = get_bundle_spec(client=client,
                                  bundle_spec_name=bundle['bundleType'])
    return validate_bundle_from_spec(bundle, bundle_spec)


class CreateBundle(object):
    '''An object that represents a bundle under construction'''

    def __init__(self, bundle_type):
        '''
        Args:
            bundle_type(str): a MimeType that is a bundle
        '''

        self.bundle_type = bundle_type
        self._content = {}

    def create_structure(self):
        '''create structure that's useful for serializing'''
        structure = {
            'type': 'bundle',
            'bundleType': self.bundle_type,
            'content': self._content
        }
        return structure

    def register_file(self, bundle_path, uri):
        '''adds a file to a bundle

        Args:
            bundle_path(str): path within the bundle where the file will be
                              placed
            uri(URI): URI of the file

        Note: Does *not* check that the file's mimetype matches the schema of
              the bundle at the specified path
        '''
        bundle_path = os.path.join('/', bundle_path)
        if bundle_path.endswith('/'):
            file_list = self._content.get(bundle_path, [])
            file_list.append(uri.document)
            self._content[bundle_path] = file_list
        else:
            self._content[bundle_path] = uri.document

    def serialize(self):
        '''return JSON serialized version of bundle, suitable for writing'''
        return json.dumps(self.create_structure())

    def __str__(self):
        '''create string'''
        from pprint import pformat
        ret = 'Bundle of type %s\nContaining:\n' % self.bundle_type
        ret += pformat(self._content)
        return ret
