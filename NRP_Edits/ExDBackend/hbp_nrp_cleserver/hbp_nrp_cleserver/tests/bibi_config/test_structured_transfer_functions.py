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
This module contains unit tests for structured transfer functions
"""

import unittest
import json
from mock import patch, MagicMock
from cle_ros_msgs.msg import Device, ExperimentPopulationInfo, TransferFunction as TF
from hbp_nrp_cle.tf_framework import *
from hbp_nrp_cle.mocks.brainsim import MockBrainCommunicationAdapter
from hbp_nrp_cle.mocks.robotsim import MockRobotCommunicationAdapter
from hbp_nrp_cleserver.bibi_config import StructuredTransferFunction

__author__ = "Georg Hinkel"


class TestStructuredTransferFunctions(unittest.TestCase):

    def setUp(self):
        start_new_tf_manager()
        config.active_node.brain_adapter = MockBrainCommunicationAdapter()

    def create_default_TF(self):
        @MapRobotPublisher("pub", Topic("/foo", Device))
        @MapSpikeSink("neuron", brain.sensors[4], leaky_integrator_alpha)
        @Neuron2Robot(Topic('/bar', TF))
        def test_tf(t, pub, neuron):
            print '42'

        return test_tf

    def create_other_TF(self):
        @MapRobotSubscriber("sub", Topic("/foo", Device))
        @MapSpikeSource("neuron", brain.actors[1:4:2], poisson)
        @Robot2Neuron()
        def test_tf_2(t, sub, neuron):
            print '42'

        return test_tf_2

    def create_variable_TF(self):

        @MapVariable("a", initial_value=42)
        @MapCSVRecorder("c", "file.csv", ["Name", "Value"])
        @NeuronMonitor(brain.actors, spike_recorder)
        def some_stupid_test_tf(t, a, c):
            pass

        return some_stupid_test_tf

    def assert_default_TF(self, test):
        self.assertIsNotNone(test)
        self.assertEqual("test_tf", test.name)
        self.assertEqual("print '42'", test.code)
        self.assertEqual(TF.NEURON2ROBOT, test.type)
        self.assertEqual(1, len(test.devices))
        self.assertEqual(2, len(test.topics))
        self.assertEqual(0, len(test.variables))
        d = test.devices[0]
        t = test.topics[0]
        self.assertEqual("neuron", d.name)
        self.assertEqual("LeakyIntegratorAlpha", d.type)
        self.assertEqual("pub", t.name)
        self.assertEqual("/foo", t.topic)
        self.assertEqual("cle_ros_msgs/Device", t.type)
        self.assertTrue(t.publishing)

    def assert_other_TF(self, test):
        self.assertIsNotNone(test)
        self.assertEqual("test_tf_2", test.name)
        self.assertEqual("print '42'", test.code)
        self.assertEqual(TF.ROBOT2NEURON, test.type)
        self.assertEqual(1, len(test.devices))
        self.assertEqual(1, len(test.topics))
        self.assertEqual(0, len(test.variables))
        d = test.devices[0]
        t = test.topics[0]
        self.assertEqual("neuron", d.name)
        self.assertEqual("Poisson", d.type)
        self.assertEqual("sub", t.name)
        self.assertEqual("/foo", t.topic)
        self.assertEqual("cle_ros_msgs/Device", t.type)
        self.assertFalse(t.publishing)

    def assert_variables_tf(self, test):
        self.assertIsNotNone(test)
        self.assertEqual("some_stupid_test_tf", test.name)
        self.assertEqual("pass", test.code)
        self.assertEqual(TF.NEURONMONITOR, test.type)
        self.assertEqual(1, len(test.devices))
        self.assertEqual(1, len(test.topics))
        self.assertEqual(2, len(test.variables))

        a = test.variables[0]
        c = test.variables[1]

        self.assertEqual("a", a.name)
        self.assertEqual("int", a.type)
        self.assertEqual("42", a.initial_value)
        self.assertEqual("c", c.name)
        self.assertEqual("csv", c.type)
        self.assertDictEqual({"filename":"file.csv", "headers": ["Name", "Value"]}, json.loads(c.initial_value))

    @patch('os.path.isfile', return_value=True)
    def test_convert_transfer_function(self, mock_isfile):

        test_tf = self.create_default_TF()
        test = StructuredTransferFunction.extract_structure(test_tf)
        self.assert_default_TF(test)

        test_tf_2 = self.create_other_TF()
        test_2 = StructuredTransferFunction.extract_structure(test_tf_2)
        self.assert_other_TF(test_2)

        test_tf_3 = self.create_variable_TF()
        test_3 = StructuredTransferFunction.extract_structure(test_tf_3)
        self.assert_variables_tf(test_3)

    def test_convert_initialized_transfer_function(self):

        test_tf = self.create_default_TF()
        test_tf_2 = self.create_other_TF()

        set_nest_adapter(MockBrainCommunicationAdapter())
        set_robot_adapter(MockRobotCommunicationAdapter())
        initialize("test")

        test = StructuredTransferFunction.extract_structure(test_tf)
        test2 = StructuredTransferFunction.extract_structure(test_tf_2)

        self.assert_default_TF(test)
        self.assert_other_TF(test2)

    @patch('hbp_nrp_cleserver.bibi_config.StructuredTransferFunction.ExperimentPopulationInfo')
    def test_extract_neurons(self, mock_exp_info):
        mock_exp_info.TYPE_ENTIRE_POPULATION = "type"
        mock_exp_info.TYPE_POPULATION_SLICE = "slice"
        mock_exp_info.TYPE_POPULATION_LISTVIEW = "list"
        StructuredTransferFunction._extract_neurons(brain.neuron_name)

        mock_exp_info.assert_called_with(name='neuron_name', type=mock_exp_info.TYPE_ENTIRE_POPULATION,
                                         ids=[], start=0, stop=0, step=0)
        StructuredTransferFunction._extract_neurons(brain.neuron_name[5])
        mock_exp_info.assert_called_with(name='neuron_name', type=mock_exp_info.TYPE_POPULATION_SLICE,
                                         ids=[], start=5, stop=6, step=1)
        StructuredTransferFunction._extract_neurons(brain.neuron_name[[5]])
        mock_exp_info.assert_called_with(name='neuron_name', type=mock_exp_info.TYPE_POPULATION_LISTVIEW,
                                         ids=[5], start=0, stop=0, step=0)
        with self.assertRaises(Exception):
            StructuredTransferFunction._extract_neurons(brain.neuron_name[{}])

    def test_generate_neurons(self):
        neurons = MagicMock()
        neurons.name = "neuron_name"
        neurons.start = 0
        neurons.type = ExperimentPopulationInfo.TYPE_ENTIRE_POPULATION

        self.assertEqual(StructuredTransferFunction._generate_neurons(neurons), "nrp.brain.neuron_name")

        neurons.type = ExperimentPopulationInfo.TYPE_POPULATION_SLICE
        neurons.stop = neurons.start + 1
        self.assertEqual(StructuredTransferFunction._generate_neurons(neurons), "nrp.brain.neuron_name[0]")

        neurons.stop = 100
        neurons.step = 5
        self.assertEqual(StructuredTransferFunction._generate_neurons(neurons), "nrp.brain.neuron_name[slice(0,100,5)]")
        neurons.type = ExperimentPopulationInfo.TYPE_POPULATION_LISTVIEW
        neurons.ids = ['1','2','3']
        self.assertEqual(StructuredTransferFunction._generate_neurons(neurons), "nrp.brain.neuron_name[[1, 2, 3]]")

    @patch('os.path.isfile', return_value=True)
    def test_roundtrip(self, mock_isfile):

        test_tf = self.create_default_TF()
        converted = StructuredTransferFunction.extract_structure(test_tf)
        code = StructuredTransferFunction.generate_code_from_structured_tf(converted)

        self.assertMultiLineEqual(
            'import cle_ros_msgs.msg\n\n'
            '@nrp.MapSpikeSink("neuron", nrp.brain.sensors[4], nrp.leaky_integrator_alpha)\n'
            '@nrp.MapRobotPublisher("pub", Topic("/foo", cle_ros_msgs.msg.Device))\n'
            '@nrp.Neuron2Robot(Topic("/bar", cle_ros_msgs.msg.TransferFunction))\n'
            'def test_tf(t, neuron, pub):\n'
            '    print \'42\'', code)

        test_tf = self.create_other_TF()
        converted = StructuredTransferFunction.extract_structure(test_tf)
        code = StructuredTransferFunction.generate_code_from_structured_tf(converted)

        self.assertMultiLineEqual(
            'import cle_ros_msgs.msg\n\n'
            '@nrp.MapSpikeSource("neuron", nrp.brain.actors[slice(1,4,2)], nrp.poisson)\n'
            '@nrp.MapRobotSubscriber("sub", Topic("/foo", cle_ros_msgs.msg.Device))\n'
            '@nrp.Robot2Neuron()\n'
            'def test_tf_2(t, neuron, sub):\n'
            '    print \'42\'', code)


        test_tf_3 = self.create_variable_TF()
        test_3 = StructuredTransferFunction.extract_structure(test_tf_3)
        code = StructuredTransferFunction.generate_code_from_structured_tf(test_3)

        self.assertMultiLineEqual(
            '\n@nrp.MapVariable("a", initial_value=42)\n'
            '@nrp.MapCSVRecorder("c", "file.csv", ["Name", "Value"])\n'
            '@nrp.NeuronMonitor(nrp.brain.actors, nrp.spike_recorder)\n'
            'def some_stupid_test_tf(t, a, c):\n'
            '    pass', code
        )
