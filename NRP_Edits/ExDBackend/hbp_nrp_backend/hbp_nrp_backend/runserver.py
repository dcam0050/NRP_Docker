# ---LICENSE-BEGIN - DO NOT CHANGE OR MOVE THIS HEADER
# This file is part of the Neurorobotics Platform software
# Copyright (C) 2014,2015,2016,2017 Human Brain Project
# https://www.humanbrainproject.eu
#
# The Human Brain Project is a European Commission funded project
# in the frame of the Horizon2020 FET Flagship plan.
# http://ec.europa.eu/programmes/horizon2020/en/h2020-section/fet-flagships
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
# ---LICENSE-END
"""
Runs the REST server
"""
import os

__author__ = 'GeorgHinkel'

import argparse
from hbp_nrp_backend.rest_server import app
from hbp_nrp_backend.rest_server.cleanup import clean_simulations
from hbp_nrp_backend.rest_server.RestSyncMiddleware import RestSyncMiddleware
import logging
import sys
import rosparam
import rospy
from threading import Thread

DEFAULT_PORT = 5000
DEFAULT_HOST = '0.0.0.0'

# We initialize the logging in the startup of the whole backend.
# This way we can access the already set up logger in the other modules.
# Also the following configuration can later be easily stored in an external
# configuration file (and then set by the user).
log_format = '%(asctime)s [%(threadName)-12.12s] [%(name)-12.12s] [%(levelname)s]  %(message)s'
# Warning: We do not use __name__  here, since it translates to "__main__"
# when this file is ran directly (such as python runserver.py)
root_logger = logging.getLogger('hbp_nrp_backend')


# This happens within the app process and so it works both in the command line
# and the uWSGI case
def start_ros():  # pragma: no cover
    """
    Starts ROS utilities and cleanup thread in the app process.
    """
    root_logger.info("Starting ROS node")
    # Block until connection to ROS master is established, and initialize a backend node
    rospy.init_node("nrp_backend")
    rosparam.set_param("/use_sim_time", "true")

    rospy_thread = Thread(target=rospy.spin)
    rospy_thread.setDaemon(True)
    rospy_thread.start()

    root_logger.info("Starting cleanup thread")
    cleanup_thread = Thread(target=clean_simulations)
    cleanup_thread.setDaemon(True)
    cleanup_thread.start()


def __process_args():  # pragma: no cover
    """
    Processes the arguments to the server.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--logfile', dest='logfile',
                        help='specify the logfile for the ExDBackend')
    parser.add_argument('--port', dest='port',
                        help='specify the application server\'s port')
    parser.add_argument('-p', '--pycharm',
                        dest='pycharm',
                        help='debug with pyCharm. IP adress and port are needed.',
                        nargs='+')
    args = parser.parse_args()

    if args.pycharm:
        # pylint: disable=import-error
        import pydevd

        pydevd.settrace(args.pycharm[0],
                        port=int(args.pycharm[1]),
                        stdoutToServer=True,
                        stderrToServer=True)

    return args


def __init_console_logging():  # pragma: no cover
    """
    Initialize the logging to stdout.
    """

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)

    assert os.environ.get('NRP_MODELS_DIRECTORY') is not None


def init_logging(args):  # pragma: no cover
    """
    Initialize the logging.
    """

    if __name__ == '__main__':
        try:
            file_handler = logging.FileHandler(args.logfile)
            file_handler.setFormatter(logging.Formatter(log_format))
            root_logger.setLevel(logging.DEBUG)
            root_logger.addHandler(file_handler)
            return
        except (AttributeError, IOError) as _:
            __init_console_logging()
            root_logger.warn("Could not write to specified logfile or no logfile specified, " +
                             "logging to stdout now!")
    else:
        # Started with uWSGI or any other framework. Logging is done through
        # the console.
        __init_console_logging()
        root_logger.warn("Application started with uWSGI or any other framework. logging "
                         "to console by default !")


# Detect uwsgi, start ros and initialize multithreading support
if __name__.find("uwsgi_file") == 0:  # pragma: no cover
    start_ros()
    app.wsgi_app = RestSyncMiddleware(app.wsgi_app, app)
    _args = __process_args()
    init_logging(_args)

# This is executed in local install mode without uwsgi
if __name__ == '__main__':  # pragma: no cover
    start_ros()
    app.wsgi_app = RestSyncMiddleware(app.wsgi_app, app)

    _args = __process_args()
    init_logging(_args)
    port = DEFAULT_PORT
    try:
        port = int(_args.port)
    except (TypeError, ValueError) as _:
        root_logger.warn(
            "Could not parse port, will use default port: " + str(DEFAULT_PORT))
    root_logger.info("Starting the REST backend server now ...")
    app.run(port=port, host=DEFAULT_HOST, threaded=True)
    root_logger.info("REST backend server terminated.")
    rospy.signal_shutdown("Backend terminates")
