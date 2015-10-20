#!/usr/bin/env python

import os


if 'APP_SETTINGS' not in os.environ:
    os.environ['APP_SETTINGS'] = 'pskb_website.config.DevelopmentConfig'

if 'DATABASE_URL' not in os.environ:
    os.environ['DATABASE_URL'] = 'postgresql://localhost/pskb_dev'


from pskb_website import app
app.run()
