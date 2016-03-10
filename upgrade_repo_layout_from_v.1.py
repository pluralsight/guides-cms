"""
This script is meant to upgrade the content repository from the layout used in
version .1.

This sort of script is probably better suited to a shell script, but we chose
Python since the remainder of the application is in Python.  Hopefully this
will help users not familiar with shell scripting to understand, contribute,
and modify this script.

This script makes only local changes to the content repository in a local
branch.  You'll have the opportunity to review and edit any commits made during
the upgrade process as you must manually push the upgrade changes to your
remote repository.
"""

import argparse
import codecs
import os
import shutil
import subprocess
import json

from pskb_website import utils
from pskb_website.models import file as file_mod


# Base url of your site. This is a copy of the BASE_URL environment variable
# just to keep the depenencies down and could be useful if you want to
# transition from one base_url to another.
BASE_URL = u'https://tutorials.pluralsight.com'

DEFAULT_STACK = u'other'

PUBLISHED = u'published'
IN_REVIEW = u'in-review'
DRAFT = u'draft'
STATUSES = (PUBLISHED, IN_REVIEW, DRAFT)

METADATA_FILE = 'details.json'


def create_required_directories():
    """
    Create required directories in current working directory

    Assumes the current working directory is root of git repo.
    """

    for status in STATUSES:
        try:
            os.mkdir(status)
        except OSError:
            if not os.path.isdir(status):
                raise


def metadata_files(content_dir='.'):
    """
    Iterator through all metadata files in content_dir (recursively)

    :param content_dir: Directory of content to search for metadata files
    """

    for root, dirs, files in os.walk(content_dir):
        for filename in files:
            if filename != METADATA_FILE:
                continue

            yield os.path.join(root, filename)



def json_from_file(filename):
    """
    Read file, parse and return as json

    :param filename: File to read
    """

    with codecs.open(filename, 'r', encoding='utf-8') as file_obj:
        str_ = json.loads(file_obj.read(), encoding='utf-8')

    return str_


def json_to_file(filename, json_data):
    """
    Write file with given json

    :param filename: File to write
    """

    with codecs.open(filename, 'w', encoding='utf-8') as file_obj:
        file_obj.write(json.dumps(json_data, sort_keys=True, indent=4,
                                  separators=(',', ': ')))


def move_guides():
    """
    Move all guide directories into the proper publish status directory

    All guides will be moved from their current location into a structure like
    the following:
        <publish_status>/<stack>/<directory_name>

    The <publish_status> is one of STATUSES and is determined by the guides'
    metadata 'publish_status' field.

    The <stack> is the first stack in the guides' metadata file.

    The <directory_name> is the same directory as the guide used before.

    Assumes the current working directory is root of git repo.
    """

    for md_file in metadata_files():
        curr_dir = os.path.dirname(md_file)

        top_dir = None
        for dir_ in curr_dir.split(os.sep):
            if dir_ == '.':
                continue

            top_dir = dir_
            break

        if top_dir in STATUSES:
            # guide already in the right directory
            continue

        metadata = json_from_file(md_file)
        stack = metadata['stacks'][0]

        new_dir = os.path.join(metadata['publish_status'],
                               utils.slugify_stack(stack),
                               curr_dir)

        dirname = os.path.dirname(new_dir)

        try:
            os.makedirs(dirname)
        except OSError:
            if not os.path.isdir(dirname):
                raise

        cmd = u'git mv %s %s' % (curr_dir, new_dir)
        subprocess.check_call(cmd.split())

    cmd = u'git commit -m'.split()
    cmd.append(u'Moving guides based on where they are in publish workflow')
    subprocess.check_call(cmd)


