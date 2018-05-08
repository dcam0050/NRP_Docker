.. _installation:

Installation
============

Install prerequisites
---------------------

.. code-block:: bash

   sudo apt-get install python-dev python-h5py libxslt1-dev python-lxml python-pip python-virtualenv autogen automake libtool build-essential \
   autoconf libltdl7-dev libreadline6-dev libncurses5-dev libgsl0-dev python-all-dev python-numpy python-scipy python-matplotlib ipython

.. caution::
   Pip starting with version 7.0.0 introduces the requirement to establish proxy connections using HTTPS or explicitly
   confirm the proxy as trusted. As the current ContinuousIntegration Makefile does not take this into account make sure
   to install Pip <= 6.1.1 and Virtualenv (which comes with a Pip wheel) <= 12.1.1. For Ubuntu 14.04 LTS the version
   contained in the official repository are suitable (1.54 and 1.11.4 respectively).

.. code-block:: bash

   sudo pip install pynn

Installation of  ROS
--------------------
This assumes work on Ubuntu (>= 13.10), otherwise use `ROS Hydro <http://wiki.ros.org/hydro/Installation/Ubuntu>`_ instead

* Add the Ubuntu package sources and `install ROS <http://wiki.ros.org/indigo/Installation/Ubuntu>`_. In short you have to run:

  .. code-block:: bash

      sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu trusty main" > /etc/apt/sources.list.d/ros-latest.list'
      wget https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -O - | sudo apt-key add -
      sudo apt-get update
      sudo apt-get install ros-indigo-desktop-full
      sudo apt-get install ros-indigo-control-toolbox ros-indigo-controller-manager ros-indigo-transmission-interface ros-indigo-joint-limits-interface



* To add the `Gazebo <http://gazebosim.org/tutorials?tut=install_ubuntu&cat=installation>`_. Ubuntu package sources, run the following commands:

  .. code-block:: bash

      sudo sh -c 'echo "deb http://packages.osrfoundation.org/gazebo/ubuntu `lsb_release -cs` main" > /etc/apt/sources.list.d/gazebo-latest.list'
      wget http://packages.osrfoundation.org/gazebo.key -O - | sudo apt-key add -
      sudo apt-get update
      sudo apt-get install gazebo4
      sudo apt-get install ros-indigo-gazebo4-msgs ros-indigo-gazebo4-plugins ros-indigo-gazebo4-ros ros-indigo-gazebo4-ros-control ros-indigo-gazebo4-ros-pkgs


Installation of the NEST simulator
----------------------------------

1. Download NEST 2.2.2 `(link) <http://www.nest-simulator.org/downloads/gplreleases/nest-2.2.2.tar.gz>`_.

   .. code-block:: bash

      wget http://www.nest-simulator.org/downloads/gplreleases/nest-2.2.2.tar.gz
      tar zxvf nest-2.2.2.tar.gz
      cd nest-2.2.2


   .. note::
      It is important to not download any newer version, particularly not 2.4.2

2. Build the sources and install the software:

   .. code-block:: bash

       ./configure --prefix=/opt/nest
       make
       sudo make install

.. _acquisition:

Acquire the sources of the backend
----------------------------------
Get the code for the ExDBackend, CLE, the adapted Gazebo Ros plugin and the Models repository. Create a folder to where
you keep your source (e.g., ``projects/HBP``)

.. code-block:: bash

     mkdir <path-to-project>
     cd <path-to-project>
     git clone ssh://<user>@bbpcode.epfl.ch/neurorobotics/ExDBackend
     git clone ssh://<user>@bbpcode.epfl.ch/neurorobotics/CLE
     git clone ssh://<user>@bbpcode.epfl.ch/neurorobotics/GazeboRosPackages
     git clone ssh://<user>@bbpcode.epfl.ch/neurorobotics/Models

Installation of the REST server
-------------------------------

.. code-block:: bash

    sudo apt-get install python-pip
    sudo pip install flask-restful-swagger progressbar

.. note::

   Note: This will install the default flask-restful-swagger package, which is fine as long as you deploy the backend
   locally. If you ever wish to deploy the backend on a server using Nginx and uwsgi, you will need to get the patched
   version that includes authentication headers. You can find our patched flask-restful-swagger in the
   ExDBackend repository.

.. note::

    Setup is easier if the virtual environment is used that is created by the ``runtest.sh`` script, see :ref:`virtualenv`


Building the patched Gazebo Plugin
----------------------------------

.. code-block:: bash

    source /opt/ros/indigo/setup.bash
    cd GazeboRosPackages
    catkin_make


Setting up the build environment
--------------------------------

.. _shell_scripts:

Shell scripts
^^^^^^^^^^^^^

In order to use some helpful environment variables and tools, add this line to your local ``.bashrc`` file:


.. code-block:: bash

    source <path-to-project>/ExDBackend/devel/setEnv.sh

.. note::

    The script assumes you acquired the code as described in :ref:`acquisition`.

This will modify the ``PYTHONPATH``, ``PATH`` and ``MODELPATH`` adequately and introduce variables to navigate to the
source folders. For instance,

.. code-block:: bash

    cd $EXDB # change into the backend directory
    cd $EXDF # change into the frontend directory
    cd $CLE # change into the CLE directory
    cd $GZ_ROS_PKGS # change into folder of the adapted Gazebo Ros Plugin
    cd $NRP_MODELS_DIRECTORY # change into the Models folder

Furthermore, the ``runbackend`` are shell scripts for interactively starting all components, see :ref:`runbackend`. The ``runbackend4`` script
starts the same script in a 4x4 shell for easier organization -- assuming that ``tmux`` is installed, see :ref:`tmux`.

.. _virtualenv:

Virtual Environment
^^^^^^^^^^^^^^^^^^^

.. note::

    This sub section requires a refinement of the creation of the ``virtualenv`` created by ``runtest.sh``

Setup the Gazebo Client
^^^^^^^^^^^^^^^^^^^^^^^

If the Gazebo Client will be used for visualzation, link the models to the ~/.gazebo/models folder. Make sure to have
set the environment variables appropriately as described in :ref:`shell_scripts`. :

.. code-block:: bash

    mkdir -p ~/.gazebo/models
    $NRP_MODELS_DIRECTORY/create-symlinks.sh

