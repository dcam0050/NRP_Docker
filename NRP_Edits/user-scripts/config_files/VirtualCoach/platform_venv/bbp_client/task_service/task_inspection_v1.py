'''utilities to extract information from a local task'''

import re
import yaml
import yaml.resolver
from collections import OrderedDict
from task_types.serialization import object_from_string_call
from task_types import TaskTypes as tt
from task_types.MimeTypes import get_mimetype

from bbp_client.task_service.task_inspection import VersionError
from task_types import TaskOps as to
from bbp_client.task_service.swagger.models.TaskProperties import TaskProperties

import logging

L = logging.getLogger(__name__)


def get_properties(_, module_src):
    '''Obtain properties for a new task registration'''

    # sensible defaults:
    props = {
        'state': 'default',
        'compatible_queues': ['all'],
        'accepts': [],
        'returns': []
    }

    func_name, func_params, docstring = parse_properties_from_source(module_src)

    props['task_name'] = func_name

    props.update(extract_properties_from_manifest(docstring))

    missing = find_missing_props(props)
    if missing:
        raise KeyError('Missing properties are required: %s' % ', '.join(missing))

    extra = find_unknown_props(props)
    if extra:
        raise KeyError('Unknown properties are not allowed: %s' % ', '.join(extra))

    if not props['accepts']:
        L.warning('Empty section: accepts')

    if not props['returns']:
        L.warning('Empty section: returns')

    props['accepts'] = sort_args(props['accepts'], func_params)

    return props


# TODO extract common src parsing functionality between v0 and v1
def parse_properties_from_source(module_src):  # pylint: disable=R0912
    '''we need to find the task parameters, such that we can
    serve a them for the gui generation.  However, we don't want to load
    the module, because we can't trust the code.  So we parse the AST
    instead

    From: http://stackoverflow.com/a/9580006
    '''
    import ast

    def visit_FunctionDef(node):
        '''visitor to function definitions, needed to extract decorator'''
        for e in node.decorator_list:
            assert isinstance(e, (ast.Call, ast.Name))

            decorator_name = ''
            if isinstance(e, ast.Call):  # @task(args, ...)
                decorator_name = e.func.id
            elif isinstance(e, ast.Name):  # @task [ie: naked]
                decorator_name = e.id

            if 'task' == decorator_name:
                visit_FunctionDef.task_count += 1

                visit_FunctionDef.function_name = node.name

                visit_FunctionDef.function_params = [to.parse_val(arg)
                                                     for arg in node.args.args]
                visit_FunctionDef.doc = ast.get_docstring(node) or ''

    visit_FunctionDef.function_name = None
    visit_FunctionDef.function_params = []
    visit_FunctionDef.doc = ''
    visit_FunctionDef.task_count = 0  # number of decorators named task

    visitor = ast.NodeVisitor()
    visitor.visit_FunctionDef = visit_FunctionDef
    visitor.visit(compile(module_src, '?', 'exec', ast.PyCF_ONLY_AST))

    if 0 == visit_FunctionDef.task_count:
        raise ValueError('Task has no @task decorator')

    elif 1 < visit_FunctionDef.task_count:
        raise ValueError('Task has too many @task decorators')

    return visit_FunctionDef.function_name, visit_FunctionDef.function_params, visit_FunctionDef.doc


MANIFEST_ALIASING = {
    'task manifest version': 'manifest_version',
    'desc': 'description',
    'full name': 'full_name',
    'compatible queues': 'compatible_queues',
    'queues': 'compatible_queues',
}

EXTRA = ('manifest_version', )

MANIFEST_ALIASING.update((k, k) for k in TaskProperties().swaggerTypes.keys())
MANIFEST_ALIASING.update((k, k) for k in EXTRA)


def inverse_dictionary(d):
    '''given a dictionary with non-unique values, return a dictionary where the original values are
    used as keys and the original keys have been grouped per value'''
    inv_map = {}
    for k, v in d.items():
        inv_map[v] = inv_map.get(v, [])
        inv_map[v].append(k)
    return inv_map


MANIFEST_ALIASES_GROUPED = inverse_dictionary(MANIFEST_ALIASING)


