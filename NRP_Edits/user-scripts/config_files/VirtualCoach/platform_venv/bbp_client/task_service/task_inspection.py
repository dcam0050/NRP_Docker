'''utilities to extract information from a local task'''

import shutil
import tempfile
import subprocess

import logging

L = logging.getLogger(__name__)


class VersionError(ValueError):
    '''Raised when the version detected in a document is incompatible with the code being used'''
    pass


def get_properties(task_filepath, git_commit, git_repo):
    '''Obtain properties for a new task registration'''

    from bbp_client.task_service import task_inspection_v0 as ti_v0
    from bbp_client.task_service import task_inspection_v1 as ti_v1

    known_props = dict(git_commit=git_commit, git_repo=git_repo)
    module_src = get_src_from_git(task_filepath, git_commit, git_repo)

    for ti in (ti_v1, ti_v0):
        try:
            return ti.get_properties(known_props, module_src)
        except VersionError:
            pass


def check_output(cmd, cwd='.'):
    """Run command with arguments and return its output as a byte string.

    Backported from Python 2.7 as it's implemented as pure python on stdlib.
    """
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=cwd)
    output, _ = process.communicate()
    retcode = process.poll()
    if retcode:
        error = subprocess.CalledProcessError(retcode, cmd)
        error.output = output
        raise error
    return output


def get_src_from_git(task_filepath, git_commit, git_repo):
    '''Obtain the contents of a source file from git'''

    root_path = tempfile.mkdtemp(prefix='add_task_git')
    try:
        check_output(['git', 'clone', git_repo, root_path])

        return check_output(['git', 'show', git_commit + ':' + task_filepath], cwd=root_path)

    finally:
        shutil.rmtree(root_path)  # delete directory
