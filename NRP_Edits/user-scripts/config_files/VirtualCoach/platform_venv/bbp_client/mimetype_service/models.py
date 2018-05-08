'''models (like in swagger) used by the MIMEType service'''

import json


class MimeTypeEncoder(json.JSONEncoder):
    """allow serializing of our type system to json """
    def default(self, obj):  # pylint: disable=E0202
        if isinstance(obj, JSONModel):
            return obj.serialize()
        return json.JSONEncoder.default(self, obj)


class CreateJSONModel(type):
    '''model method helper for creating meta class'''
    def __new__(mcs, class_name, parents, attributes):
        assert(class_name.endswith('Factory'))
        class_name = class_name[:-7]
        return type(class_name, parents, attributes)


class JSONModel(object):
    '''Base for json objects returned from MimeType service

    Don't forget the metaclass:
    __metaclass__ = CreateJSONModel
    '''
    _READ_ONLY_FIELDS = set()
    _MODELS_NAMES = ('Viewer', 'MimeType', 'Key',)

    def __init__(self, **kwargs):
        self._field_names = set()
        for attr in dir(self):
            attr_type = getattr(self, attr)
            if attr.startswith('_') or not isinstance(attr_type, type):
                continue
            if attr in kwargs:
                arg_value = kwargs[attr]
                if(isinstance(arg_value, list) and
                     arg_value and
                     isinstance(arg_value[0], dict) and
                     self.is_deserializable(arg_value[0])):
                    value = [JSONModel.deserialize(json_obj=a) for a in arg_value]
                #if isinstance(arg_value, dict) and self.is_deserializable(arg_value):
                #    value = self.deserialize(json_obj=arg_value)
                else:
                    value = attr_type(arg_value)
            else:
                #default construct
                value = attr_type()
            self._field_names.add(attr)

            #bypass read only setattr
            self.__dict__[attr] = value
        self.__dict__['model_name'] = self.__class__.__name__

    def __setattr__(self, attr, value):
        '''don't allow updates to read only field'''
        if attr in self._READ_ONLY_FIELDS:
            raise AttributeError('%s is a read only field' % attr)
        self.__dict__[attr] = value

    @staticmethod
    def is_deserializable(json_obj):
        '''see if the dictionary is deserializable to a known JSONModel'''
        return ('model_name' in json_obj and
                json_obj['model_name'] and
                json_obj['model_name'] in JSONModel._MODELS_NAMES)

    @classmethod
    def deserialize(cls, json_obj=None, **kwargs):
        '''deserialize and object, either based on its JSON dict (already json.loaded)
           or its internal members'''
        if json_obj:
            if not cls.is_deserializable(json_obj):
                raise Exception('Not a valid model_name: %s' % json_obj['model_name'])
            #this is safe, since we only allow things from MODELS_NAMES
            return eval(json_obj['model_name'] + 'Factory')(**json_obj)
        ret = cls(**kwargs)
        return ret

    def serialize(self, rw_keys_only=True, skip_fields=set(), # pylint: disable=W0102
                  cls=MimeTypeEncoder):
        '''take an object, and return the json string representing it'''
        keys = self._field_names - skip_fields
        if rw_keys_only:
            keys -= self._READ_ONLY_FIELDS
        return json.dumps(dict((k, getattr(self, k)) for k in keys), cls=cls)

    def __repr__(self):
        '''print out the model'''
        ret = '\n'.join('%s(%s): %s' % (k,
                                        'RO' if k in self._READ_ONLY_FIELDS
                                        else 'RW', getattr(self, k))
                        for k in self._field_names)
        return ret

    __str__ = __repr__

    def __eq__(self, other):
        return all(getattr(self, f) == getattr(other, f)
                   for f in self._field_names)


class KeyFactory(JSONModel):
    '''used to create Keys'''
    __metaclass__ = CreateJSONModel
    _READ_ONLY_FIELDS = set(['id', 'model_name', ])

    id = long
    model_name = str
    mimetype = int
    key = str
    value = str


class ViewerFactory(JSONModel):
    '''Used to create Viewer(s)'''
    __metaclass__ = CreateJSONModel
    _READ_ONLY_FIELDS = set(['id', 'model_name', 'created', ])

    id = long
    model_name = str
    mimetype = list
    viewer = str
    version = str
    deprecated = bool
    created = str


class MimeTypeFactory(JSONModel):
    '''Used to create MimeType(s)'''
    __metaclass__ = CreateJSONModel
    _READ_ONLY_FIELDS = set(['id', 'model_name', ])

    id = long
    model_name = str
    mimetype = str
    description = str
    viewers = list
    keys = list

    def get_key(self, key_name):
        '''return the value of a key, if it exists, raises KeyError if it doesn't exist'''
        for k in self.keys:
            if getattr(k, 'key') == key_name:
                return k
        raise KeyError('key: %s does not exist' % key_name)
