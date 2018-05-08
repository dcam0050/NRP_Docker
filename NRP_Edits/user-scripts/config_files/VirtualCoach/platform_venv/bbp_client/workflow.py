'''convenience code to represent a set of jobs that run with possible mutual data dependencies'''

import time

from bbp_client.client import Task, JobFailure

import logging
L = logging.getLogger(__name__)


class WorkflowException(Exception):
    '''General workflow exception'''
    pass


class Dependencies(object):
    '''abstracts the list of dependencies of a job on data sources and how to construct the list
    of arguments for it.

    Data sources are identified by tickets (strings) and can be either other jobs or
    values from an initial set of arguments.
    '''

    def __init__(self, tickets, combinator):
        '''build a dependencies object

        Args:
            tickets(list(string)): The list of sources of data that is required to construct the
                list of arguments for this job. Each name may be either a reference to a job
                (in which case there is a data dependency and this job must wait for that
                one to finish) or a name from the initial list of arguments that is provided
                when starting a workflow.

            combinator(callable): A piece of logic that translates the results of all the
                required data into a single list of values that can be used as the arguments for
                the depending job.
                It will be called with the values corresponding to the list of tickets preserving
                the order. The result must be a list of values.

                Note that it's possible for a ticket to produce multiple values (for example it
                references a job that produces two or more results).

                For example, imagine a job that depends on t1 and t2 and also needs some initial
                args:
                    initial_args = [a1]
                    t1_results = [x, y, z]
                    t2_results = [w, v]

                If the dependencies object was built with:
                    tickets = ['t1', 'a1', 't2']

                The combinator will be called with:
                    combinator(x, y, z, a1, w, v)
        '''
        super(Dependencies, self).__init__()
        self.tickets = tickets
        self.combinator = combinator

    @classmethod
    def default(cls, *tickets):
        '''build a dependencies object when we don't need a fancy combinator'''
        return cls(tickets, lambda *args: list(args))


