"""
Main views of PSKB app
"""

from flask import redirect, url_for, session, request, render_template, flash, g

from . import PUBLISHED, IN_REVIEW, DRAFT, STATUSES, SLACK_URL
from . import app
from . import remote
from . import models
from . import forms
from . import tasks
from . import filters
from . import utils
from . import url_for_domain
from .lib import (
        read_article,
        login_required,
        is_logged_in,
        lookup_url_redirect,
        collaborator_required)


@app.route('/')
def index():
    """Homepage"""

    # Send to login, application not fully setup yet.
    if app.config['REPO_OWNER_ACCESS_TOKEN'] is None:
        return redirect(url_for('login'))

    return render_published_articles()


@app.route('/login/')
def login():
    """Login page"""

    prev_url = session.get('previously_requested_page')

    # See if user got here from write page and highlight that tab to indicate
    # that they're trying to write and the click succeeded in getting them
    # closer to writing; specific suggestion from Ed.
    if prev_url is not None and '/write/' in prev_url:
        g.write_active = True

    return render_template('login.html')


@app.route('/contributors/')
def contributors():
    """Contributors page"""

    # The commit stats will have the avatar for all users because these stats
    # come directly from github.  However, the guide_stats are based on what
    # metadata we have stored so the image url could be empty.  So, fill in any
    # missing images with the commit stats to avoid additional API calls.
    commit_stats = models.contribution_stats()
    guide_stats = models.author_stats(statuses=(PUBLISHED,))

    for user, (count, image_url) in guide_stats.iteritems():
        if image_url is None:
            try:
                avatar_url = commit_stats[user]['avatar_url']
            except KeyError:
                pass
            else:
                guide_stats[user] = [count, avatar_url]

    # FIXME: Would be better to automatically ignore all collaborators on a
    # repo but that requires 1 API request per user and we might want to count
    # some collaborators and not others anyway.

    # We could pass this ignore_users down but then we'd have to be mindful of
    # which version was cached, etc. It's easier to do this trimming here
    # because we can trim all stats independent of lower layers and caching
    # even though this might not be as efficient.  Ideally we won't be
    # ignoring large amounts of users so shouldn't be a big issue.

    ignore_users = models.contributors_to_ignore()

    return render_template('contributors.html',
                           commit_stats=commit_stats,
                           guide_stats=guide_stats,
                           ignore_users=ignore_users)


@app.route('/faq/')
def faq():
    """FAQ page"""

    g.slack_url = SLACK_URL

    # Read and cache this for an hour, the FAQ doesn't change very frequently
    text = models.read_file('faq.md', rendered_text=False, use_cache=True, timeout=60 * 60)

    return render_template('faq.html', text=text)


@app.route('/contest/')
def contest():
    """Contest page"""

    # Read and cache this for an hour. This page won't change to often, but if
    # it does the webhook will clear the cache for us.  There won't be any
    # editing of this locally.
    text = models.read_file(models.CONTEST_FILENAME, rendered_text=False,
                            use_cache=True, timeout=60 * 60)

    return render_template('contest.html', text=text)


@app.route('/github_login')
def github_login():
    """Callback for github oauth"""

    # Using _external=True even though it's redundant for our wrapper unless
    # DOMAIN is set.
    url = url_for_domain('authorized', _external=True,
                         base_url=app.config['DOMAIN'])
    return remote.github.authorize(callback=url)


@app.route('/logout')
@login_required
def logout():
    """Logout page"""

    session.pop('github_token', None)
    session.pop('login', None)
    session.pop('name', None)
    session.pop('collaborator', None)
    session.pop('user_image', None)

    return redirect(url_for('index'))


@app.route('/github/authorized')
def authorized():
    """URL for Github auth callback"""

    resp = remote.github.authorized_response()
    if resp is None or resp.get('access_token') is None:
        flash('Access denied: reason=%s error=%s resp=%s' % (
              request.args['error'], request.args['error_description'], resp),
              category='error')
        return redirect(url_for('index'))

    session['github_token'] = (resp['access_token'], '')
    session['collaborator'] = False

    # Workaround for the first time you setup application
    if app.config['REPO_OWNER_ACCESS_TOKEN'] is None:
        app.config['REPO_OWNER_ACCESS_TOKEN'] = resp['access_token']
        app.logger.critical('Please set your REPO_OWNER_ACCESS_TOKEN environment variable to: %s', resp['access_token'])

    user = models.find_user()
    if user is None:
        flash('Unable to read user from Github API')
        return redirect(url_for('index'))

    if user.avatar_url:
        session['user_image'] = user.avatar_url

    if user.name:
        session['name'] = user.name

    if user.login:
        session['login'] = user.login

        if 'name' not in session:
            session['name'] = user.login

        session['collaborator'] = user.is_collaborator

    url = session.pop('previously_requested_page', None)
    if url is not None:
        return redirect(url)

    flash('Thanks for logging in. You can now browse guides <a href="%s"> in review</a> or <a href="%s">write new guides</a>.' % (url_for('in_review'), url_for('write')), category='info')

    return redirect(url_for('user_profile', author_name=user.login))


