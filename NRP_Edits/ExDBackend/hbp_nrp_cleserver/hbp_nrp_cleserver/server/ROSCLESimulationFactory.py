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
Advertise a ROS service to start new simulations.
"""

import logging
import rospy
import threading
import os
import argparse
import sys
import hbp_nrp_cle
import traceback
import signal
import dateutil.parser as datetime_parser
# This package comes from the catkin package ROSCLEServicesDefinitions
# in the GazeboRosPackage folder at the root of this CLE repository.
from cle_ros_msgs import srv
from hbp_nrp_cleserver.server import ROS_CLE_NODE_NAME, SERVICE_CREATE_NEW_SIMULATION, \
    SERVICE_VERSION, SERVICE_IS_SIMULATION_RUNNING
from hbp_nrp_cleserver.server.PlaybackServer import PlaybackSimulationAssembly

from hbp_nrp_commons.generated import bibi_api_gen, exp_conf_api_gen
from pyxb import ValidationError, NamespaceError
from hbp_nrp_cleserver.server import ServerConfigurations
import gc

__author__ = "Lorenzo Vannucci, Stefan Deser, Daniel Peppicelli"

logger = logging.getLogger('hbp_nrp_cleserver')

# Warning: We do not use __name__  here, since it translates to __main__
# when this file is run directly (such as python ROSCLESimulationFactory.py)


class ROSCLESimulationFactory(object):
    """
    The purpose of this class is to start simulation thread and to
    provide a ROS service for that. Only one simulation can run at a time.
    """

    def __init__(self):
        """
        Create a CLE simulation factory.
        """
        logger.debug("Creating new CLE server.")
        self.running_simulation_thread = None
        self.__is_running_simulation_terminating = False
        self.simulation_terminate_event = threading.Event()

        self.__create_simulation_service = None

    def initialize(self):
        """
        Initializes the Simulation factory
        """
        rospy.init_node(ROS_CLE_NODE_NAME, anonymous=True)
        self.__create_simulation_service = rospy.Service(
            SERVICE_CREATE_NEW_SIMULATION, srv.CreateNewSimulation, self.create_new_simulation
        )
        rospy.Service(
            SERVICE_IS_SIMULATION_RUNNING, srv.IsSimulationRunning, self.is_simulation_running
        )
        rospy.Service(SERVICE_VERSION, srv.GetVersion, self.get_version)

    def except_hook(self, e):
        """
        Gets called when the simulation server has to shut down due to an exception

        :param e: The exception that caused the simulation server to give up
        """
        logger.exception(e)
        logger.info("Giving up the simulation server")
        self.__create_simulation_service.shutdown()

    @staticmethod
    def run():
        """
        Start the factory and wait indefinitely. (see rospy.spin documentation)
        """
        rospy.spin()

    # service_request is an unused but mandatory argument
    # pylint: disable=unused-argument
    @staticmethod
    def get_version(service_request):
        """
        Handler for the ROS service. Retrieve the CLE version.
        Warning: Multiprocesses can not be used: https://code.ros.org/trac/ros/ticket/972

        :param: service_request: ROS service message (defined in hbp ROS packages)
        """
        return str(hbp_nrp_cle.__version__)

    # service_request is an unused but mandatory argument
    # pylint: disable=unused-argument
    def is_simulation_running(self, request):
        """
        Handler for the ROS service to retrieve information whether there is a simulation running

        :param request: The ROS Service message
        :return: True, if a simulation is running, otherwise False
        """
        return self.running_simulation_thread is not None and \
            self.running_simulation_thread.is_alive()

    # pylint: disable=too-many-locals, too-many-statements, too-many-branches
    def create_new_simulation(self, service_request):
        """
        Handler for the ROS service. Spawn a new simulation.
        Warning: Multiprocesses can not be used: https://code.ros.org/trac/ros/ticket/972

        :param: service_request: ROS service message (defined in hbp ROS packages)
        """
        logger.info("Create new simulation request")

        if self.__is_running_simulation_terminating:
            logger.info("Waiting for previous simulation to terminate")
            self.simulation_terminate_event.wait()

        if (self.running_simulation_thread is None) or \
                (not self.running_simulation_thread.is_alive()):
            logger.info("No simulation running, starting a new simulation.")

            environment_file = service_request.environment_file
            gzserver_host = service_request.gzserver_host
            reservation = service_request.reservation
            sim_id = service_request.sim_id
            exd_config_file = service_request.exd_config_file
            timeout = self.__get_timeout(service_request)
            playback_path = service_request.playback_path
            token = service_request.token
            ctx_id = service_request.ctx_id

            logger.info(
                "Preparing new simulation with environment file: %s "
                "and ExD config file: %s.",
                environment_file, exd_config_file
            )
            logger.info("Starting the experiment closed loop engine.")

            # Initializing the simulation
            try:
                logger.info("Read XML Files")
                exd, bibi = get_experiment_data(exd_config_file)

                # user override for number of brain processes
                if exd.bibiConf.processes != service_request.brain_processes:
                    logger.info("User overrode number of brain processes, launching with {0:d} "
                                "brain processes instead of {1:d} specified in ExD conf!"
                                .format(service_request.brain_processes, exd.bibiConf.processes))
                    exd.bibiConf.processes = service_request.brain_processes

                    # do not use MUSIC for overridden single-process simulations
                    if bibi.mode == bibi_api_gen.SimulationMode.SynchronousMUSICNestSimulation and\
                       exd.bibiConf.processes == 1:
                        bibi.mode = bibi_api_gen.SimulationMode.SynchronousNestSimulation

                # backwards compatibility, default to synchronous Nest simulation
                if bibi.mode is None:
                    bibi.mode = bibi_api_gen.SimulationMode.SynchronousNestSimulation

                # simulation playback
                if playback_path:
                    assembly = PlaybackSimulationAssembly

                # single brain process launch
                elif exd.bibiConf.processes == 1:
                    assembly = getattr(ServerConfigurations, bibi.mode)

                # distributed, multi-process launch (inline imports to avoid circular dependencies)
                else:

                    # MUSIC-based Nest distributed simulation
                    if bibi.mode == bibi_api_gen.SimulationMode.SynchronousMUSICNestSimulation:
                        logger.info("Creating distributed MUSICLauncher object")
                        from hbp_nrp_music_interface.launch.MUSICLauncher import MUSICLauncher
                        assembly = MUSICLauncher

                    # non-MUSIC based Nest distributed simulation
                    elif bibi.mode == bibi_api_gen.SimulationMode.SynchronousNestSimulation:
                        logger.info("Creating distributed NestLauncher object")
                        from hbp_nrp_distributed_nest.launch.NestLauncher import NestLauncher
                        assembly = NestLauncher

                    # unsupported multi-process mode
                    else:
                        raise Exception("Unsupported multi-process simulation mode requested: "
                                        "{0:s}".format(str(bibi.mode)))

                # create and initialize the selected launcher
                launcher = assembly(sim_id, exd, bibi,
                                    gzserver_host=gzserver_host,
                                    reservation=reservation,
                                    timeout=timeout,
                                    playback_path=playback_path,
                                    context_id=ctx_id,
                                    token=token)
                try:
                    launcher.initialize(environment_file, self.except_hook)
                # pylint: disable=broad-except
                except Exception:
                    launcher.shutdown()
                    raise

            # pylint: disable=broad-except
            except Exception:
                logger.exception("Initialization failed")
                print sys.exc_info()
                raise

            logger.info("Initialization done")

            self.running_simulation_thread = threading.Thread(
                target=self.__simulation,
                args=(launcher, )
            )
            self.running_simulation_thread.daemon = True
            logger.info(
                "Spawning new thread that will manage the experiment execution.")
            self.running_simulation_thread.start()
        else:
            error_message = "Trying to initialize a new simulation even though the " \
                            "previous one has not been terminated."
            logger.error(error_message)
            raise Exception(error_message)
        return []

    @staticmethod
    def __get_timeout(service_request):
        """
        Gets the timeout for the simulation based on the given request

        :param service_request: The service request
        :return: The time when the simulation will end or None, if no timeout was specified
        """
        if service_request.timeout == "":
            timeout = None
        else:
            timeout = datetime_parser.parse(service_request.timeout)
        return timeout

    def __simulation(self, launcher):
        """
        Main simulation method. Start the simulation from the given script file.

        :param: launcher: The assembled simulation
        """

        self.simulation_terminate_event.clear()

        # pylint: disable=broad-except
        try:
            launcher.run()  # This is a blocking call, not to be confused with
                            # threading.Thread.start
        except Exception, e:
            logger.error("Exception during simulation")
            logger.exception(e)
        # always attempt to shutdown cleanly before raising Exception
        finally:
            self.__is_running_simulation_terminating = True
            try:
                logger.info("Shutdown simulation")
                launcher.shutdown()
            except Exception, e:
                logger.error("Exception during shutdown")
                logger.exception(e)
            finally:
                self.running_simulation_thread = None
                self.__is_running_simulation_terminating = False
                self.simulation_terminate_event.set()
                gc.collect()  # NRRPLT-5374


def get_experiment_basepath(experiment_file_path):
    """
    Get the name of the folder containing the experiment configuration path.

    :param: experiment_file_path: path to the experiment configuration file
    :return: path to the directory that contains the experiment configuration
    """
    return os.path.split(experiment_file_path)[0]


def get_experiment_data(experiment_file_path):
    """
    Parse experiment and bibi and return the objects

    @param experiment_file: experiment file
    @return experiment, bibi, parsed experiment and bibi
    """
    with open(experiment_file_path) as exd_file:
        try:
            experiment = exp_conf_api_gen.CreateFromDocument(exd_file.read())
            experiment.path = experiment_file_path
        except ValidationError, ve:
            raise Exception("Could not parse experiment configuration {0:s} due to validation "
                            "error: {1:s}".format(experiment_file_path, str(ve)))

    bibi_file = experiment.bibiConf.src
    logger.info("Bibi: " + bibi_file)
    experiment_dir = os.path.dirname(experiment_file_path)
    bibi_file_abs = os.path.join(experiment_dir, bibi_file)
    experiment.dir = experiment_dir
    logger.info("BibiAbs:" + bibi_file_abs)
    with open(bibi_file_abs) as b_file:
        try:
            bibi = bibi_api_gen.CreateFromDocument(b_file.read())
            bibi.path = bibi_file_abs
        except ValidationError, ve:
            raise Exception("Could not parse brain configuration {0:s} due to validation "
                            "error: {1:s}".format(bibi_file_abs, str(ve)))
        except NamespaceError, ne:
            # first check to see if the BIBI file appears to have a valid
            # namespace
            namespace = str(ne).split(" ", 1)[0]
            if not namespace.startswith("http://schemas.humanbrainproject.eu/SP10") or \
               not namespace.endswith("BIBI"):
                raise Exception("Unknown brain configuration file format for: {0:s} with "
                                "namespace: {1:s}".format(bibi_file_abs, namespace))

            # notify the user that their file is out of date
            raise Exception("The BIBI file for the requested experiment is out of date and no "
                            "longer supported. Please contact neurorobotics@humanbrainproject.eu "
                            "with the following information for assistance in updating this file."
                            "\n\nExperiment Configuration:\n\tName: {0:s}\n\tBIBI: {1:s}"
                            "\n\tVersion: {2:s}".format(experiment.name, bibi_file, namespace))

    return experiment, bibi


# pylint: disable=unused-argument
def print_full_stack_trace(sig, frame):
    """
    Log the stack trace of all the threads
    :param sig: The received signal
    :param frame: The current stack frame
    """
    logger.warn("*** STACKTRACE - START ***")
    code = []
    # pylint: disable=protected-access
    for threadId, stack in sys._current_frames().items():
        code.append("# ThreadID: %s" % threadId)
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename,
                                                        lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    for line in code:
        logger.warn(line)
    logger.warn("*** STACKTRACE - END ***")


def __except_hook(ex_type, value, ex_traceback):
    """
    Logs the unhandled exception

    :param ex_type: The exception type
    :param value: The exception value
    :param ex_traceback: The traceback
    """
    logger.critical(
        "Unhandled exception of type {0}: {1}".format(ex_type, value))
    logger.exception(ex_traceback)


def set_up_logger(logfile_name, verbose=False):
    """
    Configure the root logger of the CLE application
    :param: logfile_name: name of the file created to collect logs
    :param: verbose: increase logging verbosity
    """
    # We initialize the logging in the startup of the whole CLE application.
    # This way we can access the already set up logger in the children modules.
    # Also the following configuration can later be easily stored in an external
    # configuration file (and then set by the user).
    log_format = '%(asctime)s [%(threadName)-12.12s] [%(name)-12.12s] [%(levelname)s]  %(message)s'

    try:
        file_handler = logging.FileHandler(logfile_name)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.root.addHandler(file_handler)
    except (AttributeError, IOError) as _:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(log_format))
        logging.root.addHandler(console_handler)
        logger.warn("Could not write to specified logfile or no logfile specified, "
                    "logging to stdout now!")
    logging.root.setLevel(logging.DEBUG if verbose else logging.INFO)

    sys.excepthook = __except_hook


def main():
    """
    Main function of ROSCLESimulationFactory
    """
    if os.environ["ROS_MASTER_URI"] == "":
        raise Exception("You should run ROS first.")

    signal.signal(signal.SIGUSR1, print_full_stack_trace)
    parser = argparse.ArgumentParser()
    parser.add_argument('--logfile', dest='logfile',
                        help='specify the CLE logfile')
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    parser.add_argument('-p', '--pycharm',
                        dest='pycharm',
                        help='debug with pyCharm. IP adress and port are needed.',
                        nargs='+')
    args = parser.parse_args()

    if args.pycharm:  # pragma: no cover
        # pylint: disable=import-error
        import pydevd

        pydevd.settrace(args.pycharm[0],
                        port=int(args.pycharm[1]),
                        stdoutToServer=True,
                        stderrToServer=True)

    server = ROSCLESimulationFactory()
    server.initialize()
    set_up_logger(args.logfile, args.verbose)
    server.run()
    logger.info("CLE Server exiting.")


if __name__ == '__main__':  # pragma: no cover
    main()
