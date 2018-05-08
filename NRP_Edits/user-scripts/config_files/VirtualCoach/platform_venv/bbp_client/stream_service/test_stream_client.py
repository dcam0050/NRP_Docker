# pylint: disable=C0111
from bbp_client.stream_service.client import Client

from mock import patch, Mock, ANY


class TestStreamClient(object):
    def setUp(self):
        self.mock_oidc = Mock()
        self.stream = Client('api/', self.mock_oidc)

    def test_register_activity(self):
        with patch('bbp_client.stream_service.client.requests') as mock_req:
            mock_req.post.return_value = resp = Mock()
            resp.status_code = 201

            self.stream.register_activity({'actor': 'actor'})
            mock_req.post.assert_called_once_with('api/activity/', json={'actor': 'actor',
                                                                         'time': ANY},
                                                  headers=ANY)
