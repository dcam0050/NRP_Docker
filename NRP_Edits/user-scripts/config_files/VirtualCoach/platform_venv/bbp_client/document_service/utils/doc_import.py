'''script to import files from a local directory as external links to DS'''

import argparse
import logging
import mimetypes
import os
import sys
import yaml

from collections import namedtuple
from os.path import join as joinp
from urllib2 import HTTPError

from bbp_services.client import get_services, get_environment_aliases

from bbp_client.client import DEFAULT_LOG_FORMAT
from bbp_client.swagger_helpers import SwaggerException
from bbp_client.oidc.client import BBPOIDCClient
from bbp_client.document_service.client import Client as DSClient
from bbp_client.document_service.client import DocException

L = logging.getLogger(__name__)
VERBOSITY_LEVELS = (logging.WARNING, logging.INFO, logging.DEBUG)


ImportReturn = namedtuple('ImportReturn', 'src dst content_type uuid new')

EXAMPLE_YAML = '''\
path: /gpfs/bbp.cscs.ch/project/proj30/post_sim_wf/Ca1p5_1/BlueConfig
portal_path: /workflow_test/simulations/Ca1p5_1/BlueConfig
contentType: application/vnd.bbp.Simulation.BlueConfig
description: |
  This lives in cscs
'''


class ImportInfo(object):
    '''Encapsulates the information regarding an import of a folder or file
    to the document service.'''

    # entity type enum
    FILE = 1
    FOLDER = 2

    def __init__(self, src, dst, entity_type, standard_attr=None, metadata=None,
                 upload=False):
        '''information about a new entity to import'''
        L.info('%s -> %s', src, dst)
        self.entity_type = entity_type
        self.src = src
        self.dst = dst
        self.standard_attr = standard_attr or {}
        self.standard_attr['_description'] = \
            self.standard_attr.get('_description', 'automatically added by doc_import')
        self.metadata = metadata or {}
        self.upload = upload

    def do_import(self, client):
        '''Perform the import

        This may mean creating a remote folder, uploading a file's contents
        or registering a file as an external link. It may also push metadata
        or standard attributes to the newly created entity.

        Args:
            client - the DS client to perform the operations on

        Returns:
            uuid of the newly imported item
        '''

        intermediates = os.path.dirname(self.dst)
        client.makedirs(intermediates)

        if self.entity_type == ImportInfo.FILE:
            if self.upload:
                if '_contentType' not in self.standard_attr:
                    raise ValueError('No _contentType known for file "%s"' % self.src)

                uuid = client.upload_file(self.src, self.dst,
                                          self.standard_attr['_contentType'],
                                          self.standard_attr)
            else:
                uuid = client.create_external_link(self.src, self.dst,
                                                   self.standard_attr)
        else:
            assert self.entity_type == ImportInfo.FOLDER
            uuid = client.mkdir(self.dst)

        if self.metadata:
            client.set_metadata_by_id(uuid, self.metadata)

        return uuid


def viewer_url(hbp_portal_url, ds_path):
    '''given root url to the hbp, construct a unique url to the detail view of a ds object'''
    dst_sections = ds_path.strip('/').split(os.path.sep)
    project, rest = dst_sections[0], joinp(*dst_sections[1:])

    return joinp(hbp_portal_url, '#/projects', project, 'view', rest)


def collect_from_local_fs(root_src, root_dst, upload=False):
    '''recursively explores a local directory and returns a generator that builds objects of type
    ImportInfo representing local folders or files and the desired path of the imported document
    service equivalent
    '''
    if not os.path.exists(root_src):
        raise ValueError("Source path doesn't exist")

    for src, _, files in os.walk(root_src):
        dst = src.replace(root_src, root_dst)
        yield ImportInfo(src, dst, ImportInfo.FOLDER, upload=upload)

        for f in files:
            yield collect_single_file(joinp(src, f), joinp(dst, f),
                                      upload=upload)


def collect_single_file(src, dst, mimetype=None, upload=False):
    '''create an ImportInfo for a single file'''

    if mimetype is None:
        m, _ = mimetypes.guess_type(src)
        L.debug('guessed mime type: %s', m)
        mimetype = m

    standard_attributes = None
    if mimetype is not None:
        standard_attributes = {'_contentType': mimetype}
        L.warning('Ignoring unrecognised mimetype %s', mimetype)

    return ImportInfo(src, dst,
                      entity_type=ImportInfo.FILE,
                      standard_attr=standard_attributes,
                      upload=upload)


