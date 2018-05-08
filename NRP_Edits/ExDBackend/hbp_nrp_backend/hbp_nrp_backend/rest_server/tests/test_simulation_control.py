# -*- coding: utf-8 -*-
# Failing test about non ascii character? -> The line above (encoding) has to be the first of the file.

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
Code for testing all classes in hbp_nrp_backend.rest_server.__SimulationControl
"""

__author__ = 'Alessandro Ambrosano'

import unittest
import mock
import rospy
import json
from hbp_nrp_backend.rest_server import NRPServicesClientErrorException,\
    NRPServicesGeneralException, NRPServicesUnavailableROSService, app
from hbp_nrp_backend.simulation_control import simulations, Simulation
from hbp_nrp_backend.rest_server.__SimulationControl import MaterialControl, LightControl,\
    UserAuthentication
from hbp_nrp_backend.rest_server.tests import RestTest


class MockServiceProxy(object):
    """
    This class mocks the rospy ServiceProxy, its just returns its service name when called.
    """

    def __init__(self, service_name, service_class):
        self.service_name = service_name
        self.service_class = service_class

    def __call__(self, *args, **kwargs):
        TestScript.called_path = self.service_name

    def wait_for_service(self, timeout=0):  #pylint: disable=W0613, R0201
        """
        Mock for ServiceProxy.wait_for_service, it does nothing.
        """
        return None


class TestScript(RestTest):
    """
    Class for testing hbp_nrp_backend.rest_server.__SimulationControl.
    """

    def setUp(self):
        rospy.ServiceProxy = MockServiceProxy
        rospy.wait_for_service = mock.Mock(return_value=mock.Mock())

        self.mc = MaterialControl()
        self.lc = LightControl()

        del simulations[:]
        simulations.append(Simulation(0, 'test', None, 'default-owner', 'created'))

    # The following methods test the class hbp_nrp_backend.rest_server.__SimulationControl
    # .MaterialControl

    def test_material_control_wrong_user(self):
        """
        This method crafts a request from an user which is not the owner of the simulation.
        """

        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "wrong-owner"}
        with app.test_request_context(headers=hdr):
            self.assertRaises(NRPServicesClientErrorException, self.mc.put, 0)
            try:
                self.mc.put(0)
            except NRPServicesClientErrorException as e:
                self.assertEquals(e.error_code, 401)

    def test_material_control_no_visual_path(self):
        """
        This methods crafts a request from the owner of the simulation but missing the
        'visual_path'.
        """

        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {'material': 'Gazebo/Blue'}
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertEqual(self.mc.put(0)[1], 400)

    def test_material_control_no_material(self):
        """
        This methods crafts a request from the owner of the simulation but missing the
        material' parameter.
        """

        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {'visual_path': 'randomstring'}
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertEqual(self.mc.put(0)[1], 400)

    def test_material_control_invalid_visual_path(self):
        """
        This method crafts a request from the owner of the simulation with an invalid
        'visual_path' parameter.
        """

        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {'visual_path': 'randomstring::randomstring', 'material': 'Gazebo/Red'}
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            try:
                self.mc.put(0)
            except NRPServicesClientErrorException as e:
                self.assertEquals(e.error_code, 404)

    def test_material_control_ros_wait_for_service_failure(self):
        """
        This method performs a good request while ROS is unavailable.
        """

        oldwfs = rospy.wait_for_service
        rospy.wait_for_service = lambda x, y: (_ for _ in ()).throw(rospy.ROSException)
        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {'visual_path': 'model::link::visual', 'material': 'Gazebo/Red'}
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertRaises(NRPServicesUnavailableROSService, self.mc.put, 0)
            try:
                self.mc.put(0)
            except NRPServicesUnavailableROSService as e:
                self.assertEquals(e.error_code, 500)

        rospy.wait_for_service = oldwfs

    def test_material_control_ros_wait_service_proxy_failure(self):
        """
        This method performs a good request with a ROS failure in the service proxy.
        """

        oldsp = rospy.ServiceProxy
        rospy.ServiceProxy = mock.Mock(return_value=lambda model_name='', link_name='',
            visual_name='', property_name='', property_value='': (_ for _ in ()).throw(rospy.ServiceException))
        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {"visual_path": "model::link::visual", 'material': 'Gazebo/Red'}
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertRaises(NRPServicesGeneralException, self.mc.put, 0)
            try:
                self.mc.put(0)
            except NRPServicesGeneralException as e:
                self.assertEquals(e.error_code, 500)

        rospy.ServiceProxy = oldsp

    def test_material_control_good_request(self):
        """
        This method crafts some successful requests.
        """

        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {
            'visual_path': 'sensible_model::actual_link::existing_visual',
            'material': 'known_material'
        }
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertEquals(self.mc.put(0)[1], 200)

    # The following methods test the class hbp_nrp_backend.rest_server.__SimulationControl
    # .LightControl
    def test_light_control_wrong_user(self):
        """
        This method crafts a request from an user which is not the owner of the simulation.
        """

        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "wrong-owner"}
        ddict = {}
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertRaises(NRPServicesClientErrorException, self.lc.put, 0)
            try:
                self.lc.put(0)
            except NRPServicesClientErrorException as e:
                self.assertEquals(e.error_code, 401)

    def test_light_control_no_params(self):
        """
        This method crafts a request from the owner of the simulation missing the other parameters.
        """

        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {}
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertRaises(NRPServicesClientErrorException, self.lc.put, 0)
            try:
                self.lc.put(0)
            except NRPServicesClientErrorException as e:
                self.assertEquals(e.error_code, 400)

    def test_light_control_only_name(self):
        """
        This method crafts a request from the owner of the simulation with only the 'name'
        parameter.
        """

        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {"name": "notreallyimportant"}
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertRaises(Exception, self.lc.put, 0)

    def test_light_control_no_attenuation_constant(self):
        """
        This method crafts a request from the owner of the simulation missing only the
        'attenuation_constant' parameter.
        """

        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {
            "name": "notreallyimportant",
            "diffuse": {
                "r": "0",
                "g": "0",
                "b": "0",
                "a": "0"
           },
            "attenuation_linear": "0",
            "attenuation_quadratic": "0"
        }
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertRaises(Exception, self.lc.put, 0)

    def test_light_control_no_attenuation_linear(self):
        """
        This method crafts a request from the owner of the simulation missing only the
        'attenuation_linear' parameter.
        """

        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {
            "name": "notreallyimportant",
            "diffuse": {
                "r": "0",
                "g": "0",
                "b": "0",
                "a": "0"
           },
            "attenuation_constant": "0",
            "attenuation_quadratic": "0"
        }
        did_it_fail = True
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertRaises(Exception, self.lc.put, 0)

    def test_light_control_no_attenuation_quadratic(self):
        """
        This method crafts a request from the owner of the simulation missing only the
        'attenuation_quadratic' parameter.
        """

        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {
            "name": "notreallyimportant",
            "diffuse": {
                "r": "0",
                "g": "0",
                "b": "0",
                "a": "0"
           },
            "attenuation_constant": "0",
            "attenuation_linear": "0"
        }
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertRaises(Exception, self.lc.put, 0)

    def test_light_control_no_diffuse(self):
        """
        This method crafts a request from the owner of the simulation missing only the
        'diffuse' parameter.
        """

        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {
            "name": "notreallyimportant",
            "attenuation_constant": "0",
            "attenuation_linear": "0",
            "attenuation_quadratic": "0"
        }
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertRaises(Exception, self.lc.put, 0)

    def test_good_request_light_control_ros_wait_for_service_failure(self):
        """
        This method performs a good request while ROS is unavailable.
        """

        oldwfs = rospy.wait_for_service
        rospy.wait_for_service = lambda x, y: (_ for _ in ()).throw(rospy.ROSException)
        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {
            "name": "notreallyimportant",
            "diffuse": {
                "r": "0",
                "g": "0",
                "b": "0",
                "a": "0"
            },
            "attenuation_constant": "0",
            "attenuation_linear": "0",
            "attenuation_quadratic": "0"
        }
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertRaises(NRPServicesUnavailableROSService, self.lc.put, 0)
            try:
                self.lc.put(0)
            except NRPServicesUnavailableROSService as e:
                self.assertEquals(e.error_code, 500)

        rospy.wait_for_service = oldwfs

    def test_bad_request_light_control_ros_wait_for_service_failure(self):
        """
        This method performs a bad request while ROS is unavailable.
        """

        oldwfs = rospy.wait_for_service
        rospy.wait_for_service = lambda x, y: (_ for _ in ()).throw(rospy.ROSException)
        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {"name": "notreallyimportant"}
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertRaises(NRPServicesUnavailableROSService, self.lc.put, 0)
            try:
                self.lc.put(0)
            except NRPServicesUnavailableROSService as e:
                self.assertEquals(e.error_code, 500)

        rospy.wait_for_service = oldwfs

    def test_good_request_light_control_ros_service_proxy_failure(self):
        """
        This method performs a good request with a ROS failure in the service proxy
        """

        oldsp = rospy.ServiceProxy
        rospy.ServiceProxy = mock.Mock(return_value=lambda light_name='', diffuse='',
                attenuation_constant='', attenuation_linear='', attenuation_quadratic='':
                (_ for _ in ()).throw(rospy.ServiceException))
        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {
            "name": "notreallyimportant",
            "diffuse": {
                "r": "0",
                "g": "0",
                "b": "0",
                "a": "0"
           },
            "attenuation_constant": "0",
            "attenuation_linear": "0",
            "attenuation_quadratic": "0"
        }
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertRaises(NRPServicesClientErrorException, self.lc.put, 0)
            try:
                self.lc.put(0)
            except NRPServicesClientErrorException as e:
                self.assertEquals(e.error_code, 400)

        rospy.ServiceProxy = oldsp

    def test_bad_request_light_control_ros_service_proxy_failure(self):
        """
        This method performs a bad request with a ROS failure in the service proxy
        """

        oldsp = rospy.ServiceProxy
        rospy.ServiceProxy = mock.Mock(return_value=lambda light_name='', diffuse='',
                attenuation_constant='', attenuation_linear='', attenuation_quadratic='':
                (_ for _ in ()).throw(rospy.ServiceException))
        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {"name": "notreallyimportant"}
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertRaises(NRPServicesClientErrorException, self.lc.put, 0)
            try:
                self.lc.put(0)
            except NRPServicesClientErrorException as e:
                self.assertEquals(e.error_code, 400)

        rospy.ServiceProxy = oldsp

    def test_light_control_good_request(self):
        """
        This method crafts a successful request.
        """

        hdr = {UserAuthentication.HTTP_HEADER_USER_NAME: "default-owner"}
        ddict = {
            "name": "notreallyimportant",
            "diffuse": {
                "r": "0",
                "g": "0",
                "b": "0",
                "a": "0"
            },
            "attenuation_constant": "0",
            "attenuation_linear": "0",
            "attenuation_quadratic": "0"
        }
        with app.test_request_context(headers=hdr, data=json.dumps(ddict)):
            self.assertEqual(self.lc.put(0)[1], 200)

    def test_light_control_as_ascii(self):
        self.assertEquals(LightControl.as_ascii(None), None)
        # Failing test about non ascii character? -> The encoding line (see top of file) has to be
        # the first of the file.
        self.assertEquals(LightControl.as_ascii(u"no utf-8 here.àèìòù"), "no utf-8 here.")
        self.assertEquals(LightControl.as_ascii("abababa"), "abababa")

if __name__ == '__main__':
    unittest.main()
