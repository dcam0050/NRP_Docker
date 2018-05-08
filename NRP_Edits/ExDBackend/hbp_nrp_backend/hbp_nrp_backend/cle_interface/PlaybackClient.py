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
Takes care of making the appropriate ROS call(s) to play a simulation recording.
On the other side of ROS, the calls are handled by PlaybackServer.py
"""

import logging

from cle_ros_msgs import srv
from hbp_nrp_backend.cle_interface import SERVICE_SIM_RESET_ID, SERVICE_SIM_EXTEND_TIMEOUT_ID

from hbp_nrp_backend.cle_interface.ROSCLEClient import ROSCLEClient
from hbp_nrp_backend.cle_interface.ROSCLEClient import ROSCLEServiceWrapper

logger = logging.getLogger(__name__)


class PlaybackClient(ROSCLEClient):
    """
    Client around the ROS controlled simulation playback server.
    """

    # pylint: disable=super-init-not-called
    def __init__(self, sim_id):
        """
        Create the wrapper client with minimal compatibility for ROSCLEClient interfaces.

        :param sim_id: The simulation id
        """

        self._ROSCLEClient__cle_reset = ROSCLEServiceWrapper(
            SERVICE_SIM_RESET_ID(sim_id), srv.ResetSimulation, self)

        self._ROSCLEClient__cle_extend_timeout = ROSCLEServiceWrapper(
            SERVICE_SIM_EXTEND_TIMEOUT_ID(sim_id), srv.ExtendTimeout, self)

        # required to support simulation launch
        self._ROSCLEClient__cle_get_transfer_functions = srv.GetTransferFunctionsResponse
        self._ROSCLEClient__cle_get_brain = lambda: srv.GetBrainResponse(brain_populations='{}')

        # required to support reset
        self._ROSCLEClient__cle_set_brain = lambda a, b, c, d, e: srv.SetBrainResponse()
        self._ROSCLEClient__cle_add_transfer_function = \
                                       lambda a: srv.AddTransferFunctionResponse(error_message=None)

        # optional support for editor tabs
        self._ROSCLEClient__cle_get_populations = srv.GetPopulationsResponse
        self._ROSCLEClient__cle_get_structured_transfer_functions = \
                                                          srv.GetStructuredTransferFunctionsResponse
        self._ROSCLEClient__cle_get_CSV_recorders_files = srv.GetCSVRecordersFiles

        # no support required for backwards compatibility
        self._ROSCLEClient__cle_edit_transfer_function = lambda: None
        self._ROSCLEClient__cle_set_structured_transfer_function = lambda: None
        self._ROSCLEClient__cle_delete_transfer_function = lambda: None
        self._ROSCLEClient__simulation_recorder = lambda c: None

        self._ROSCLEClient__stop_reason = None
