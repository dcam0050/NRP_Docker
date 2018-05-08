'''python client for the Platform Task Manager'''
import logging
import time
import dateutil.parser

import bbp_client.swagger_helpers as sh
from bbp_client.task_service.task_inspection import get_properties
from bbp_client.task_service.swagger import swagger
from bbp_client.task_service.swagger import TaskApi, JobApi
from bbp_client.task_service.swagger.models import (PostJobSchema, PostTaskSchema)

from task_types.TaskTypes import JSONable

L = logging.getLogger(__name__)


class TaskException(Exception):
    '''local exception'''
    pass


class JobFailure(TaskException):
    '''A job execution failed'''
    pass


class Client(object):
    '''Interface to the platform task manager service via python

        Example:
            >>> #you'll likely need a user for authentication
            >>> user = 'gevaert'
            >>> server = 'http://localhost:8888'
            >>> from bbp_client.oidc.client import BBPOIDCClient
            >>> client = BBPOIDCClient.implicit_auth(user)
            >>> from bbp_client.task_service.client import Client
            >>> ts = Client(server, client)
            >>> ts.get_tasks()

    '''
    def __init__(self, host, oauth_client=None, headers=None):
        '''
        Args:
           host: the protocol and name, 'http://localhost:port
           oauth_client: instance of the bbp_client.oidc.client
           headers: HTTP headers passed to server
        '''
        #mangle server and port
        self.host = host
        self.oauth_client = oauth_client
        self.headers = headers or {}

        if self.oauth_client:
            self.headers['Authorization'] = self.oauth_client.get_auth_header()
        self.headers['User-Agent'] = 'py_task_service_client'

        self._api = swagger.ApiClient('api_key', host)
        sh.patch_swagger_callapi(self._api, self._get_headers)

        self._task_api = TaskApi.TaskApi(self._api)
        self._job_api = JobApi.JobApi(self._api)

    def _get_headers(self):
        '''return the headers required for the http call'''
        #TODO, when to do client refresh?
        #self.client.refresh()
        return self.headers

    @sh.swagger_error
    def get_tasks(self, task_name=None, git_commit=None, git_repo=None):
        '''get the tasks from the platform task manager

        Args:
            task_name(string): The name of the task to be registered
            git_commit(string): The commit used when the task is checked out
            git_repo(string): The repo that contains the task code

            The tasks returned will be a combination matching all the above
            requirements.  The function can be called with no arguments to get
            all tasks.

        Returns:
            A list of dictionaries matching the queries
        '''

        query_fields = {}
        if task_name:
            query_fields['task_name'] = task_name
        if git_commit:
            query_fields['git_commit'] = git_commit
        if git_repo:
            query_fields['git_repo'] = git_repo

        tasks = self._task_api.GetTask(**query_fields)
        tasks = [sh.swagger_type_to_dict(t) for t in tasks.tasks]
        return tasks

    @sh.swagger_error
    def get_task(self, task_id):
        '''get a task from the platform task manager

        Args:
            task_id(string): The id of the task

        Returns:
            A dictionary with the information about the task
        '''
        task = self._task_api.GetTaskArg(task_id)
        return sh.swagger_type_to_dict(task)

    # pylint: disable=R0913
    @sh.swagger_error
    def register_task(self, task_filepath,
                      git_commit, git_repo, customizations, properties,
                      file_filters=None, base_env='', env_vars=None):
        '''Register a task with the Platform Task Manager

        Args:
            task_filepath(string): The path to the file containing the task from the repository root
            git_commit(string): The commit used when the task is checked out
            git_repo(string): The repo that contains the task code
            customizations(dict): where key is 'python', and value is a list of  packages
                                  required for the running the task
                                  ex: {'python': ['BeautifulSoup>=3.2.0', 'numpy==1.6.2']}
            properties(dict): where key is a string representing a property of the task
                             (name, caption, state, categories, accepts, returns, compatible_queues,
                             description, author)
            file_filters(dict): Contains keys 'ignored' and 'wanted'
                                The values for these keys are lists of shell-style
                                globs of paths to be ignored or wanted
            base_env: The base environment, currently not used
            env_vars(dict): A dictionary of environment variables.  Key is the variable
                            name and the value is the value

        Returns:
            task_info(dict): the result of registering the task.
                             A dictionary with the key 'task_id'

        Raises:

        '''
        args = {}
        args['task_filepath'] = task_filepath
        args['git_commit'] = git_commit
        args['git_repo'] = git_repo
        args['requirements'] = {}
        args['requirements']['customizations'] = customizations
        args['requirements']['file_filters'] = file_filters or {}
        args['requirements']['base_env'] = base_env or 'none'
        args['requirements']['env_vars'] = env_vars or {}

        args['properties'] = JSONable.data_hierachy_pre_json(properties)

        body = sh.swagger_create_type(PostTaskSchema.PostTaskSchema, args)
        return sh.swagger_type_to_dict(self._task_api.PostTask(body))

    @sh.swagger_error
    def add_task(self, task_filepath, git_commit, git_repo, customizations,
                 file_filters=None, base_env='', env_vars=None):
        '''Inspects a task to obtain its properties and registers it with the service

        Convenience method equivalent to register_task but that first uses git to try to
        extract the task properties from the source.

        Args:
            task_filepath(string): The path to the file containing the task from the repository root
            git_commit(string): The commit used when the task is checked out
            git_repo(string): The repo that contains the task code
            customizations(dict): where key is 'python', and value is a list of  packages
                                  required for the running the task
                                  ex: {'python': ['BeautifulSoup>=3.2.0', 'numpy==1.6.2']}
            file_filters(dict): Contains keys 'ignored' and 'wanted'
                                The values for these keys are lists of shell-style
                                globs of paths to be ignored or wanted
            base_env: The base environment, currently not used
            env_vars(dict): A dictionary of environment variables.  Key is the variable
                            name and the value is the value

        Returns:
            task_info(dict): the result of registering the task.
                             A dictionary with the key 'task_id'

        Raises:

        '''
        properties = get_properties(task_filepath, git_commit, git_repo)

        return self.register_task(task_filepath,
                                  git_commit, git_repo,
                                  customizations, properties,
                                  file_filters, base_env, env_vars)

    @sh.swagger_error
    def get_jobs(self):
        '''Get the jobs for the user

        Returns:
            List of dictionaries, containing the job information
        '''
        jobs = self._job_api.GetJob()
        jobs = [sh.swagger_type_to_dict(j) for j in jobs.jobs]
        return jobs

    @sh.swagger_error
    def get_job(self, job_id):
        '''get a job by id

        Args:
            job_id(str): the job id
        '''
        job = self._job_api.GetJobArg(job_id)
        return sh.swagger_type_to_dict(job)

    @sh.swagger_error
    def cancel_job(self, job_id):
        '''Attempts to cancel a job

        Args:
            job_id(str): the job id
        '''
        return self._job_api.DeleteJobArg(job_id)

    # pylint: disable=W0613,R0913
    @sh.swagger_error
    def start_job(self, task_id, output_location, arguments, job_name,
                  cpu_cores=1, total_physical_memory=2 * 1024, requested_queue='cscs_viz'):
        '''Launch a job on through the platfrom task manager

        Args:
            task_id(string): The uuid of the task to be launched
            output_location(string): Location that where this job saves its outputs
            arguments: The arguments that are passed to the task, they must
                       match the expectations of the parameters
            cpu_cores(int): number of requested cores
            total_physical_memory(int): number of megabytes per node
            requested_queue(string): Where the job is expected to be launched

        Returns:
            A dictionary with information to track the the launched job:
            job_id(string): the unique identifier of the launched job
            websocket(string): url to a websocket where all logging of the job  can be listened to

        Raises:

        '''
        arguments = JSONable.data_hierachy_pre_json(arguments)

        body = sh.swagger_create_type(PostJobSchema.PostJobSchema, locals())
        return sh.swagger_type_to_dict(self._job_api.PostJob(body))

    def get_latest_task(self, task_name, version=None):
        '''Get the latest version of a task by name

        if multiple tasks exist with the same name and vesion, the one with the latest
        add date is chosen

        '''
        tasks = self.get_tasks(task_name=task_name)
        L.debug('found %d versions of task %s', len(tasks), task_name)

        if version is None:
            for t in tasks:
                if version is None or version < t['properties']['version']:
                    version = t['properties']['version']

        same_version_tasks = [t for t in tasks if t['properties']['version'] == version]

        most_recent = None
        for t in same_version_tasks:
            info = self.get_task(t['task_id'])
            info['add_date'] = dateutil.parser.parse(info['add_date'])

            if most_recent is None or most_recent['add_date'] < info['add_date']:
                most_recent = info

        L.debug('using task version %s added on %s',
                most_recent['properties']['version'], most_recent['add_date'])

        return most_recent

    def wait_job(self, job_id, check_every=2):
        '''run an instance of a task and return the results

        Returns:
            The latest info about the job

        Raises:
            JobFailure: If the job fails
        '''
        return self.wait_jobs([job_id], check_every)[job_id]

    def wait_jobs(self, job_ids, check_every=2):
        '''wait for a list of jobs to be done

        Returns:
            The list of job infos

        Raises:
            JobFailure: As soon as a job failure is detected
        '''

        infos = dict((job_id, None) for job_id in job_ids)

        done = False
        while not done:
            done = True
            time.sleep(check_every)

            for job_id in job_ids:
                job_info = self.get_job(job_id)
                if not infos[job_id] or job_info['state'] != infos[job_id]['state']:
                    L.debug('job is %s', job_info['state'].lower())
                    infos[job_id] = job_info

                finish_reason = job_info['finish_reason']
                if finish_reason != 'None' and finish_reason != 'return':
                    raise JobFailure('Job %s (%s) did not finish correctly. Finish reason: %s' %
                                     (job_id, job_info['job_name'], finish_reason))

                done = done and job_info['state'] == 'closed'

        return infos
