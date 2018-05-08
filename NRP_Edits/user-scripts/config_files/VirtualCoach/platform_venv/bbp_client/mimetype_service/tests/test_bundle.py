import copy
import json

from bbp_client.mimetype_service import bundle

from task_types.TaskTypes import URI

from bbp_client.mimetype_service import client
from bbp_client.mimetype_service import models

from mock import Mock, patch
from nose.tools import ok_, eq_, raises, assert_raises

EX_BUNDLE_SPEC = {
    'type': 'bundleTypeSpec',
    'bundleType': 'demoBundles',
    'content': {
        '/': {
            'type': 'image/png',
            'count': [0, 2]
        },
        '/foo/bar_*': {
            'type': 'application/json',
            'count': '*'
        },
        '/foo/bal_*':  {
            'type': 'application/json',
            'count': '+'
        },
        '/gul/':  {
            'type': 'application/json',
            'count': 10
        },
        '/gul/baz':  'application/json'
    }
}

EX_BUNDLE = {
    'type': 'bundle',
    'bundleType': 'demoBundles',
    'content': {
        '/': ['root.png', ],
        '/foo/bar_0': 'foo_bar0.json',
        '/foo/bar_1': 'foo_bar1.json',
        '/foo/bal_0': 'foo_bal0.json',
        '/gul/':  range(10),
        '/gul/baz':  'gul_baz.json'
    }
}

def get_ex_bundle_spec():
    return copy.deepcopy(EX_BUNDLE_SPEC)

def get_ex_bundle():
    return copy.deepcopy(EX_BUNDLE)

def get_mimetype_client(spec):
    '''returns client and mock'''
    #create mimetype with associated key for bundle spec
    mimetype_name = 'application/vnd.bbp.bundle.demo'
    mt = models.MimeTypeFactory(mimetype=mimetype_name)
    bundle_spec = models.KeyFactory(key='bundleTypeSpec', value=json.dumps(spec))
    mt.keys.append(bundle_spec)

    mock_client = Mock()
    mock_client.find_mimetype.return_value = mt

    return mock_client

@raises(ValueError)
def test__check_mimetype():
    mock_requests = Mock()
    mock_requests.get.return_value.json.return_value = {'count': 0,
                                                        'next': None,
                                                        'previous': None,
                                                        'results': [],
                                                        }
    with patch('bbp_client.mimetype_service.client.requests', mock_requests):
        c = client.Client('http://localhost:8000')
        #import ipdb; ipdb.set_trace()  # XXX BREAKPOINT
        bundle._check_mimetype(c, 'does not exist')


def test_get_bundle_spec():
    mimetype_name = 'application/vnd.bbp.bundle.demo'
    c = get_mimetype_client(spec=EX_BUNDLE_SPEC)
    spec = bundle.get_bundle_spec(c, mimetype_name)
    ok_(isinstance(spec, dict))


def test_validate_bundle():
    b = TestCreateBundle.create_bundle()
    c = get_mimetype_client(spec=EX_BUNDLE_SPEC)
    bundle.validate_bundle(b.create_structure(), c)


def test__validate_bundle_spec_structure():
    #missing bundleType
    bad_spec = get_ex_bundle_spec()
    del bad_spec['bundleType']
    assert_raises(ValueError, bundle._norm_bundle_spec_structure, bad_spec)

    #bad type
    bad_spec = get_ex_bundle_spec()
    bad_spec['type'] = 'foo'
    assert_raises(ValueError, bundle._norm_bundle_spec_structure, bad_spec)

    #bad content
    bad_spec = get_ex_bundle_spec()
    del bad_spec['content']
    assert_raises(ValueError, bundle._norm_bundle_spec_structure, bad_spec)

    bad_spec['content'] = {
        '/': {
            'type': 'image/png',
            'count': [0, 1, 2]
        }}
    assert_raises(ValueError, bundle._norm_bundle_spec_structure, bad_spec)

    bad_spec['content']['/']['count'] = [1, 0]
    assert_raises(ValueError, bundle._norm_bundle_spec_structure, bad_spec)

    bad_spec['content']['/']['count'] = 'not +/*'
    assert_raises(ValueError, bundle._norm_bundle_spec_structure, bad_spec)

    bad_spec['content']['/']['count'] = 'not +/*'
    assert_raises(ValueError, bundle._norm_bundle_spec_structure, bad_spec)

    bad_spec['content']['/']['count'] = {}
    assert_raises(ValueError, bundle._norm_bundle_spec_structure, bad_spec)

    del bad_spec['content']['/']['type']
    assert_raises(ValueError, bundle._norm_bundle_spec_structure, bad_spec)


