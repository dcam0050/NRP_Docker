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
#!/usr/bin/env python
"""
This script contains common code to launch services on the Lugano viz cluster.
"""

import re
import pexpect
import logging
import os
import datetime
import subprocess

# Info messages sent to the notificator will be forwarded as notifications
# this does not require a cle import dependency in commons
notificator = logging.getLogger('hbp_nrp_cle.user_notifications')
logger = notificator.parent


# This will be the method called by the pexpect object to log.
# pexpect is expecting kwargs unused argument.
def _log_write(*args, **kwargs):  # pylint: disable=unused-argument
    """
    Translation between pexpect log to file mechanism and python logging module
    """
    content = args[0]
    # let's ignore other params, pexpect only use one arg AFAIK
    if content in [' ', '', '\n', '\r', '\r\n']:
        return  # don't log empty lines
    for eol in ['\r\n', '\r', '\n']:
        # remove ending EOL, the logger will add it anyway
        content = re.sub(r'\%s$' % eol, '', content)
    return logger.info(content)  # call the logger info method with the reworked content


def _set_up_logger():
    """
    Configure the root logger of the application
    :param: logfile_name: name of the file created to collect logs
    """
    # give the logger the methods required by pexpect
    logger.write = _log_write
    logger.flush = lambda: None

_set_up_logger()


