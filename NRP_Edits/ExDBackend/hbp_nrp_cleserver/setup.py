'''setup.py'''
import os

from setuptools import setup
import pip
from pip.req import parse_requirements
from optparse import Option

import hbp_nrp_cleserver


def parse_reqs(reqs_file):
    ''' parse the requirements '''
    options = Option('--workaround')
    options.skip_requirements_regex = None
    # Hack for old pip versions
    # Versions greater than 1.x have a required parameter "session" in
    # parse_requirements
    if pip.__version__.startswith('1.'):
        install_reqs = parse_requirements(reqs_file, options=options)
    else:
        from pip.download import PipSession  # pylint:disable=no-name-in-module
        options.isolated_mode = False
        install_reqs = parse_requirements(  # pylint:disable=unexpected-keyword-arg
            reqs_file,
            session=PipSession,
            options=options
        )
    return [str(ir.req) for ir in install_reqs]


BASEDIR = os.path.dirname(os.path.abspath(__file__))
REQS = parse_reqs(os.path.join(BASEDIR, 'requirements.txt'))

# ensure we install numpy before the main list of requirements, ignore
# failures if numpy/cython are not requirements and just proceed (futureproof)
try:
    cython_req = next(r for r in REQS if r.startswith('cython'))
    numpy_req = next(r for r in REQS if r.startswith('numpy'))
    pip.main(['install', '--no-clean', cython_req, numpy_req])
# pylint: disable=bare-except
except:
    pass

EXTRA_REQS_PREFIX = 'requirements_'
EXTRA_REQS = {}
for file_name in os.listdir(BASEDIR):
    if not file_name.startswith(EXTRA_REQS_PREFIX):
        continue
    base_name = os.path.basename(file_name)
    (extra, _) = os.path.splitext(base_name)
    extra = extra[len(EXTRA_REQS_PREFIX):]
    EXTRA_REQS[extra] = parse_reqs(file_name)

config = {
    'description': 'CLE Simulation Factory for HBP SP10',
    'author': 'HBP Neurorobotics',
    'url': 'http://neurorobotics.net',
    'author_email': 'neurorobotics@humanbrainproject.eu',
    'version': hbp_nrp_cleserver.__version__,
    'install_requires': REQS,
    'extras_require': EXTRA_REQS,
    'packages': ['hbp_nrp_cleserver',
                 'hbp_nrp_cleserver.bibi_config',
                 'hbp_nrp_cleserver.server'],
    'package_data': {
        'hbp_nrp_cleserver.bibi_config': ['tf_template.pyt']
    },
    'scripts': [],
    'name': 'hbp-nrp-cleserver',
    'include_package_data': True,
}

setup(**config)
