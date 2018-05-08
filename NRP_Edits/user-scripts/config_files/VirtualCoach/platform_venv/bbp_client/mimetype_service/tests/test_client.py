from datetime import datetime, timedelta
from nose.tools import ok_, eq_
from mock import Mock, patch, ANY

from bbp_client.mimetype_service import client
from bbp_client.mimetype_service import models
from bbp_client.mimetype_service.tests.data import *

mock_requests = Mock()
@patch('bbp_client.mimetype_service.client.requests', mock_requests)
class TestClientMimeType(object):
    SIMPLE_MODEL = MIMETYPE_DICT
    def setUp(self):
        mock_requests.reset_mock()
        self.c = client.Client('http://localhost:8000')

    def tearDown(self):
        pass

    def test_str(self):
        print str(self.c)

    def test_get_mimetype(self):
        mimetype_name = 'image/png'
        mock_requests.get.return_value.json.return_value = self.SIMPLE_MODEL
        mt = self.c.get_mimetype(mimetype_id=1)
        eq_(mt.mimetype, mimetype_name)

        #id does not exist
        mock_requests.get.return_value.json.return_value = {}
        mt = self.c.get_mimetype(mimetype_id=1)
        eq_(mt, None)

    def test_find_mimetype(self):
        mimetype_name = 'image/png'
        mock_requests.get.return_value.json.return_value = {
            'results': [self.SIMPLE_MODEL,]}
        r = self.c.find_mimetype(mimetype=mimetype_name)
        eq_(len(r), 1)

    def test_find_mimetype_paged(self):
        mimetype_name = 'image/png'
        self.count = 5
        self.remaining = self.count

        def mock_get_json():
            if self.remaining > 1:
                self.remaining -= 1
                return {
                    'count': self.count,
                    'next': 'http://next',
                    'results': [self.SIMPLE_MODEL,]}
            else:
                return {
                    'count': self.count,
                    'results': [self.SIMPLE_MODEL,]}

        mock_requests.get.return_value.json = mock_get_json
        r = self.c.find_mimetype(mimetype=mimetype_name)
        eq_(len(r), self.count)
        mock_requests.get.return_value.json = Mock()

    def test_find_mimetype_cached(self):
        mimetype_name = 'image/png'
        cache_client = client.Client('http://localhost:8000', cache_enabled=True)
        mock_requests.get.return_value.json.return_value = {
            'results': [self.SIMPLE_MODEL,]}
        r = cache_client.find_mimetype(mimetype=mimetype_name)
        eq_(len(r), 1)
        mock_requests.get.assert_called_once_with(ANY)

        cached = cache_client.find_mimetype(mimetype=mimetype_name)
        mock_requests.get.assert_called_once_with(ANY)
        eq_(len(cached), 1)
        eq_(r, cached)

        mock_requests.get.reset_mock()
        fake_date = datetime.now() + timedelta(hours=2)
        with patch('bbp_client.mimetype_service.client.datetime') as mock_date:
            mock_date.now.return_value = fake_date
            r = cache_client.find_mimetype(mimetype=mimetype_name)
            mock_requests.get.assert_called_once_with(ANY)

    def test_register_mimetype(self):
        mimetype_name = 'application/nonexistant'
        mock_requests.post.return_value.json.return_value = self.SIMPLE_MODEL
        mock_requests.post.return_value.json.return_value['mimetype'] = mimetype_name
        mt = models.MimeTypeFactory(mimetype=mimetype_name,
                                    description='Hopefully this does not exist')
        r = self.c.register_mimetype(mt)
        eq_(r.mimetype, mimetype_name)

    def test_update_mimetype(self):
        mimetype_name = 'image/png'
        mock_requests.put.return_value.json.return_value = self.SIMPLE_MODEL
        mock_requests.get.return_value.json.return_value = {
            'results': [self.SIMPLE_MODEL,]}
        r = self.c.find_mimetype(mimetype=mimetype_name)
        mt = r[0]
        self.c.update_mimetype(mt)
        mt.description = 'new description'
        self.c.update_mimetype(mt)

        #remove a key
        mt.keys = mt.keys[:-1]
        #change key
        mt.keys[0].value = 'new value'
        #add key
        new_key = models.KeyFactory(key='new_key', value='new_key_value')
        mt.keys.append(new_key)

        #reset counts
        mock_requests.reset_mock()
        self.c.update_mimetype(mt)

        #check keys updating
        ok_(mock_requests.put.called)
        ok_(mock_requests.post.called)
        ok_(mock_requests.delete.called)

    def test_delete_mimetype(self):
        mt = models.MimeTypeFactory(**self.SIMPLE_MODEL)
        self.c.delete_mimetype(mt)

@patch('bbp_client.mimetype_service.client.requests', mock_requests)
class TestClientViwer(object):
    SIMPLE_MODEL = {
        'model_name': 'Viewer',
        'viewer': 'test viewer',
        'version': '3.1.4',
        'id': 1
    }
    def setUp(self):
        mock_requests.reset()
        self.c = client.Client('http://localhost:8000')

    def tearDown(self):
        pass

    def test_str(self):
        print str(self.c)

    def test_get_viewer(self):
        viewer_name = 'test viewer'
        mock_requests.get.return_value.json.return_value = self.SIMPLE_MODEL
        v = self.c.get_viewer(viewer_id=1)
        eq_(v.viewer, viewer_name)

        #id does not exist
        mock_requests.get.return_value.json.return_value = { }
        v = self.c.get_viewer(viewer_id=1)
        eq_(v, None)

    def test_find_viewer(self):
        viewer_name = 'test viewer'
        mock_requests.get.return_value.json.return_value = {
            'results': [self.SIMPLE_MODEL,]}
        r = self.c.find_viewer(viewer=viewer_name)
        eq_(len(r), 1)

    def test_register_viewer(self):
        viewer_name = 'nonexistant viewer'
        mock_requests.post.return_value.json.return_value = self.SIMPLE_MODEL
        mock_requests.post.return_value.json.return_value['viewer'] = viewer_name
        v = models.ViewerFactory(viewer=viewer_name,
                                    description='Hopefully this does not exist')
        r = self.c.register_viewer(v)
        eq_(r.viewer, viewer_name)

    def test_update_viewer(self):
        viewer_name = 'image/png'
        mock_requests.put.return_value.json.return_value = self.SIMPLE_MODEL
        mock_requests.get.return_value.json.return_value = {
            'results': [self.SIMPLE_MODEL,]}
        r = self.c.find_viewer(viewer=viewer_name)
        v = r[0]
        self.c.update_viewer(v)
        v.description = 'new description'
        self.c.update_viewer(v)

    def test_delete_viewer(self):
        v = models.ViewerFactory(**self.SIMPLE_MODEL)
        self.c.delete_viewer(v)

@patch('bbp_client.mimetype_service.client.requests', mock_requests)
class TestClientKey(object):
    def setUp(self):
        mock_requests.reset()
        self.c = client.Client('http://localhost:8000')

    def tearDown(self):
        pass

    def test_str(self):
        print str(self.c)

    def test_register_key(self):
        mock_requests.post.return_value.json.return_value = KEY_DICT
        key = models.KeyFactory(**KEY_DICT)
        r = self.c.register_key(key)
        eq_(r, key)

    def test_update_key(self):
        mock_requests.put.return_value.json.return_value = KEY_DICT
        key = models.KeyFactory(**KEY_DICT)
        r = self.c.update_key(key)
        eq_(r, key)

    def test_delete_key(self):
        key = models.KeyFactory(**KEY_DICT)
        self.c.delete_key(key)