@app.route('/user/<author_name>', methods=['GET'])
def old_profile(author_name):
    return redirect(url_for('user_profile', author_name=author_name), 301)


# Note this URL is directly linked to the filters.url_for_user filter.
# These must be changed together!
@app.route('/author/<author_name>', methods=['GET'])
def user_profile(author_name):
    """Profile page"""

    if author_name is None:
        author_name = session.get('login', None)
        # Must pass author name via URL if not logged in
        if author_name is None:
            return redirect(url_for('index'))

    user = models.find_user(author_name)
    if not user:
        flash('Unable to find user "%s"' % (author_name), category='error')
        return redirect(url_for('index'))

    # Only owners can see their own drafts
    if is_logged_in() and user.login == session['login']:
        articles = models.get_articles_for_author(user.login)
    else:
        articles = models.get_public_articles_for_author(user.login)

    published = []
    in_review = []
    draft = []

    for status, group in models.group_articles_by_status(articles):
        if status == PUBLISHED:
            published = list(group)
        elif status == IN_REVIEW:
            in_review = list(group)
        elif status == DRAFT:
            draft = list(group)

    return render_template('profile.html', user=user, published=published,
                           in_review=in_review, draft=draft)


@app.route('/my-drafts/')
@login_required
def my_drafts():
    """Users drafts"""

    g.drafts_active = True
    articles = models.get_articles_for_author(session['login'],
                                              status=DRAFT)
    featured_article = models.get_featured_article()

    return render_template('index.html', articles=articles,
                           featured_article=featured_article)


@app.route('/write/<stack>/<title>', methods=['GET'])
@app.route('/write/', defaults={'stack': None, 'title': None}, methods=['GET'])
@login_required
def write(stack, title):
    """Editor page"""

    article = None
    selected_stack = None

    if stack is not None and title is not None:
        branch = request.args.get('branch', u'master')
        status = request.args.get('status', DRAFT)
        article = read_article(stack, title, branch, status,
                               rendered_text=False)
        if article is None:
            flash('Failed reading guide', category='error')
            return render_template('editor.html', article=article,
                                   stacks=forms.STACK_OPTIONS,
                                   selected_stack=selected_stack), 404


        if article.sha is None:
            article.sha = ''

        # Only allowing a single stack choice now but the back-end article
        # model can handle multiple.
        if article.stacks:
            selected_stack = article.stacks[0]

    return render_template('editor.html',
                           article=article,
                           stacks=forms.STACK_OPTIONS,
                           selected_stack=selected_stack,
                           username=session['login'])


@app.route('/partner/import/')
@login_required
def partner_import():
    """Special 'hidden' URL to import articles to secondary repo"""

    article = None
    branch_article = False
    secondary_repo = True

    flash('You are posting an guide to the partner repository!',
          category='info')

    return render_template('editor.html', article=article,
                           branch_article=branch_article,
                           secondary_repo=secondary_repo)


@app.route('/in-review/', methods=['GET'])
def in_review():
    """In review page"""

    return render_article_list_view(IN_REVIEW)


@app.route('/review/<title>', methods=['GET'])
def review(title):
    """
    This URL only exists for legacy reasons so try to find the article where
    it is in the new scheme and return 301 to indicate moved.
    """

    branch = request.args.get('branch', u'master')

    article = models.search_for_article(title)
    if article is not None:
        return redirect(filters.url_for_article(article, branch=branch), 301)

    return missing_article(request.base_url, title=title, branch=branch)


