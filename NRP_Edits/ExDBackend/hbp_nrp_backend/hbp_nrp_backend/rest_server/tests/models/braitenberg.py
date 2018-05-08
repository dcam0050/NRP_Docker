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
# -*- coding: utf-8 -*-
"""
This file contains the setup of the neuronal network running the Husky experiment with neuronal image recognition
"""
# pragma: no cover

__author__ = 'Lazar Mateev, Georg Hinkel'

import hbp_nrp_cle.tf_framework as nrp
import logging
import pyNN.nest as sim
import numpy as np
from pyNN.nest import *


nest.SetKernelStatus({'dict_miss_is_error': False})
logger = logging.getLogger(__name__)

def create_brain():
    """
    Initializes PyNN with the neuronal network that has to be simulated
    """
    C_m = 25.0
    g_L = 2.5
    t_m = C_m / g_L

    SENSORPARAMS = {'a': 0.0,
                    'b': 0.0,
                    'delta_T': 0.0,
                    'tau_w': 10.0,
                    'v_spike': 0.0,
                    'cm': C_m,
                    'v_rest': -60.5,
                    'tau_m': t_m,
                    'e_rev_E': 0.0,
                    'e_rev_I': -75.0,
                    'v_reset': -60.5,
                    'v_thresh': -60.0,
                    'tau_refrac': 10.0,
                    'tau_syn_E': 2.5,
                    'tau_syn_I': 2.5}

    GO_ON_PARAMS = {'a': 0.0,
                    'b': 0.0,
                    'delta_T': 0.0,
                    'tau_w': 10.0,
                    'v_spike': 0.0,
                    'cm': C_m,
                    'v_rest': -60.5,
                    'tau_m': t_m,
                    'e_rev_E': 0.0,
                    'e_rev_I': -75.0,
                    'v_reset': -61.6,
                    'v_thresh': -60.51,
                    'tau_refrac': 10.0,
                    'tau_syn_E': 2.5,
                    'tau_syn_I': 2.5}

    # 3 sensor neurons
    # SENSORS = sim.Population(5, sim.EIF_cond_exp_isfa_ista, cellparams=SENSORPARAMS)
    # # Go-on-node and 2 actor neurons
    # GO_ON = sim.Population(1, sim.EIF_cond_exp_isfa_ista, cellparams=GO_ON_PARAMS)
    # ACTORS = sim.Population(2, sim.EIF_cond_exp_isfa_ista, cellparams=SENSORPARAMS)
    cells = sim.Population(8, sim.EIF_cond_alpha_isfa_ista)
    params = {'U': 1.0, 'tau_rec': 0.0, 'tau_facil': 0.0}
    syndynamics = sim.SynapseDynamics(fast=sim.TsodyksMarkramMechanism(**params))
    # sim.initialize(SENSORS, 'v', SENSORS[0].v_rest)
    # sim.initialize(GO_ON, 'v', SENSORS[0].v_rest)
    # sim.initialize(ACTORS, 'v', ACTORS[0].v_rest)

    # CIRCUIT = SENSORS + GO_ON + ACTORS  # Assembly of 8 neurons

    # Synaptic weights
    WEIGHT_RED_TO_ACTOR = 1.5e-4
    WEIGHT_RED_TO_GO_ON = 1.2e-3  # or -1.2e-3?
    WEIGHT_GREEN_BLUE_TO_ACTOR = 1.05e-4
    WEIGHT_GO_ON_TO_RIGHT_ACTOR = 1.4e-4
    DELAY = 0.1

    # Connect neurons
    CONN = sim.AllToAllConnector(weights=abs(WEIGHT_RED_TO_ACTOR),
                                 delays=DELAY)

    sim.Projection(cells[2:3], cells[7:8], CONN, synapse_dynamics=syndynamics, target='excitatory')
    sim.Projection(cells[3:4], cells[6:7], CONN, synapse_dynamics=syndynamics, target='excitatory')
    CONN = sim.AllToAllConnector(weights=abs(WEIGHT_RED_TO_GO_ON),
                                 delays=DELAY)

    sim.Projection(cells[0:2], cells[5:6], CONN, synapse_dynamics=syndynamics, target='inhibitory')
    CONN = sim.AllToAllConnector(weights=abs(WEIGHT_GREEN_BLUE_TO_ACTOR),
                                 delays=DELAY)

    sim.Projection(cells[4:5], cells[7:8], CONN, synapse_dynamics=syndynamics, target='excitatory')
    CONN = sim.AllToAllConnector(weights=abs(WEIGHT_GO_ON_TO_RIGHT_ACTOR),
                                 delays=DELAY)

    sim.Projection(cells[5:6], cells[7:8], CONN, synapse_dynamics=syndynamics, target='excitatory')


    #connect to color detection neurons

    formatted_circuit = {
        "population": cells,
        "x": np.float64(np.array([0, 1, 2, 3, 4, 5, 6, 7])),
        "y": np.float64(np.array([0, 1, 2, 3, 4, 5, 6, 7])),
        "z": np.float64(np.array([0, 1, 2, 3, 4, 5, 6, 7])),
        "layer": np.int16(np.array([1, 1, 1, 1, 1, 2, 3, 3])),
        "mtype": np.array(['SC', 'SC', 'SC', 'SC', 'SC', 'GOC', 'AC', 'AC']),
        "a": np.float64(np.array([SENSORPARAMS.get('a')] * 5 + [GO_ON_PARAMS.get('a')] +
                                 [SENSORPARAMS.get('a')] * 2)),
        "b": np.float64(np.array([SENSORPARAMS.get('b')] * 5 + [GO_ON_PARAMS.get('b')] +
                                 [SENSORPARAMS.get('b')] * 2)),
        "V_th": np.float64(np.array([SENSORPARAMS.get('v_thresh')] * 5 +
                                    [GO_ON_PARAMS.get('v_thresh')] +
                                    [SENSORPARAMS.get('v_thresh')] * 2)),
        "Delta_T": np.float64(np.array([SENSORPARAMS.get('delta_T')] * 5 +
                                       [GO_ON_PARAMS.get('delta_T')] +
                                       [SENSORPARAMS.get('delta_T')] * 2)),
        "C_m": np.float64(
            np.array([SENSORPARAMS.get('cm')] * 5 + [GO_ON_PARAMS.get('cm')] +
                     [SENSORPARAMS.get('cm')] * 2)),
        "g_L": np.float64(np.array([g_L] * 8)),
        "V_reset": np.float64(np.array([SENSORPARAMS.get('v_reset')] * 5 +
                                       [GO_ON_PARAMS.get('v_reset')] +
                                       [SENSORPARAMS.get('v_reset')] * 2)),
        "tau_w": np.float64(np.array([SENSORPARAMS.get('tau_w')] * 5 +
                                     [GO_ON_PARAMS.get('tau_w')] +
                                     [SENSORPARAMS.get('tau_w')] * 2)),
        "t_ref": np.float64(np.array([SENSORPARAMS.get('tau_refrac')] * 5 +
                                     [GO_ON_PARAMS.get('tau_refrac')] +
                                     [SENSORPARAMS.get('tau_refrac')] * 2)),
        "V_peak": np.float64(np.array([SENSORPARAMS.get('v_spike')] * 5 +
                                      [GO_ON_PARAMS.get('v_spike')] +
                                      [SENSORPARAMS.get('v_spike')] * 2)),
        "E_L": np.float64(np.array([SENSORPARAMS.get('v_rest')] * 5 +
                                   [GO_ON_PARAMS.get('v_rest')] +
                                   [SENSORPARAMS.get('v_rest')] * 2)),
        "E_ex": np.float64(np.array([SENSORPARAMS.get('e_rev_E')] * 5 +
                                    [GO_ON_PARAMS.get('e_rev_E')] +
                                    [SENSORPARAMS.get('e_rev_E')] * 2)),
        "E_in": np.float64(np.array([SENSORPARAMS.get('e_rev_I')] * 5 +
                                    [GO_ON_PARAMS.get('e_rev_I')] +
                                    [SENSORPARAMS.get('e_rev_I')] * 2)),
        "tau_syn_E": np.float64(np.array([SENSORPARAMS.get('tau_syn_E')] * 5 +
                                         [GO_ON_PARAMS.get('tau_syn_E')] +
                                         [SENSORPARAMS.get('tau_syn_E')] * 2)),
        "tau_syn_I": np.float64(np.array([SENSORPARAMS.get('tau_syn_I')] * 5 +
                                         [GO_ON_PARAMS.get('tau_syn_I')] +
                                         [SENSORPARAMS.get('tau_syn_I')] * 2)),
        "excitatory": np.array([90, 90, 110, 110, 110, 110, 110, 110])
    }

    population = formatted_circuit['population']

    # AdEx parameters are set
    population.tset('a', formatted_circuit["a"])  # nS
    population.tset('b', formatted_circuit["b"] * 1e-3)  # pA -> nA
    population.tset('v_thresh', formatted_circuit["V_th"])
    population.tset('delta_T', formatted_circuit["Delta_T"])
    population.tset('cm', formatted_circuit["C_m"] * 1e-3)  # pF->nF
    population.tset('tau_m', formatted_circuit["C_m"] / formatted_circuit["g_L"])
    population.tset('v_reset', formatted_circuit["V_reset"])
    population.tset('tau_w', formatted_circuit["tau_w"])
    population.tset('tau_refrac', formatted_circuit["t_ref"])
    population.tset('v_spike', formatted_circuit["V_peak"])
    population.tset('v_rest', formatted_circuit["E_L"])
    population.tset('e_rev_E', formatted_circuit["E_ex"])
    population.tset('e_rev_I', formatted_circuit["E_in"])
    population.tset('tau_syn_E', formatted_circuit["tau_syn_E"])
    population.tset('tau_syn_I', formatted_circuit["tau_syn_I"])

    sim.initialize(population, 'v',
                   population.get('v_rest'))


    logger.debug("Circuit description: " + str(population.describe()))
    return population


circuit = create_brain()

