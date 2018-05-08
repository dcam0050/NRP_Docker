# NRP_Docker
-bashrc_iCub contains all environment variables declared in compilation of dockerfile

-bashrc references bashrc_iCub in its initialisation

-Vector2.hh has added functions that stop gazebo compilation from crashing. Gazebo requires compilation against libignition-math2 however certain functions reference those of libignition-math4. This file adds the missing functions.

-NRP/ExDBackend changes `NRP/ExDBackend/hbp-flask-restful-swagger-master/flask_restful_swagger/swagger.py` changes ``from flask.ext.restful import Resource, fields`` to ``from flask_restful import Resource, fields``

-NRP/user-scripts/configure_nrp removed nginx update which is blocking call on docker

-NRP/user-scripts/nrp_aliases change cle-backend alias to run locally rather than via uwsgi. This was done to pass in port parameter 8080 to solve EOCONNECTREFUSED error with cle-proxy

-NRP/user-scripts/nrp_functions changed installation code such that parts can be installed individually. This helps with debugging of docker installations


-NRP/user-scripts/update_nrp changed shell commands to take into consideration parameters passed when specifying parts to install. Required for the changed done in nrp\_functions

Compile using `docker build -t $(tagName) . --build-arg VIDEO_GID=$(VIDEO_GID)`

Run instructions at https://hub.docker.com/r/dcamilleri13/hbp_nrp/

To run HBP components, after spinning up container:

1. Run `terminator` to launch multi-tab terminal.
2. In first tab run `cle-nginx`. This will block but is running correctly.
3. In the second tab run `cle-start`.
4. In the third tab run `cle-frontend`.