# Note this URL is directly linked to the filters.url_for_article filter.
# These must be changed together!
@app.route('/<stack>/<title>', methods=['GET'])
def article_view(stack, title):
    """
    Find article with given stack/stack combination and display it

    Note all publish statuses are searched and the first one found is returned.
    This allows us to keep the same URL through the publish workflow process
    since the status is only a 'hint' and query string.

    By default, the statuses are searched in the order of importance:
    published, in-review, and finally draft.

    GET parameters used:
        - status: Hint on what publish status to search for FIRST
            - Default is 'published' which makes the published articles have
              clean URLs without any query string.
        - branch: Branch of article to display
            - Default is master
    """

    # Support for old URL /title/article.md
    if title == 'article.md':
        return redirect(url_for('review', title=stack))

    # We don't allow any of these characters in stack or title so go ahead and
    # reject this without doing any github API requests.  This especially
    # prevents issues when articles have bad image links in them that do not
    # have a path, which would end up making requests to this URL. For example,
    # <img src="test.png"/> on a /python/my-article page would try to find the
    # image at /python/test.png.
    if '.' in stack or '.' in title:
        return not_found()

    branch = request.args.get('branch', u'master')

    # User came from a heart attempt and logged in
    if request.args.get('hearted', False) and is_logged_in():
        models.add_heart(stack, title, session.get('login'))

    # Search all status so an article's canonical URL can always stay the same
    # regardless of the status, i.e we use the status argument as a hint on
    # which file listing to use first but we always search the others until we
    # find article.
    status = request.args.get('status', PUBLISHED)

    # draft articles are only visible by logged in users
    if status == DRAFT and not is_logged_in():
        session['previously_requested_page'] = request.url
        return redirect(url_for('login'))

    # Save this so if user tries to heart guide we'll redirect them back to
    # guide when they login
    elif not is_logged_in():
        session['previously_requested_page'] = '%s?hearted=1' % (request.url)

    article = read_article(stack, title, branch, status, rendered_text=False)
    if article is not None:
        return render_article_view(request, article)

    # Branches are deleted once they are accepted or rejected so show the
    # master if we can find it.
    if branch != u'master':
        flash('Unable to find %s branch, maybe those changes were accepted into the master branch below.' % (branch),
              category='info')

        # Master is default branch so don't bother including, just for cleaner
        # URL
        master_url = url_for('article_view', stack=stack, title=title)

        return redirect(master_url, code=301)

    return missing_article(request.base_url, stack=stack, title=title,
                           branch=branch)


def render_article_list_view(status):
    """
    Render list of articles with given status

    :param status: PUBLISHED, IN_REVIEW, or DRAFT
    """

    articles = models.get_available_articles(status=status)
    return render_template('review.html', articles=articles,
                            stacks=forms.STACK_OPTIONS)


def render_article_view(request_obj, article, only_visible_by_user=None):
    """
    Render article view

    :param request_obj: Request object
    :param article: Article object to render view for
    :param branch: Branch of article to read
    :param only_visible_by_user: Name of user that is allowed to view article
                                 or None to allow anyone to read it
    """

    g.review_active = True
    login = session.get('login', None)
    collaborator = session.get('collaborator', False)

    recently_saved = request.args.get('saved', 0)
    status = request.args.get('status', PUBLISHED)

    publish_statuses = ()

    if login == article.branch or article.author_name == login:
        allow_delete = True

        # Regular users cannot directly publish
        publish_statuses = (IN_REVIEW, DRAFT)
    else:
        allow_delete = False

    # Collaborators aka editors can use all statuses
    if collaborator:
        publish_statuses = STATUSES

    # Use http as canonical protocol for url to avoid having two separate
    # comment threads for an article. Disqus uses this variable to save
    # comments.
    canonical_url = request_obj.base_url.replace('https://', 'http://')

    article_identifier = article.first_commit
    redirect_url = None
    if article_identifier is None:
        # Backwards compatability for disqus comments. We didn't track the
        # first commit before version .2 and all disqus comments used the
        # slugified title for the unique id.  Disqus doesn't allow for changing
        # this so we're stuck with it if we want to maintain the comments
        # before version .2.
        article_identifier = utils.slugify(article.title)

        # Hack to save our old social shares. The po.st service doesn't handle
        # 301 redirects so need to share with the old url to keep the counts.
        redirect_url = u'%s/review/%s' % (app.config['DOMAIN'],
                                          article_identifier)
    else:
        # Use full domain for redirect_url b/c this controls the po.st social
        # sharing numbers.  We want these numbers to stick with the domain
        # we're running on so counts go with us.
        redirect_url = filters.url_for_article(article,
                                               base_url=app.config['DOMAIN'])

    # Filter out the current branch from the list of branches
    branches = [b for b in article.branches if b != article.branch]

    # Always include a link to original article if this is a branched version
    if article.branch != u'master':
        branches.append([article.author_name, u'master'])

    g.header_white = True

    user = models.find_user(article.author_name)
    if only_visible_by_user is not None and only_visible_by_user != user.login:
        return redirect(url_for('index'))

    # Don't allow comments when we're testing b/c disqus will create a
    # 'discussion' for every article and there's no way to delete them!
    allow_comments = not app.debug

    allow_set_featured = collaborator and (
                         models.allow_set_featured_article()) and (
                         article.published)

    hearted = False
    if login is not None:
        hearted = models.has_hearted(article.stacks[0], article.title, login)

    return render_template('article.html',
                           article=article,
                           hearted=hearted,
                           allow_delete=allow_delete,
                           canonical_url=canonical_url,
                           article_identifier=article_identifier,
                           branches=branches,
                           allow_set_featured=allow_set_featured,
                           user=user,
                           publish_statuses=publish_statuses,
                           redirect_url=redirect_url,
                           allow_comments=allow_comments,
                           recently_saved=recently_saved,
                           status=status)


