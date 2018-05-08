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
Test for single functions of the bibi configuration script
"""

__author__ = 'GeorgHinkel'

from hbp_nrp_commons.bibi_functions import *
import hbp_nrp_commons.generated.bibi_api_gen as api
import unittest
import pyxb


class TestScript(unittest.TestCase):

    def test_print_expression_raises(self):
        self.assertRaises(Exception, print_expression, "foo")

    def test_get_neuron_count(self):
        self.assertEqual(3, get_neuron_count(api.List(population="pop", element=[1, 2, 3])))
        self.assertEqual(1, get_neuron_count(api.Index(population="pop")))
        self.assertEqual(4, get_neuron_count(api.Range(population="pop", from_=3, to=7)))
        self.assertEqual(2, get_neuron_count(api.Range(population="pop", from_=0, to=5, step=2)))
        self.assertEqual(42, get_neuron_count(api.Population(population="pop", count=42)))
        self.assertRaises(Exception, get_neuron_count, 'foo')

    def test_get_device_name(self):
        __device_types = {'ACSource': 'ac_source', 'DCSource': 'dc_source',
                          'FixedFrequency': 'fixed_frequency',
                          'LeakyIntegratorAlpha': 'leaky_integrator_alpha',
                          'LeakyIntegratorExp': 'leaky_integrator_exp',
                          'NCSource': 'nc_source',
                          'Poisson': 'poisson'}
        for k in __device_types.keys():
            self.assertEqual(get_device_name(k), __device_types[k])

    def test_print_expression_property_none(self):
        ar = api.ArgumentReference()
        ar.property_ = None
        ar.name = 'Test'
        self.assertEqual(print_expression(ar), ar.name)

    def test_print_expression_exception(self):
        x = None
        self.assertRaises(Exception, print_expression, x)
        self.assertRaises(Exception, get_neurons_index, x)

    def test_print_expression(self):
        s = api.Scale(factor=5.0, inner=api.Constant(value_=0.0))
        self.assertEqual(print_expression(s), '5.0 * 0.0')
        c = api.Call(type="foo", argument=[api.Argument(name="bar", value_=api.Constant(value_=0))])
        self.assertEqual(print_expression(c), 'foo(bar=0.0)')
        c = api.Call(type="foo", argument=[api.Argument(name="bar", value_=api.Constant(value_=0)),
                                           api.Argument(name="foobar", value_=api.Constant(value_=1))])
        self.assertEqual(print_expression(c), 'foo(bar=0.0, foobar=1.0)')
        o = api.Add(operand=[api.Constant(value_=1.0), api.Constant(value_=2.0)])
        self.assertEqual(print_expression(o), '(1.0 + 2.0)')
        ar = api.ArgumentReference(name="foo", property_="bar")
        self.assertEqual(print_expression(ar), 'foo.bar')
        c = api.Constant(value_=1.2)
        self.assertEqual(print_expression(c), '1.2')
        s = api.SimulationStep()
        self.assertEqual(print_expression(s), 't')

    def test_print_operator(self):
        o = api.Subtract(operand=[api.Constant(value_=1.2), api.Constant(value_=3.4)])
        self.assertEqual(print_operator(o), '(1.2 - 3.4)')
        o = api.Add(operand=[api.Constant(value_=1.2), api.Constant(value_=3.4)])
        self.assertEqual(print_operator(o), '(1.2 + 3.4)')
        o = api.Multiply(operand=[api.Constant(value_=1.2), api.Constant(value_=3.4)])
        self.assertEqual(print_operator(o), '1.2 * 3.4')
        o = api.Divide(operand=[api.Constant(value_=1.2), api.Constant(value_=3.4)])
        self.assertEqual(print_operator(o), '1.2 / 3.4')
        o = api.Min(operand=[api.Constant(value_=1.2), api.Constant(value_=3.4)])
        self.assertEqual(print_operator(o), 'min(1.2, 3.4)')
        o = api.Max(operand=[api.Constant(value_=1.2), api.Constant(value_=3.4)])
        self.assertEqual(print_operator(o), 'max(1.2, 3.4)')

    def test_get_default_property(self):
        self.assertEqual(get_default_property('ACSource'), 'amplitude')
        self.assertEqual(get_default_property('DCSource'), 'amplitude')
        self.assertEqual(get_default_property('FixedFrequency'), 'rate')
        self.assertEqual(get_default_property('LeakyIntegratorAlpha'), 'voltage')
        self.assertEqual(get_default_property('LeakyIntegratorExp'), 'voltage')
        self.assertEqual(get_default_property('NCSource'), 'mean')
        self.assertEqual(get_default_property('Poisson'), 'rate')
        self.assertEqual(get_default_property('PopulationRate'), 'rate')
        self.assertEqual(get_default_property('SpikeRecorder'), 'times')

    def test_print_neurons_index(self):
        idx = api.Index()
        idx.population = "Foo"
        idx.index = 42
        self.assertEqual(get_neurons_index(idx), str(idx.index))
        self.assertEqual(print_neurons(idx, "nrp.brain."), "nrp.brain.Foo[42]")

    def test_print_neurons_range(self):
        rng = api.Range()
        rng.population = "Foo"
        rng.from_ = 7
        rng.to = 12
        self.assertEqual(print_neurons_index(rng), "slice(7, 12)")
        self.assertEqual(get_neurons_index(rng), "7:12")
        self.assertEqual(print_neurons(rng), "Foo[7:12]")
        self.assertEqual(print_neurons(rng, "nrp.brain."), "nrp.brain.Foo[slice(7, 12)]")
        rng.step = 2
        self.assertEqual(print_neurons_index(rng), "slice(7, 12, 2)")
        self.assertEqual(get_neurons_index(rng), "7:2:12")
        self.assertEqual(print_neurons(rng), "Foo[7:2:12]")
        self.assertEqual(print_neurons(rng, "nrp.brain."), "nrp.brain.Foo[slice(7, 12, 2)]")

    def test_print_neurons_list(self):
        lst = api.List()
        lst.population = "Foo"
        self.assertEqual(get_neurons_index(lst), "[]")
        self.assertEqual(print_neurons(lst), "Foo[[]]")
        self.assertEqual(print_neurons(lst, "nrp.brain."), "nrp.brain.Foo[[]]")
        lst.element.append(5)
        self.assertEqual(get_neurons_index(lst), "[5]")
        self.assertEqual(print_neurons(lst), "Foo[[5]]")
        self.assertEqual(print_neurons(lst, "nrp.brain."), "nrp.brain.Foo[[5]]")
        lst.element.append(10)
        self.assertEqual(get_neurons_index(lst), "[5, 10]")
        self.assertEqual(print_neurons(lst), "Foo[[5, 10]]")
        self.assertEqual(print_neurons(lst, "nrp.brain."), "nrp.brain.Foo[[5, 10]]")

    def test_print_neurons_population(self):
        pop = api.Population()
        pop.population = "Foo"
        pop.count = 42
        self.assertEqual(get_neurons_index(pop), None)
        self.assertEqual(print_neurons(pop), "Foo")
        self.assertEqual(print_neurons(pop, "nrp.brain."), "nrp.brain.Foo")

    def test_print_neurons_index_template(self):
        idx = api.IndexTemplate()
        idx.index = "i+3"
        self.assertEqual(get_neuron_template(idx), "[i+3]")

    def test_print_neurons_range_template(self):
        rng = api.RangeTemplate()
        rng.from_ = "i+7"
        rng.to = "2*i+12"
        self.assertEqual(get_neuron_template(rng), "[slice(i+7, 2*i+12)]")
        rng.step = 2
        self.assertEqual(get_neuron_template(rng), "[slice(i+7, 2*i+12, 2)]")

    def test_print_neurons_list_template(self):
        lst = api.ListTemplate()
        self.assertEqual(get_neuron_template(lst), "[[]]")
        lst.element.append("i")
        self.assertEqual(get_neuron_template(lst), "[[i]]")
        lst.element.append("2*(i+1)")
        self.assertEqual(get_neuron_template(lst), "[[i, 2*(i+1)]]")

    def test_print_template_raises(self):
        self.assertRaises(Exception, get_neuron_template, None)

    def test_get_all_neurons_as_dict_range(self):
        populations = [api.Range(population='foo', from_=0, to=2)]
        self.assertEqual(get_all_neurons_as_dict(populations), {'foo':slice(0,2)})
        populations = [api.List(population='foo', element=[1,3])]
        self.assertEqual(get_all_neurons_as_dict(populations), {'foo':[1,3]})
        populations = [api.Population(population='foo', count=5)]
        self.assertEqual(get_all_neurons_as_dict(populations), {'foo':None})
        self.assertRaises(Exception, get_all_neurons_as_dict, ['foo'])

    def test_get_collection_source_range(self):
        rng = api.Range()
        rng.population = "Foo"
        rng.from_ = 7
        rng.to = 12
        self.assertEqual(get_collection_source(rng), "range(7, 12)")
        rng.step = 2
        self.assertEqual(get_collection_source(rng), "range(7, 12, 2)")

    def test_get_collection_source_list(self):
        lst = api.List()
        lst.population = "Foo"
        self.assertEqual(get_collection_source(lst), "[]")
        lst.element.append(5)
        self.assertEqual(get_collection_source(lst), "[5]")
        lst.element.append(11)
        self.assertEqual(get_collection_source(lst), "[5, 11]")

    def test_get_collection_source_population(self):
        pop = api.Population()
        pop.population = "Foo"
        pop.count = 42
        self.assertEqual(get_collection_source(pop), "range(0, 42)")

    def test_get_collection_source_raises(self):
        self.assertRaises(Exception, get_collection_source, None)

    def test_print_neurons_exception(self):
        x = None
        self.assertRaises(Exception, get_neurons_index, x)

    def test_print_neuron_group_chain(self):
        chain = api.ChainSelector()
        chain.connectors.append(api.ChainSelector())
        self.assertEqual(print_neuron_group(chain), "nrp.chain_neurons(nrp.chain_neurons())")
        chain = api.ChainSelector()
        chain.neurons.append(api.Population(population="Foo", count=42))
        self.assertEqual(print_neuron_group(chain), "nrp.chain_neurons(nrp.brain.Foo)")
        chain.neurons.append(api.Population(population="Bar", count=23))
        self.assertEqual(print_neuron_group(chain),
                         "nrp.chain_neurons(nrp.brain.Foo, nrp.brain.Bar)")
        chain.connectors.append(api.ChainSelector())
        self.assertEqual(print_neuron_group(chain),
                         "nrp.chain_neurons(nrp.brain.Foo, nrp.brain.Bar, nrp.chain_neurons())")

    def test_print_neuron_group_map(self):
        map = api.MapSelector()
        map.source = api.Population(population="Foo", count=42)
        map.pattern = api.IndexTemplate(index="i")
        self.assertEqual(print_neuron_group(map),
                         "nrp.map_neurons(range(0, 42), lambda i: nrp.brain.Foo[i])")

    def test_print_neuron_group_invalid(self):
        self.assertRaises(Exception, print_neuron_group, 'foo')

    def test_print_synapse_dynamic(self):
        syn = api.TsodyksMarkramMechanism(u=1.0, tau_rec=0.0, tau_facil=0.0)
        self.assertEqual(print_synapse_dynamics(syn),
                         "{'type':'TsodyksMarkram', 'U':1.0, 'tau_rec':0.0, 'tau_facil':0.0}")
        self.assertRaises(Exception, print_synapse_dynamics, None)

    def test_print_connector(self):
        con = api.OneToOneConnector(delays=0.8, weights=42.0)
        self.assertEqual(print_connector(con),
                         "{'mode':'OneToOne', 'weights':42.0, 'delays':0.8}")
        con = api.AllToAllConnector(delays=0.8, weights=42.0)
        self.assertEqual(print_connector(con),
                         "{'mode':'AllToAll', 'weights':42.0, 'delays':0.8}")
        con = api.FixedNumberPreConnector(delays=0.8, weights=42.0, count=5)
        self.assertEqual(print_connector(con),
                         "{'mode':'Fixed', 'n':5, 'weights':42.0, 'delays':0.8}")
        self.assertRaises(Exception, print_connector, None)

    def test_print_device_config(self):
        dev = api.DeviceChannel()
        self.assertEqual(print_device_config(dev), "")
        dev.synapseDynamicsRef = api.SynapseDynamicsRef(ref="Foo")
        dev.connectorRef = api.NeuronConnectorRef(ref="Bar")
        dev.target = 'Inhibitory'
        self.assertEqual(print_device_config(dev), ", synapse_dynamics=Foo, connector=Bar, receptor_type='inhibitory'")
        dev.synapseDynamics = api.TsodyksMarkramMechanism(u=1.0, tau_rec=2.0, tau_facil=3.0)
        dev.connector = api.OneToOneConnector(delays=0.8, weights=42.0)
        self.assertEqual(print_device_config(dev),
                         ", synapse_dynamics={'type':'TsodyksMarkram', 'U':1.0, 'tau_rec':2.0, 'tau_facil':3.0}, " +
                         "connector={'mode':'OneToOne', 'weights':42.0, 'delays':0.8}, receptor_type='inhibitory'")

if __name__ == '__main__':
    unittest.main()
