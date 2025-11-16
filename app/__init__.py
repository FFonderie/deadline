"""
The flask application package.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

'''deadline_app is the object'''
db = SQLAlchemy()

basedir = os.path.abspath(os.path.dirname(__file__))

def create_app():
    deadline_app = Flask(__name__)
    deadline_app.config.from_mapping(
        SECRET_KEY = 'shmortobius',

        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS = False
    )

    db.init_app(deadline_app)
    with deadline_app.app_context():
        from app import routes, models
        db.create_all()

    return deadline_app