class WorkflowDefinition(object):
    '''represents a graph of tasks with possible data dependencies between them

    Note that dependencies are many to many (many jobs may depend on one and one job may depend
    on many). However, this graph is expected to be directed and the client must make sure
    that there are no loops involved (no checks are performed).

    This is the static representation of a workflow of jobs.
    It that can be instantiated and a Workflow object will be returned that abstracts the
    execution of the actual jobs.

    Example:
    >>> from bbp_client.client import Client
    >>> from bbp_client.workflow import WorkflowDefinition, Dependencies
    >>> from task_types.TaskTypes import URI
    >>>
    >>> client = Client.new()
    >>> filter_image_task = client.get_latest_task('filter_image_task')
    >>> wfd = WorkflowDefinition()
    >>> f0 = wfd.add_job(filter_image_task, Dependencies.default('image', 'filter0'))
    >>> f1 = wfd.add_job(filter_image_task, Dependencies.default(f0, 'filter1'))
    >>> f2 = wfd.add_job(filter_image_task, Dependencies.default('image', 'filter1'))
    >>>
    >>> my_image = URI('image/png', 'c1e0d582-2109-4ce5-8703-a9672a3e28cb')
    >>> wf = wfd.start('/my_tests', dict(image=my_image,
    >>>                                  filter0='BLUR',
    >>>                                  filter1='FIND_EDGES'))
    >>> wf.wait()
    >>> results = wf.collect_results()
    >>> edges_blurred_image_uri = results[f1]
    >>> edges_image_uri = results[f2]

    '''
    class Job(object):
        '''represents a the information required to launch a job in a workflow'''
        def __init__(self, launcher, dependencies, max_tries):
            self.launch = launcher
            self.dependencies = dependencies
            self.max_tries = max_tries

    def __init__(self):
        self.schedule = {}

    def add_job(self, launcher, dependencies, ticket=None, max_tries=1):
        '''adds a new job to the graph but does not launch it

        Args:
            launcher: A callable object that receives an output location and a set of arguments
                and will execute a remote job. The result of
                    bbp_client.client.Task.job_launcher()

                A Task handle object is also valid, in which case, the job will use the default
                excution context

            dependencies(Dependencies): an object representing the dependencies of the scheduled
                job.

            ticket (string): a unique identifier for the job in this workflow. This is for the
                purpose of dependency management and reference within this workflow and has no
                relation to task's job_ids or provenance information.
                If none is provided, a new one is generated and returned.

        Returns:
            A ticket (string) that uniquely identifies the job in this workflow definition.

        '''
        launcher = launcher.job_launcher() if isinstance(launcher, Task) else launcher

        ticket = (ticket if ticket is not None
                  else '%s_%d' % (launcher.task_name, len(self.schedule)))

        if ticket in self.schedule:
            raise WorkflowException('Ticket %s must be unique in this workflow' % ticket)

        self.schedule[ticket] = WorkflowDefinition.Job(launcher, dependencies, max_tries)

        return ticket

    def get_initial_jobs(self):
        '''returns the group of all initial jobs
        (jobs that have no dependencies within the workflow).

        Returns:
            A set of tickets
        '''
        return set([ticket
                    for ticket, job in self.schedule.items()
                    if all(dep not in self.schedule for dep in job.dependencies.tickets)])

    def get_leaf_jobs(self):
        '''returns the group of all leaf jobs
        (jobs that are not a dependency for another one).

        Returns:
            A set of tickets
        '''
        return set([ticket
                    for ticket in self.schedule
                    if not self._is_dependency(ticket)])

    def get_intermediate_jobs(self):
        '''returns the group of all intermediate jobs
        (jobs that are a dependency for another one).

        Returns:
            A set of tickets
        '''
        return set(self.schedule.keys()) - self.get_leaf_jobs()

    def _is_dependency(self, ticket):
        '''check if a job is a dependency of any other job'''
        return any(ticket in other.dependencies.tickets
                   for other in self.schedule.values())

    def start(self, output_location, initial_args):
        '''instantiate the workflow by launching all initial jobs with a set of initial arguments

        Args:
            output_location(string): A path on the document service where all results of the jobs
                will be saved.

            initial_args(dict): a map connecting argument names to values. Each job has listed in
                its dependencies the names of the arguments that it wants.

        Raises:
            KeyError if a job lists a dependency on an initial arg that is not provided.
            KeyError if a job lists a dependency on an ticket referencing another job that has not
            been added.

        Returns:
            A Workflow object that represents a running instance of this workflow definition.
        '''
        for ticket, job_def in self.schedule.items():
            if ticket not in initial_args:
                for dep in job_def.dependencies.tickets:
                    if dep not in self.schedule and dep not in initial_args:
                        raise KeyError('Job %s has a dependency %s which is an unknown job '
                                         '(expected one of: %s) or argument (expected one of: %s)' %
                                         (ticket, dep,
                                          ', '.join(self.schedule.keys()),
                                          ', '.join(initial_args.keys())))

        for i in initial_args:
            if i in self.schedule:
                L.warning('Value for %s provided as an argument. '
                          'Ignoring registered job with the same ticket.', i)

        return Workflow(self, output_location, initial_args)


