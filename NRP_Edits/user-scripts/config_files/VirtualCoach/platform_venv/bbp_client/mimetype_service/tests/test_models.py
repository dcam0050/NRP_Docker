import json

from nose.tools import ok_, eq_, raises, assert_raises

from bbp_client.mimetype_service import models
from bbp_client.mimetype_service.tests.data import *

@raises(Exception)
def test_bad_model():
    models.Key(foo='bar')


@raises(Exception)
def test_bad_deserialization():
    models.JSONModel.deserialize(json_obj={'model_name': 'fake', 'foo': 'bar'})


def test_viewer_model():
    v = models.ViewerFactory.deserialize(json_obj=VIEWER_DICT)
    eq_(v.id, 1)

    v = models.ViewerFactory(**VIEWER_DICT)
    eq_(v.id, 1)

    v = models.ViewerFactory.deserialize(**VIEWER_DICT)
    eq_(v.id, 1)


def test_mimetype_model():
    m = models.MimeTypeFactory.deserialize(json_obj=MIMETYPE_DICT)
    eq_(m.id, 1)

    m = models.MimeTypeFactory(**MIMETYPE_DICT)
    eq_(m.id, 1)

    assert_raises(KeyError, m.get_key, 'does not exist')


def test_key_model():
    k = models.KeyFactory.deserialize(json_obj=KEY_DICT)
    eq_(k.id, 3)

    k = models.KeyFactory(**KEY_DICT)
    eq_(k.id, 3)

    k = models.JSONModel.deserialize(json_obj=KEY_DICT)
    eq_(k.id, 3)


def test_serialize():
    data = dict(KEY_DICT)
    k = models.KeyFactory.deserialize(json_obj=data)

    serialized = k.serialize(rw_keys_only=False)
    eq_(data, json.loads(serialized))

    serialized = k.serialize()
    for k in models.KeyFactory._READ_ONLY_FIELDS:
        del data[k]
    eq_(data, json.loads(serialized))


def test_repr():
    k = models.KeyFactory.deserialize(json_obj=KEY_DICT)
    ok_('mimetype' in str(k))

@raises(AttributeError)
def test_read_only():
    k = models.KeyFactory.deserialize(json_obj=KEY_DICT)
    k.id = 'not an id'