def upgrade_metadata():
    """
    Upgrade all metadata files in current working directory with new fields and
    renamed fields

    The following modifications are made to metadata:
        1. The 'published' field field is removed if it exists in favor of the
           new 'publish_status'.
        2. The 'publish_status' of every article is set to 'draft' unless
           'published' is True.
        3. The list of 'stacks' is set to DEFAULT_STACK if there are no stacks
           already.

    Assumes the current working directory is root of git repo.
    """

    files_changed = 0
    for md_file in metadata_files():
        metadata = json_from_file(md_file)

        changed_file = False

        try:
            _ = metadata['stacks'][0]
        except (IndexError, KeyError):
            metadata['stacks'] = [DEFAULT_STACK]
            changed_file = True

        status = False

        try:
            status = metadata['published']
        except KeyError:
            try:
                status = metadata['publish_status']
            except KeyError:
                changed_file = True
        else:
            del metadata['published']
            changed_file = True

        if status not in STATUSES:
            changed_file = True

            if status:
                metadata['publish_status'] = PUBLISHED
            else:
                metadata['publish_status'] = DRAFT

        if changed_file:
            json_to_file(md_file, metadata)

            cmd = u'git add %s' % (md_file)
            subprocess.check_call(cmd.split())
            files_changed += 1

    if files_changed:
        cmd = u'git commit -m'.split()
        cmd.append(u'Upgrading metadata: Rename published to publish_status and added default stack')
        subprocess.check_call(cmd)


def rename_file_listing():
    """
    Rename file listing files at top-level of repo to new names reflecting the
    new publish workflow

    - Changes unpublished.md to draft.md if it exists
    """

    draft_file = u'%s.md' % (DRAFT)
    cmd = u'git mv unpublished.md %s' % (draft_file)

    try:
        subprocess.check_call(cmd.split())
    except subprocess.CalledProcessError:
        print '%s file already exists, please manually merge contents of unpublished.md into %s' % (draft_file, draft_file)
        raise

    cmd = u'git commit -m'.split()
    cmd.append(u'unpublished.md is now %s' % (draft_file))
    subprocess.check_call(cmd)


def upgrade_file_listing_urls(status):
    filename = '%s.md' % (status)

    articles = []
    with codecs.open(filename, 'r', encoding='utf-8') as file_obj:
        articles = file_mod.read_items_from_file_listing(file_obj.read())

    new_sections = []
    for article in articles:
        stacks = article.stacks if article.stacks else [u'other']
        name = article.author_real_name or article.author_name

        query_str = u'' if status == PUBLISHED else u'?status=%s' % (status)
        url = u'%s/%s/%s%s' % (BASE_URL, utils.slugify_stack(stacks[0]),
                               utils.slugify(article.title), query_str)

        author_url = u'%s/user/%s' % (BASE_URL, article.author_name)

        section = file_mod.get_updated_file_listing_text(u'',
                                                         url,
                                                         article.title,
                                                         author_url,
                                                         name,
                                                         article.author_img_url,
                                                         article.thumbnail_url,
                                                         stacks)

        new_sections.append(section)

    with codecs.open(filename, 'w', encoding='utf-8') as file_obj:
        file_obj.write(u'\n\n'.join(new_sections))

    cmd = u'git add %s' % (filename)
    subprocess.check_call(cmd.split())

    cmd = u'git commit -m'.split()
    cmd.append(u'Updating URLs in %s' % (filename))
    subprocess.check_call(cmd)


def remote_branches():
    """
    Iterator through all remote branches

    Assumes the current working directory is root of git repo.
    """

    output = subprocess.check_output(u'git branch -r'.split())
    for line in output.splitlines():
        yield line.strip()


def upgrade_branches(merge_branch):
    """
    Merge all remote branches with master to upgrade their layout

    :param merge_branch: Branch to merge all other branches with

    Assumes the current working directory is root of git repo.
    """

    subprocess.check_call(u'git fetch --all'.split())

    for branch in remote_branches():
        if branch.endswith(u'master') or branch == merge_branch:
            continue

        cmd = u'git checkout --track %s' % (branch)
        try:
            subprocess.check_call(cmd.split())
        except subprocess.CalledProcessError:
            # Maybe branch already exists
            cmd = u'git checkout %s' % (branch.split(os.sep)[1])
            subprocess.check_call(cmd.split())

        cmd = u'git merge %s' % (merge_branch)

        try:
            subprocess.check_call(cmd.split())
        except subprocess.CalledProcessError as err:
            print u'Error: %s' % (err)
            print u'Problem merging master into %s, handle the conflicts and hit enter to continue or ctrl-D to quit' % (branch)
            _ = raw_input()


