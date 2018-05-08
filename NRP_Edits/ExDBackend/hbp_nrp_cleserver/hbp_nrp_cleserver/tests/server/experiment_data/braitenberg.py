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

import pyNN.nest as sim
import numpy as np
import logging

logger = logging.getLogger(__name__)


def create_brain():
    """
    Initializes PyNN with the neuronal network that has to be simulated
    """
    SENSORPARAMS = {'v_rest': -60.5,
                    'cm': 0.025,
                    'tau_m': 10.,
                    'tau_refrac': 10.0,
                    'tau_syn_E': 2.5,
                    'tau_syn_I': 2.5,
                    'e_rev_E': 0.0,
                    'e_rev_I': -75.0,
                    'v_thresh': -60.0,
                    'v_reset': -60.5}

    GO_ON_PARAMS = {'v_rest': -60.5,
                    'cm': 0.025,
                    'tau_m': 10.0,
                    'e_rev_E': 0.0,
                    'e_rev_I': -75.0,
                    'v_reset': -61.6,
                    'v_thresh': -60.51,
                    'tau_refrac': 10.0,
                    'tau_syn_E': 2.5,
                    'tau_syn_I': 2.5}

    # POPULATION_PARAMS = SENSORPARAMS * 5 + GO_ON_PARAMS + SENSORPARAMS * 2

    population = sim.Population(8, sim.IF_cond_alpha())
    population[0:5].set(**SENSORPARAMS)
    population[5:6].set(**GO_ON_PARAMS)
    population[6:8].set(**SENSORPARAMS)

    # Shared Synapse Parameters
    syn_params = {'U': 1.0, 'tau_rec': 1.0, 'tau_facil': 1.0}

    # Synaptic weights
    WEIGHT_RED_TO_ACTOR = 1.5e-4
    WEIGHT_RED_TO_GO_ON = 1.2e-3  # or -1.2e-3?
    WEIGHT_GREEN_BLUE_TO_ACTOR = 1.05e-4
    WEIGHT_GO_ON_TO_RIGHT_ACTOR = 1.4e-4
    DELAY = 0.1

    # Connect neurons
    CIRCUIT = population

    SYN = sim.TsodyksMarkramSynapse(weight=abs(WEIGHT_RED_TO_ACTOR),
                                    delay=DELAY, **syn_params)
    sim.Projection(presynaptic_population=CIRCUIT[2:3],
                   postsynaptic_population=CIRCUIT[7:8],
                   connector=sim.AllToAllConnector(),
                   synapse_type=SYN,
                   receptor_type='excitatory')
    sim.Projection(presynaptic_population=CIRCUIT[3:4],
                   postsynaptic_population=CIRCUIT[6:7],
                   connector=sim.AllToAllConnector(),
                   synapse_type=SYN,
                   receptor_type='excitatory')

    SYN = sim.TsodyksMarkramSynapse(weight=abs(WEIGHT_RED_TO_GO_ON),
                                    delay=DELAY, **syn_params)
    sim.Projection(presynaptic_population=CIRCUIT[0:2],
                   postsynaptic_population=CIRCUIT[5:6],
                   connector=sim.AllToAllConnector(),
                   synapse_type=SYN,
                   receptor_type='inhibitory')

    SYN = sim.TsodyksMarkramSynapse(weight=abs(WEIGHT_GREEN_BLUE_TO_ACTOR),
                                    delay=DELAY, **syn_params)
    sim.Projection(presynaptic_population=CIRCUIT[4:5],
                   postsynaptic_population=CIRCUIT[7:8],
                   connector=sim.AllToAllConnector(),
                   synapse_type=SYN,
                   receptor_type='excitatory')

    SYN = sim.TsodyksMarkramSynapse(weight=abs(WEIGHT_GO_ON_TO_RIGHT_ACTOR),
                                    delay=DELAY, **syn_params)
    sim.Projection(presynaptic_population=CIRCUIT[5:6],
                   postsynaptic_population=CIRCUIT[7:8],
                   connector=sim.AllToAllConnector(),
                   synapse_type=SYN,
                   receptor_type='excitatory')

    sim.initialize(population, v=population.get('v_rest'))

    logger.debug("Circuit description: " + str(population.describe()))

    return population


circuit = create_brain()
