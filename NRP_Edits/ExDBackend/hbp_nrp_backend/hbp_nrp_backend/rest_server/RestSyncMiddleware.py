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
This module makes some rest requests multi-threadable.
By default, all rest requests are considered not thread safe and are therefore synchronized.
Requests that are known to be thread-safe, are executed concurrently.
To mark a rest request as thread-safe, decorate the Resource function handling the request
(get, post, delete, put) with the decorator @RestSyncMiddleware.threadsafe
"""
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class RestSyncMiddleware(object):
    """
    Middleware that allows thread-safe requests to be executed concurrently
    """

    def __init__(self, wsgi_app, app):
        self.wsgi_app = wsgi_app
        self.app = app
        self.threadLock = Lock()

    @staticmethod
    def threadsafe(func):
        """
        Decorates functions as thread-safe
        """
        func.is_threadsafe = True
        return func

    def __call__(self, environ, start_response):
        pathinfo = environ.get("PATH_INFO")
        method = environ.get("REQUEST_METHOD")

        viewfunction, _ = self.app.url_map.bind(
            'localhost', default_method=method).match(pathinfo)
        viewclass = self.app.view_functions[viewfunction].view_class
        viewfn = getattr(viewclass, method.lower())

        if not hasattr(viewfn, "is_threadsafe"):
            self.threadLock.acquire()

        try:
            res = self.wsgi_app(environ, start_response)
        # pylint: disable=broad-except
        except Exception, e:
            logger.exception(e)
            res = None
        finally:
            if not hasattr(viewfn, "is_threadsafe"):
                self.threadLock.release()

        return res
