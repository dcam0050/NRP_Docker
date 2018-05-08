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
This file contains the unit tests for the simulation topics service
"""

from flask import Response
from mock import patch, Mock, PropertyMock
from hbp_nrp_backend.rest_server.tests import RestTest
from hbp_nrp_backend.rest_server.__SimulationControl import _get_simulation_or_abort
from hbp_nrp_backend.simulation_control import simulations
import json
from transitions import MachineError

class TestSimulationTopics(RestTest):

    def setUp(self):
        self.publishers = []
        self.subscribers = []
        self.types = {}

    def test_topics_husky_available(self):
        self.assertTrue(self.__assert_topic_visible("/husky/camera", "sensor_msgs/msg/camera"))
        self.assertTrue(self.__assert_topic_visible("/husky/cmd_vel", "cmd_msgs/cmd_vel"))

    def test_gazebo_topics_filtered(self):
        self.assertFalse(self.__assert_topic_visible("/gazebo/joint_states", "gazebo_ros_msgs/msg/jointStates"))

    def test_clock_topic_filtered(self):
        self.assertFalse(self.__assert_topic_visible("/clock", "Time"))

    def test_monitor_topics_filtered(self):
        self.assertFalse(self.__assert_topic_visible("/monitor/spike_recorder", "ros_cle_msgs/msg/SpikeRecorder"))

    def test_internal_topics_filtered(self):
        self.assertFalse(self.__assert_topic_visible("/ros_cle_simulation/status", "ros_cle_msgs/Status"))
        self.assertFalse(self.__assert_topic_visible("/ros_cle_simulation/error", "ros_cle_msgs/CLEError"))

    def test_topics_from_last_simulation_invisible(self):
        self.__subscribe("/husky/cmd_vel", "geometry/Twist")
        self.__publish("/husky/camera", "Image")
        self.__publish("/monitor/spike_recorder", "monitoring/SpikeMsg")
        self.__unsubscribe("/husky/cmd_vel")
        self.__unpublish("/husky/camera")
        self.__publish("/icub/whatever", "SomeControlMessageType")

        self.assertIn("/husky/camera", self.types)
        response = self.__get_topics()

        self.assertEqual(1, len(response))
        self.assertEqual("/icub/whatever", response[0]['topic'])
        self.assertEqual("SomeControlMessageType", response[0]['topicType'])


    def __publish(self, topic, topic_type):
        self.publishers.append([topic, ['tests']])
        self.types[topic] = topic_type

    def __unpublish(self, topic):
        for i in range(len(self.publishers)-1,-1,-1):
            if self.publishers[i][0] == topic:
                del self.publishers[i]

    def __subscribe(self, topic, topic_type):
        self.subscribers.append([topic, ['tests']])
        self.types[topic] = topic_type

    def __unsubscribe(self, topic):
        for i in range(len(self.subscribers)-1,-1,-1):
            if self.subscribers[i][0] == topic:
                del self.subscribers[i]

    def __assert_topic_visible(self, topic, topic_type):
        self.__publish(topic, topic_type)
        published = self.__check_topic(topic, topic_type)
        self.__unpublish(topic)
        self.__subscribe(topic, topic_type)
        subscribed = self.__check_topic(topic, topic_type)
        self.__unsubscribe(topic)
        self.assertEqual(published, subscribed)
        return published

    def __get_topics(self):
        with patch("hbp_nrp_backend.rest_server.__SimulationTopics.master") as master_mock:
            master_mock.Master().getSystemState.return_value = [self.publishers, self.subscribers, []]
            master_mock.Master().getTopicTypes.return_value = [[top, self.types[top]] for top in self.types]
            topic_response = self.client.get("/simulation/topics")
            self.assertEqual(200, topic_response.status_code)
            return json.loads(topic_response.data)['topics']

    def __check_topic(self, topic, topic_type):
        topics_list = self.__get_topics()
        if len(topics_list) == 1:
            self.assertEqual(topic, topics_list[0]['topic'])
            self.assertEqual(topic_type, topics_list[0]['topicType'])
            return True
        elif len(topics_list) == 0:
            return False
        else:
            raise Exception("Too many topics returned: " + repr(topics_list))
