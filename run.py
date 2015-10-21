#!/usr/bin/env python

import os

os.environ['APP_SETTINGS'] = 'config.DevelopmentConfig'

from pskb_website import app

# Uncomment to see the config you're running with
#for key, value in app.config.iteritems():
    #print key, value

app.run()
