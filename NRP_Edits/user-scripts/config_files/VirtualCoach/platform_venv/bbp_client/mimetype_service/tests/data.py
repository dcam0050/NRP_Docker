import json

VIEWER_JSON = '''\
{
    "model_name": "Viewer",
    "mimetype": [
        1
    ],
    "viewer": "Test config viewer",
    "version": "3.1.4",
    "created": "2014-11-20T09:55:55.654Z",
    "deprecated": false,
    "id": 1
}'''
VIEWER_DICT = json.loads(VIEWER_JSON)

MIMETYPE_JSON = '''\
{
    "model_name": "MimeType",
    "mimetype": "image/png",
    "viewers": [
      1
    ],
    "keys": [
        {
            "id": 1,
            "model_name": "Key",
            "key": "foo",
            "value": "bar",
            "mimetype": 2
        },
        {
            "id": 2,
            "model_name": "Key",
            "key": "asdf",
            "value": "asdf",
            "mimetype": 2
        }
    ],
    "id": 1
}'''
MIMETYPE_DICT = json.loads(MIMETYPE_JSON)

KEY_JSON = '''\
{
    "id": 3,
    "model_name": "Key",
    "key": "keyasdf",
    "value": "newvalue",
    "mimetype": 1
}
'''
KEY_DICT = json.loads(KEY_JSON)
