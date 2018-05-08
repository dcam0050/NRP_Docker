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
ROSNotificator unit test
"""

from hbp_nrp_cleserver.server.ROSNotificator import ROSNotificator

import unittest
from mock import patch, MagicMock, Mock
from testfixtures import log_capture

import json
import logging


class TestROSNotificator(unittest.TestCase):

    def setUp(self):
        rospy_patcher = patch('hbp_nrp_cleserver.server.ROSNotificator.rospy')
        self.__mocked_rospy = rospy_patcher.start()

        self.__ros_notificator = ROSNotificator()

        # Be sure we create as many publishers as required.
        from hbp_nrp_cleserver.server import *
        number_of_publishers = 0
        for var_name in vars().keys():
            if (var_name.startswith("TOPIC_")):
                number_of_publishers += 1

        # Lifecycle topic not published by ROSNotificator
        number_of_publishers -= 1

        self.assertEqual(number_of_publishers, self.__mocked_rospy.Publisher.call_count)

        # Assure that also the publish method of the rospy.Publisher is
        # injected as a mock here so that we can use it later in our single
        # test methods
        self.__mocked_pub = ROSNotificator.rospy.Publisher()
        self.__mocked_pub.publish = MagicMock()
        self.__mocked_rospy.Publisher.return_value = self.__mocked_pub

    def test_ros_node_initialized(self):
        self.__mocked_rospy.init_node.assert_called_with('ros_cle_simulation', anonymous=True)

    def test_shutdown(self):

        tmp = ROSNotificator()

        mock_unregister = Mock()
        tmp._ROSNotificator__ros_status_pub.unregister = mock_unregister
        tmp._ROSNotificator__ros_cle_error_pub.unregister = mock_unregister

        mock_publish = Mock()
        tmp._ROSNotificator__ros_status_pub.publish = mock_publish
        tmp._ROSNotificator__ros_cle_error_pub.publish = mock_publish

        # shutdown should unregister the publishers
        tmp.shutdown()

        self.assertEquals(mock_unregister.call_count, 2)
        self.assertEquals(tmp._ROSNotificator__ros_status_pub, None)
        self.assertEquals(tmp._ROSNotificator__ros_cle_error_pub, None)

        # publish methods should fail now
        tmp.publish_state('foo')
        tmp.publish_error('bar')
        self.assertEquals(mock_publish.call_count, 0)

    def test_publish(self):

        self.__mocked_pub.reset_mock()
        self.__ros_notificator.publish_state('foo')
        self.__mocked_pub.publish.assert_called_once_with('foo')

        self.__mocked_pub.reset_mock()
        self.__ros_notificator.publish_error('bar')
        self.__mocked_pub.publish.assert_called_once_with('bar')

    def test_task(self):
        mock_publisher = Mock()
        self.__ros_notificator._ROSNotificator__ros_status_pub = mock_publisher
        self.__ros_notificator.start_task('task', 'subtask', 1, False)
        self.assertEquals(mock_publisher.publish.call_count, 1)
        self.__ros_notificator.update_task('new_subtask', True, False)
        self.assertEquals(mock_publisher.publish.call_count, 2)
        self.__ros_notificator.finish_task()
        self.assertEquals(mock_publisher.publish.call_count, 3)

    def test_start_task(self):
        self.__mocked_pub.reset_mock()

        task_name = 'test_name'
        subtask_name = 'test_subtaskname'
        number_of_subtasks = 1
        block_ui = False
        self.__ros_notificator.start_task(task_name, subtask_name, number_of_subtasks, block_ui)
        self.assertEqual(1, self.__mocked_pub.publish.call_count)
        message = {'progress': {'task': task_name,
                                'subtask': subtask_name,
                                'number_of_subtasks': number_of_subtasks,
                                'subtask_index': 0,
                                'block_ui': block_ui}}
        self.__mocked_pub.publish.assert_called_with(json.dumps(message))

        with patch.object(self.__ros_notificator, 'finish_task') as mock_finish:
            self.__ros_notificator.start_task(task_name, subtask_name, number_of_subtasks, block_ui)
            mock_finish.assert_called_once()


    @log_capture(level=logging.WARNING)
    def test_current_task_no_task(self, logcapture):
        self.__ros_notificator.update_task("new_subtask", True, True)
        logcapture.check(
            ('hbp_nrp_cleserver.server.ROSNotificator', 'WARNING', "Can't update a non existing task.")
        )

    @log_capture(level=logging.WARNING)
    def test_finish_task_no_task(self, logcapture):
        self.__ros_notificator.finish_task()
        logcapture.check(
            ('hbp_nrp_cleserver.server.ROSNotificator', 'WARNING', "Can't finish a non existing task.")
        )

    def test_task_notifier(self):

        with patch.object(self.__ros_notificator, 'start_task') as mock_start,\
             patch.object(self.__ros_notificator, 'finish_task') as mock_finish:
        
            with self.__ros_notificator.task_notifier('foo', 'bar') as tn:
                mock_start.assert_called_once_with('foo', 'bar', number_of_subtasks=0, block_ui=True)

            mock_finish.assert_called_once()
