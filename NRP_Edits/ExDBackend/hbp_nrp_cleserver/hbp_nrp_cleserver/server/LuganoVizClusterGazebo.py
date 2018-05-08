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
#!/usr/bin/env python
"""
This module contains the classes needed to have all gazebo services running on the Lugano viz
cluster.
"""

import pexpect
import time
import logging
import os
import sys
import netifaces

from hbp_nrp_commons.cluster.LuganoVizCluster import LuganoVizCluster, notificator, logger
from hbp_nrp_cleserver.server.GazeboInterface import IGazeboServerInstance
from hbp_nrp_watchdog.WatchdogServer import WatchdogClient


class LuganoVizClusterGazebo(LuganoVizCluster, IGazeboServerInstance):
    """
    Represents an instance of gzserver running on the Lugano viz cluster.

    There is a wide usage of pexpect in this class because of the remote connections via
    ssh needed to access the Lugano machines. Every time a remote command is launched,
    expect() is used to match strings with the shell output in order to understand its status.
    """

    DEFAULT_GZSERVER_PORT = 11345
    GAZEBO_PROCESSES = 4
    GAZEBO_GPUS = 1
    VGLCONNECT_CMD = 'vglconnect bbpnrsoa@{node}.cscs.ch -M -K'

    def __init__(self, timezone=None, reservation=None):

        # direct first parent is LuganoVizCluster, reuse the CLE user notifier logger
        super(LuganoVizClusterGazebo, self).__init__(LuganoVizClusterGazebo.GAZEBO_PROCESSES,
                                                     LuganoVizClusterGazebo.GAZEBO_GPUS,
                                                     timezone, reservation)

        # secondary parent is the IGazeboServerInstance interface
        IGazeboServerInstance.__init__(self)

        # local gazebo specific allocation information
        self._x_server_process = None
        self._remote_xvnc_process = None
        self._gazebo_remote_process = None
        self._remote_display_port = -1
        self._watchdog_client = None

    def _start_fake_X(self):
        """
        Start an in memory graphical server. Xvfb or X virtual framebuffer is a display server
        implementing the X11 display server protocol. In contrast to other display servers Xvfb
        performs all graphical operations in memory without showing any screen output. The goal
        is to be able to use vglconnect from the local node to the remote viz cluster node. For
        that, we do need an XServer.

        Xvfb startup should generally produce no output, but handle the following cases:
        - server is already running (e.g. started by root and could not be killed, valid)
        - server needs to initialize GPU/hardware extensions (valid but strange configuration)
        - no output (expected, handled by short timeout with no output)
        - failure to launch (EOF when process reports failure, invalid so abort)
        """
        notificator.info('Starting backend graphics server')
        self._x_server_process = pexpect.spawn('Xvfb :1', logfile=logger)
        result = self._x_server_process.expect(
            [
                'Server is already active for display',
                'Initializing built-in extension',
                pexpect.TIMEOUT,    # no output (expected)
                pexpect.EOF
            ],       # crash/failed launch
            self.SMALL_TIMEOUT
        )

        if result == 3:
            raise(XvfbXvnError("Cannot start Xvfb"))

    def _spawn_vglconnect(self):
        """
        Return a pexpect object connected to the allocated viz cluster node.
        """
        if self._node is None or self._allocation_process is None:
            raise(Exception("Cannot connect to a cluster node without a proper Job allocation."))

        # Ensure $HOME is valid otherwise vglconnect will fail to write session data, this depends
        # on if we are launching from a backend VM or from another cluster node via SSH session
        env = dict(os.environ, DISPLAY=':1')
        if not os.path.exists(os.environ.get('HOME')):
            env['HOME'] = '/gpfs/bbp.cscs.ch/home/bbpnrsoa'

        # Launch a clean bash session and vglconnect with reused ssh authentication
        vglconnect_process = pexpect.spawn('bash', env=env, logfile=logger)
        vglconnect_process.sendline(self.VGLCONNECT_CMD.format(node=self._node))

        # We do expect a prompt here
        result = vglconnect_process.expect([r'\[bbpnrsoa@' + self._node + r'\ ~\]\$',
                                            'password',
                                            pexpect.TIMEOUT])
        if result == 1:
            raise(Exception("Viz cluster node can't be used without password."))
        if result == 2:
            raise(Exception("Cannot connect to node."))

        # Always load virtualgl on vgl connections to be able to use a 3D display
        vglconnect_process.sendline('module load virtualgl')
        vglconnect_process.sendline('export VGL_FORCEALPHA=1')  # force 32-bit buffers

        return vglconnect_process  # This object has to live until the end.

    def _start_xvnc(self):
        """
        Start a remote Xvnc server. This is the only (known to us) way to have Gazebo using
        the graphic card.
        """
        if self._node is None or self._allocation_process is None:
            raise(Exception("Cannot connect to a cluster node without a proper Job allocation."))

        notificator.info('Starting cluster node graphics server')
        self._remote_xvnc_process = self._spawn_vglconnect()

        # Cleanup any leftover Xvnc sessions from our user on this cluster node from failed
        # sessions (e.g. crashes or other rare network issues). This won't impact other cluster
        # node users or their running Xvnc sessions.
        self._remote_xvnc_process.sendline('killall -9 Xvnc')

        # Find the first available Xvnc port to use, we are not the only cluster user so we cannot
        # guarantee that no other Xvnc is running on a port or that we have access to running
        # sessions. Ohter users may also spawn instances arbitrarily, this ensures a valid session.
        for p in xrange(10, 100):
            self._remote_xvnc_process.sendline('Xvnc :' + str(p))
            result = self._remote_xvnc_process.expect([
                'created VNC server for screen 0',
                'Server is already active for display',
                'server already running',
                pexpect.TIMEOUT], self.TIMEOUT
            )

            # valid Xvnc session spawned on port, stop searching
            if result == 0:
                self._remote_display_port = p
                return

            # timeout while trying to start Xvnc, abort
            elif result == 3:
                raise(XvfbXvnError("Cannot start Xvnc, unknown error."))

        # unable to find an open Xvnc port (very unlikely), abort
        raise(XvfbXvnError("Cannot start Xvnc, no open display ports."))

    def _start_gazebo(self, ros_master_uri, models_path=None, gzserver_args=None):
        """
        Start gazebo on the remote server
        """
        if self._node is None or self._allocation_process is None:
            raise(Exception("Cannot connect to a cluster node without a proper Job allocation."))
        if self._remote_display_port == -1:
            raise(Exception("Gazebo needs a remote X Server running"))

        notificator.info('Configuring the cluster node environment')
        self._gazebo_remote_process = self._spawn_vglconnect()

        # Kill any active gzservers (this should never happen).
        self._gazebo_remote_process.sendline('killall -9 gzserver')

        # source environment modules init file
        self._gazebo_remote_process.sendline('source /opt/rh/python27/enable')
        self._gazebo_remote_process.sendline('source /usr/share/Modules/init/bash 2> /dev/null')

        # configure environment variables and get project path
        proj_path = self._configure_environment(self._gazebo_remote_process)

        # loading the environment modules configuration files
        modules_path = proj_path + 'server-scripts/nrp-services-modules.sh'
        self._gazebo_remote_process.sendline('source %s' % modules_path)
        result = self._gazebo_remote_process.expect(['NRP modules loaded.',
                                                      pexpect.TIMEOUT])

        if result == 1:
            raise(Exception("Error while configuring cluster node, gpfs may not be mounted." +
                            str(self._gazebo_remote_process.after)))

        # configure variables after all module loads (that could overwrite values)
        self._gazebo_remote_process.sendline('export DISPLAY=:' + str(self._remote_display_port))
        self._gazebo_remote_process.sendline('export ROS_MASTER_URI=' + ros_master_uri)

        # Use the appropriate dev or staging models based on this backend version
        self._gazebo_remote_process.sendline('export GAZEBO_MODEL_PATH=%s/models' % proj_path)

        # disable online (unreachable) model searching, only use local NRP models
        self._gazebo_remote_process.sendline('export GAZEBO_MODEL_DATABASE_URI=')

        # copy robot, if needed
        if models_path is not None:
            notificator.info("Copy robot to remote server")
            self._copy_to_remote(models_path)
            self._gazebo_remote_process.sendline('export GAZEBO_MODELS_PATH='
                                                  '{trg}:$GAZEBO_MODELS_PATH'
                                                  .format(trg=self._tmp_dir))

        # launch the watchdog inside the NRP virtualenv
        self._gazebo_remote_process.sendline('source %s/platform_venv/bin/activate' % proj_path)
        self._gazebo_remote_process.sendline('sleep 10 && python '
                                              '-m hbp_nrp_watchdog.WatchdogServer -n Watchdog '
                                              '-p gzserver -t /gazebo/health &')
        self._gazebo_remote_process.sendline('export WATCHDOG_PID=$!')
        self._gazebo_remote_process.sendline('deactivate')

        # activate ROS python venv to launch Gazebo
        self._gazebo_remote_process.sendline('source $ROS_PYTHON_VENV/bin/activate')

        # configure command line arguments for gzserver if provided
        if gzserver_args is not None:
            self._gazebo_remote_process.sendline('export GZSERVER_ARGS="%s"' % gzserver_args)

        # launch Gazebo with virtualgl, use -nodl to redirect native opengl calls to virtualgl
        notificator.info('Starting Gazebo server on the cluster node')
        self._gazebo_remote_process.sendline(
            'vglrun -nodl $GAZEBO_BIN_DIR/gzserver ' +
            '$GZSERVER_ARGS ' +
            '--pause ' +
            '-s $ROS_HBP_PACKAGES_LIB_DIR/libgazebo_ros_api_plugin.so ' +
            '-s $ROS_HBP_PACKAGES_LIB_DIR/libgazebo_ros_paths_plugin.so ' +
            '-s $ROS_HBP_PACKAGES_LIB_DIR/libgazebo_ros_recording_plugin.so ' +
            '-s $ROS_HBP_PACKAGES_LIB_DIR/libgazebo_ros_playback_plugin.so ' +
            '--verbose')

        result = self._gazebo_remote_process.expect(['Gazebo multi-robot simulator',
                                                      pexpect.TIMEOUT])

        if result == 1:
            raise(Exception("Error while starting gazebo: " +
                            str(self._gazebo_remote_process.after)))

    def _start_watchdog_client(self):
        """
        Starts the watchdog client
        """
        self._watchdog_client = WatchdogClient("/gazebo/health", self._raise_gazebo_died)
        # Delay starting the watchdog client by 10s (because we delay the start of the watchdog 10s)
        self._watchdog_client.start(delay=10)

    def start(self, ros_master_uri, models_path=None, gzserver_args=None):
        """
        Start gzserver on the Lugano viz cluster
        """
        try:
            self._allocate_job(reuse_nodes=False) # only one gzserver per cluster node
            self._start_fake_X()
            self._start_xvnc()
            self._start_gazebo(ros_master_uri, models_path, gzserver_args)
            self._start_watchdog_client()
        # pylint: disable=broad-except
        except Exception:
            logger.exception('Failure launching gzserver on remote node.')

            # always cleanup, but only raise the start exception up, not any shutdown errors
            try:
                self.stop()
            # pylint: disable=broad-except
            except Exception:
                pass

            raise

    def try_extend(self, new_timeout):
        """"
        Verifies that the gazebo can accept the new simulation timeout
        Returns whether the timeout is accepted
        """
        return self._allocation_time is None or new_timeout <= self._allocation_time

    @property
    def gazebo_master_uri(self):
        """
        Returns a string containing the gzserver master
        URI (like:'http://bbpviz001.cscs.ch:11345')
        """
        if self._node is not None:
            return ('http://' +
                    self._node +
                    self.NODE_DOMAIN +
                    ':' +
                    str(self.DEFAULT_GZSERVER_PORT))
        else:
            return None

    def stop(self):

        # stop the local watchdog client before terminating the remote side
        if self._watchdog_client is not None:
            self._watchdog_client.stop()
            self._watchdog_client = None

        # cluster node cleanup (this can fail, but make sure we always release the job below)
        try:
            # terminate running remote watchdog, gzserver, and invoking bash shell
            if self._gazebo_remote_process:
                notificator.info('Stopping Gazebo server on the cluster node')
                self._gazebo_remote_process.sendcontrol('z')
                self._gazebo_remote_process.sendline('kill -v -n 9 $WATCHDOG_PID')
                self._gazebo_remote_process.sendline('killall -v -9 gzserver')
                self._gazebo_remote_process.expect([pexpect.TIMEOUT,
                                                     'Killed',
                                                     'gzserver: no process killed'], self.TIMEOUT)
                self._gazebo_remote_process.terminate()

            # directly terminate Xvnc process (not invoked via bash)
            if self._remote_xvnc_process:
                notificator.info('Stopping cluster node graphics server')
                self._remote_xvnc_process.terminate()

        # pylint: disable=broad-except
        except Exception:
            logger.exception('Error cleaning up cluster node.')
        finally:
            self._gazebo_remote_process = None
            self._remote_xvnc_process = None
            self._remote_display_port = -1

        # SLURM cleanup and temporary folder deletion (must happen after any cluster cleanup as this
        # will deallocate the process)
        LuganoVizCluster.stop(self)

        # cleserver cleanup Xvfb, this is not critical
        if self._x_server_process:
            notificator.info('Stopping backend graphics server')
            self._x_server_process.terminate()
            self._x_server_process = None

    def restart(self, ros_master_uri):
        notificator.info("Restarting Gazebo server on the cluster")
        self.stop()
        self.start(ros_master_uri)


class XvfbXvnError(Exception):
    """
    This exception class is a marker for errors coming from Xvfb or Xvn.
    """
    pass


def _get_roscore_master_uri():
    """
    Return roscore master URI. If the env variable ROS_MASTER_URI is not set,
    then construct it like this: http:// + local_ip + :11311
    """

    master_uri = os.environ.get("ROS_MASTER_URI")
    if not master_uri:
        local_ip = netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr']
        master_uri = 'http://' + local_ip + ':11311'
    return master_uri

# Useful to test out the code.
if __name__ == '__main__':  # pragma: no cover
    logger.setLevel(logging.DEBUG)
    log_format = '%(asctime)s [%(threadName)-12.12s] [%(name)-12.12s] [%(levelname)s]  %(message)s'
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    gazebo = LuganoVizClusterGazebo()
    gazebo.start(_get_roscore_master_uri())
    time.sleep(100)
    gazebo.stop()
