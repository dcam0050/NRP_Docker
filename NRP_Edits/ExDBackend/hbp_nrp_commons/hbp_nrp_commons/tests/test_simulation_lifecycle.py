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
Unit tests for the simulation lifecycle
"""

from transitions import MachineError
from mock import patch, Mock
from hbp_nrp_commons.simulation_lifecycle import SimulationLifecycle
from cle_ros_msgs.msg import SimulationLifecycleStateChange
import unittest

__author__ = 'Georg Hinkel'

class MockLifecycle(SimulationLifecycle):

    def __init__(self):
        super(MockLifecycle, self).__init__("simulationLifecycle")
        self.last_state_change = None
        self.last_transition = None

    def start(self, state_change):
        self.last_state_change = state_change
        self.last_transition = "start"

    def initialize(self, state_change):
        self.last_state_change = state_change
        self.last_transition = "initialize"

    def fail(self, state_change):
        self.last_state_change = state_change
        self.last_transition = "fail"

    def pause(self, state_change):
        self.last_state_change = state_change
        self.last_transition = "pause"

    def reset(self, state_change):
        self.last_state_change = state_change
        self.last_transition = "reset"

    def stop(self, state_change):
        self.last_state_change = state_change
        self.last_transition = "stop"

    def patch_transition(self, transition):
        return patch(__name__ + ".MockLifecycle." + transition, side_effect=Exception)

class TestLifecycle(unittest.TestCase):
    def setUp(self):
        with patch("hbp_nrp_commons.simulation_lifecycle.Publisher") as publisher_mock:
            with patch("hbp_nrp_commons.simulation_lifecycle.Subscriber") as subscriber_mock:
                self.lifecycle = MockLifecycle()
                self.assertEqual("simulationLifecycle", publisher_mock.call_args[0][0])
                self.assertIs(SimulationLifecycleStateChange, publisher_mock.call_args[0][1])
                self.publisher_mock = publisher_mock()
                self.assertEqual("simulationLifecycle", subscriber_mock.call_args[0][0])
                self.assertIs(SimulationLifecycleStateChange, subscriber_mock.call_args[0][1])
                self.subscriber_handler = subscriber_mock.call_args[0][2]
                self.subscriber_mock = subscriber_mock()
        caller_id_patch = patch("hbp_nrp_commons.simulation_lifecycle.get_caller_id")
        self.caller_id = caller_id_patch.start()
        self.caller_id.return_value = "unittests"
        self.addCleanup(caller_id_patch.stop)

    def assertPublisherCalledWith(self, start_state, transition, dest_state):
        self.publisher_mock.publish.assertCalled()
        args = self.publisher_mock.publish.call_args[-2]
        self.assertEqual("unittests", args[0])
        self.assertEqual(start_state, args[1])
        self.assertEqual(transition, args[2])
        self.assertEqual(dest_state, args[3])

    def send_state_change(self, origin, source_state, transition, target_state):
        self.subscriber_handler(SimulationLifecycleStateChange(origin, source_state, transition, target_state))

    def test_created_simulation_must_be_initialized(self):
        self.assertRaises(MachineError, self.lifecycle.accept_command, "started")
        self.assertRaises(MachineError, self.lifecycle.accept_command, "paused")
        self.assertIsNone(self.lifecycle.last_state_change)
        self.lifecycle.accept_command("initialized")
        self.assertEqual("initialize", self.lifecycle.last_transition)
        self.assertEqual("created", self.lifecycle.last_state_change.transition.source)
        self.assertEqual("paused", self.lifecycle.last_state_change.transition.dest)
        self.assertEqual("initialized", self.lifecycle.last_state_change.event.name)
        self.assertEqual("paused", self.lifecycle.state)

    def test_lifecycle_normal_workflow(self):
        # Start by initializing a simulation
        self.lifecycle.accept_command("initialized")
        self.assertEqual("paused", self.lifecycle.state)
        self.assertEqual("initialize", self.lifecycle.last_transition)
        self.assertEqual(1, self.publisher_mock.publish.call_count)
        # Then, we start the simulation
        self.lifecycle.accept_command("started")
        self.assertEqual("started", self.lifecycle.state)
        self.assertEqual("start", self.lifecycle.last_transition)
        self.assertEqual(2, self.publisher_mock.publish.call_count)
        # Pause the simulation
        self.lifecycle.accept_command("paused")
        self.assertEqual("paused", self.lifecycle.state)
        self.assertEqual("pause", self.lifecycle.last_transition)
        self.assertEqual(3, self.publisher_mock.publish.call_count)
        # Resume it
        self.lifecycle.accept_command("started")
        self.assertEqual("started", self.lifecycle.state)
        self.assertEqual("start", self.lifecycle.last_transition)
        self.assertEqual(4, self.publisher_mock.publish.call_count)
        # Finally, we are done
        self.lifecycle.accept_command("stopped")
        self.assertEqual("stopped", self.lifecycle.state)
        self.assertEqual("stop", self.lifecycle.last_transition)
        self.assertEqual(5, self.publisher_mock.publish.call_count)

    def test_lifecycle_normal_workflow_synchronized(self):
        # Start by initializing a simulation
        self.send_state_change("backend", "created", "initialized", "paused")
        self.assertEqual("paused", self.lifecycle.state)
        self.assertEqual("initialize", self.lifecycle.last_transition)
        self.assertEqual(0, self.publisher_mock.publish.call_count)
        # Then, we start the simulation
        self.send_state_change("backend", "paused", "started", "started")
        self.assertEqual("started", self.lifecycle.state)
        self.assertEqual("start", self.lifecycle.last_transition)
        self.assertEqual(0, self.publisher_mock.publish.call_count)
        # Pause the simulation
        self.send_state_change("backend", "started", "paused", "paused")
        self.assertEqual("paused", self.lifecycle.state)
        self.assertEqual("pause", self.lifecycle.last_transition)
        self.assertEqual(0, self.publisher_mock.publish.call_count)
        # Resume it
        self.send_state_change("backend", "paused", "started", "started")
        self.assertEqual("started", self.lifecycle.state)
        self.assertEqual("start", self.lifecycle.last_transition)
        self.assertEqual(0, self.publisher_mock.publish.call_count)
        # Finally, we are done
        self.send_state_change("backend", "started", "stopped", "stopped")
        self.assertEqual("stopped", self.lifecycle.state)
        self.assertEqual("stop", self.lifecycle.last_transition)
        self.assertEqual(0, self.publisher_mock.publish.call_count)

    def test_lifecycle_error_during_initialize(self):
        with self.lifecycle.patch_transition("initialize"):
            self.assertRaises(Exception, self.lifecycle.accept_command, "initialized")
        self.assertEqual("failed", self.lifecycle.state)
        # We need to tell others that the simulation crashed
        self.assertPublisherCalledWith("created", "failed", "failed")

    def test_lifecycle_error_in_simulation_server_while_initializing(self):
        # Again, we initialize the simulation
        self.lifecycle.accept_command("initialized")
        self.assertEqual("initialize", self.lifecycle.last_transition)
        self.assertEqual(1, self.publisher_mock.publish.call_count)
        # From the simulation server, we get feedback that the simulation could not be initialized
        # Therefore, any resources are released
        self.send_state_change("simulation", "created", "failed", "failed")
        self.assertEqual("stop", self.lifecycle.last_transition)
        self.assertEqual(1, self.publisher_mock.publish.call_count)
        # We still know that an error happened
        self.assertEqual("failed", self.lifecycle.state)

    def test_lifecycle_error_synchronizing_initialization(self):
        with self.lifecycle.patch_transition("initialize"):
            self.send_state_change("backend", "created", "initialized", "paused")
        self.assertEqual("halted", self.lifecycle.state)
        self.assertPublisherCalledWith("paused", "failed", "halted")

    def test_lifecycle_error_in_simulation_server_while_running(self):
        # Again, we initialize the simulation
        self.lifecycle.accept_command("initialized")
        self.assertEqual("initialize", self.lifecycle.last_transition)
        self.assertEqual(1, self.publisher_mock.publish.call_count)
        # We start it
        self.lifecycle.accept_command("started")
        self.assertEqual("start", self.lifecycle.last_transition)
        self.assertEqual(2, self.publisher_mock.publish.call_count)
        # From the simulation server, we get feedback that the simulation has failed
        self.send_state_change("simulation", "started", "failed", "halted")
        self.assertEqual("fail", self.lifecycle.last_transition)
        self.assertEqual(2, self.publisher_mock.publish.call_count)
        # Shutting down the simulation
        self.lifecycle.accept_command("stopped")
        self.assertEqual("stop", self.lifecycle.last_transition)
        self.assertEqual(3, self.publisher_mock.publish.call_count)
        # We still know that an error happened
        self.assertEqual("failed", self.lifecycle.state)

    def test_lifecycle_error_while_running(self):
        # Again, we initialize the simulation
        self.send_state_change("backend", "created", "initialized", "paused")
        self.assertEqual("initialize", self.lifecycle.last_transition)
        self.assertEqual(0, self.publisher_mock.publish.call_count)
        # We start it
        self.send_state_change("backend", "paused", "started", "started")
        self.assertEqual("start", self.lifecycle.last_transition)
        self.assertEqual(0, self.publisher_mock.publish.call_count)
        # From the simulation server, we get feedback that the simulation has failed
        self.lifecycle.failed()
        self.assertEqual("fail", self.lifecycle.last_transition)
        self.assertEqual(1, self.publisher_mock.publish.call_count)
        # Shutting down the simulation
        self.send_state_change("backend", "halted", "stopped", "failed")
        self.assertEqual("stop", self.lifecycle.last_transition)
        self.assertEqual(1, self.publisher_mock.publish.call_count)
        # We still know that an error happened
        self.assertEqual("failed", self.lifecycle.state)

    def test_invalid_lifecycle(self):
        invalid = SimulationLifecycle('foo')
        self.assertRaises(Exception, invalid.accept_command, 'bar')
        self.assertRaises(Exception, invalid.initialize, 'bar')
        self.assertRaises(Exception, invalid.start, 'bar')
        self.assertRaises(Exception, invalid.pause, 'bar')
        self.assertRaises(Exception, invalid.stop, 'bar')
        self.assertRaises(Exception, invalid.fail, 'bar')
        self.assertRaises(Exception, invalid.reset, 'bar')

    def test_shutdown(self):
        self.lifecycle.shutdown(None)
        self.assertEqual(self.subscriber_mock.unregister.call_count, 1)
        self.assertEqual(self.publisher_mock.unregister.call_count, 1)
