"""
Routes and views for the flask application.
"""

from datetime import datetime
from flask import render_template
from app import deadline_app

@deadline_app.route('/')
@deadline_app.route('/home')
def home():
    """Renders the home page."""
    return render_template(
        'index.html',
        title='Home Page',
        year=datetime.now().year,
    )
