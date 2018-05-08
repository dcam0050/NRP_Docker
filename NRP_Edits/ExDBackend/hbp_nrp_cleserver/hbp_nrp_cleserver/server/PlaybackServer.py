# pylint: disable=too-many-lines
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
Playback ROS wrapper overriding the SimulationServer implementation for playback
"""
from hbp_nrp_cleserver.server.SimulationServer import SimulationServer
from hbp_nrp_cleserver.server.PlaybackServerLifecycle import PlaybackServerLifecycle
from hbp_nrp_cleserver.server.CLEGazeboSimulationAssembly import GazeboSimulationAssembly
from hbp_nrp_cleserver.bibi_config.notificator import NotificatorHandler

import rospy
from cle_ros_msgs import srv
from rosgraph_msgs.msg import Clock
from std_srvs.srv import Trigger

import logging

logger = logging.getLogger(__name__)

# We use the logger hbp_nrp_cle.user_notifications in the CLE to log
# information that is useful to know for the user.
# In here, we forward any info message sent to this logger to the notificator
gazebo_logger = logging.getLogger('hbp_nrp_cle.user_notifications')
gazebo_logger.setLevel(logging.INFO)
notificator_handler = NotificatorHandler()


class PlaybackServer(SimulationServer):
    """
    Playback ROS server overriding the ROSCLEServer implementation for playback
    """

    def __init__(self, sim_id, timeout, gzserver, notificator):
        """
        Create the playback server

        :param sim_id: The simulation id
        :param timeout: The datetime when the simulation runs into a timeout
        :param gzserver: Gazebo simulator launch/control instance
        :param notificator: ROS state/error notificator interface
        """
        super(PlaybackServer, self).__init__(sim_id, timeout, gzserver, notificator)

        # simulation time from playback for frontend display
        self.__sim_clock = 0
        self.__sim_clock_subscriber = None

        # path to current active playback, accessible by Gazebo
        self.__playback_path = None

        # services to interact with playback plugin
        self.__service_configure = None
        self.__service_start = None
        self.__service_pause = None
        self.__service_stop = None
        self.__service_reset = None

    @property
    def playback_path(self):
        """
        Gets the playback path
        """
        return self.__playback_path

    @playback_path.setter
    def playback_path(self, value):
        """
        Sets the playback path
        """
        self.__playback_path = value

    def prepare_simulation(self, except_hook=None):
        """
        The CLE will be initialized within this method and ROS services for
        starting, pausing, stopping and resetting are setup here.

        :param playback_path: Recorded simulation playback path accessible by gzserver.
        :param except_hook: A handler method for critical exceptions
        """

        super(PlaybackServer, self).prepare_simulation(except_hook)

        def clock_callback(t):
            """
            This function is called when there is a new clock message

            :param t: The current simulation time
            """
            self.__sim_clock = t.clock.secs
        self.__sim_clock_subscriber = rospy.Subscriber('/clock', Clock, clock_callback)

        # instantiate the service proxies
        base = '/gazebo/playback/%s'
        self.__service_configure = rospy.ServiceProxy(base % 'configure', srv.SimulationPlayback)
        self.__service_start = rospy.ServiceProxy(base % 'start', Trigger)
        self.__service_pause = rospy.ServiceProxy(base % 'pause', Trigger)
        self.__service_stop = rospy.ServiceProxy(base % 'stop', Trigger)
        self.__service_reset = rospy.ServiceProxy(base % 'reset', srv.SimulationPlayback)

        # configure the plugin path and check for failure
        resp = self.__service_configure(self.__playback_path)
        if not resp.success:
            raise Exception('Configuration of playback plugin failed: %s' % resp.message)

    def _create_lifecycle(self, except_hook):
        """
        Creates the lifecycle for the current simulation
        :param except_hook: An exception handler
        :return: The created lifecycle
        """
        return PlaybackServerLifecycle(self.simulation_id, self, except_hook)

    def _create_state_message(self):
        """
        Creates a status message
        :return: A dictionary with status information
        """
        return {
            'simulationTime': int(self.__sim_clock),
            'realTime': int(self.__sim_clock),
            'transferFunctionsElapsedTime': {},
            'brainsimElapsedTime': 0,
            'robotsimElapsedTime': 0
        }

    def process_lifecycle_command(self, command):
        """
        Issue a lifecycle state change as a playback plugin command

        :param command One of the supported commands [start, stop, pause]
        """

        # ensure we have configured the plugin before issuing commands
        if not self.__service_start or not self.__service_stop or not self.__service_pause:
            raise Exception('Playback server has not been configured, cannot issue commands!')

        # ensure the command is valid
        if command not in ['start', 'stop', 'pause']:
            raise ValueError('Invalid playback command: %s!' % command)

        # issue the service command
        # pylint: disable=bare-except
        try:
            if command == 'start':
                resp = self.__service_start()
            elif command == 'pause':
                resp = self.__service_pause()
            elif command == 'stop':
                resp = self.__service_stop()

            # check for playback command failure
            if not resp.success:
                raise Exception('Playback command failed: %s' % resp.message)

        # allow stop to fail during crash/shutdown
        except:
            if command != 'stop':
                raise

    def reset_simulation(self, request):
        """
        Reset the playback

        :param request: the ROS service request message (cle_ros_msgs.srv.ResetSimulation).
        """

        # if uninitialized, we can't reset the path
        if not self.__playback_path:
            return False, 'Playback path is not configured, cannot reset!'

        # reset the internal status clock (probably happens anyway)
        self.__sim_clock = 0

        # perform the reset and (re-)configure
        resp = self.__service_reset(self.__playback_path)
        return resp.success, resp.message

    def shutdown(self):
        """
        Shutdown the playback
        """
        super(PlaybackServer, self).shutdown()
        if self.__sim_clock_subscriber is not None:
            self.__sim_clock_subscriber.unregister()
            self.__sim_clock_subscriber = None


class PlaybackSimulationAssembly(GazeboSimulationAssembly):
    """
    This class is used to realize the assembly of a playback simulation
    """

    def __init__(self, sim_id, exc, bibi, **par):
        """
        Creates a new simulation assembly to simulate an experiment using the CLE and Gazebo
        :param sim_id: The simulation id
        :param exc: The experiment configuration
        :param bibi: The BIBI configuration
        """
        super(PlaybackSimulationAssembly, self).__init__(sim_id, exc, bibi)
        self.__playback_path = par.get('playback_path', None)
        self.playback = None

    def _initialize(self, environment, except_hook):
        """
        Internally initialize the simulation
        :param environment: The environment that should be simulated
        :param except_hook: A method that should be called when there is a critical error
        """
        # TODO: validate playback path / download with storage server API

        # create the CLE server and lifecycle first to report any failures
        # properly
        logger.info("Creating Playback Server")
        self.playback = PlaybackServer(self.sim_id, self._timeout, self.gzserver,
                                         self.ros_notificator)

        # disable roslaunch for playback
        self.exc.rosLaunch = None

        # start Gazebo simulator and bridge (RNG seed is irrelevant for
        # playback)
        self._start_gazebo(123456, self.__playback_path, None, environment)

        # create playback CLE server
        logger.info("Preparing Playback Server")
        self.playback.prepare_simulation(self.__playback_path, except_hook)

    def _shutdown(self, notifications):
        """
        Shutdown the CLE and any hooks before shutting down Gazebo

        :param notifications: A flag indicating whether notifications should be attempted to send
        """
        try:
            if notifications:
                self.ros_notificator.update_task("Shutting down Playback",
                                                 update_progress=True, block_ui=False)

            self.playback.shutdown()
        #pylint: disable=broad-except
        except Exception, e:
            logger.error("The cle server could not be shut down")
            logger.exception(e)

    def run(self):
        """
        Runs the simulation
        """
        self.playback.run()