def setup_repo(clone_url, branch, force):
    """
    Setup repo for upgrade by updating from origin and creating branch

    :param clone_url: URL to clone into current working directory
    :param branch: Branch to checkout/create for changes
    :param force: Remove the branch if it already exists and start fresh
    :returns: Directory name of repo cloned or None of user decided to quit
    """

    repo_dir = os.path.abspath(clone_url.split(os.sep)[-1])

    if os.path.isdir(repo_dir):
        answer = raw_input('The %s directory already exists. Want to overwrite with checkout? (y/n)' % (repo_dir))
        if answer.lower() != 'y':
            return None

        shutil.rmtree(repo_dir)

    # Make sure we're up to date and we branch from master
    cmd = u'git clone %s' % (clone_url)
    subprocess.check_call(cmd.split())

    os.chdir(repo_dir)

    subprocess.check_call(u'git pull origin master'.split())
    subprocess.check_call(u'git checkout master'.split())

    checkout_branch = u'git checkout -b %s' % (branch)

    try:
        subprocess.check_call(checkout_branch.split())
    except subprocess.CalledProcessError:
        if not force:
            raise

        subprocess.check_call(u'git checkout master'.split())

        cmd = u'git branch -D %s' % (branch)
        subprocess.check_call(cmd.split())

        subprocess.check_call(checkout_branch.split())

    return repo_dir


def main(clone_url, branch='upgrade_from_v.1', force=False,
         upgrade_remote_branches=False):
    """
    Upgrade repository in given directory using given branch

    :param clone_url: URL of git repository serving as the content/database for
                      hack.guides() CMS content
    :param branch: Name of branch to make all changes in
    :param force: Remove the branch if it already exists and start fresh
    :param upgrade_remote_branches: Upgrade remote branches (interactive)
    """

    orig_cwd = os.getcwd()

    try:
        content_dir = setup_repo(clone_url, branch, force)
        if content_dir is None:
            return

        os.chdir(content_dir)

        create_required_directories()
        upgrade_metadata()
        rename_file_listing()

        # Remember, we don't have anything in-review during upgrade
        for status in (PUBLISHED, DRAFT):
            upgrade_file_listing_urls(status)

        move_guides()

        if upgrade_remote_branches:
            upgrade_branches(branch)
    finally:
        os.chdir(orig_cwd)

    print ('\n\n\nYou can now inspect the changes in the %s branch.\n'
           'Once satisfied push this branch to github.com with a command like\n'
           '"git push origin %s:master"' % (branch, branch))


def _parse_args():
    parser = argparse.ArgumentParser(description='Upgrade repository layout from version .1 layout')

    parser.add_argument('-c', '--clone-url', action='store',
                        dest='clone_url', required=True,
                        help='URL to clone git repo for hack.guides() CMS content')

    parser.add_argument('-b', '--branch', action='store',
                        default='upgrade_from_v.1', dest='branch',
                        required=False,
                        help='Name of branch to perform upgrade in. This is the branch you will push to your remote repository.')

    parser.add_argument('-f', '--force', action='store_true',
                        dest='force', required=False, default=False,
                        help='Remove branch if already exists')

    parser.add_argument('--upgrade-branches', action='store_true',
                        dest='upgrade_branches', required=False, default=False,
                        help='Interactively upgrade remote branches')

    return vars(parser.parse_args())


if __name__ == '__main__':
    args = _parse_args()
    main(args['clone_url'], args['branch'], args['force'],
         args['upgrade_branches'])
