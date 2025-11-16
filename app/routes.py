"""
Routes and views for the flask application.
"""

from datetime import datetime
from flask import render_template
# from app import deadline_app
from flask import current_app as deadline_app
from app.forms import LoginForm

@deadline_app.route('/')
@deadline_app.route('/home')
def home():
    """renders the home page"""
    return render_template(
        'index.html',
        title='Deadline',
        year=datetime.now().year,
    )
@deadline_app.route('/login')
def login():
    """renders a login page, placeholder for now"""
    form = LoginForm()
    return render_template(
        'login.html',
        title='DeadLine',
        form = form
    )
