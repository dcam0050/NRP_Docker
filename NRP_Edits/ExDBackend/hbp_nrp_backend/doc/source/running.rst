.. _running:

Running the backend
===================

Running on a local machine
--------------------------

This is a step-by-step description for running the backend for the case that **the backend is locally installed on developer a machine**.


1. Make sure you installed everything according to :ref:`installation`

2. Start the required software components such as ``roscore``, the backend server and the ``gazebo`` server. This can
   all be done using the ``runbackend`` script as decribed in :ref:`shell_scripts` or manually by:

   a. Start a roscore:

      .. code-block:: bash

         roscore

   b. Start the backend server (in a different terminal window):

      .. code-block:: bash

          python $EXDB/hbp_nrp_backend/hbp_nrp_backend/runserver.py

      This will start the backend server running on 127.0.0.1:5000. If you wish to run the server on another port, you have
      to provide another argument

      .. code-block:: bash

         python $EXDB/hbp_nrp_backend/hbp_nrp_backend/runserver.py 9000
   c. Start the ROSCLESimulationFactory, a ROS service needed by the backend to start an instance of the CLE

      .. code-block:: bash

         python $CLE/hbp_nrp_cle/hbp_nrp_cle/cle/ROSCLESimulationFactory.py
   d. Start the Gazebo server. Be careful that our patched Gazebo plugin is loaded instead of the default one.

      .. code-block:: bash

            source $GZ_ROS_PKGS/devel/setup.bash
            rosrun gazebo_ros gzserver

   e. Start a Gazebo client if you wish to view the results on your machine (not required when using the frontend)

      .. code-block:: bash

            rosrun gazebo_ros gzclient

   f. Load an experiment. The experiment configuration is the path to your experiment relative to
      $NRP_MODELS_DIRECTORY or your current folder if the first is not set

      .. code-block:: bash

            curl -X POST 127.0.0.1:5000/simulation -d '{"experimentConfiguration":"ExDConf/ExDXMLExample.xml"}'


Building the documentation
--------------------------

General documentation and Python API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The documentation and Python API (the pages you are currently reading) is created and can be read by calling

.. code-block:: bash

    cd $EXDB/doc
    make html
    firefox build/html/index.html


Swagger API
^^^^^^^^^^^

`Swagger <http://swagger.io>`_ is a standard to documenting services offered by restful application server.
The documentation is available once the server is running (see :ref:`running`) under this `address <http://localhost:5000/api/spec.html>`_.


Running the unit test for the CLE in a local machine
----------------------------------------------------

After downloading the CLE repository as shown in the wiki page :ref:`acquisition`, it would be useful run the unit test in a local machine.
In order to run the unit test locally you need to perform a few steps:

* Download the CLE repository according to Installing ExDBackend
* Copy numpy h5py and cv2.so in CLE/platform_venv/lib/python2.7/site-packages (In ubuntu, if you installed them, they are located in  /usr/lib/python2.7/dist-packages)
* Connect to the vpn
* Run once the script CLE/run_tests.sh (It will say that numpy directory already exists)
* Remove the numpy directory from CLE/platform_venv/lib/python2.7/site-packages
* Run again CLE/run_tests.sh
* If the script fails with errors pointing to unresolvable libraries (e.g. lxml, scipy) copy the respective directories from the local python installation to the virtual environment similar as in the second step.

From now on you can execute the unit testing running the script CLE/run_tests.sh

