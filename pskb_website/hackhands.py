from flask import redirect, url_for, session, request, render_template, flash, g

from flask_oauthlib.client import OAuth

from . import app


oauth = OAuth(app)

hackhands = oauth.remote_app(
    'hackhands',
    consumer_key=app.config['HACK_HANDS_CLIENT_ID'],
    consumer_secret=app.config['HACK_HANDS_CLIENT_SECRET'],
    request_token_params={'scope': []},
    authorize_url='https://pegasus.hackhands.com/api/o/authorize/',
    request_token_url=None,
    base_url=app.config.get('HACK_HANDS_BASE_URL', 'https://hackhands.com'),
    access_token_method='POST',
    access_token_url='/api/o/token/',
)


@hackhands.tokengetter
def get_hackhands_oauth_token():
    """Read hackhands token from session"""
    return session.get('hackhands_token', None)


@app.route('/hackhands_login')
def hackhands_login():
    """hack.hands() oauth2 authorization"""
    return hackhands.authorize(callback='http://guides-dev.herokuapp.com/auth/hackhands', _external=True)


@app.route('/auth/hackhands')
def authorized_hackhands():
    """Callback for hack.hands() oauth2"""
    resp = hackhands.authorized_response()
    if resp is None:
        flash(u'It was not possible to connect your hack.hands() account.', category='error')
        return redirect(url_for('index'))

    token = resp['access_token']
    session['hackhands_token'] = token

    headers = {'Accept': 'application/json'}
    resp = hackhands.get('/api/users/self', token=(token,), headers=headers)

    if resp and resp.status == 200:
        if resp.data.get('slug', None):
            user = models.find_user()
            hackhands_data = {
                'id': resp.data['id'],
                'slug': resp.data.get('slug', None),
                'token': token,
                'is_approved_expert': resp.data.get('is_approved_expert', False),
                'is_expert': resp.data.get('is_expert', False),
            }
            flash('You connected your hack.hands() account successfully')
        else:
            flash('Sorry, but you are not an approved expert in hack.hands() yet. Try connecting your account after being approved.', category='error')
    else:
        flash(u'It was not possible to read your hack.hands() account.', category='error')
    return redirect(url_for('index'))