def extract_properties_from_manifest(manifest_src):
    '''return a dictionary with the properties of a task read from a task manifest if it exists'''

    if not any(key.lower() in manifest_src.lower()
               for key in MANIFEST_ALIASES_GROUPED['manifest_version']):
        raise VersionError('Missing Task Manifest Version, must be v0')

    props = ordered_load(manifest_src)

    if not isinstance(props, dict):
        raise TypeError('Docstring should be a yaml dictionary. Got %s instead.' %
                        type(props).__name__)

    props = OrderedDict((MANIFEST_ALIASING.get(p.lower(), p.lower()), v) for p, v in props.items())

    if 'manifest_version' not in props:
        # note that it MUST be present because we check for it in the entire string just above
        # probably this is broken yaml
        raise KeyError('Missing Task Manifest Version, must be present')

    if props['manifest_version'] != 1:
        raise VersionError('Unknown Task Manifest Version %s' % props['manifest_version'])

    props = parse_args_from_manifest(props)

    props.pop('manifest_version')

    return props


def parse_args_from_manifest(props):
    '''make sense out of the accepts and returns properties as expressed in yaml'''
    for p in props:
        if p in ('accepts', 'returns'):
            new = []
            if props[p] is not None:
                for k, v in props[p].items():
                    arg_def = {'name': k}
                    try:
                        arg_def.update(parse_argument_definition_from_manifest(v))
                    except ValueError as e:
                        raise ValueError('Failed to parse definition for %s field "%s": %s' %
                                         (p, k, e.message))
                    new.append(arg_def)

            props[p] = new

    return props


def ordered_load(stream):
    '''load yaml dictionaries preserving the order in the file'''

    class OrderedLoader(yaml.Loader):  # pylint: disable=R0901
        '''custom ordered yaml loader'''
        pass

    def construct_mapping(loader, node):
        '''custom ordered yaml loader'''
        loader.flatten_mapping(node)
        return OrderedDict(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)

    return yaml.load(stream, OrderedLoader)


MANIFEST_ARGUMENT_ALIASING = {
    'type': ['type'],
    'description': ['desc', 'description'],
    'default': ['default']
}


def parse_argument_definition_from_manifest(value):
    '''parse an argument definition for the accepts or returns lists from a loaded manifest'''
    if isinstance(value, basestring):
        arg_type = parse_type(value)
        return {'type': arg_type}

    elif isinstance(value, dict):
        arg_def = {}
        for k, v in value.items():
            if k in MANIFEST_ARGUMENT_ALIASING['type']:
                arg_def['type'] = parse_type(v)

            elif k in MANIFEST_ARGUMENT_ALIASING['description']:
                arg_def['description'] = v

            elif k in MANIFEST_ARGUMENT_ALIASING['default']:
                arg_def['default'] = v

            else:
                raise ValueError('Invalid argument definition property %s in %s' % (k, value))

        return arg_def

    else:
        raise ValueError('Invalid argument definition: %s' % value)


def parse_type(original):
    '''parse a type string from the manifest allowing for some syntactic sugar'''
    if not isinstance(original, str):
        raise TypeError('Expected string but got %s instead (for: "%s")' %
                        (type(original).__name__, original))

    value = original.lower()

    alias_map = {
        tt.LongType: ['int', 'long'],
        tt.DoubleType: ['float', 'double'],
        tt.BooleanType: ['bool', 'boolean'],
        tt.StringType: ['str', 'string'],
    }

    for cl, aliases in alias_map.items():
        if value in aliases:
            return cl()

    match = re.search(r'list\(([a-zA-Z0-9=;/\.\+]+)\)', original)
    if match:
        subtype = parse_type(match.group(1))
        return tt.ListOf(subtype=subtype)

    try:
        get_mimetype(original)
        return tt.URIType(category=original)

    except ValueError:
        pass

    return object_from_string_call(original)


def find_missing_props(manifest_props):
    '''Find properties required for a task post that are missing from the extracted info'''
    return set(TaskProperties().swaggerTypes.keys()) - set(manifest_props.keys())


def find_unknown_props(manifest_props):
    '''Find properties not required for a task post that are found int the extracted info'''
    return set(manifest_props.keys()) - set(TaskProperties().swaggerTypes.keys())


def sort_args(args, names):
    '''sort the argument information obtained from the manifest with the same order as the
    variable names extracted from the function

    Raises:
         KeyError if the values in args and those in names don't match
    '''
    found_names = set(a['name'] for a in args)
    if found_names != set(names):
        raise KeyError('Documented names and actual argument names do not match: %s' %
                       set(names).symmetric_difference(found_names))

    return sorted(args, key=lambda p: names.index(p['name']))