class LuganoVizCluster(object):
    """
    Represents a SLURM allocation instance running on the Lugano viz cluster.

    There is a wide usage of pexpect in this class because of the remote connections via
    ssh needed to access the Lugano machines. Every time a remote command is launched,
    expect() is used to match strings with the shell output in order to understand its status.
    """

    # -M option is necessary to allow to spawn child ssh connections for doing file transfer
    # -K option means that we are using Kerberos
    CLUSTER_SSH = 'ssh -M -K bbpnrsoa@{node}.cscs.ch'
    CLUSTER_SLURM_FRONTEND = 'bbpviz1'
    CLUSTER_DIR_COPY = 'scp -r {src} bbpnrsoa@{node}.cscs.ch:{trg}'
    # SLURM salloc calls allocates a node on the cluster. From salloc man page:
    #
    # salloc - Obtain a SLURM job allocation (a set of nodes), execute a command,and then release
    # the allocation when the command is finished.
    # SYNOPSIS
    # salloc [options] [<command> [command args]]
    #
    # -c, --cpus-per-task=<ncpus>
    # Advise the SLURM controller that ensuing job steps will require ncpusnumber of processors
    # per task. Without this option, the controller willjust try to allocate one processor per
    # task.
    # For instance,consider an application that has 4 tasks, each requiring 3 processors. If
    # ourcluster is comprised of quad-processors nodes and we simply ask for12 processors, the
    # controller might give us only 3 nodes. However, by usingthe --cpus-per-task=3 options, the
    # controller knows that each task requires3 processors on the same node, and the controller
    # will grant an allocationof 4 nodes, one for each of the 4 tasks.
    #
    # -I, --immediate[=<seconds>]
    # exit if resources are not available within thetime period specified.If no argument is given,
    # resources must be available immediatelyfor the request to succeed.By default, --immediate is
    # off, and the commandwill block until resources become available. Since this option'sargument
    # is optional, for proper parsing the single letter option mustbe followed immediately with the
    # value and not include a space betweenthem. For example "-I60" and not "-I 60".
    #
    # --gres=<list>
    # Specifies a comma delimited list of generic consumable resources.The format of each entry on
    # the list is "name[:count[*cpu]]".The name is that of the consumable resource.The count is the
    # number of those resources with a default value of 1.The specified resources will be allocated
    # to the job on each nodeallocated unless "*cpu" is appended, in which case the resourceswill
    # be allocated on a per cpu basis.The available generic consumable resources is configurable
    # by the systemadministrator.A list of available generic consumable resources will be printed
    # and thecommand will exit if the option argument is "help".Examples of use
    # include "--gres=gpus:2*cpu,disk=40G" and "--gres=help".
    #
    # -t, --time=<time>
    # Set a limit on the total run time of the job allocation. If therequested time limit exceeds
    # the partition's time limit, the job willbe left in a PENDING state (possibly indefinitely).
    # The default timelimit is the partition's default time limit. When the time limit is reached,
    # each task in each job step is sent SIGTERM followed by SIGKILL. Theinterval between signals
    # is specified by the SLURM configurationparameter KillWait. A time limit of zero requests
    # that no timelimit be imposed. Acceptable time formats include "minutes","minutes:seconds",
    # "hours:minutes:seconds", "days-hours","days-hours:minutes" and "days-hours:minutes:seconds".
    #
    # -p, --partition=<partition_names>
    # Request a specific partition for the resource allocation. If not specified,the default
    # behavior is to allow the slurm controller to select the defaultpartition as designated by
    # the system administrator. If the job can use morethan one partition, specify their names
    # in a comma separate list and the oneoffering earliest initiation will be used.
    #
    # -A, --account=<account>
    # Charge resources used by this job to specified account.The account is an arbitrary string.
    # The account name maybe changed after job submission using the scontrolcommand.
    #
    # --reservation=<name>
    # Allocate resources for the job from the named reservation.

    ALLOCATION_TIME = datetime.timedelta(hours=10)
    DEALLOCATION_COMMAND = 'scancel %s'
    CURRENT_NODES_COMMAND = 'squeue -u bbpnrsoa -t PENDING,RUNNING -h -o "%N"'
    NODE_DOMAIN = '.cscs.ch'
    # Timeout used for pexpect ssh connection calls.
    TIMEOUT = 20
    # Timeout used for pexpect calls that should return immediately (default pexpect timeout is 30
    # seconds).
    SMALL_TIMEOUT = 2

    def __init__(self, processes, gpus=0, timezone=None, reservation=None):

        # actual allocation info on cluster
        self._allocation_process = None
        self._job_ID = None
        self._node = None

        # Holds the state of the SLURM job. The states are defined in SLURM.
        self._state = "UNDEFINED"

        # common temporary directory, removed on deallocation
        self._tmp_dir = None

        # construct the allocation command based on given parameters
        self._allocation_time = None
        if timezone is not None:
            self._allocation_time = datetime.datetime.now(
                timezone) + LuganoVizCluster.ALLOCATION_TIME

        if (reservation is not None):
            reservation = str(reservation)
        else:
            reservation = ''
        LuganoVizCluster.ALLOCATION_COMMAND = (
            "salloc --immediate=25" +
            " --time=" + str(LuganoVizCluster.ALLOCATION_TIME) +
            " --reservation=" + reservation +
            " -p interactive -c " + str(processes) +
            " --account=proj30 " +
            (" --gres=gpu:" + str(gpus) if gpus > 0 else "")
        )

    def _spawn_ssh_SLURM_frontend(self):
        """
        Return a pexpect object connected to the SLURM frontend.
        SLURM (Simple Linux Utility for Resource Management) is the entry point to
        allocate or manage jobs on the cluster.
        """
        return self._spawn_ssh(self.CLUSTER_SLURM_FRONTEND)

    def _spawn_ssh_node(self):
        """
        Return a pexpect object connected to the allocated node.
        """
        return self._spawn_ssh(self._node)

    def _spawn_ssh(self, target):
        """
        Return a pexpect object connected to the target node.
        """
        ssh_SLURM_frontend_process = pexpect.spawn('bash',
                                                   logfile=logger)
        ssh_SLURM_frontend_process.sendline(self.CLUSTER_SSH.format(node=target))
        result = ssh_SLURM_frontend_process.expect(['[bbpnrsoa@%s ~]$' % target,
                                                    'password',
                                                    pexpect.TIMEOUT], self.TIMEOUT)
        if result == 1:
            raise(Exception("SLURM front-end node can't be used without password."))
        if result == 2:
            raise(Exception("Cannot connect to the SLURM front-end node."))

        return ssh_SLURM_frontend_process

    def _allocate_job(self, reuse_nodes=True):
        """
        Allocate a new job on the cluster. Return a pexpect object with a ssh
        connection to the allocated node. If once call exit on this object, the
        allocation will be cancelled.

        The reuse paramter specified if we can launch our process on already
        allocated nodes.
        """
        notificator.info("Requesting resources on the cluster")
        self._allocation_process = self._spawn_ssh_SLURM_frontend()

        # clear the buffer before issuing the commands, otherwise parsing the final
        # list may fail with ssh banner header info filling the buffer
        result = self._allocation_process.expect([pexpect.TIMEOUT,
                                                   '[bbpnrsoa@bbpviz1 ~]$'], self.TIMEOUT)
        if result == 0:
            raise(Exception("Cannot connect to the SLURM front-end node."))

        # if we cannot reuse nodes, generate a list of allocated nodes
        used_nodes = None
        if not reuse_nodes:
            # determine which nodes are already in use, we can't currently support
            # running multiple gzserver instances on the same backend (yet)
            self._allocation_process.sendline(self.CURRENT_NODES_COMMAND)
            result = self._allocation_process.expect([pexpect.TIMEOUT,
                                                       '[bbpnrsoa@bbpviz1 ~]$'], self.TIMEOUT)
            if result == 0:
                raise(Exception("Cannot retrieve list of currently allocated SLURM nodes."))

            # get the list of current nodes between our command and the new prompt
            used_nodes = self._allocation_process.before.replace('\r', '')  # replace all ^M
            used_nodes = used_nodes.rsplit(self.CURRENT_NODES_COMMAND, 1)[1]
            used_nodes = used_nodes.split('[bbpnrsoa@bbpviz1 ~]$', 1)[0].strip()
            used_nodes = used_nodes.replace('\n', ',')

        # exclude any currently used nodes if requested, otherwise allow any
        if used_nodes:
            logger.info('Currently allocated bbpnrsoa nodes: %s' % used_nodes)
            self._allocation_process.sendline(self.ALLOCATION_COMMAND + (' -x %s' % used_nodes))
        else:
            self._allocation_process.sendline(self.ALLOCATION_COMMAND)
        result = self._allocation_process.expect(['Granted job allocation ([0-9]+)',
                                                   'Submitted batch job [0-9]+',
                                                   'error: spank-auks: cred forwarding failed',
                                                   'error: Unable to allocate resources',
                                                   'error: .+'])
        if result == 2:
            raise(Exception("Kerberos authentication missing"))
        elif result == 3:
            raise(Exception("No resources available on the cluster. "
                            "Try again later."))
        elif result == 4:
            raise(Exception("Job allocation failed: " + str(self._allocation_process.after)))

        # Find out which node has been allocated
        self._job_ID = self._allocation_process.match.groups()[0]
        self._allocation_process.sendline("scontrol show job " + str(self._job_ID))
        self._allocation_process.expect('JobState=[A-Z]+')
        self._state = self._allocation_process.after[9:]
        if self._state != 'RUNNING':
            raise Exception("Job is not running.")
        self._allocation_process.expect(r' NodeList=(\w+)')
        self._node = self._allocation_process.match.groups()[0]

    def _deallocate_job(self):
        """
        Deallocate a job previously allocated through __allocate_job. The idea is
        that exiting from the terminal opened through the allocation causes SLURM
        to complete the Job.
        """
        if self._allocation_process is not None:
            self._allocation_process.sendline('exit')
            self._allocation_process.terminate()
            self._allocation_process = None
            self._job_ID = None
            self._state = "UNDEFINED"
            self._node = None

    def _copy_to_remote(self, local_path):
        """
        Create a temporary directory if needed and copy remote files to it.
        """

        # create a tmp dir on the remote host if we have not already
        if not self._tmp_dir:
            copy_process = self._spawn_ssh_node()
            result = copy_process.expect(['[bbpnrsoa@%s ~]$' % self._node,
                                          pexpect.TIMEOUT], self.TIMEOUT)
            if result == 1:
                raise(Exception("Cannot connect to the node."))
            copy_process.sendline('tmpdir=$(mktemp -d)')
            copy_process.sendline('echo $tmpdir')
            # Pexpect compiles strings to regular expressions
            copy_process.expect(r'echo \$tmpdir')
            copy_process.readline()
            self._tmp_dir = copy_process.readline().rstrip()
            copy_process.terminate()

        # This is done outside the existing ssh connection, but will reuse the ssh connection
        scp_cmd = self.CLUSTER_DIR_COPY.format(node=self._node, src=local_path, trg=self._tmp_dir)
        logger.info(scp_cmd)
        result = subprocess.call(scp_cmd.split())
        self._check_scp_result(result)

    def _clean_remote_files(self):
        """
        Remove the temporary remote working files
        """
        if self._node is not None and self._allocation_process is not None:
            clean_process = self._spawn_ssh_node()
            clean_process.sendline('rm -rf /tmp/.X*')
            if self._tmp_dir is not None:
                clean_process.sendline('rm -rf {0}'.format(self._tmp_dir))
            clean_process.terminate()

    @staticmethod
    def _check_scp_result(result):
        """
        Checks the result of an scp call and raise an exception in case of a problem

        :param result: the return code of the scp execution
        """
        if result != 0:
            if result == 9:
                error = "File transfer protocol mismatch"
            elif result == 10:
                error = "File not found"
            elif result == 65:
                error = "Host did not allow connection"
            elif result == 66:
                error = "General ssh protocol error"
            else:
                error = "Unknown error"
            raise Exception("The robot could not be copied to the remote cluster: " + error)

    @staticmethod
    def _configure_environment(process):
        """
        Configures the given process by setting necessary ENVIRONMENT and version variables
        on the remote node as set by puppet on the backend.

        :param process: the process to send commands to
        """

        # determine deployment environment based on an environment variable defined by Puppet
        # (either dev or staging)
        environment = os.environ.get('ENVIRONMENT')

        # set the ENVIRONMENT variable on the cluster side in order
        # to load the appropriate modules there.
        process.sendline('export ENVIRONMENT=' + environment)

        # load modules versions specified in the nrp_variables script generated by Puppet
        # (versions are environment dependent)
        if environment == 'staging':
            with open(os.environ.get('NRP_VARIABLES_PATH')) as f:
                content = f.readlines()
            versions = [x.strip() for x in content if '_VERSION=' in x]
            for v in versions:
                process.sendline(v)

        # access the dev or staging project resources
        proj_path = '/gpfs/bbp.cscs.ch/project/proj30/neurorobotics/%s/' % environment
        return proj_path

    def stop(self):
        """
        Delete any temporary directory files and deallocate the node.
        """

        # cluster node cleanup (this can fail, but make sure we always release the job below)
        try:
            # delete remote locks and any files
            notificator.info('Cleaning up temporary files on the cluster node')
            self._clean_remote_files()

        # pylint: disable=broad-except
        except Exception:
            logger.exception('Error cleaning up cluster node.')
        finally:
            self._tmp_dir = None

        # SLURM cleanup (not on the cluster node), always try even if cluster cleanup fails
        if self._allocation_process:
            notificator.info('Releasing resources on the cluster')
            self._deallocate_job()
