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
This package defines the simulation lifecycle such as used in the NRP
"""

from transitions.extensions import LockedMachine as Machine
from transitions import MachineError
from rospy import Publisher, Subscriber, get_caller_id
from cle_ros_msgs.msg import SimulationLifecycleStateChange
import logging
import time

__author__ = 'Georg Hinkel'


logger = logging.getLogger(__name__)


class SimulationLifecycle(object):
    """
    Defines the lifecycle of a simulation
    """

    states = [
        'created', 'paused', 'started', 'stopped',
        'halted', 'failed'
    ]

    final_states = ['stopped', 'failed']

    def __propagate_state_change(self, state_change):
        """
        Propagates the state change to other simulation lifecycle implementations

        :param state_change: The event that caused the state change
            From this, the trigger that caused the event is available as state_change.event.name
            The source state of the transition is state_change.transition.source
            The target state of the transition is state_change.transition.dest
        """
        if not 'silent' in state_change.kwargs or not state_change.kwargs['silent']:
            logger.info("Changing simulation lifecycle state from {0} to {1}"
                        .format(state_change.transition.source, state_change.transition.dest))
            self.__publisher.publish(get_caller_id(),
                                     state_change.transition.source,
                                     state_change.event.name,
                                     state_change.transition.dest)
        if state_change.transition.dest in SimulationLifecycle.final_states:
            time.sleep(1)
            self.shutdown(state_change)

    def __synchronized_lifecycle_changed(self, state_change):
        """
        Gets called when the lifecycle of the simulation changed in a different ROS node

        :param state_change: The state change message as a SimulationLifecycleStateChange message
        """
        if self.__subscriber is None:
            logger.warning("Undead lifecycle message detected.")
            return
        try:
            if get_caller_id() == state_change.source_node:
                return
            if self.state != state_change.source_state:
                logger.warning("The local simulation lifecycle and the remote version "
                               "have diverged.")
                logger.warning("Moving to selected source state now")
                self.__machine.set_state(state_change.source_state)
            # pylint: disable=broad-except
            try:
                self.__machine.events[state_change.event].trigger(silent=True)
            except Exception, e:
                self.__machine.set_state(state_change.target_state)
                logger.exception("Error while synchronizing the lifecycle: " + str(e))
                self.failed()
        except Exception, e2:
            logger.exception("Error failing the simulation (this should never happen): " + str(e2))

    def __init__(self, synchronization_topic, initial_state='created'):
        """
        Creates a new synchronization lifecycle for the given topic

        :param synchronization_topic: The topic used to synchronize the simulation lifecycle
        """
        # Transitions adds some members based on the states and transitions
        # We assign them stupid values here to avoid pylint warnings
        self.state = initial_state
        self.failed = lambda: None
        self.__machine = Machine(model=self, states=SimulationLifecycle.states,
                                 initial=initial_state)
        self.__machine.after_state_change = self.__propagate_state_change
        self.__machine.send_event = True

        self.__publisher = Publisher(synchronization_topic, SimulationLifecycleStateChange,
                                     queue_size=1)
        self.__subscriber = Subscriber(synchronization_topic, SimulationLifecycleStateChange,
                                       self.__synchronized_lifecycle_changed)

        self._add_transition(trigger='initialized',
                              source='created',
                              dest='paused',
                              before='initialize')
        self._add_transition(trigger='started',
                              source='paused',
                              dest='started',
                              before='start')
        self._add_transition(trigger='paused',
                              source='started',
                              dest='paused',
                              before='pause')
        self._add_transition(trigger='stopped',
                              source=['created', 'paused', 'started'],
                              dest='stopped',
                              before='stop')
        self._add_transition(trigger='failed',
                              source=['started', 'paused'],
                              dest='halted',
                              after='fail')
        self._add_transition(trigger='failed',
                              source='created',
                              dest='failed',
                              before='stop')
        self._add_transition(trigger='stopped',
                              source='halted',
                              dest='failed',
                              before='stop')
        self._add_transition(trigger='initialized',
                              source=['paused', 'started'],
                              dest='paused',
                              before='reset')

    def _add_transition(self, trigger, source, dest, before=None, after=None):
        """
        Registers a new transition in the simulation lifecycle

        :param trigger: The trigger that should be used to activate the transition
        :param source: The source state, either as state name or list of states
        :param dest: The destination state name
        :param before: The method that should be run before the transition is applied and propagated
        :param after: The method that should be run after the transition has been applied
        successfully, yet still before state propagation
        """
        if not dest == source and not dest in source:
            self.__machine.add_transition(trigger=trigger, source=dest, dest=dest,
                                          before='set_silent')
        elif trigger in self.__machine.events:
            event = self.__machine.events[trigger]
            if dest in event.transitions:
                del event.transitions[dest]
        self.__machine.add_transition(trigger=trigger, source=source, dest=dest,
                                      before=before, after=after)

    def accept_command(self, command):
        """
        Accepts the given command for the simulation lifecycle

        :param command: the command that should be activated
        """
        # pylint: disable=broad-except
        try:
            self.__machine.events[command].trigger()
        except MachineError:
            raise
        except Exception, e:
            logger.error("Error trying to execute command {0}".format(command))
            logger.exception(e)
            try:
                self.failed()
            except Exception, e2:
                logger.error("Error trying to perform cleanup operation for command {0}"
                             .format(command))
                logger.exception(e2)
            raise

    @staticmethod
    def set_silent(state_change):
        """
        Specifies that the given state change should not be propagated to other synchronized
         lifecycles

        :param state_change: The state change that should not be propagated
        """
        state_change.kwargs['silent'] = True

    # These methods will be overridden in the derived classes, thus we need to exclude them
    # from pylint
    #pylint: disable=unused-argument
    #pylint: disable=no-self-use

    def shutdown(self, shutdown_event):
        """
        Shuts down this simulation lifecycle instance

        :param shutdown_event: The event that caused the shutdown
        """
        subscriber = self.__subscriber
        publisher = self.__publisher
        if subscriber is not None:
            subscriber.unregister()
            self.__subscriber = None
        if publisher is not None:
            publisher.unregister()
            self.__publisher = None

    def initialize(self, state_change):
        """
        Gets called when the simulation should be initialized

        :param state_change: The state change that caused the simulation to initialize
        """
        raise Exception("This state transition needs to be implemented in a concrete lifecycle")

    def start(self, state_change):
        """
        Gets called when the simulation needs to be started

        :param state_change: The state change that caused the simulation to start
        """
        raise Exception("This state transition needs to be implemented in a concrete lifecycle")

    def pause(self, state_change):
        """
        Gets called when the simulation needs to be paused

        :param state_change: The state change that caused the simulation to pause
        """
        raise Exception("This state transition needs to be implemented in a concrete lifecycle")

    def stop(self, state_change):
        """
        Gets called when the simulation needs to be stopped

        :param state_change: The state change that caused the simulation to stop
        """
        raise Exception("This state transition needs to be implemented in a concrete lifecycle")

    def fail(self, state_change):
        """
        Gets called when the simulation fails

        :param state_change: The state change that caused the simulation to fail
        """
        raise Exception("This state transition needs to be implemented in a concrete lifecycle")

    def reset(self, state_change):
        """
        Gets called when the simulation is reset

        :param state_change: The state change that caused the simulation to reset
        """
        raise Exception("This state transition needs to be implemented in a concrete lifecycle")
