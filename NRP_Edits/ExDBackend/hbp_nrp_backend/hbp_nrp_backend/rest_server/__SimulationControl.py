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
This module contains the REST implementation for the simulation control
"""
__author__ = 'GeorgHinkel'

from hbp_nrp_backend.rest_server import NRPServicesClientErrorException, \
    NRPServicesWrongUserException, NRPServicesUnavailableROSService, \
    NRPServicesGeneralException, ErrorMessages

from hbp_nrp_commons.bibi_functions import docstring_parameter

from flask import request
from flask_restful import Resource, abort, marshal_with, fields
from flask_restful_swagger import swagger

from hbp_nrp_backend.simulation_control import simulations, Simulation
from hbp_nrp_backend.__UserAuthentication import UserAuthentication

from std_msgs.msg import ColorRGBA
from gazebo_msgs.srv import SetVisualProperties, SetLightProperties, GetLightProperties
import rospy

# pylint: disable=no-self-use


def _get_simulation_or_abort(sim_id):
    """
    Gets the simulation with the given simulation id or aborts the simulation otherwise

    :param sim_id: The simulation id
    """
    if sim_id < 0 or sim_id >= len(simulations):
        abort(404)
    return simulations[sim_id]


class SimulationControl(Resource):
    """
    The resource to control the simulation
    """

    @swagger.operation(
        notes='Gets the simulation with given sim_id',
        responseClass=Simulation.__name__,
        parameters=[
            {
                "name": "sim_id",
                "description": "The ID of the simulation whose state shall be retrieved",
                "required": True,
                "allowMultiple": False,
                "paramType": "path",
                "dataType": int.__name__
            }
        ],
        responseMessages=[
            {
                "code": 404,
                "message": ErrorMessages.SIMULATION_NOT_FOUND_404
            },
            {
                "code": 200,
                "message": "Success. The simulation with the given ID is retrieved"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404)
    @marshal_with(Simulation.resource_fields)
    def get(self, sim_id):
        """
        Gets the simulation with the specified simulation id

        :param sim_id: The simulation id

        :> json string state: The current state of the simulation
        :> json integer simulationID: The id of the simulation (needed for further REST calls)
        :> json string experimentConfiguration: Path and name of the experiment configuration file
        :> json string environmentConfiguration: Path and name of the environment configuration file
        :> json string owner: The simulation owner (Unified Portal user id or 'hbp-default')
        :> json string creationDate: Date of creation of this simulation
        :> json string gzserverHost: Denotes where the simulation will run once started. Set to
                                     'local' for localhost and 'lugano' for a dedicate machine on
                                     the Lugano viz cluster
        :> json string reservation: the name of the cluster reservation subsequently used to
                                    allocate a job
        :> json string experimentID: The expeirment ID if the experiment is using the storage
        :> json integer brainProcesses: Number of brain processes to use (overrides ExD conf.)
        :> json string creationUniqueID: unique creation ID (used by Frontend to identify this sim.)

        :status 404: {0}
        :status 200: The simulation with the given ID is successfully retrieved
        """
        return _get_simulation_or_abort(sim_id), 200


@swagger.model
class _RGBADescription(object):
    """Describe a RGBA color"""
    resource_fields = {
        'r': fields.Float,
        'g': fields.Float,
        'b': fields.Float,
        'a': fields.Float,
    }


@swagger.model
@swagger.nested(diffuse=_RGBADescription.__name__, )
class _LightDescription(object):
    """
    Describe a light

    :< json string name: name of the light
    """
    resource_fields = {
        'name': fields.String,
        'diffuse': fields.Nested(_RGBADescription.resource_fields),
        'attenuation_constant': fields.Float,
        'attenuation_linear': fields.Float,
        'attenuation_quadratic': fields.Float,
    }
    required = ['name']


class LightControl(Resource):
    """
    The resource to change the light intensity
    """

    @swagger.operation(
        notes='Controls the light of the given light source',
        parameters=[
            {
                "name": "sim_id",
                "description": "The ID of the simulation on which light should be changed",
                "paramType": "path",
                "required": True,
                "dataType": int.__name__
            },
            {
                "name": "light",
                "description": "Description of the light to change",
                "paramType": "body",
                "required": True,
                "dataType": _LightDescription.__name__
            }
        ],
        responseMessages=[
            {
                "code": 404,
                "message": ErrorMessages.SIMULATION_NOT_FOUND_404
            },
            {
                "code": 401,
                "message": ErrorMessages.SIMULATION_PERMISSION_401
            },
            {
                "code": 400,
                "message": "The parameters are invalid"
            },
            {
                "code": 200,
                "message": "Successfully raised event"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401)
    def put(self, sim_id):
        """
        Raises a light event

        :param sim_id: The simulation ID

        :< json string name: The light to change
        :< json RGBADescription diffuse: the diffuse color
        :< json float attenuation_constant: the attenuation constant
        :< json float attenuation_linear: the attenuation linear
        :< json float attenuation_quadratic: the attenuation quadratic

        :status 404: {0}
        :status 401: {1}
        :status 400: The parameters are invalid
        :status 200: Successfully raised event
        """
        simulation = _get_simulation_or_abort(sim_id)

        if not UserAuthentication.matches_x_user_name_header(request, simulation.owner):
            raise NRPServicesClientErrorException(
                "You need to be the simulation owner to trigger interactions", error_code=401)

        body = request.get_json(force=True)
        if 'name' not in body:
            raise NRPServicesClientErrorException("No name given")

        in_name = LightControl.as_ascii(body['name'])
        in_diffuse = body.get('diffuse')

        in_attenuation_constant = LightControl.as_float(body.get('attenuation_constant'))
        in_attenuation_linear = LightControl.as_float(body.get('attenuation_linear'))
        in_attenuation_quadratic = LightControl.as_float(body.get('attenuation_quadratic'))

        diffuse = None

        if in_diffuse is not None:
            diffuse = ColorRGBA(float(in_diffuse['r']), float(in_diffuse['g']),
                                float(in_diffuse['b']), float(in_diffuse['a']))

        if in_diffuse is None or in_attenuation_constant is None \
                or in_attenuation_linear is None or in_attenuation_quadratic is None:
            try:
                rospy.wait_for_service('/gazebo/get_light_properties', 3)
            except rospy.ROSException as exc:
                raise NRPServicesUnavailableROSService(str(exc))

            get_light_properties = rospy.ServiceProxy('/gazebo/get_light_properties',
                                                      GetLightProperties)

            try:
                light_properties = get_light_properties(light_name=in_name)

                if in_attenuation_constant is None:
                    in_attenuation_constant = light_properties.attenuation_constant
                if in_attenuation_linear is None:
                    in_attenuation_linear = light_properties.attenuation_linear
                if in_attenuation_quadratic is None:
                    in_attenuation_quadratic = light_properties.attenuation_quadratic
                if in_diffuse is None:
                    diffuse = light_properties.diffuse

            except rospy.ServiceException as exc:
                raise NRPServicesClientErrorException(
                    "Service did not process request:" + str(exc))

        try:
            rospy.wait_for_service('/gazebo/set_light_properties', 3)
        except rospy.ROSException as exc:
            raise NRPServicesUnavailableROSService(str(exc))

        set_light_properties = rospy.ServiceProxy('/gazebo/set_light_properties',
                                                  SetLightProperties)

        try:
            set_light_properties(light_name=in_name,
                                 diffuse=diffuse,
                                 attenuation_constant=in_attenuation_constant,
                                 attenuation_linear=in_attenuation_linear,
                                 attenuation_quadratic=in_attenuation_quadratic)
        except rospy.ServiceException as exc:
            raise NRPServicesClientErrorException("Service did not process request: " + str(exc))

        return "Changed light intensity", 200

    @staticmethod
    def as_float(val):
        """
        Converts the given object to a float, provided it is not None

        :param val: The value that should be converted, can be a string, a number or None
        """
        if val is None:
            return None
        else:
            return float(val)

    @staticmethod
    def as_ascii(val):
        """
        Converts the given object to an ascii-string

        :param val: The value object that should be converted to an ascii string
        """
        if val is None:
            return None
        elif type(val) == unicode:
            return val.encode('ascii', 'ignore')
        else:
            return val


class MaterialControl(Resource):
    """
    The resource to raise a material change
    """

    @swagger.model
    class _MaterialChange(object):
        """Describe a material change command"""
        resource_fields = {
            'visual_path': fields.String,
            'material': fields.String
        }

    def __set_material(self, visual_path, material):
        """
        Sets the material of a particular visual

        :param visual_path: The visual path in the world description,
                            e.g., 'left_screen::body::screen_glass',
                            i.e., model_name::link_name::visual_name.
        :param material: The material
        :return: The response
        """
        try:
            rospy.wait_for_service('/gazebo/set_visual_properties', 3)
        except rospy.ROSException as exc:
            raise NRPServicesUnavailableROSService(str(exc))
        set_visual_properties = rospy.ServiceProxy(
            '/gazebo/set_visual_properties',
            SetVisualProperties
        )
        names = visual_path.split('::')
        if len(names) < 3:
            raise NRPServicesClientErrorException(
                "Invalid visual path: " + visual_path +
                ".\n Expected: model_name::link_name::visual_name",
                error_code=404
            )
        assert(material is not None)
        try:
            set_visual_properties(
                model_name=names[0],
                link_name="::".join(names[1:-1]),
                visual_name=names[-1],
                property_name='material:script:name',
                property_value=material
            )
        except rospy.ServiceException as exc:
            raise NRPServicesGeneralException(
                "Service did not process request: " + str(exc),
                "rospy service exception"
            )
        return {'message': 'Material changed successfully'}, 200

    @swagger.operation(
        notes='Change the material of a given visual. Currently, only the change of screen'
              'materials is implemented',
        parameters=[
            {
                "name": "sim_id",
                "description": "The ID of the simulation on which to raise the event",
                "paramType": "path",
                "required": True,
                "dataType": int.__name__
            },
            {
                "name": "material_change",
                "description": "the path to the visual target and the material to apply",
                "paramType": "body",
                "required": True,
                "dataType": _MaterialChange.__name__
            }
        ],
        responseMessages=[
            {
                "code": 404,
                "message": ErrorMessages.SIMULATION_NOT_FOUND_404
            },
            {
                "code": 401,
                "message": ErrorMessages.SIMULATION_PERMISSION_401
            },
            {
                "code": 400,
                "message": "The parameters are invalid"
            },
            {
                "code": 200,
                "message": "Material applied successfully"
            }
        ]
    )
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401)
    def put(self, sim_id):
        """
        Change the material of a given visual. Currently, only the change of screen materials is
        implemented

        :param sim_id: The simulation ID

        :< json string visual_path: The path to the visual for which a change in material is
                                    requested
        :< json string material_name: The name of the material that will be applied

        :status 404: {0}
        :status 401: {1}
        :status 400: The parameters are invalid
        :status 200: Material applied successfully
        """
        simulation = _get_simulation_or_abort(sim_id)

        if not UserAuthentication.matches_x_user_name_header(request, simulation.owner):
            raise NRPServicesWrongUserException()

        body = request.get_json(force=True)
        if 'visual_path' not in body:
            return "No visual_path given", 400
        if 'material' not in body:
            return "No material given", 400

        return self.__set_material(body['visual_path'], body['material'])
