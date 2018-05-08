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
This module implements an utility class for managing notifications during a simulation.
"""

__author__ = 'Alessandro Ambrosano, Georg Hinkel'


import logging


class Notificator(object):
    """
    Notification manager for notification created during a simulation.
    """

    # http://stackoverflow.com/questions/6287459/python-function-of-a-default-argument
    __notification_function = staticmethod(lambda y, z: ())

    @staticmethod
    def register_notification_function(notification_function):
        """
        Registers a notification function where to forward notifications.
        :param notification_function: The function to be registered.
        """
        # May also become a list of notification function if needed
        Notificator.__notification_function = staticmethod(notification_function)

    @staticmethod
    def notify(message, update_progress):
        """
        Forwards a notification to the currently registered notification function.
        :param message: Title of the first subtask. Could be empty (example: loading Virtual Room).
        :param update_progress: Boolean. Index of current subtask should be updated? (usually yes).
        """
        Notificator.__notification_function(message, update_progress)


class NotificatorHandler(logging.Handler):
    """
    Log handler that forwards any logged messages to the notificator
    """

    def __init__(self):
        super(NotificatorHandler, self).__init__()

    def emit(self, record):
        """
        Emits the record to the notificator

        :param record: The log record
        """
        if record.levelno == logging.INFO:
            try:
                Notificator.notify(record.getMessage(), False)
            # pylint: disable=broad-except
            except Exception:
                self.handleError(record)
