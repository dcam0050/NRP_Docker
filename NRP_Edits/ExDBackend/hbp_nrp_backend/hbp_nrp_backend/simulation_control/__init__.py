"""
This package controls the simulations
"""

import pytz

__author__ = 'GeorgHinkel'

timezone = pytz.timezone('Europe/Zurich')
simulations = []

from hbp_nrp_backend.simulation_control.__Simulation import Simulation
