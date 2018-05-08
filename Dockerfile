FROM nvidia/cuda:8.0-cudnn5-devel-ubuntu16.04

ARG cores=6

COPY keyboard /etc/default/keyboard
COPY bashrc /root/.bashrc

RUN apt-get update && apt-get install -y --allow-unauthenticated	\
	build-essential 						\
	cmake-curses-gui 						\
	mesa-utils 								\
	pkg-config 								\
	checkinstall 							\
	bash-completion 						\
	apt-utils  								\
	vim										\
	software-properties-common 				\
	xterm 									\
	gedit									\
	net-tools								\
	iputils-ping 							\
	openssh-server							\
	expect 									\
	doxygen									\
	pciutils								\
	libasound2 								\
	libpango1.0-0 							\
	pulseaudio-utils 						\
	alsa-base 								\
	alsa-utils								\
	tmux                                    \
    terminator             					\
    git 									\
    wget									\
    && apt-get clean 						\
   	&& rm -rf /var/lib/apt/lists/*          

RUN wget https://download.sublimetext.com/sublime-text_build-3126_amd64.deb && \
	dpkg -i sublime-text_build-3126_amd64.deb && rm sublime-text_build-3126_amd64.deb

RUN \
  add-apt-repository -y ppa:nginx/stable && \
  apt-get update && \
  apt-get install -y nginx && \
  rm -rf /var/lib/apt/lists/* && \
  echo "\ndaemon off;" >> /etc/nginx/nginx.conf

WORKDIR /root

ENV SRC_FOLDER=/root
RUN mkdir NRP
ENV HBP=/root/NRP
ENV NRP_INSTALL_MODE=user

RUN apt-get update && \
	apt-get install -y cmake git build-essential \
					   doxygen python-dev python-h5py python-lxml  \
					   autogen automake libtool build-essential autoconf  \
					   libltdl7-dev libreadline6-dev libncurses5-dev libgsl0-dev \
					   python-all-dev python-numpy python-scipy python-matplotlib \
					   ipython libxslt1-dev zlib1g-dev python-opencv ruby libtar-dev \
					   libprotoc-dev protobuf-compiler imagemagick libtinyxml2-dev \
					   git python-virtualenv libffi-dev uwsgi-plugin-python python-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ROS KINETIC
RUN apt-get update && apt-get install -y --no-install-recommends \
    dirmngr \
    gnupg2  && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# setup keys
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 421C365BD9FF1F717815A3895523BAEEB01FA116

# setup sources.list
RUN echo "deb http://packages.ros.org/ros/ubuntu xenial main" > /etc/apt/sources.list.d/ros-latest.list

# install bootstrap tools
RUN apt-get update && apt-get install --no-install-recommends -y \
    python-rosdep \
    python-rosinstall \
    python-vcstools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# setup environment
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

# bootstrap rosdep
RUN rosdep init \
    && rosdep update

# install ros packages
ENV ROS_DISTRO kinetic
RUN apt-get update && apt-get install -y \
    ros-kinetic-desktop \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get -y install python-wstool  && pip install defusedxml rospkg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# setup catkin workspace
RUN apt-get update && apt-get install -y ros-kinetic-catkin && pip install catkin_pkg empy && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN echo "source /opt/ros/kinetic/setup.sh" >> /root/.sourceScripts                &&  \
    echo "source $SRC_FOLDER/catkin_ws/devel/setup.bash" >> /root/.sourceScripts   &&  \
    chmod +x /opt/ros/kinetic/setup.sh                                                  &&  \
    mkdir -p $SRC_FOLDER/catkin_ws/src                                                  &&  \
    cd $SRC_FOLDER/catkin_ws                                                            &&  \
    /bin/bash -c 'source /opt/ros/kinetic/setup.sh; catkin_make'

RUN echo 'ROS_IP=127.0.0.1' >> /root/.sourceScripts
RUN echo 'ROS_MASTER_URI=http://$ROS_IP:11311' >> /root/.sourceScripts

RUN apt-get update && apt-get install -y ros-kinetic-web-video-server ros-kinetic-control-toolbox ros-kinetic-controller-manager ros-kinetic-transmission-interface ros-kinetic-joint-limits-interface ros-kinetic-rosauth ros-kinetic-smach-ros python-rospkg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y libsimbody-dev libgts-dev libgdal-dev ruby-ronn xsltproc graphviz-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get remove --purge python-pynn && \
	apt-get install -y libgsl0-dev bison byacc libgts-dev libjansson-dev libblas-dev liblapack-dev libhdf5-dev gfortran lua-cjson ruby-compass nginx-extras && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y libqt4-dev libqtwebkit-dev libfreeimage-dev libignition-transport-dev libignition-transport0-dev libtbb-dev mpich ros-kinetic-image-common && \
	apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

RUN pip uninstall swagger flask-swagger flask-restful-swagger && pip install pyxb==1.2.4

RUN wget https://raw.githubusercontent.com/creationix/nvm/v0.33.0/install.sh && chmod +x install.sh && ./install.sh

ENV NVM_DIR="/root/.nvm"
RUN echo 'source $NVM_DIR/nvm.sh' >> /root/.sourceScripts

RUN /bin/bash -c 'source $NVM_DIR/nvm.sh && nvm install 0.10 &&	nvm install 8 && nvm alias default 8 && npm install -g bower grunt grunt-cli uuid-v4'

RUN echo 'source $HBP/user-scripts/nrp_variables' >> /root/.sourceScripts && \
    echo 'source $HBP/user-scripts/nrp_aliases' >> /root/.sourceScripts

ENV PYTHONPATH=""

RUN apt-get update && apt-get install -y libignition-math2-dev && \
 	apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN cd /usr/include/ignition/math2/ignition/math/ && rm Vector2.hh
ADD Vector2.hh  /usr/include/ignition/math2/ignition/math/Vector2.hh

COPY NRP /root/NRP

RUN cd $HBP/ExDFrontend && gem install compass 

RUN cd $HBP/nrpBackendProxy && /bin/bash -c 'source $NVM_DIR/nvm.sh && npm install' && pip install mpi4py && mkdir -p /root/.local/etc/init.d

RUN cd $HBP/user-scripts && /bin/bash -c 'source $HBP/user-scripts/nrp_variables && source $HBP/user-scripts/nrp_aliases && ./configure_nrp'

RUN cd $HBP/user-scripts &&  /bin/bash -c 'source $HBP/user-scripts/nrp_variables && source $HBP/user-scripts/nrp_aliases && ./update_nrp build prerequisites'
RUN cd $HBP/user-scripts &&  /bin/bash -c 'source $HBP/user-scripts/nrp_variables && source $HBP/user-scripts/nrp_aliases && ./update_nrp build mvapich'
RUN cd $HBP/user-scripts &&  /bin/bash -c 'source $HBP/user-scripts/nrp_variables && source $HBP/user-scripts/nrp_aliases && ./update_nrp build music'
RUN cd $HBP/user-scripts &&  /bin/bash -c 'source $HBP/user-scripts/nrp_variables && source $HBP/user-scripts/nrp_aliases && ./update_nrp build nest'
RUN cd $HBP/user-scripts &&  /bin/bash -c 'source $HBP/user-scripts/nrp_variables && source $HBP/user-scripts/nrp_aliases && ./update_nrp build gazebo_ros'
RUN cd $HBP/user-scripts &&  /bin/bash -c 'source $HBP/user-scripts/nrp_variables && source $HBP/user-scripts/nrp_aliases && ./update_nrp build backend'
RUN cd $HBP/user-scripts &&  /bin/bash -c 'source $HBP/user-scripts/nrp_variables && source $HBP/user-scripts/nrp_aliases && ./update_nrp build fixcv'
RUN cd $HBP/user-scripts &&  /bin/bash -c 'source $HBP/user-scripts/nrp_variables && source $HBP/user-scripts/nrp_aliases && ./update_nrp build frontend'
RUN cd $HBP/user-scripts &&  /bin/bash -c 'source $HBP/user-scripts/nrp_variables && source $HBP/user-scripts/nrp_aliases && ./update_nrp build gzweb'

RUN cd $HBP/ExDFrontend && rm -r node_modules && /bin/bash -c 'source $NVM_DIR/nvm.sh && npm install'
RUN apt-get update && apt-get install -y firefox && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 9001 8081

COPY bashrc_iCub /root/.bashrc_iCub  
ENTRYPOINT bash

