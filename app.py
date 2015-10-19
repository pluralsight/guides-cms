"""
Main entry point of PSKB app
"""

from flask import Flask

app = Flask(__name__)


@app.route('/')
def hello():
    return 'hi'


if __name__ == '__main__':
    app.run()
