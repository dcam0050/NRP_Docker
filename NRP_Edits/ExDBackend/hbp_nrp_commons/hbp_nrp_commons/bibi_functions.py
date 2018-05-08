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
This module provides helper functions for the Brain and Body Integrator model (BIBI)
"""

from hbp_nrp_commons.generated import bibi_api_gen
import itertools

__author__ = "Georg Hinkel"


__device_types = {'ACSource': 'ac_source', 'DCSource': 'dc_source',
                  'FixedFrequency': 'fixed_frequency',
                  'LeakyIntegratorAlpha': 'leaky_integrator_alpha',
                  'LeakyIntegratorExp': 'leaky_integrator_exp',
                  'NCSource': 'nc_source',
                  'Poisson': 'poisson',
                  'PopulationRate': 'population_rate',
                  'SpikeRecorder': 'spike_recorder'
                  }
__device_properties = {'ACSource': 'amplitude', 'DCSource': 'amplitude',
                       'FixedFrequency': 'rate',
                       'LeakyIntegratorAlpha': 'voltage',
                       'LeakyIntegratorExp': 'voltage',
                       'NCSource': 'mean',
                       'Poisson': 'rate',
                       'PopulationRate': 'rate',
                       'SpikeRecorder': 'times'}
__operator_symbols = {bibi_api_gen.Subtract: '({0} - {1})',
                      bibi_api_gen.Add: '({0} + {1})',
                      bibi_api_gen.Multiply: '{0} * {1}',
                      bibi_api_gen.Divide: '{0} / {1}',
                      bibi_api_gen.Min: 'min({0}, {1})',
                      bibi_api_gen.Max: 'max({0}, {1})'}


def print_expression(expression):
    """
    Prints the given flow expression to a string

    :param expression: The expression to be printed
    """

    # Pylint demands less *if* statements but each *if* is very simple so that should be ok
    # pylint: disable=R0911
    if isinstance(expression, bibi_api_gen.Scale):
        return str(expression.factor) + ' * ' + print_expression(expression.inner)
    if isinstance(expression, bibi_api_gen.Call):
        temp = expression.type + '('
        i = 1
        for argument in expression.argument:
            temp += argument.name + '=' + print_expression(argument.value_)
            if i < len(expression.argument):
                temp += ', '
            i += 1
        return temp + ')'
    if isinstance(expression, bibi_api_gen.Operator):
        return print_operator(expression)
    if isinstance(expression, bibi_api_gen.ArgumentReference):
        if expression.property_ is None:
            return expression.name
        else:
            return expression.name + '.' + expression.property_
    if isinstance(expression, bibi_api_gen.Constant):
        return str(expression.value_)

    if isinstance(expression, bibi_api_gen.SimulationStep):
        return "t"

    raise Exception('No idea how to print expression of type ' + repr(type(expression)))


def print_operator(expression):
    """
    Prints the given operator expression to a string

    :param expression: The operator expression to be printed
    """
    text = print_expression(expression.operand[0])
    operator = __operator_symbols[type(expression)]
    for i in range(1, len(expression.operand)):
        text = operator.format(text, print_expression(expression.operand[i]))
    return text


def get_default_property(device_type):
    """
    Gets the default property for the given device type

    :param device_type: The device type
    """
    return __device_properties[device_type]


def print_neurons(neuron_selector, prefix=None):
    """
    Gets a string representing the accessed neuron population

    :param neuron_selector: The neuron selector
    :param prefix: the neuron prefix
    """
    if prefix is not None:
        index = print_neurons_index(neuron_selector)
    else:
        index = get_neurons_index(neuron_selector)
        prefix = ""
    if index is not None:
        return prefix + neuron_selector.population + "[" + index + "]"
    return prefix + neuron_selector.population


def __get_neurons_index(neurons, slice_format):
    """
    Gets the indexing operator for the given neuron selector

    :param neurons: The neuron selector
    :return: A string with the appropriate index or None
    """

    if isinstance(neurons, bibi_api_gen.Index):
        return str(neurons.index)
    elif isinstance(neurons, bibi_api_gen.Range):
        return slice_format(neurons.from_, neurons.step, neurons.to)
    elif isinstance(neurons, bibi_api_gen.List):
        if len(neurons.element) == 0:
            return '[]'
        neuron_list = '[' + str(neurons.element[0])
        for i in range(1, len(neurons.element)):
            neuron_list = neuron_list + ', ' + str(neurons.element[i])
        return neuron_list + ']'
    elif isinstance(neurons, bibi_api_gen.Population):
        return None
    raise Exception("Neuron Print: Don't know how to process neuron selector " + str(neurons))


def get_neurons_index(neurons):
    """
    Gets the indexing operator for the given neuron selector in a comprehensive style

    :param neurons: The neuron selector
    :return: A string with the appropriate index or None
    """
    def slice_format(from_, step, to):
        """
        Formats a slice appropriately

        :param from_: The start parameter of a slice
        :param step: The step parameter of a slice
        :param to: The stop parameter
        """
        if step is not None:
            return str(from_) + ":" + str(step) + ":" + str(to)
        else:
            return str(from_) + ":" + str(to)
    return __get_neurons_index(neurons, slice_format)


def print_neurons_index(neurons):
    """
    Gets the indexing operator for the given neuron selector in a python style

    :param neurons: The neuron selector
    :return: A string with the appropriate index or None
    """
    def slice_format(from_, step, to):
        """
        Formats a slice appropriately

        :param from_: The start parameter of a slice
        :param step: The step parameter of a slice
        :param to: The stop parameter
        """
        if step is not None:
            return "slice(" + str(from_) + ", " + str(to) + ", " + str(step) + ")"
        else:
            return "slice(" + str(from_) + ", " + str(to) + ")"
    return __get_neurons_index(neurons, slice_format)


def get_device_name(device_type):
    """
    Gets the CLE name of the given device type

    :param device_type: The device type
    """
    return __device_types[device_type]


def get_neuron_count(neurons):
    """
    Gets the amount of neurons connected

    :param neurons: The neuron selector
    :return: The amount of neurons as int
    """
    if isinstance(neurons, bibi_api_gen.Index):
        return 1
    elif isinstance(neurons, bibi_api_gen.Range):
        if neurons.step is None:
            return neurons.to - neurons.from_
        return (neurons.to - neurons.from_) / neurons.step
    elif isinstance(neurons, bibi_api_gen.List):
        return len(neurons.element)
    elif isinstance(neurons, bibi_api_gen.Population):
        return neurons.count
    raise Exception("Neuron Count: Don't know how to process neuron selector "
                    + str(type(neurons)))


def get_neuron_template(neurons):
    """
    Prints the given neuron selector template

    :param neurons: The neurons selector template
    :return: The neurons selection
    """
    if isinstance(neurons, bibi_api_gen.IndexTemplate):
        return "[" + str(neurons.index) + "]"
    if isinstance(neurons, bibi_api_gen.RangeTemplate):
        step_string = ""
        if neurons.step is not None:
            step_string = ', ' + str(neurons.step)
        return '[slice(' + str(neurons.from_) + ', ' + str(neurons.to) \
               + step_string + ')]'
    if isinstance(neurons, bibi_api_gen.ListTemplate):
        if len(neurons.element) == 0:
            return '[[]]'
        neuron_list = '[[' + neurons.element[0]
        for i in range(1, len(neurons.element)):
            neuron_list = neuron_list + ', ' + neurons.element[i]
        return neuron_list + ']]'
    raise Exception("Neuron Print: Don't know how to process neuron selector "
                    + str(type(neurons)))


def get_all_neurons_as_dict(populations):
    """
    Gets the indexing operator for the given neuron selector

    :param populations: All populations
    :return: A dict with population name and slice()/list/None
    """
    pop = dict()
    for neurons in populations:
        if isinstance(neurons, bibi_api_gen.Range):
            if hasattr(neurons, 'step'):
                pop[neurons.population] = slice(neurons.from_, neurons.to, neurons.step)
            else:
                pop[neurons.population] = slice(neurons.from_, neurons.to)
        elif isinstance(neurons, bibi_api_gen.List):
            n_list = []
            for element in neurons.element:
                n_list.append(element)
            pop[neurons.population] = n_list
        elif isinstance(neurons, bibi_api_gen.Population):
            pop[neurons.population] = None
        else:
            raise Exception("Neuron Print: Don't know how to process neuron selector " +
                            str(neurons))

    return pop


def get_collection_source(selector):
    """
    Gets the collection specifier for the given neuron source

    :param selector: The neuron source
    :return: A collection specifier as string
    """
    if isinstance(selector, bibi_api_gen.Range):
        step_string = ""
        if selector.step is not None:
            step_string = ', ' + str(selector.step)
        return 'range(' + str(selector.from_) + ', ' + str(selector.to) \
               + step_string + ')'
    elif isinstance(selector, bibi_api_gen.List):
        if len(selector.element) == 0:
            return '[]'
        neuron_list = '[' + str(selector.element[0])
        for i in range(1, len(selector.element)):
            neuron_list = neuron_list + ', ' + str(selector.element[i])
        return neuron_list + ']'
    elif isinstance(selector, bibi_api_gen.Population):
        return "range(0, " + str(selector.count) + ")"
    raise Exception("Neuron Print: Don't know how to process neuron selector "
                    + str(type(selector)))


def print_neuron_group(neuron_group):
    """
    Prints the given neuron group

    :param neuron_group: The given neuron group
    :return: The neuron group printed to text
    """
    if isinstance(neuron_group, bibi_api_gen.MapSelector):
        result = "nrp.map_neurons(" + get_collection_source(neuron_group.source) + ", " + \
                 "lambda i: nrp.brain." + neuron_group.source.population + \
                 get_neuron_template(neuron_group.pattern) + ")"
        return result
    elif isinstance(neuron_group, bibi_api_gen.ChainSelector):
        result = "nrp.chain_neurons("
        anything = False
        for neuron_selector in neuron_group.neurons:
            if anything:
                result += ", "
            else:
                anything = True
            result += print_neurons(neuron_selector, "nrp.brain.")
        for group in neuron_group.connectors:
            if anything:
                result += ", "
            else:
                anything = True
            result += print_neuron_group(group)
        result += ")"
        return result
    raise Exception("Don't know how to print group of type " + str(type(neuron_group)))


def get_referenced_connectors(tf, config):
    """
    Gets the connectors referenced by the given transfer function

    :param tf: The given transfer function
    :return: A list of connectors
    """
    connector_names = []
    for dev in itertools.chain(tf.device, tf.deviceGroup):
        if dev.connectorRef is not None and not dev.connectorRef.ref in connector_names:
            connector_names.append(dev.connectorRef.ref)
    if len(connector_names) > 0:
        conn_dict = {}
        for conn in config.connectors:
            conn_dict[conn.name] = conn
        for i in range(0, len(connector_names)):
            connector_names[i] = conn_dict[connector_names[i]]
    return connector_names


def get_referenced_dynamics(tf, config):
    """
    Gets the connectors referenced by the given transfer function

    :param tf: The given transfer function
    :return: A list of connectors
    """
    assert isinstance(tf, bibi_api_gen.BIBITransferFunction)
    assert isinstance(config, bibi_api_gen.BIBIConfiguration)
    dynamics_names = []
    for dev in itertools.chain(tf.device, tf.deviceGroup):
        if dev.synapseDynamicsRef is not None and not dev.synapseDynamicsRef.ref in dynamics_names:
            dynamics_names.append(dev.synapseDynamicsRef.ref)
    if len(dynamics_names) > 0:
        dynamics_dict = {}
        for dyn in config.synapseDynamics:
            dynamics_dict[dyn.name] = dyn
        for i in range(0, len(dynamics_names)):
            dynamics_names[i] = dynamics_dict[dynamics_names[i]]
    return dynamics_names


def print_device_config(dev):
    """
    Prints the configuration of the given device or device group

    :param dev: The device or device group
    :return: The device configuration as string
    """
    res = ""
    if dev.synapseDynamics is not None:
        res += ", synapse_dynamics=" + print_synapse_dynamics(dev.synapseDynamics)
    elif dev.synapseDynamicsRef is not None:
        res += ", synapse_dynamics=" + dev.synapseDynamicsRef.ref
    if dev.connector is not None:
        res += ", connector=" + print_connector(dev.connector)
    elif dev.connectorRef is not None:
        res += ", connector=" + dev.connectorRef.ref
    if dev.target is not None:
        res += ", receptor_type='" + dev.target.lower() + "'"
    return res


def print_synapse_dynamics(synapse_dynamics):
    """
    Creates a synapse dynamics initialization

    :param synapse_dynamics: The synanapse dynamics element
    :return: Code that creates the synapse dynamics
    """
    if isinstance(synapse_dynamics, bibi_api_gen.TsodyksMarkramMechanism):
        return "{{'type':'TsodyksMarkram', 'U':{0}, 'tau_rec':{1}, 'tau_facil':{2}}}" \
            .format(synapse_dynamics.u, synapse_dynamics.tau_rec, synapse_dynamics.tau_facil)
    raise Exception(
        "Don't know how to print synapse dynamics of type " + str(type(synapse_dynamics)))


def print_connector(connector):
    """
    Creates a neuron connector

    :param connector: The neuron connector model
    :return: Code that creates the neuron connector
    """
    if isinstance(connector, bibi_api_gen.OneToOneConnector):
        return "{{'mode':'OneToOne', 'weights':{0}, 'delays':{1}}}".format(connector.weights,
                                                                           connector.delays)
    if isinstance(connector, bibi_api_gen.AllToAllConnector):
        return "{{'mode':'AllToAll', 'weights':{0}, 'delays':{1}}}".format(connector.weights,
                                                                           connector.delays)
    if isinstance(connector, bibi_api_gen.FixedNumberPreConnector):
        return "{{'mode':'Fixed', 'n':{2}, 'weights':{0}, 'delays':{1}}}".format(
            connector.weights, connector.delays, connector.count)
    raise Exception("Don't know how to print connector of type " + str(type(connector)))


def find_changed_strings(list_a, list_b):
    """
    Returns a list that contains changed population names,
    i.e. stings from list_a are searched for in list_b. Not found strings are returned.

    :param list_a: looked up strings to be found in list_b
    :param list_b: looked up strings are compared against strings in list_a

    :return: a list of strings
    """
    changed = []
    for element_a in list_a:
        if element_a not in list_b:
            changed.append(element_a)
    return changed


def docstring_parameter(*sub):
    """
    Helper functions to include variables in docstrings using the @docstring_parameter decorator

    :param sub: List of variables to be included in the docstring.
    """
    def dec(obj):
        """
        Reformat docstring with variables.
        """
        obj.__doc__ = obj.__doc__.format(*sub)
        return obj

    return dec
