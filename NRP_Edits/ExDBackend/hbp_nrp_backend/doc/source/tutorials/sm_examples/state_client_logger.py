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
from hbp_nrp_excontrol.nrp_states import RobotPoseMonitorState, ClientLogState

sm = StateMachine(outcomes=['FINISHED', 'ERROR', 'PREEMPTED'])

with sm:
    StateMachine.add(
        "wait_for_husky_left",
        RobotPoseMonitorState(lambda ud, p: not ((-1 < p.position.x < 1) and
                    (-2.5 < p.position.y < -1.8) and
            (0 < p.position.z < 1))),
        transitions={'valid': 'wait_for_husky_left',
                     'invalid': 'log_husky_at_left',
                     'preempted': 'PREEMPTED'}
    )

    StateMachine.add(
        "log_husky_at_left",
        ClientLogState("Husky is at the LEFT!"),
        transitions={'succeeded': 'wait_for_husky_right',
                     'aborted': 'ERROR'}
    )

    StateMachine.add(
        "wait_for_husky_right",
        RobotPoseMonitorState(lambda ud, p: not ((-1 < p.position.x < 1) and
                    (1.8 < p.position.y < 2.5) and
            (0 < p.position.z < 1))),
        transitions={'valid': 'wait_for_husky_right',
                     'invalid': 'log_husky_at_right',
                     'preempted': 'PREEMPTED'}
    )

    StateMachine.add(
        "log_husky_at_right",
        ClientLogState("Husky is at the RIGHT!"),
        transitions={'succeeded': 'wait_for_husky_left',
                     'aborted': 'ERROR'}
    )
