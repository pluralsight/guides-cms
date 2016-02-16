"""
Main views of PSKB app
"""

from functools import wraps
import os

from flask import redirect, url_for, session, request, render_template, flash, json, g

from . import app
from . import remote
from . import models
from . import forms
from . import tasks
from . import filters


def login_required(f):
    """
    Decorator to require login and save URL for redirecting user after login
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'github_token' not in session:
            # Save off the page so we can redirect them to what they were
            # trying to view after logging in.
            session['previously_requested_page'] = request.url

            return redirect(url_for('login'))

        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def index():
    # FIXME: This should only fetch the most recent x number.
    articles = list(models.get_available_articles(published=True))
    featured = os.environ.get('FEATURED_TITLE')
    featured_article = None

    if featured is not None:
        for ii, article in enumerate(articles):
            if article.title == featured:
                # This is only safe b/c we won't continue iterating it after we
                # find the featured one!
                featured_article = articles.pop(ii)
                break

    return render_template('index.html', articles=articles,
                           featured_article=featured_article)


@app.route('/login/')
def login():
    prev_url = session.get('previously_requested_page')

    # See if user got here from write page and highlight that tab to indicate
    # that they're trying to write and the click succeeded in getting them
    # closer to writing; specific suggestion from Ed.
    if prev_url is not None and '/write/' in prev_url:
        g.write_active = True

    return render_template('login.html')


@app.route('/gh_rate_limit')
def gh_rate_limit():
    """Debug request to view rate limit on Github"""

    return repr(remote.check_rate_limit())


@app.route('/faq/')
def faq():
    file_details = models.read_file('faq.md', rendered_text=True)
    return render_template('faq.html', details=file_details)


@app.route('/github_login')
def github_login():
    return remote.github.authorize(callback=url_for('authorized', _external=True))


@app.route('/logout')
@login_required
def logout():
    session.pop('github_token', None)
    session.pop('login', None)
    session.pop('name', None)

    return redirect(url_for('index'))


@app.route('/github/authorized')
def authorized():
    """URL for Github auth callback"""

    resp = remote.github.authorized_response()
    if resp is None:
        flash('Access denied: reason=%s error=%s' % (
              request.args['error'], request.args['error_description']),
              category='error')
        return redirect(url_for('index'))

    session['github_token'] = (resp['access_token'], '')
    session['collaborator'] = False

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

        session['collaborator'] = user.is_collaborator()

    user = models.find_user()
    if user is None:
        flash('Unable to read user from Github API')
        return redirect(url_for('index'))

    if user.name:
        session['name'] = user.name

    if user.login:
        session['login'] = user.login

        if 'name' not in session:
            session['name'] = user.login

    url = session.pop('previously_requested_page', None)
    if url is not None:
        return redirect(url)

    flash('Thanks for logging in. You can now <a href="/review/"> review unpublished tutorials</a> and <a href="/write/">write new tutorials</a>.', category='info')

    return redirect(url_for('user_profile'))


# Note this URL is directly linked to the filters.url_for_user filter.
# These must be changed together!
@app.route('/user/<author_name>', methods=['GET'])
@app.route('/user/', defaults={'author_name': None})
def user_profile(author_name):
    user = models.find_user(author_name)
    if not user:
        flash('Unable to find user "%s"' % (author_name), category='error')
        return redirect(url_for('index'))

    articles = models.get_articles_for_author(user.login)
    return render_template('profile.html', user=user, articles=articles)

@login_required
@app.route('/drafts/')
def drafts():
    g.drafts_active = True

    user = models.find_user(None)
    if not user:
        flash('Unable to find logged in user', category='error')
        return redirect(url_for('index'))

    articles = models.get_articles_for_author(user.login, published=False)
    return render_template('index.html', articles=articles)


@app.route('/write/<path:article_path>/', methods=['GET'])
@app.route('/write/', defaults={'article_path': None})
@login_required
def write(article_path):
    article = None
    branch_article = False
    selected_stack = None

    if article_path is not None:
        branch = request.args.get('branch', u'master')
        article = models.read_article(article_path, rendered_text=False,
                                      branch=branch)

        if article.sha is None:
            article.sha = ''

        # Only allowing a single stack choice now but the back-end article
        # model can handle multiple.
        if article.stacks:
            selected_stack = article.stacks[0]

        user = models.find_user(session['login'])
        if user is None:
            flash('Cannot save unless logged in', category='error')
            return render_template('index.html'), 404

        if user.login != article.author_name:
            branch_article = True

    return render_template('editor.html', article=article,
                           branch_article=branch_article,
                           stacks=forms.STACK_OPTIONS,
                           selected_stack=selected_stack)


@app.route('/partner/import/')
@login_required
def partner_import():
    """Special 'hidden' URL to import articles to secondary repo"""

    article = None
    branch_article = False
    secondary_repo = True

    flash('You are posting an article to the partner repository!',
          category='info')

    return render_template('editor.html', article=article,
                           branch_article=branch_article,
                           secondary_repo=secondary_repo)


# Note this URL is directly linked to the filters.url_for_article filter.
# These must be changed together!
@app.route('/review/<path:article_path>', methods=['GET'])
@app.route('/review/', defaults={'article_path': None}, methods=['GET'])
def review(article_path):
    g.review_active = True

    if article_path is None:
        articles = models.get_available_articles(published=False)
        return render_template('review.html', articles=articles,
                               stacks=forms.STACK_OPTIONS)

    branch = request.args.get('branch', u'master')
    article = models.read_article(article_path, branch=branch)

    if article is None:
        flash('Failed reading article', category='error')
        return redirect(url_for('index'))

    login = session.get('login', None)
    collaborator = session.get('collaborator', False)

    # Always allow editing to help illustrate to viewers they can contribute.
    # We'll redirect them to login if they aren't already logged in.
    allow_edits = True

    if login == branch or article.author_name == login:
        allow_delete = True
    else:
        allow_delete = False

    # Use http as canonical protocol for url to avoid having two separate
    # comment threads for an article. Disqus uses this variable to save
    # comments.
    canonical_url = request.base_url.replace('https://', 'http://')

    # Filter out the current branch from the list of branches
    branches = [b for b in article.branches if b != branch]

    # Always include a link to original article if this is a branched version
    if branch != u'master':
        branches.append(u'master')

    g.header_white = True

    return render_template('article.html',
                           article=article,
                           allow_edits=allow_edits,
                           allow_delete=allow_delete,
                           canonical_url=canonical_url,
                           branches=branches,
                           visible_branch=branch,
                           collaborator=collaborator)

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
        flash('No secondary article configuration', category='error')
        return redirect(url_for('index'))

    if article_path is None:
        articles = models.get_available_articles(published=True,
                                                 repo_path=repo_path)
        return render_template('review.html', articles=articles)

    article = models.read_article(article_path, repo_path=repo_path)
    if article is None:
        flash('Failed reading article', category='error')
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


@app.route('/save/', methods=['POST'])
@login_required
def save():
    user = models.find_user(session['login'])
    if user is None:
        flash('Cannot save unless logged in', category='error')
        return render_template('index.html'), 404

    # Data is stored in form with input named content which holds json. The
    # json has the 'real' data in the 'content' key.
    content = json.loads(request.form['content'])['content']

    path = request.form['path']
    title = request.form['title']
    sha = request.form['sha']

    # Form only accepts 1 stack right now but we can handle multiple on the
    # back-end.
    if not request.form['stacks']:
        stacks = None
    else:
        stacks = request.form.getlist('stacks')

    if path:
        message = 'Updates to "%s"' % (title)
    else:
        message = 'New article, "%s"' % (title)

    # Hidden option for admin to save articles to our other repo that's not
    # editable
    repo_path = None
    if request.form.get('secondary_repo', None) is not None:
        repo_path = '%s/%s' % (app.config['SECONDARY_REPO_OWNER'],
                               app.config['SECONDARY_REPO_NAME'])

    # Hidden option for admin to save articles to our other repo that's not
    # editable
    repo_path = None
    if request.form.get('secondary_repo', None) is not None:
        repo_path = '%s/%s' % (app.config['SECONDARY_REPO_OWNER'],
                               app.config['SECONDARY_REPO_NAME'])

    article = models.branch_or_save_article(title, path, message, content,
                                            user.login, user.email, sha,
                                            user.avatar_url,
                                            stacks=stacks,
                                            repo_path=repo_path,
                                            author_real_name=user.name)

    if not article:
        flash('Failed creating article on github', category='error')
        return redirect(url_for('index'))

    if repo_path is not None:
        return redirect(url_for('partner', article_path=article.path,
                                branch=article.branch))

    # Update file listing but only if the article is unpublished. Publishing an
    # article and updating that listing is a separate action.
    if not article.published:
        # Use these filter wrappers so we get absolute URL instead of relative
        # URL to this specific site.
        url = filters.url_for_article(article)
        author_url = filters.url_for_user(article.author_name)

        tasks.update_listing(url, article.title, author_url,
                             article.author_real_name, user.login, user.email,
                             stacks=article.stacks, branch=article.branch,
                             published=False)

    return redirect(url_for('review', article_path=article.path,
                            branch=article.branch))


@app.route('/delete/', methods=['POST'])
@login_required
def delete():
    user = models.find_user(session['login'])
    if user is None:
        flash('Cannot delete unless logged in', category='error')
        return render_template('index.html'), 404

    path = request.form['path']
    branch = request.form['branch']

    article = models.read_article(path, rendered_text=False, branch=branch)

    if article is None:
        flash('Cannot find article to delete', category='error')
        return redirect(url_for('index'))

    if not models.delete_article(article, 'Removing article', user.login,
                                 user.email):
        flash('Failed removing article', category='error')
    else:
        flash('Article successfully deleted', category='info')

    # This article should have only been on one of these lists but trying to
    # remove it doesn't hurt so just forcefully remove it from both just in
    # case.
    published = False
    tasks.remove_from_listing(article.title, published, user.login, user.email,
                              branch=article.branch)

    published = not published
    tasks.remove_from_listing(article.title, published, user.login, user.email,
                              branch=article.branch)

    return redirect(url_for('index'))


@app.route('/publish/', methods=['POST'])
@login_required
def change_publish_status():
    """Publish or unpublish article via POST"""

    user = models.find_user(session['login'])
    if user is None:
        flash('Cannot change publish status unless logged in', category='error')
        return render_template('index.html'), 404

    if not user.is_collaborator():
        flash('Only official repository collaborators can change publish status on articles', category='error')
        return redirect('index.html')

    path = request.form['path']
    branch = request.form['branch']

    # Convert to int first b/c '0' will be True by bool()!
    publish_status = bool(int(request.form['publish_status']))

    if branch != u'master':
        flash('Cannot change publish status on articles from branches other than master', category='error')
        return redirect(url_for('review', article_path=path, branch=branch))

    article = models.read_article(path, rendered_text=False, branch=branch)
    if article is None:
        flash('Cannot find article to change publish status', category='error')
        return redirect(url_for('index'))

    author_url = url_for('user_profile', author_name=article.author_name)
    article_url = url_for('review', article_path=path)

    article.published = publish_status
    if not models.save_article_meta_data(article, user.login, user.email):
        flash('Failed updating article publish status', category='error')
        return redirect(article_url)

    tasks.update_listing(article_url, article.title, author_url,
                         article.author_name, user.login, user.email,
                         stacks=article.stacks, branch=article.branch,
                         published=publish_status)

    publishing = 'publish' if publish_status else 'unpublish'
    msg = 'The article has been queued up to %s. Please <a href="mailto: prateek-gupta@pluralsight.com">contact us</a> if the change does not show up within a few minutes.' % (publishing)

    flash(msg, category='info')

    return redirect(article_url)


@app.route('/subscribe/', methods=['POST'])
def subscribe():
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


@app.route('/img_upload/', methods=['POST'])
@login_required
def img_upload():
    user = models.find_user(session['login'])
    if user is None:
        app.logger.error('Cannot upload image unless logged in')
        return Response(response='', status=500, mimetype='application/json')

    file_ = request.files['file']

    try:
        ext = file_.filename.split(os.extsep)[1]
    except IndexError:
        ext = ''

    # Always save images to master branch because image uploads might happen
    # before the article is saved so don't know the article name or branch to
    # save alongside.
    url = models.save_image(file_.stream, ext, 'Saving new article image',
                            user.login, user.email, branch='master')

    if url is None:
        app.logger.error('Failed uploading image')
        return Response(response='', status=500, mimetype='application/json')

    return Response(response=json.dumps(url), status=200,
                    mimetype='application/json')


@app.route('/sync_listing/')
def sync_listing():
    user = models.find_user('durden')
    if user is None:
        app.logger.error('Cannot sync listing unless logged in')
        return render_template('index.html'), 500

    if not user.is_collaborator():
        app.logger.error('Cannot sync listing unless collaborator')
        return render_template('index.html'), 500

    published = bool(int(request.args.get('published', 1)))
    tasks.synchronize_listing.delay(published, user.login, user.email)

    flash('Queued up %s sync' % ('published' if published else 'unpublished'),
          category='info')

    return redirect(url_for('index'))


@app.context_processor
def template_globals():
    return {'repo_url': remote.default_repo_url(),
            'form': forms.SignupForm(), 'stack_options': forms.STACK_OPTIONS}


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html'), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html'), 404
