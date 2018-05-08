#!/usr/bin/env python
'''Client to standardize access to information regarding services

Simplifies changing server names, and updating them in code.  Code should
never include hardcoded server names/urls, etc.
'''

import os
joinp = os.path.join

import yaml


class ServiceInfo(dict):
    '''Wrap info from yaml so we can perform name mapping if necessary'''

    # Have a set of name maps, in case more than one exists
    # key -> 'true' version; ex: 'devel' -> 'dev'
    # true ones are 'dev'/'staging'/'prod'
    NAME_MAPS = {'devel': 'dev',
                 'development': 'dev',
                 'preprod': 'prod',
                 'production': 'prod',
                 }

    @staticmethod
    def _map_name(name):
        '''try and map name from INFRA scheme to ours '''
        if name in ServiceInfo.NAME_MAPS:
            return ServiceInfo.NAME_MAPS[name]
        return name

    def __getitem__(self, name):
        name = self._map_name(name)
        return super(ServiceInfo, self).__getitem__(name)

    def __contains__(self, name):
        name = self._map_name(name)
        return super(ServiceInfo, self).__contains__(name)

    def get(self, k, d=None):
        '''overload get so that it behaves properly with our name mapping'''
        try:
            return self[k]
        except KeyError:
            return d


def _get_yaml_files():
    '''return the yaml list of files'''
    data_dir = joinp(os.path.dirname(__file__), 'data')
    return [joinp(data_dir, d) for d in os.listdir(data_dir) if d.endswith('yaml')]


def _parse_yaml(yaml_file):
    '''return a dictionary of properties based from yaml file'''
    with open(yaml_file) as fd:
        d = yaml.safe_load(fd)
        return ServiceInfo(d)


def get_services():
    '''returns a dict of services

    Parses the data/.yaml files, and creates returns a dictionary of
    structure::

        {
        'task_service': {
            'properties': {
            'confluence': '....',
            'description': 'Task service, runs tasks (aka PlatformTaskManager)',
            'puppet_url': '....',
            'ports': ['8000(nginx auth)', ...],
            'other_service':.
            },
            #the environments
            'dev': {
            'human_url': 'http://bbpsrvi35:8000/ui/',
            'machine': 'bbpsrvi35',
            'oauth_dev': 'dev',
            'url': 'http://bbpsrvi35:8000'},

            'prod': (same as dev, but for prod),
            'staging': (same as dev, but for staging)}

        }

    Thus, you can easily pick the service you want to connect to:

    >>> import bbp_services.client as bsc
    >>> services = bsc.get_services()
    >>> env = 'dev'  # or prod, or picked by the command line
    >>> oauth_url = services['oauth_service'][env]['url']

    '''
    ret = {}
    for service in _get_yaml_files():
        (service_name, _) = os.path.splitext(os.path.basename(service))
        ret[service_name] = _parse_yaml(service)
    return ret


def get_environments():
    '''get the available environments known to bbp_services

    We `voted <http://www.polljunkie.com/poll/bkwgbd/environment-naming/view>`_:
    9 responses::

        * dev: 88%, development: 11%
        * staging: 88%, preprod: 11%
        * prod: 66%, production: 33%

    So internally, our services are referred to by: dev/staging/prod

    >>> import bbp_services.client as bsc
    >>> bsc.get_environments()
    ['prod', 'staging', 'dev']

    '''
    return ['prod', 'staging', 'dev']


def get_environment_aliases():
    '''get all the available environment names

    These consist of the environments defined by get_environments()
    plus all their aliases
    '''
    return tuple(set(ServiceInfo.NAME_MAPS.keys() + get_environments()))


def confluence_services_table():  # pylint: disable=R0912
    '''create a confluence markup table about our services'''
    services = get_services()

    HEADINGS = ['Name', 'Dev', 'Staging', 'Prod', 'Ports', 'Puppet', 'Confluence']
    ret = ['||' + '||'.join(HEADINGS) + '||']

    def confluence_url(url):
        '''create confluence urls from full urs'''
        our_space = 'https://bbpteam.epfl.ch/project/spaces/display/BBPWFA/'
        if url.startswith(our_space):
            url = str(url[len(our_space):]).replace('+', ' ')
        return '[%s]' % url

    for name in services.keys():
        service = services[name]
        row = ['', name]

        for env in ('dev', 'staging', 'prod'):
            if env not in service:
                row.append('-')
                continue
            serv_env = service[env]
            if 'machine' in serv_env and 'human_url' in serv_env:
                row.append('[%s|%s]' % (serv_env['machine'],
                                        serv_env['human_url']))
            elif 'machine' in serv_env:
                row.append(serv_env['machine'])
            else:
                row.append('-')

        props = service['properties']
        if 'ports' in props:
            row.append(', '.join([str(i) for i in props['ports']]))
        else:
            row.append('-')

        if 'puppet_url' in props:
            row.append(confluence_url(props['puppet_url']))
        else:
            row.append('-')

        if 'confluence' in props:
            row.append(confluence_url(props['confluence']))
        else:
            row.append('-')

        row.append('')  # ensure ending |
        ret.append(' | '.join(row))

    return '\n'.join(ret)


if __name__ == '__main__':
    print(confluence_services_table())
