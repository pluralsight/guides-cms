"""
Main entry point of PSKB app
"""

import os

from flask import Flask

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])


@app.route('/')
def hello():
    return 'hi'


if __name__ == '__main__':
    print os.environ['APP_SETTINGS']
    app.run()
