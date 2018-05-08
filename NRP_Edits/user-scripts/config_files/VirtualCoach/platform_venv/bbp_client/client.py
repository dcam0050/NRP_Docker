'''A convenience single client that combines functionality from the different services'''
import datetime
from functools import partial

from task_types.TaskTypes import URI
from bbp_services.client import get_services

from bbp_client.task_service.client import Client as TaskClient
from bbp_client.task_service.client import TaskException, JobFailure
from bbp_client.provenance_service.client import Client as ProvClient
from bbp_client.document_service.client import Client as DocumentClient
from bbp_client.mimetype_service.client import Client as MIMETypeClient
from bbp_client.oidc.client import BBPOIDCClient


import logging
L = logging.getLogger(__name__)


DEFAULT_LOG_FORMAT = u'[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d] %(message)s'


class JobNotFinished(TaskException):
    '''The job is still running'''
    pass


DEFAULT_JOB_CONTEXT = dict(
    cpu_cores=1,
    total_physical_memory=2 * 1024,
    requested_queue='cscs_viz'
)


def _format_docstring_args(args, sep):
    '''formats a list of accepts or returns definitions into a docstring-like str'''
    return sep + sep.join(['%s(%s)' % (arg['name'], arg['type']) for arg in args])


class Client(object):
    '''A single client that combines functionality from the different services

    Provides a high level abstraction for job launching and management

    Handles finding tasks and jobs, creating a 'context' of execution, and then
    binding the arguments to the particular run.

    A 'context' describes the computing resources that are required for the
    particular job instance.

    Example:
        >>> from task_types.TaskTypes import URI
        >>> from bbp_client.client import Client
        >>>
        >>> my_image = URI('image/png', 'c1e0d582-2109-4ce5-8703-a9672a3e28cb')
        >>> tl = Client.new()
        >>> filter_image_task = tl.get_latest_task('filter_image_task')
        >>> filter_image_launcher = filter_image_task.job_launcher()
        >>> job1 = filter_image_launcher('/my_test_project', my_image, 'BLUR')
        >>> results = job1.wait()
        >>> blurred_image = results[0]
    '''
    def __init__(self, task_client, prov_client, document_client, mimetype_client):
        super(Client, self).__init__()
        self.task = task_client
        self.prov = prov_client
        self.document = document_client
        self.mimetype = mimetype_client

    @classmethod
    def new(cls, environment='prod', user=None, password=None):
        '''create a new cross-service client'''
        services = get_services()

        oauth_client = BBPOIDCClient().implicit_auth(
            user=user, password=password, oauth_url=services['oidc_service'][environment]['url'])

        return cls(
            task_client=TaskClient(
                host=services['task_service'][environment]['url'],
                oauth_client=oauth_client),
            prov_client=ProvClient(
                host=services['prov_service'][environment]['url'],
                oauth_client=oauth_client),
            document_client=DocumentClient(
                host=services['document_service'][environment]['url'],
                oauth_client=oauth_client),
            mimetype_client=MIMETypeClient(
                host=services['mimetype_service'][environment]['url']))

    def get_access_token(self):
        '''return bearer token'''
        return self.task.oauth_client.get_auth_header()

    def get_sorted_job_returns(self, job_id):
        ''' retrieve the returned values of a finished job as a list ordered as per the task
        definition'''

        results_map = self.prov.get_job_returns(job_id)

        job_info = self.task.get_job(job_id)
        task_info = self.task.get_task(job_info['task_id'])

        results_ordered = []
        for ret_def in task_info['properties']['returns']:
            value = results_map[ret_def['name']]

            #TODO unhack when URI objects are removed from the task service or added to provenance
            if isinstance(ret_def['type'], dict):
                if ret_def['type']['object'] == 'URIType':
                    value = URI(ret_def['type']['contents']['category'], value)

                elif ret_def['type']['object'] == 'ListOf':
                    subtype = ret_def['type']['contents']['subtype']
                    if isinstance(subtype, dict) and subtype['object'] == 'URIType':
                        value = [URI(subtype['contents']['category'], v['contents']['document'])
                                 for v in value]

            results_ordered.append(value)

        return results_ordered

    def get_tasks(self, task_name=None, git_commit=None, git_repo=None):
        '''get all the tasks that match the arguments

        Args:
            task_name(str): name of the task, can be None
            git_commit(str): git commit of the task, can be None
            git_repo(str): git repo of the task, can be None

        Returns:
            A collection of Task objects
        '''
        tasks_brief = self.task.get_tasks(task_name, git_commit, git_repo)
        return set(self.get_task(brief['task_id']) for brief in tasks_brief)

    def get_task(self, task_id):
        '''get the task given its id

        Args:
            task_id(str): unique id of the task
        '''
        return Task(self, task_id)

    def get_latest_task(self, task_name):
        '''get the latest version of a task by name

        Args:
            task_name(str): name of the task
        '''
        info = self.task.get_latest_task(task_name)
        return Task(self, info['task_id'])

    def get_job(self, job_id):
        '''get the job given its id

        Args:
            job_id(str): unique id of the job

        Returns:
            A Job object
        '''
        return Job(self, job_id)

    def get_jobs(self):
        '''get all the jobs visible for this client

        Returns:
            A collection of Job objects
        '''
        jobs_brief = self.task.get_jobs()
        return set(self.get_job(brief['job_id']) for brief in jobs_brief)

    def get_running_jobs(self):
        '''get all the jobs visible for this client that are currently running

        Note that jobs are running asyncronously so they may be finished at any point
        including by the time this function returns.

        Returns:
            A collection of Job objects
        '''
        return set(j for j in self.get_jobs() if j.state == 'running')