def test_valid_bundle():
    test_bundle = get_ex_bundle()
    bundle.validate_bundle_from_spec(test_bundle, bundle_spec=EX_BUNDLE_SPEC)

    test_bundle = get_ex_bundle()
    del test_bundle['content']
    assert_raises(ValueError, bundle.validate_bundle_from_spec, test_bundle, bundle_spec=EX_BUNDLE_SPEC)

    test_bundle = get_ex_bundle()
    del test_bundle['type']
    assert_raises(ValueError, bundle.validate_bundle_from_spec, test_bundle, bundle_spec=EX_BUNDLE_SPEC)

    test_bundle = get_ex_bundle()
    test_bundle['type'] = 'not a bundle'
    assert_raises(ValueError, bundle.validate_bundle_from_spec, test_bundle, bundle_spec=EX_BUNDLE_SPEC)

    test_bundle = get_ex_bundle()
    del test_bundle['bundleType']
    assert_raises(ValueError, bundle.validate_bundle_from_spec, test_bundle, bundle_spec=EX_BUNDLE_SPEC)

    test_bundle = get_ex_bundle()
    test_bundle['content']['/gul/'] = range(1)
    assert_raises(ValueError, bundle.validate_bundle_from_spec, test_bundle, bundle_spec=EX_BUNDLE_SPEC)

    test_bundle = get_ex_bundle()
    test_bundle['content']['/'] = 'not a list'
    assert_raises(ValueError, bundle.validate_bundle_from_spec, test_bundle, bundle_spec=EX_BUNDLE_SPEC)

    test_bundle = get_ex_bundle()
    test_bundle['content']['/foo'] = ['a', 'list', ]
    assert_raises(ValueError, bundle.validate_bundle_from_spec, test_bundle, bundle_spec=EX_BUNDLE_SPEC)

    #missing a /foo/bal_*
    test_bundle = get_ex_bundle()
    del test_bundle['content']['/foo/bal_0']
    assert_raises(ValueError, bundle.validate_bundle_from_spec, test_bundle, bundle_spec=EX_BUNDLE_SPEC)

    #too many files in root
    test_bundle = get_ex_bundle()
    test_bundle['content']['/'] = range(3)
    assert_raises(ValueError, bundle.validate_bundle_from_spec, test_bundle, bundle_spec=EX_BUNDLE_SPEC)


class TestCreateBundle(object):
    @staticmethod
    def create_bundle():
        b = bundle.CreateBundle('demoBundles')
        b.register_file('/', URI('image/png', 'foo.png'))
        b.register_file('/foo/bar_0', URI('application/json', 'qwer.json'))
        b.register_file('/foo/bal_0', URI('application/json', 'qwer.json'))
        for i in range(10):
            b.register_file('/gul/', URI('application/json', str(i) + '.json'))
        b.register_file('/gul/baz', URI('application/json', 'baz'))

        return b

    def test_validate_bundle(self):
        b = TestCreateBundle.create_bundle()
        print b

        structure = b.create_structure()
        bundle.validate_bundle_from_spec(bundle=structure, bundle_spec=EX_BUNDLE_SPEC)

        s = b.serialize()
        ret_bundle = json.loads(s)
        bundle.validate_bundle_from_spec(bundle=ret_bundle, bundle_spec=EX_BUNDLE_SPEC)
