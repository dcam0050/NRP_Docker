"""
This package contains the python code to run the REST web server and supportive tooling
"""

from hbp_nrp_backend.version import VERSION as __version__  # pylint: disable=unused-import
from hbp_nrp_backend import config
import os
import time
import string

__author__ = 'GeorgHinkel'


class NRPServicesGeneralException(Exception):
    """
    General exception class that can be used to return meaningful messages
    to the ExD frontend.

    :param message: message displayed to the end user.
    :param error_type: Type of error (like 'CLE Error')
    :param error_code: The HTTP error code to send to the frontend.
    """

    def __init__(self, message, error_type, error_code=500, data=None):
        super(NRPServicesGeneralException, self).__init__(message)
        # These fields are handled by the front-end JS code.
        self.error_type = error_type
        self.error_code = error_code
        self.data = data

    def __str__(self):
        return "{0} ({1})".format(repr(self.message), self.error_type)


class NRPServicesClientErrorException(NRPServicesGeneralException):
    """
    Exception class for client (4xx) errors. It can be used to return meaningful messages
    to the ExD frontend.

    :param message: message displayed to the end user.
    :param error_code: The HTTP error code to send to the frontend.
    """

    def __init__(self, message, error_type="Client error", error_code=400):
        super(NRPServicesClientErrorException, self).__init__(
            message, error_type, error_code)


class NRPServicesStateException(NRPServicesGeneralException):
    """
    State exception class that can be used to return meaningful messages to the HBP frontend.

    :param message: message displayed to the end user.
    """

    def __init__(self, message):
        super(NRPServicesStateException, self).__init__(
            message, "Transition error", 400)


class NRPServicesDuplicateNameException(NRPServicesGeneralException):
    """
    Duplicate name exception that can be used to return meaningful messages to the HBP frontend in
    case simulation scripts (transfer-functions or state-machines) or populations contain duplicate
    names.

    :param message: message displayed to the end user.
    """

    def __init__(self, message):
        super(NRPServicesDuplicateNameException, self).\
            __init__(message, "Duplicate name error", 403)


class NRPServicesTransferFunctionException(NRPServicesGeneralException):
    """
    Transfer function exception class that can be used to return meaningful messages
    to the HBP frontend in case source code updates fail.

    :param message: message displayed to the end user.
    """

    def __init__(self, message):
        super(NRPServicesTransferFunctionException, self).\
            __init__(message, "Transfer function error", 400)


class NRPServicesStateMachineException(NRPServicesClientErrorException):
    """
    State machine exception class that can be used to return meaningful messages
    to the HBP frontend in case source code updates fail.
    :param message: message displayed to the end user.
    """

    def __init__(self, message, error_code):
        super(NRPServicesStateMachineException, self).\
            __init__(message, "State machine error", error_code)


class NRPServicesWrongUserException(NRPServicesClientErrorException):
    """
    Exception class that can be used to return meaningful messages
    to the HBP frontend in case an invalid user is detected.
    :param message: message displayed to the end user.
    """

    def __init__(self):
        super(NRPServicesWrongUserException, self).\
            __init__(
                "You need to be the simulation owner to apply your changes.\
                If you are the owner, try leaving and then re-joining the experiment.",
                "Wrong user",
                401
            )


class NRPServicesUnavailableROSService(NRPServicesGeneralException):
    """
    Server error with status 500 (internal error) issued when a ROS service is unavailable.
    It can be used to return meaningful messages to the ExD frontend.

    :param message: message displayed to the end user. It contains the text of the
                    corresponding ROS exception
    """

    def __init__(self, message):
        super(NRPServicesUnavailableROSService, self).__init__(
            "ROS service not available: " + message,
            "Unavailable ROS service"
        )


def get_date_and_time_string():
    """
    Utility function that returns a string reflecting the current date and time
    with a format that is suitable for file or folder names

    :return a string containing the date and time under the format
    YYYY-mm-dd_HH-MM-SS
    """
    return string.join([time.strftime("%Y-%m-%d"), time.strftime("%H-%M-%S")], '_')