def format_register(register):
    '''creates a ImportInfo object from an entry in our human-friendly registry.
    Those look like:
        path: /bgscratch/bbp/l5/release/2012.07.23/circuit/\
        SomatosensoryCxS1-v4.lowerCellDensity.r151/1x7_0/merged_circuit/CircuitConfig
        portal_path: /my_test_project/2012.07.23-SomatosensoryCxS1-v4.lowerCellDensity
        .r151-1x7_0-circuit_config_externlink
        contentType: application/vnd.bbp.Circuit.Config
        force_upload: True  #this is optional, and defaults to False: ie: external-link
        description: |
          Decoupled network
          Ek reversal potential = -57mV
          Mg2+ concentration set to 0.5 mM (default is 1mM)
    '''

    # we allow skipping '_' for some standard attributesa...
    stdattr = ('createdOn', 'modifiedOn', 'createdBy', 'description', 'entityType', 'contentType')

    #...and have human-friendlier aliases for some properties
    field_alias = {'portal_path': '_contentUri', }

    metadata = {}
    attributes = {}

    dst = None
    src = None
    force_upload = False
    ignore_fs_check = False

    for key, value in register.items():
        key = field_alias.get(key, key)
        if key in stdattr:
            key = '_' + key

        if key == '_contentUri':
            dst = value
        elif key == 'path':
            src = value
        elif key == 'force_upload':
            force_upload = value
        elif key == 'ignore_fs_check':  # don't look at FS for file, assume it's a file
            ignore_fs_check = value
        else:
            container = attributes if key.startswith('_') else metadata
            container[key] = value

    if not dst or not src:
        raise ValueError('Incomplete information. Expected at least src and dst, '
                         'got:  %s -> %s' % (src, dst))

    if os.path.isfile(src) or ignore_fs_check:
        entity_type = ImportInfo.FILE

        if '_contentType' not in attributes:
            raise SystemExit(_get_missing_contenttype_msg(src, None))

        #allow for cp like semantics: cp /path/src_file /dst/dir/
        # ie: don't need to specify the src_file name in the dst dir
        if dst.endswith('/'):
            dst = joinp(dst, os.path.basename(src))

    else:
        assert os.path.isdir(src)
        entity_type = ImportInfo.FOLDER

    return ImportInfo(src=src, dst=dst, entity_type=entity_type,
                      standard_attr=attributes, metadata=metadata,
                      upload=force_upload)


def collect_from_registry(src_files):
    '''returns a collection of ImportInfo objects that map local files to
    desired remote document service destinations'''

    for src in src_files:
        if not os.path.exists(src):
            raise ValueError("Source path doesn't exist")

        with open(src) as fd:
            all_registers = yaml.load_all(fd.read())

            for register in all_registers:
                if register:
                    yield format_register(register)


def get_parser():
    '''return the argument parser'''
    parser = argparse.ArgumentParser()
    modes = parser.add_subparsers(dest='subcommand')

    path_mode = modes.add_parser('path')
    path_mode.add_argument('src', help='directory to import')
    path_mode.add_argument('dst', help='path in the document service (/project/folder)')
    path_mode.add_argument('--upload', default=False, action='store_true',
                           help='Upload file contents instead of registering them as '
                                'external links')

    yaml_mode = modes.add_parser('yaml')
    yaml_mode.add_argument('src', nargs='*',
                           help='path to yaml containing all the data to import')

    yaml_mode.add_argument('--ex-yaml', default=False, action='store_true',
                           help='Print example yaml and quit')

    parser.add_argument('-v', '--verbose', action='count', dest='verbose',
                        default=0, help='-v for INFO, -vv for DEBUG')

    parser.add_argument('-e', '--env', default='prod', choices=get_environment_aliases(),
                        help='Environment to login to')

    parser.add_argument('-u', '--user', default=None,
                        help='User to login as')

    parser.add_argument('--return', dest='return_imports', default=False, action='store_true',
                        help='Do not print links, instead return a list: '
                             'Useful for programmatic use.')

    parser.add_argument('--password', default=None, help='Password to log into the document '
                                                         'service. Useful for programmatic use.')

    parser.add_argument('-s', '--server',
                        help='Server where the document service runs. Overrides the env for the ds.'
                             ' Example: http://localhost:8888')

    parser.add_argument('--fail-hard', dest='fail_hard', default=False, action='store_true',
                        help='If an import failed, stop the process (by default log it and carry '
                             'on with the rest)')

    contenttype_group = path_mode.add_mutually_exclusive_group()

    contenttype_group.add_argument(
        '--ignore-type', default=False, action='store_true',
        help='If src is a file indicate that we dont want to set the content type. '
             'Otherwise, a valid mime type must be provided with the option --type. '
             'Has no effect if dst is folder.')

    contenttype_group.add_argument(
        '--type', default=None,
        help='Mime type to store as the content type of the file. Required only if src is a file. '
             'Suppress requirement using --ignore-type.')

    return parser