class Task(object):
    '''wrapper around a task as returned from bbp_client.task_service'''

    def __init__(self, client, task_id):
        '''
        Args:
            client(bbp_client.client.Client): authenticated client instance
            info(dict): task information as returned by bbp_client.task_service
        '''
        super(Task, self).__init__()
        self.client = client
        self.task_id = task_id
        info = self.client.task.get_task(task_id)
        self.task_name = info['properties']['task_name']
        self.__doc__ = (
            '%s\n\n%s\n\n'
            'Args:%s\n\n'
            'Returns:%s\n' %
            (info['properties']['caption'],
             info['properties']['description'],
             _format_docstring_args(info['properties']['accepts'], '\n    '),
             _format_docstring_args(info['properties']['returns'], '\n    ')))

    def __repr__(self):
        return self.task_name

    def __eq__(self, other):
        '''task handles are equal if they point at the same task id'''
        return self.task_id == other.task_id

    def __ne__(self, other):
        '''task handles are equal if they point at the same task id'''
        return self.task_id != other.task_id

    # TODO accept kwargs and merge them with args into a single list following the task def
    def __call__(self, job_context, output_location, *args):
        '''launches a job

        Args:
            job_context(dict): parameters relative to the job execution context
            output_location(str): where results should be saved
            *args: arguments for the task

        Returns:
            A Job that can be used to keep track of the state of a remote job
        '''
        start_time = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M.%S')
        job_name = '%s_%s' % (self.task_name, start_time)
        launch_info = self.client.task.start_job(
            arguments=args,
            job_name=job_name,
            output_location=output_location,
            task_id=self.task_id,
            **job_context)

        job = Job(self.client, launch_info['job_id'])
        return job

    @property
    def info(self):
        '''all the information about the the task'''
        return self.client.task.get_task(self.task_id)

    def job_launcher(self, job_context=None):
        '''creates a wrapper around the job_context that is ready to launch the task'''
        job_context = job_context or DEFAULT_JOB_CONTEXT
        launcher = partial(self.__call__, job_context)
        launcher.task_name = self.task_name
        launcher.__doc__ = self.__doc__
        return launcher


class Job(object):
    ''''A handle on a remote job that can be used to keep track of its state and retrieve
    any results'''
    def __init__(self, client, job_id):
        super(Job, self).__init__()
        self.client = client
        self.job_id = job_id
        job_info = self.client.task.get_job(self.job_id)
        self.__doc__ = job_info['job_name']

    def __repr__(self):
        return self.__doc__

    def __eq__(self, other):
        '''job handles are equal if they point at the same job id'''
        return self.job_id == other.job_id

    def __ne__(self, other):
        '''job handles are equal if they point at the same job id'''
        return self.job_id != other.job_id

    def cancel(self):
        '''cancel a pending or running job'''
        self.client.task.cancel_job(self.job_id)

    def wait(self):
        '''wait for a the job to be done

        Returns:
            The returned values of the job

        Raises:
            JobFailure: If the job fails
        '''
        self.client.task.wait_job(self.job_id)
        return self.get_results()

    @property
    def info(self):
        '''all the information about the the job'''
        return self.client.task.get_job(self.job_id)

    @property
    def state(self):
        '''the state of the job (str)'''
        return self.info['state']

    def get_task(self):
        '''the task that this job is an instance of'''
        return Task(self.client, self.info['task_id'])

    def _verify_job_finished(self, check_success=True):
        '''check that the job finished and raise otherwise'''

        job_info = self.client.task.get_job(self.job_id)
        finish_reason = job_info['finish_reason']

        if finish_reason is None or finish_reason == 'None':
            raise JobNotFinished('Job %s has not finished and its results can not be '
                                 'retrieved' % self.job_id)

        if check_success:
            if finish_reason != 'return':
                raise JobFailure('Job %s (%s) did not finish correctly. Finish reason: %s' %
                                 (self.job_id, job_info['job_name'], finish_reason))

    def get_results(self):
        '''collect the results of the job

        Returns:
            A list with the returned values of the job

        Raises:
            JobNotFinished: If the job is not done
            JobFailure: If the job fails
        '''
        self._verify_job_finished()

        return self.client.get_sorted_job_returns(self.job_id)

    def get_log(self):
        '''obtain the contents of the job execution log

        Returns:
            A dictionary of strings containing the different sections
            of the job execution log. For example:
            {
                'STDERR': '....'
                'SDTOUT': '....'
                ...
            }

        Raises:
            JobNotFinished: If the job is not done
        '''
        self._verify_job_finished(check_success=False)

        log_uuid = self.client.prov.get_job_log(self.job_id)
        log = self.client.document.download_file_by_id(log_uuid)

        # TODO change when we have a better solution for logs
        d = dict(FILES=[], RETURN=[], LOGS=[], STDOUT=[], STDERR=[], OTHER=[])
        key = 'OTHER'
        for line in log.split('\n'):
            if line in d.keys():
                key = line
            else:
                d[key].append(line)

        return dict((k, '\n'.join(v)) for k, v in d.items())