@app.route('/partner/<path:article_path>', methods=['GET'])
@app.route('/partner/', defaults={'article_path': None}, methods=['GET'])
def partner(article_path):
    """
    URL for articles from hackhands blog -- these articles are not
    editable.
    """

    try:
        repo_path = '%s/%s' % (app.config['SECONDARY_REPO_OWNER'],
                               app.config['SECONDARY_REPO_NAME'])
    except KeyError:
        flash('No secondary guide configuration', category='error')
        return redirect(url_for('index'))

    if article_path is None:
        articles = models.get_available_articles(status=PUBLISHED,
                                                 repo_path=repo_path)
        return render_template('review.html', articles=articles)

    article = models.read_article(article_path, repo_path=repo_path)
    if article is None:
        flash('Failed reading guide', category='error')
        return redirect(url_for('index'))

    # Use http as canonical protocol for url to avoid having two separate
    # comment threads for an article. Disqus uses this variable to save
    # comments.
    canonical_url = request.base_url.replace('https://', 'http://')

    form = forms.SignupForm()

    return render_template('article.html',
                           article=article,
                           allow_edits=False,
                           canonical_url=canonical_url,
                           form=form,
                           disclaimer=True)


@app.route('/delete/', methods=['POST'])
@login_required
def delete():
    """Delete POST page"""

    user = models.find_user()
    if user is None:
        flash('Cannot delete unless logged in', category='error')
        return render_published_articles(status_code=401)

    path = request.form['path']
    branch = request.form['branch']

    article = models.read_article(path, rendered_text=False, branch=branch)

    if article is None:
        flash('Cannot find guide to delete', category='error')
        return redirect(url_for('index'))

    msg = u'Removing guide "%s"' % (article.title)
    if not models.delete_article(article, msg, user.login, user.email):
        flash('Failed removing guide', category='error')
    else:
        flash('Guide successfully deleted', category='info')

    # This article should have only been on one of these lists but trying to
    # remove it doesn't hurt so just forcefully remove it from both just in
    # case.
    for status in STATUSES:
        tasks.remove_from_listing(article.title, status, user.login,
                                  user.email, branch=article.branch)

    return redirect(url_for('index'))


@app.route('/publish/', methods=['POST'])
@login_required
def change_publish_status():
    """Publish or unpublish article via POST"""

    user = models.find_user()
    if user is None:
        flash('Cannot change publish status unless logged in', category='error')
        return render_published_articles(status_code=401)

    path = request.form['path']
    branch = request.form['branch']

    publish_status = request.form['publish_status']
    if publish_status not in STATUSES:
        flash('Invalid publish status, must be one of "%s"' % (STATUSES),
              category='error')
        return render_template('index.html')

    if branch != u'master':
        flash('Cannot change publish status on guides from branches other than master', category='error')
        return redirect(url_for('index'))

    article = models.read_article(path, rendered_text=False, branch=branch)
    if article is None:
        flash('Cannot find guide to change publish status', category='error')
        return redirect(url_for('index'))

    if article.publish_status == publish_status:
        flash('Guide already in %s publish status' % (publish_status),
              category='warning')
        return redirect(filters.url_for_article(article))

    if not user.is_collaborator:
        if article.author_name != user.login:
            flash('Only collaborators can change publish status on guides they do not start',
                  category='error')
            return redirect(url_for('index'))

        if publish_status == PUBLISHED:
            flash('Only collaborators can publish guides')
            return redirect(url_for('index'))

    curr_path = article.path

    app.logger.info(u'Requesting publish change for "%s" from "%s" to "%s"',
                    article.title, article.publish_status, publish_status)

    article.publish_status = publish_status

    author_url = filters.url_for_user(article.author_name,
                                      base_url=app.config['DOMAIN'])

    # Create this link AFTER changing the status b/c the URL will have the
    # status in it if the article is not published yet.
    article_url = filters.url_for_article(article,
                                          base_url=app.config['DOMAIN'])

    tasks.update_listing.delay(article_url,
                               article.title,
                               author_url,
                               article.author_real_name,
                               user.login,
                               user.email,
                               author_img_url=article.image_url,
                               thumbnail_url=article.thumbnail_url,
                               stacks=article.stacks,
                               branch=article.branch,
                               status=article.publish_status)

    tasks.move_article.delay(curr_path, article.path, article.title,
                             user.login, user.email,
                             new_publish_status=article.publish_status)

    return redirect(filters.url_for_article(article, saved=1))


