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


def condition_30_cb(user_data, status):
    # ... parse JSON in status message ...
    # return TRUE as long as condition is not met
    return status.simulationTime < 30


def condition_spike_cb(user_data, spike):
    # ... parse JSON in spike message ...
    # return TRUE as long as condition is not met
    return spike < 10


if __name__ == "__main__":
    # Create a ROS node for this state machine
    rospy.init_node("hbp_nrp_backend_sm_exp_control")

    sm = smach.Concurrence(outcomes=['FINISHED', 'ERROR', 'CONDITION_PREEMPTED'],
                           default_outcome='ERROR', input_keys=[], output_keys=[],
                           outcome_map = {'FINISHED':{'CONDITION_30':'invalid', 'CONDITION_SPIKE':'invalid'},
                                     'CONDITION_PREEMPTED':{'CONDITION_30':'preempted'},
                                     'CONDITION_PREEMPTED':{'CONDITION_SPIKE':'preempted'}})

    with sm:
        smach.Concurrence.add('CONDITION_30', smach_ros.MonitorState('/ros_cle_simulation/status',
                                                      String,
                                                      condition_30_cb))

        smach.Concurrence.add('CONDITION_SPIKE', smach_ros.MonitorState('/monitoring/left_wheel_neuron_rate_monitor',
                                                      String,
                                                      condition_spike_cb))

    result = sm.execute()
    rospy.loginfo(result)
