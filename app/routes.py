"""
Routes and views for the flask application.
"""

from datetime import datetime
from flask import render_template
# from app import deadline_app
from flask import current_app as deadline_app
from app.forms import LoginForm

@deadline_app.route('/')
def home():
    """renders the home page"""
    return render_template(
        'index.html',
        title='Deadline',
        year=datetime.now().year,
    )

@deadline_app.route('/login')
def login():
    """renders a login page"""
    form = LoginForm()
    return render_template(
        'login.html',
        title='Login',
        form = form
    )

@deadline_app.route('/timeline')
def timeline():
    """renders a timeline page"""
    return render_template(
        'timeline.html',
        title='TimeLine',
    )

@deadline_app.route('/classes')
def classes():
    """renders a classes page"""
    return render_template(
        'classes.html',
        title='Classes',
    )

@deadline_app.route('/deadlines')
def deadlines():
    """renders a deadlines page"""
    return render_template(
        'deadlines.html',
        title='DeadLines',
    )
