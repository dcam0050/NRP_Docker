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
This module contains the REST services to download sdf files
describing the world in which a simulation is carried out.
"""

__author__ = 'UgoAlbanese'

from hbp_nrp_backend.rest_server import NRPServicesClientErrorException, \
     NRPServicesUnavailableROSService
from gazebo_msgs.srv import ExportWorldSDF
from flask_restful import fields, Resource
from flask_restful_swagger import swagger
import logging
import rospy
from lxml import etree as ET

# pylint: disable=no-self-use

logger = logging.getLogger(__name__)


class WorldSDFService(Resource):
    """
    The sdf world file download service
    """

    @swagger.model
    class sdfData(object):
        """
        Represents environment sdf file
        Only used for swagger documentation
        """
        resource_fields = {
            'sdf': fields.String()
        }

        required = ['sdf']

    @swagger.operation(
        notes='Returns the SDF file describing the world without robots',
        responseClass=sdfData.__name__,
        responseMessages=[
            {
                "code": 500,
                "message": "ROS service not available"
            },
            {
                "code": 400,
                "message": "A ROS error occurred"
            },
            {
                "code": 200,
                "message": "SDF successfully returned"
            }
        ]
    )
    def get(self):
        """
        Returns the SDF file describing the world in which the simulation is carried out

        :> json string sdf: the SDF string describing the world excluding the robots involved

        :status 500: ROS service not available
        :status 400: A ROS error occurred
        :status 200: SDF file successfully returned
        """

        try:
            rospy.wait_for_service('/gazebo/export_world_sdf', 3)
        except rospy.ROSException as exc:
            raise NRPServicesUnavailableROSService(str(exc))

        dump_sdf_world = rospy.ServiceProxy('/gazebo/export_world_sdf', ExportWorldSDF)

        try:
            sdf_string = dump_sdf_world().sdf_dump
            tree = ET.fromstring(sdf_string)
            for m in tree.findall(".//model[@name='robot']"):
                m.getparent().remove(m)
            sdf_string = ET.tostring(tree, encoding='utf8', method='xml')
        except rospy.ServiceException as exc:
            raise NRPServicesClientErrorException(
                "Service did not process request:" + str(exc))

        return {"sdf": sdf_string}, 200
