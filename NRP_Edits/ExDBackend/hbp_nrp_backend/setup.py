'''setup.py'''

from setuptools import setup

import hbp_nrp_backend
import pip

from pip.req import parse_requirements
from optparse import Option
options = Option('--workaround')
options.skip_requirements_regex = None
reqs_file = './requirements.txt'
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
reqs = [str(ir.req) for ir in install_reqs]

# ensure we install numpy before the main list of requirements, ignore
# failures if numpy/cython are not requirements and just proceed (future proof)
try:
    cython_req = next(r for r in reqs if r.startswith('cython'))
    numpy_req = next(r for r in reqs if r.startswith('numpy'))
    pip.main(['install', '--no-clean', cython_req, numpy_req])
# pylint: disable=bare-except
except:
    pass

config = {
    'description': 'Experiment Backend for HBP SP10',
    'author': 'HBP Neurorobotics',
    'url': 'http://neurorobotics.net',
    'author_email': 'neurorobotics@humanbrainproject.eu',
    'version': hbp_nrp_backend.__version__,
    'install_requires': reqs,
    'packages': ['hbp_nrp_backend',
                 'hbp_nrp_backend.rest_server',
                 'hbp_nrp_backend.storage_client_api',
                 'hbp_nrp_backend.simulation_control',
                 'hbp_nrp_backend.exd_config',
                 'hbp_nrp_backend.exd_config.generated',
                 'hbp_nrp_backend.cle_interface'],
    'scripts': [],
    'name': 'hbp_nrp_backend',
    'include_package_data': True,
}

setup(**config)
