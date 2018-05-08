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
import smach_ros
from smach import StateMachine
from hbp_nrp_excontrol.nrp_states import RobotPoseMonitorState
from hbp_nrp_excontrol.logs import clientLogger

clientLogger.info("Start SM")


def robot_pose_cb(user_data, state):
    clientLogger.info("pos: x: " + str(state.position.x) +
                      ", y: " + str(state.position.y) +
                      ", z: " + str(state.position.z))

    return True

sm = StateMachine(outcomes=['FINISHED', 'ERROR', 'PREEMPTED'])
with sm:
    StateMachine.add('initial_condition',
                     RobotPoseMonitorState(robot_pose_cb),
                     transitions={'valid': 'initial_condition',
                                  'invalid': 'initial_condition',
                                  'preempted': 'PREEMPTED'})
