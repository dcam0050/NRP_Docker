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

import rospy
import smach
import smach_ros

from std_msgs.msg import String
from gazebo_msgs.srv import SetVisualProperties
from gazebo_msgs.srv import SetVisualPropertiesRequest


def time_30secs_cb(user_data, status):
    # ... parse JSON in status message ...
    # return TRUE as long as condition is not met
    return status.simulationTime < 30


if __name__ == "__main__":
    # Create a ROS node for this state machine
    rospy.init_node("hbp_nrp_backend_sm_exp_control")

    sm = smach.StateMachine(
    outcomes=['FINISHED', 'ERROR', 'CONDITION_PREEMPTED',
              'ACTION_PREEMPTED', 'ACTION_ERROR'])

    with sm:
        smach.StateMachine.add('CONDITION',
                               smach_ros.MonitorState('/ros_cle_simulation/status',
                                                      String,
                                                      time_30secs_cb),
                               {'valid': 'CONDITION', 'invalid': 'ACTION',
                                'preempted': 'CONDITION_PREEMPTED'})
        smach.StateMachine.add('ACTION',
                               smach_ros.ServiceState('/gazebo/set_visual_properties',
                                                      SetVisualProperties,
                                                      request=SetVisualPropertiesRequest(
                                                          'right_vr_screen', 'body', 'screen_glass',
                                                          'material:script:name', 'Gazebo/Red')),
                               {'succeeded': 'FINISHED', 'aborted': 'ACTION_ERROR',
                                'preempted': 'ACTION_PREEMPTED'})

    result = sm.execute()
    rospy.loginfo(result)
