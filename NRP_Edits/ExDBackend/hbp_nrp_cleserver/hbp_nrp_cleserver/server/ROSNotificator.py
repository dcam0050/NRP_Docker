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
This module implements a ROS Notificator interface for status/error messages.
"""

import contextlib
import json
import logging
import rospy

from std_msgs.msg import String
from cle_ros_msgs.msg import CLEError

from hbp_nrp_cleserver.server import ROS_CLE_NODE_NAME, TOPIC_STATUS, TOPIC_CLE_ERROR

logger = logging.getLogger(__name__)


class ROSNotificator(object):
    """
    This class encapsulates publishing of state/errors/task status to the frontend/clients.
    """

    def __init__(self):

        # ROS allows multiple calls to init_node, as long as the arguments are the same.
        # Allow multiple distributed processes to spawn nodes of the same name.
        rospy.init_node(ROS_CLE_NODE_NAME, anonymous=True)

        # Not expecting more that 10hz
        self.__ros_status_pub = rospy.Publisher(TOPIC_STATUS, String, queue_size=10)

        # Not expecting more that 10hz
        self.__ros_cle_error_pub = rospy.Publisher(TOPIC_CLE_ERROR, CLEError, queue_size=10)

        # task specific bookkeeping
        self.__current_task = None
        self.__current_subtask_count = 0
        self.__current_subtask_index = 0

        logger.info('ROS notificator initialized')

    def shutdown(self):
        """
        Shutdown all publishers, notification will no longer function after called.
        """

        logger.info('Shutting down ROS notificator')

        logger.info('Unregister error/transfer_function topic')
        self.__ros_cle_error_pub.unregister()
        self.__ros_cle_error_pub = None

        logger.info('Unregister status topic')
        self.__ros_status_pub.unregister()
        self.__ros_status_pub = None

    def publish_state(self, state_msg):
        """
        Publishes a state message

        :param state_msgs A string of formatted JSON to publish.
        """
        if self.__ros_status_pub is None:
            logger.error('Attempting to publish state after shutdown!')
            return

        self.__ros_status_pub.publish(state_msg)

    def publish_error(self, error_msg):
        """
        Publishes an error message

        :param error_msg and cle_ros_msgs.CLEError message to publish.
        """
        if self.__ros_cle_error_pub is None:
            logger.error('Attempting to publish error after shutdown!')
            return

        self.__ros_cle_error_pub.publish(error_msg)

    def start_task(self, task_name, subtask_name, number_of_subtasks, block_ui):
        """
        Sends a status notification that a task starts on the ROS status topic.
        This method will save the task name and the task size in class members so that
        it could be reused in subsequent call to the update_task method.

        :param: task_name: Title of the task (example: initializing experiment).
        :param: subtask_name: Title of the first subtask. Could be empty
                (example: loading Virtual Room).
        :param: number_of_subtasks: Number of expected subsequent calls to
                update_current_task(_, True, _).
        :param: block_ui: Indicate that the client should block any user interaction.
        """
        if self.__current_task is not None:
            logger.warn(
                "Previous task was not closed properly, closing it now.")
            self.finish_task()
        self.__current_task = task_name
        self.__current_subtask_count = number_of_subtasks
        message = {'progress': {'task': task_name,
                                'subtask': subtask_name,
                                'number_of_subtasks': number_of_subtasks,
                                'subtask_index': self.__current_subtask_index,
                                'block_ui': block_ui}}
        self.publish_state(json.dumps(message))

    def update_task(self, new_subtask_name, update_progress, block_ui):
        """
        Sends a status notification that the current task is updated with a new subtask.

        :param: subtask_name: Title of the first subtask. Could be empt
                (example: loading Virtual Room).
        :param: update_progress: Boolean indicating if the index of the current subtask
                should be updated (usually yes).
        :param: block_ui: Indicate that the client should block any user interaction.
        """
        if self.__current_task is None:
            logger.warn("Can't update a non existing task.")
            return
        if update_progress:
            self.__current_subtask_index += 1
        message = {'progress': {'task': self.__current_task,
                                'subtask': new_subtask_name,
                                'number_of_subtasks': self.__current_subtask_count,
                                'subtask_index': self.__current_subtask_index,
                                'block_ui': block_ui}}
        self.publish_state(json.dumps(message))

    def finish_task(self):
        """
        Sends a status notification that the current task is finished.
        """
        if self.__current_task is None:
            logger.warn("Can't finish a non existing task.")
            return
        message = {'progress': {'task': self.__current_task,
                                'done': True}}
        self.publish_state(json.dumps(message))
        self.__current_subtask_count = 0
        self.__current_subtask_index = 0
        self.__current_task = None

    @contextlib.contextmanager
    def task_notifier(self, task_name, subtask_name):
        """
        Task notifier context manager

        :param task_name:
        :param subtask_name:
        """

        self.start_task(task_name, subtask_name, number_of_subtasks=0, block_ui=True)
        try:
            yield
        finally:
            self.finish_task()
