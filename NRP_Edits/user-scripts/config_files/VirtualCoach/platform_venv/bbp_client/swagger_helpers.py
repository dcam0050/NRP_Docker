'''helper functions for working with swagger'''

import json
import logging

from functools import wraps
from urllib2 import HTTPError
import re

L = logging.getLogger(__name__)


class SwaggerException(Exception):
    '''exceptions to wrap swagger'''
    pass


def patch_swagger_callapi(api, header_callback):
    '''need to patch the callAPI function so we can add our custom headers

    Args:
        api: The swagger API
        header_callback: Additional headers to be added to the callback

    Note: This doesn't currently attempt to do a client token refresh, might
          want to do that in your header_callback if you have an
          BBPOIDCClient instance
    '''
    # save the old function
    old = api.callAPI_old = api.callAPI

    def patch(resourcePath, method, queryParams, postData, headerParams):
        '''function we subsitute for the real swagger.callAPI function
            allows us to add additional headers, if necessary (like for oauth)
        '''
        if not headerParams:
            headerParams = {}

        headerParams.update(header_callback())

        return old(resourcePath, method, queryParams, postData, headerParams)

    L.debug('patching the swagger callapi')

    api.callAPI = patch


def swagger_create_type(obj_type, values):
    '''swagger doesn't have constructors (!!!?), so this takes an
       object model (obj_type), and a dict of values, and creates the type
    '''
    obj = obj_type()
    for attr, attr_type in obj.swaggerTypes.iteritems():
        if attr in values:
            attr_val = values[attr]
        elif attr_type in ('str', 'int', 'long', 'float', 'bool'):
            attr_val = eval(attr_type + '()')
        #elif 'integer' == attr_type:
        #    attr_val = int()
        #elif 'boolean' == attr_type:
        #    attr_val = bool()
        elif 'object' == attr_type:
            attr_val = dict()
        elif re.match(r'list\[.+]', attr_type):  # list[str]
            attr_val = list()
        else:
            raise SwaggerException('Unrecognised type %s (obj: %s)' % (attr_type, obj_type))

        setattr(obj, attr, attr_val)
    return obj


def swagger_type_to_dict(obj):
    '''recursively change swagger objects into dictionaries'''
    if hasattr(obj, 'swaggerTypes'):
        ret = {}
        for attr in obj.swaggerTypes.keys():
            ret[attr] = swagger_type_to_dict(getattr(obj, attr))
    else:
        ret = obj

    return ret


def swagger_error(func):
    '''decorate functions that make swagger calls, and intercept HTTPError

    replace with better exception, that is more informative
    '''

    @wraps(func)
    def wrapper(*args, **kwargs):
        '''wrapper function'''
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            body = e.fp.read()
            try:
                body = json.loads(body)
            except ValueError:
                pass

            #python2.6 has a different HTTPError exception :-(
            if hasattr(e, 'reason'):
                reason = '%s (%s)' % (e.reason, e.msg)
            else:
                reason = str(e)

            exc_str = ('Swagger failed (URL: %s Code %d): %s (%s)'
                       % (e.url, int(e.code), reason, body))
            raise SwaggerException(exc_str)
    return wrapper
