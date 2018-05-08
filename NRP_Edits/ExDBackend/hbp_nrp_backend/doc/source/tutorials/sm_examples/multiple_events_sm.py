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
from smach import CBState
import smach_ros

from std_msgs.msg import String


def condition_30_cb(user_data, status):
    # ... parse JSON in status message ...
    # return TRUE as long as condition is not met
    return status.simulationTime < 30


@smach.cb_interface(input_keys=[], output_keys=[], outcomes=['finished'])
def action_30_cb(user_data):
    # ... do something
    return 'finished'


def condition_spike_cb(user_data, spike):
    # ... parse JSON in spike message ...
    # return TRUE as long as condition is not met
    return spike < 10


@smach.cb_interface(input_keys=[], output_keys=[], outcomes=['finished'])
def action_spike_cb(user_data):
    # ... do something
    return 'finished'

if __name__ == "__main__":
    # Create a ROS node for this state machine
    rospy.init_node("hbp_nrp_backend_sm_exp_control")

    sm_one = smach.StateMachine(
    outcomes=['FINISHED', 'ERROR', 'CONDITION_PREEMPTED',
              'ACTION_PREEMPTED', 'ACTION_ERROR'])

    with sm_one:
        smach.StateMachine.add('CONDITION_30',
                               smach_ros.MonitorState('/ros_cle_simulation/status',
                                                      String,
                                                      condition_30_cb),
                               {'valid': 'CONDITION_30', 'invalid': 'ACTION_30',
                                'preempted': 'CONDITION_PREEMPTED'})
        smach.StateMachine.add('ACTION_30', CBState(action_30_cb),
                               {'finished': 'FINISHED'})

    sm_two = smach.StateMachine(
    outcomes=['FINISHED', 'ERROR', 'CONDITION_PREEMPTED',
              'ACTION_PREEMPTED', 'ACTION_ERROR'])

    with sm_two:
        smach.StateMachine.add('CONDITION_SPIKE',
                               smach_ros.MonitorState('/monitoring/left_wheel_neuron_rate_monitor',
                                                      String,
                                                      condition_spike_cb),
                               {'valid': 'CONDITION_SPIKE', 'invalid': 'ACTION_SPIKE',
                                'preempted': 'CONDITION_PREEMPTED'})
        smach.StateMachine.add('ACTION_SPIKE', CBState(action_spike_cb),
                               {'finished': 'FINISHED'})

    sm = smach.Concurrence(outcomes=['FINISHED', 'ERROR', 'CONDITION_PREEMPTED'],
                           default_outcome='ERROR', input_keys=[], output_keys=[],
                           outcome_map = {'FINISHED':{'SM_ONE':'FINISHED', 'SM_TWO':'FINISHED'},
                                     'CONDITION_PREEMPTED':{'SM_ONE':'CONDITION_PREEMPTED'},
                                     'CONDITION_PREEMPTED':{'SM_TWO':'CONDITION_PREEMPTED'}})

    with sm:
        smach.Concurrence.add('SM_ONE', sm_one)
        smach.Concurrence.add('SM_TWO', sm_two)

    result = sm.execute()
    rospy.loginfo(result)
