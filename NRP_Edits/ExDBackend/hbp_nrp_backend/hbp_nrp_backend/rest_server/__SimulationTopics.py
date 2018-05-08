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
This resource represents the topics contained in a running simulation
"""
from flask_restful import Resource
import rosgraph.masterapi as master


__author__ = "Georg Hinkel"


# pylint: disable=no-self-use
class SimulationTopics(Resource):
    """
    This resource represents the topics contained in a running simulation
    """

    def get(self):
        """
        Gets a list of topics available in the current simulation
        """
        m = master.Master('masterapi')
        filtered_dict = {
            k: v for k, v in m.getTopicTypes()
            if not k.startswith('/monitor') and
            not k.startswith('/gazebo') and
            not k.startswith('/ros') and
            not k.startswith('/odom') and
            not k.startswith('/clock')
            }
        topics = []
        topic_names = []
        system_state = m.getSystemState()
        # consider subscribers and publishers, but not services
        for topic_list in system_state[0:2]:
            for topic_info in topic_list:
                topic_name = topic_info[0]
                if (
                    topic_name in filtered_dict and
                    not topic_name in topic_names
                ):
                    topic_e = {
                        'topic': topic_name,  # e.g., '/husky/cmd'
                        'topicType': filtered_dict[topic_name]  # e.g., '/gazebo'
                    }
                    topics.append(topic_e)
                    topic_names.append(topic_name)
        return {'topics': topics}, 200
