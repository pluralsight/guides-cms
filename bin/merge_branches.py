"""
Script to merge all remote branches with the master branch
"""

import argparse
import os
import subprocess


def setup_repo():
    """
    Update master branch in repo for merging

    Assumes current working directory is root level of repo
    """

    # Make sure we're up to date and we branch from master
    subprocess.check_call(u'git pull origin master'.split())
    subprocess.check_call(u'git checkout master'.split())


def remote_branches():
    """
    Iterator through all remote branches

    Assumes the current working directory is root of git repo.
    """

    output = subprocess.check_output(u'git branch -r'.split())
    for line in output.splitlines():
        yield line.strip()


def merge_branches(merge_branch):
    """
    Merge all remote branches with given branch

    Assumes the current working directory is root of git repo.
    """

    subprocess.check_call(u'git fetch --all'.split())

    for branch in remote_branches():
        if branch.endswith(merge_branch):
            continue

        # Name with out origin/
        branch_name = branch.split(os.sep)[1]

        cmd = u'git checkout --track %s' % (branch)
        try:
            subprocess.check_call(cmd.split())
        except subprocess.CalledProcessError:
            # Maybe branch already exists
            cmd = u'git checkout %s' % (branch_name)
            subprocess.check_call(cmd.split())

        cmd = u'git merge %s' % (merge_branch)
        try:
            subprocess.check_call(cmd.split())
        except subprocess.CalledProcessError as err:
            print u'Error: %s' % (err)
            print u'Problem merging %s into %s, handle the conflicts and hit enter to continue or ctrl-D to quit' % (merge_branch, branch)
            _ = raw_input()

        print u'Would you like to push the %s remote branch now (y/n)?' % (branch)
        answer = raw_input()
        if answer.lower() == 'y':
            cmd = u'git push origin %s' % (branch_name)
            subprocess.check_call(cmd.split())


def main(content_dir, branch):
    """
    Merge all remote branches with master

    :param content_dir: Directory of git repository serving as the
                        content/database for hack.guides() CMS content
    :param branch: Branch to merge with
    """

    orig_cwd = os.getcwd()
    os.chdir(content_dir)

    try:
        setup_repo()
        merge_branches(branch)
    finally:
        os.chdir(orig_cwd)


def _parse_args():
    parser = argparse.ArgumentParser(description='Merge remote branches with another branch')

    parser.add_argument('-d', '--content-dir', action='store',
                        dest='content_dir', required=True,
                        help='Directory containing git repo for hack.guides() CMS content')

    parser.add_argument('-b', '--branch', action='store',
                        dest='branch',
                        required=True,
                        help='Name of branch to merge all other branches with')

    return vars(parser.parse_args())


if __name__ == '__main__':
    args = _parse_args()
    main(args['content_dir'], args['branch'])