def _get_missing_contenttype_msg(src, mimetype=None):
    '''returns a human friendly error for missing contentType'''
    return ('Expected valid mime type for %s but got %s.\n'
            'Please use --type with a valid mime type or --ignore-type.' %
            (src, mimetype))


def _handle_import_error(info, e, fail_hard):
    '''handle an exception during  an import according to arguments'''
    msg = 'Failed to import %s -> %s.\nReason: %s' % (info.src, info.dst, e)
    if fail_hard:
        raise e
    else:
        L.error(msg)


def do_single_import(ds_client, info, fail_hard=False):
    '''does a single document import'''
    content_type = info.standard_attr.get('_contentType', None)
    try:
        uuid = info.do_import(ds_client)
        L.info('Imported %s -> %s', info.src, info.dst)
        return ImportReturn(info.src, info.dst, content_type, uuid, True)

    except SwaggerException as e:
        try:
            existing = ds_client.get_standard_attr(info.dst)
            if existing['_contentUri'] == info.src and existing['_contentType'] == content_type:
                L.debug('Link already exists %s -> %s', info.src, info.dst)
                return ImportReturn(info.src, info.dst,
                                    existing['_contentType'], existing['_uuid'], False)
            else:
                _handle_import_error(
                    info,
                    ValueError('Can not create external link %s pointing to %s,'
                               'existing points to %s' % (info.dst, info.src,
                                                          existing['_contentUri'])),
                    fail_hard)

        except DocException:
            _handle_import_error(info, e, fail_hard)

    except (OSError, ValueError, HTTPError, SwaggerException) as e:
        _handle_import_error(info, e, fail_hard)

    return None


def do_import(ds_client, all_info, fail_hard=False):
    '''do import all collected items and return a list of successful imports

    Returns two lists of ImpotReturn objects. The first contains new imports, the second
    of files that have already been imported with matching standard attributes
    '''
    new_imports = []
    existing_imports = []

    for info in all_info:
        i = do_single_import(ds_client, info, fail_hard)

        if i:
            if i.new:
                new_imports.append(i)
            else:
                existing_imports.append(i)

    return new_imports, existing_imports


def main(args=None):
    '''Main function'''
    args = args or sys.argv[1:]
    args = get_parser().parse_args(args)

    if hasattr(args, 'ex_yaml') and args.ex_yaml:
        print EXAMPLE_YAML
        return

    L.debug('Environment: %s Username: %s', args.env, args.user)

    logging.basicConfig(level=VERBOSITY_LEVELS[min(args.verbose, len(VERBOSITY_LEVELS) - 1)],
                        format=DEFAULT_LOG_FORMAT)

    if args.subcommand == 'path':
        if os.path.isfile(args.src):
            if args.type is not None or args.ignore_type:
                all_info = [collect_single_file(args.src, args.dst, args.type, args.upload)]
            else:
                raise SystemExit(_get_missing_contenttype_msg(args.src, args.type))
        else:
            all_info = collect_from_local_fs(args.src, args.dst, args.upload)

    else:
        assert args.subcommand == 'yaml'
        if not args.src:
            raise SystemExit('Must supply at least one yaml file to import')
        all_info = collect_from_registry(args.src)

    oidc_client = BBPOIDCClient.implicit_auth(user=args.user, password=args.password,
                                              oauth_url=args.env)
    ds_server = args.server or args.env
    ds_client = DSClient(ds_server, oidc_client)

    services = get_services()
    hbp_portal_url = services['hbp_portal'][args.env]['url']

    new_imports, _ = do_import(ds_client, all_info, args.fail_hard)

    if not args.return_imports:
        for i in new_imports:
            print 'Link:', viewer_url(hbp_portal_url, i.dst)
        print 'imported', len(new_imports), 'items'
    else:
        return new_imports