class Workflow(object):
    '''represents a running instance of a workflow definition

    It keeps track of running jobs and automatically launches those whose
    dependencies have been fulfilled
    '''
    def __init__(self, definition, output_location, initial_args):
        '''
        Args:
            definition(WorkflowDefinition): graph of tasks
            output_location(str): ouput path in the document service
            initial_args(dict): a map connecting argument names to values
        '''
        self.definition = definition
        self.output_location = output_location
        self.issued_jobs = {}  # ticket -> job handle
        self.try_count = {}  # ticket -> number of relaunch tries (only for job tickets)
        self.failed = []  # list of failed tickets (only for job tickets)
        self.results = initial_args.copy()  # ticket -> results

    def update(self):
        '''progress the execution of the workflow.

        launches any jobs whose dependencies have been fulfilled

        Raises:
            JobFailure if a job that is the dependency of another fails
        '''
        self._try_collect_results()

        for ticket, job_def in self.definition.schedule.items():
            if ticket not in self.issued_jobs:
                if ticket not in self.closed_tickets():
                    args = self._try_get_args(job_def.dependencies)
                    if args is not None:
                        self._issue_job(ticket, job_def, args)

    def _try_collect_results(self):
        '''check every issued job and collect its results
        allow retry of failed jobs

        updates self.results and self.failed
        '''
        # only during try_collect_results we synchronise with the state of the server
        # that avoids race conditions (with the is_done method for example)
        # and limits the number of requests that we do per update
        # however it means that nowhere else in this code should we be using the job handles

        for ticket, job in self.issued_jobs.items():
            if ticket not in self.closed_tickets():
                if job.state == 'closed':
                    try:
                        self.results[ticket] = job.get_results()

                    except JobFailure:
                        L.error('Job %s (%s) failed. After %d tries (max: %d)',
                                self.issued_jobs[ticket].job_id,
                                ticket,
                                self.try_count[ticket],
                                self.definition.schedule[ticket].max_tries)

                        if self.try_count[ticket] >= self.definition.schedule[ticket].max_tries:
                            self.failed.append(ticket)
                            raise
                        else:
                            del self.issued_jobs[ticket]

    def _try_get_args(self, dependencies):
        '''get the combined output of the results of a dependency set

        Returns:
            None if any dependency is still pending.
            A list of results otherwise.

        Raises:
            JobFailure: If any of the dependencies failed

        Raises:
            JobFailure: If the job fails
        '''
        if any(d not in self.results for d in dependencies.tickets):
            return None

        else:
            results = []
            for ticket in dependencies.tickets:
                if ticket in self.definition.schedule:
                    # list must be flattened for job outputs
                    results.extend(self.results[ticket])
                else:
                    results.append(self.results[ticket])

            return dependencies.combinator(*results)

    def _issue_job(self, ticket, job_def, args):
        '''launch a job'''
        L.debug('launching %s with %s', ticket, args)
        job_handle = job_def.launch(self.output_location, *args)
        self.issued_jobs[ticket] = job_handle
        self.try_count[ticket] = self.try_count.get(ticket, 0) + 1

    def is_done(self):
        '''check we have data for all the tickets'''
        return self.all_tickets() == self.closed_tickets()

    def wait(self, timeout=None, check_every=2, callback=None):
        '''wait for the full workflow to be done

        Args:
            timeout(float): how long (in number of seconds) that this function is allowed to wait
                for the workflow to be done.
            check_every(float): how often (in number of seconds) that this function checks the
                current state of issued jobs with the remote service.
            callback(callable): function that is called after every check (so after check_every
                seconds) with the workflow as an option. Note: the check loop is blocked when
                in this callback

        Raises:
            JobFailure: If any of the dependencies failed
        '''
        waited = 0
        while not self.is_done() and (timeout is None or waited <= timeout):
            self.update()
            time.sleep(check_every)
            waited += check_every
            if callback is not None:
                callback(self, waited)

    def all_tickets(self):
        '''get the group of all tickets'''
        return set(self.definition.schedule.keys() + self.results.keys())

    def closed_tickets(self):
        '''return the group of tickets that have been closed
        A ticket is closed if one of the following is true:
            - It was provided in the list of initial args
            - A job was run, finished and we managed to get its results
            - A job was run, failed and exceeded the maximum number of retries'''
        return set(self.results.keys() + self.failed)

    def collect_results(self, tickets=None):
        '''returns the results of all successfully finished jobs

        Args:
            tickets(iterable): collection of tickets whose results should be looked up.
                If None is provided, the list of leaf jobs will be used.

        Returns:
            A dict where the index is the job ticket and the value the list of results
            Note that some tickets may be missing if their job hasn't finished or it failed
        '''
        tickets = tickets if tickets is not None else self.definition.get_leaf_jobs()
        return dict((t, self.results[t]) for t in tickets if t in self.results)
