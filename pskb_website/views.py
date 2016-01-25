"""
Main views of PSKB app
"""

from functools import wraps

from flask import redirect, url_for, session, request, render_template, flash, json, g

from . import app
from . import remote
from . import models
from . import forms


def login_required(f):
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
    articles = models.get_available_articles(published=True)

    file_details = models.read_file('welcome.md', rendered_text=True)

    text = u''
    if file_details is not None:
        text = file_details.text

    g.index_active = True
    return render_template('index.html', articles=articles, welcome_text=text,
                           stacks=forms.STACK_OPTIONS)


@app.route('/login')
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


@app.route('/faq')
def faq():
    g.faq_active = True

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
    resp = remote.github.authorized_response()
    if resp is None:
        flash('Access denied: reason=%s error=%s' % (
              request.args['error'], request.args['error_description']),
              category='error')
        return redirect(url_for('index'))

    session['github_token'] = (resp['access_token'], '')

    user = models.find_user()

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


@app.route('/user/<author_name>', methods=['GET'])
@app.route('/user/', defaults={'author_name': None})
def user_profile(author_name):
    user = models.find_user(author_name)
    if not user:
        flash('Unable to find user "%s"' % (author_name), category='error')
        return redirect(url_for('index'))

    articles = models.get_articles_for_author(user.login)

    g.profile_active = True
    return render_template('profile.html', user=user, articles=articles)


@app.route('/write/<path:article_path>/', methods=['GET'])
@app.route('/write/', defaults={'article_path': None})
@login_required
def write(article_path):
    article = None
    branch_article = False
    g.write_active = True
    selected_stack = None

    if article_path is not None:
        article = models.read_article(article_path, rendered_text=False)

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


# Special 'hidden' URL to import articles to secondary repo
@app.route('/partner/import/')
@login_required
def partner_import():
    article = None
    branch_article = False
    g.write_active = True
    secondary_repo = True

    flash('You are posting an article to the partner repository!',
          category='info')

    return render_template('editor.html', article=article,
                           branch_article=branch_article,
                           secondary_repo=secondary_repo)


@app.route('/review/<path:article_path>', methods=['GET'])
@app.route('/review/', defaults={'article_path': None}, methods=['GET'])
def review(article_path):
    g.review_active = True

    if article_path is None:
        articles = models.get_available_articles(published=False)
        return render_template('review.html', articles=articles,
                               stacks=forms.STACK_OPTIONS)

    branch = request.args.get('branch', 'master')
    article = models.read_article(article_path, branch=branch)

    if article is None:
        flash('Failed reading article', category='error')
        return redirect(url_for('index'))

    login = session.get('login', None)

    # Only allow editing if user is logged in and it's the master branch (i.e.
    # they can branch from it) or it's their own branch.
    if (login and branch == 'master') or login == branch:
        allow_edits = True
    else:
        allow_edits = False

    if login == branch or article.author_name == login:
        allow_delete = True
    else:
        allow_delete = False

    # Use http as canonical protocol for url to avoid having two separate
    # comment threads for an article. Disqus uses this variable to save
    # comments.
    canonical_url = request.base_url.replace('https://', 'http://')

    form = forms.SignupForm()

    return render_template('article.html',
                           article=article,
                           allow_edits=allow_edits,
                           allow_delete=allow_delete,
                           canonical_url=canonical_url,
                           form=form)

# URL for articles from hackhands blog -- these articles are not editable.
@app.route('/partner/<path:article_path>', methods=['GET'])
@app.route('/partner/', defaults={'article_path': None}, methods=['GET'])
def partner(article_path):
    g.review_active = True

    try:
        repo_path = '%s/%s' % (app.config['SECONDARY_REPO_OWNER'],
                               app.config['SECONDARY_REPO_NAME'])
    except KeyError:
        flash('No secondardy article configuration', category='error')
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
        message = 'Updates to %s' % (title)
    else:
        message = 'New article %s' % (title)

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

    # Successful creation
    if article:
        if repo_path is not None:
            url = url_for('partner', article_path=article.path,
                          branch=article.branch)
        else:
            url = url_for('review', article_path=article.path,
                          branch=article.branch)

        return redirect(url)

    flash('Failed creating article on github', category='error')
    return redirect(url_for('index'))


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

    return redirect(url_for('index'))


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
