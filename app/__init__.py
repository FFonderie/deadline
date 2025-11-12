"""
The flask application package.
"""

from flask import Flask
deadline_app = Flask(__name__)

import app.views
