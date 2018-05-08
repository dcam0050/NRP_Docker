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
This module contains a small python program that checks the availability of a local program
"""

from hbp_nrp_watchdog.Timer import Timer
import psutil
import logging


__author__ = "Georg Hinkel"


logger = logging.getLogger(__name__)


class Watchdog(object):
    """
    This class implements a watchdog that regularly checks whether a given process is still alive
    """
    def __init__(self, process, callback, pid=None, interval=1):
        """
        Creates a watchdog to monitor whether the given process is still running

        :param process: The process name that should be watched for
        :param callback: The method pointer that should be called when the process disappeared
        :param pid: The pid of the watched process, if already known (otherwise looked up)
        :param interval: The interval in which the process should be polled
        """
        self.__pid = pid
        self.__process = process
        self.__callback = callback
        self.__timer = Timer(interval, self._watch)

        if pid is not None:
            try:
                p = psutil.Process(pid)
                if process not in p.name():
                    logger.warn("The given process id is not valid. The process with the given "
                                "name is called {0} and does not match the given pattern {1}."
                                .format(p.name(), process))
                    self.__pid = None
            except psutil.NoSuchProcess:
                logger.warn("The specified process id does not exist. Ignoring process id")
                self.__pid = None

    def _watch(self):
        """
        Watches the process
        """
        if not self._is_alive():
            self.__callback()

    def reset(self):
        """
        Resets the watched pid
        """
        self.__pid = None

    @property
    def pid(self):
        """
        The process id that is watched for
        """
        return self.__pid

    def start(self):
        """
        Starts the watchdog in a new thread
        """
        self.__timer.start()

    def stop(self):
        """
        Stops the watchdog
        """
        self.__timer.cancel_all()

    def _is_alive(self):
        """
        Determines whether the watched process is still alive

        :return:
        """
        if self.__pid is None:
            for p in psutil.process_iter():
                if self.__process in p.name():
                    self.__pid = p.pid
                    return True
            if self.__pid is None:
                logger.info("Process {0} could not be found".format(self.__process))
                return False
        return psutil.pid_exists(self.__pid)
