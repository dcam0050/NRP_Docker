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
This module contains classes to access the watchdog functionality via a ROS in a distributed setting
"""

import rospy
from std_msgs.msg import Bool
from hbp_nrp_watchdog.Watchdog import Watchdog
from hbp_nrp_watchdog.Timer import Timer
import time

__author__ = "Georg Hinkel"


class WatchdogServer(Watchdog):
    """
    Represents a class that exposes the watchdog functionality via a ROS topic
    """

    def __init__(self, process, topic, interval=1):
        """
        Creates a watchdog that pushes any sights to the given topic

        :param process: The process name
        :param topic: The target topic
        :param interval: The interval in which the process is watched, by default 1s
        """
        super(WatchdogServer, self).__init__(process, None, None, interval)
        self.__publisher = rospy.Publisher(topic, Bool, queue_size=1)

    def _watch(self):
        """
        Watches the process
        """
        is_alive = self._is_alive()
        self.__publisher.publish(is_alive)

    def stop(self):
        """
        Stops the watchdog
        """
        super(WatchdogServer, self).stop()
        self.__publisher.unregister()


class WatchdogClient(object):
    """
    Represents a class that receives watchdog signals from a different machine via ROS
    """

    def __init__(self, topic, callback, timeout=5):
        """
        Creates a new watchdog client

        :param topic: The topic on which the watchdog information will be made available
        :param timeout: The maximum allowed time between two heartbeat messages (in seconds)
        """
        self.__subscriber = rospy.Subscriber(topic, Bool, self.__watchdog_handler)
        self.__timeout = timeout
        self.__last_sight = None
        self.__timer = Timer(1, self.__timer_check)
        self.__callback = callback

    def start(self, delay=None):
        """
        Starts the watchdog client
        """
        self.__last_sight = time.time()
        if delay is not None:
            self.__last_sight += delay
        self.__timer.start()

    def stop(self):
        """
        Stops the watchdog client
        """
        self.__subscriber.unregister()
        self.__timer.cancel_all()

    def __timer_check(self):
        """
        Checks whether the last message from the watchdog server is at most (timeout)
        seconds old
        """
        curr_time = time.time()
        sight_time = self.__last_sight
        if sight_time is not None and curr_time - sight_time > self.__timeout:
            self.__callback()

    def __watchdog_handler(self, data):
        """
        Handles a new incoming data message from the watchdog server

        :param data: The data sent from the watchdog server as a BoolResponse message
        """
        self.__last_sight = time.time()
        if not data.data:
            self.__callback()


if __name__ == "__main__":  # pragma: no cover
    import signal
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name", dest="name")
    parser.add_argument("-p", "--process", dest='process')
    parser.add_argument("-t", "--topic", dest='topic')
    parser.add_argument('-d', '--pycharm',
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

    rospy.init_node(args.name)
    server = WatchdogServer(args.process, args.topic)
    signal.signal(signal.SIGINT, lambda sig, stack: server.stop())
    server.start()
    rospy.spin()
