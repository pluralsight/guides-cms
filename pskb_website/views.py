"""
Main views of PSKB app
"""

import os

from . import app
from .models import Article


@app.route('/')
def hello():
    return 'hi'
