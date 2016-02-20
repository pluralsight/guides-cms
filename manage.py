#!/usr/bin/env python

from flask.ext.script import Manager
import os

if 'APP_SETTINGS' not in os.environ:
    os.environ['APP_SETTINGS'] = 'config.DevelopmentConfig'

from pskb_website import app

manager = Manager(app)
manager.run()