@app.route('/subscribe/', methods=['POST'])
def subscribe():
    """Subscribe POST page"""

    form = forms.SignupForm()

    # Note this helper automatically grabs request.form
    if form.validate_on_submit():
        app.logger.debug('Adding new subscriber: %s - %s' % (form.email.data,
                                                             form.stacks.data))

        sub_id = models.add_subscriber(form.email.data, form.stacks.data)
        if not sub_id:
            flash('Failed adding to list', category='error')
        else:
            flash('Thanks for subscribing!', category='info')

        return redirect(request.referrer)
    else:
        for input_name, errors in form.errors.iteritems():
            for error in errors:
                flash('%s - %s' % (input_name, error), category='error')

        return redirect(request.referrer)


@app.route('/sync_listing/<publish_status>')
@collaborator_required
def sync_listing(publish_status):
    """Sync listing page"""

    user = models.find_user()
    if user is None:
        app.logger.error('Cannot sync listing unless logged in')
        return render_template('index.html'), 500

    if publish_status not in STATUSES:
        flash('Invalid publish status, must be one of "%s"' % (u','.join(STATUSES)),
              category='error')
        return render_template('index.html')

    tasks.synchronize_listing.delay(publish_status, user.login, user.email)

    flash('Queued up %s sync' % (publish_status), category='info')

    return redirect(url_for('index'))


@app.route('/feature/', methods=['POST'])
@collaborator_required
def set_featured_title():
    """Form POST to update featured title"""

    title = request.form['title']
    stack = request.form['stack']

    article = models.search_for_article(title, stacks=[stack], status=PUBLISHED)
    if article is None:
        flash('Cannot find published guide "%s" stack "%s"' % (title, stack),
              category='error')

        url = session.pop('previously_requested_page', None)
        if url is None:
            url = url_for('index')

        return redirect(url)

    models.set_featured_article(article)
    flash('Featured guide updated', category='info')

    return redirect(url_for('index'))


@app.context_processor
def template_globals():
    """Global variables available to all responses"""

    return {'repo_url': remote.default_repo_url(),
            'form': forms.SignupForm(), 'stack_options': forms.STACK_OPTIONS}


@app.errorhandler(500)
def internal_error(error=None):
    """Unknown error page"""

    return render_template('error.html'), 500


@app.errorhandler(404)
def not_found(error=None):
    """Not found error page"""

    return render_template('error.html'), 404


def render_published_articles(status_code=200):
    """
    Render published article listing and featured article

    This is extracted into a stand-alone function so we can render this in
    multiple locations without redirects which could hurt SEO and usability.
    """

    # FIXME: This should only fetch the most recent x number.
    articles = list(models.get_available_articles(status=PUBLISHED))

    featured_article = models.get_featured_article(articles)
    if featured_article:
        articles.remove(featured_article)

    return render_template('index.html', articles=articles,
                           featured_article=featured_article), status_code


def missing_article(requested_url=None, stack=None, title=None, branch=None):
    """
    Handle missing articles by checking if URL is should be 301 redirect or
    showing published articles in the URL is truly bad
    """

    # See if this URL is setup as a redirect due to an title change, etc.
    if requested_url is not None:
        new_url = lookup_url_redirect(requested_url)
        if new_url is not None:
            return redirect(new_url, code=301)

    app.logger.error(
        'Failed finding guide - stack: "%s", title: "%s", branch: "%s"',
        stack, title, branch)

    flash('We could not find that guide. Give these fresh ones a try.')
    return render_published_articles(status_code=404)
