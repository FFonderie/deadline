"""
The flask application package.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

'''deadline_app is the object'''
db = SQLAlchemy()
login_manager = LoginManager()

basedir = os.path.abspath(os.path.dirname(__file__))

def create_app():
    deadline_app = Flask(__name__)
    deadline_app.config.from_mapping(
        SECRET_KEY='shmortobius',
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(basedir, 'app.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    db.init_app(deadline_app)
    login_manager.init_app(deadline_app)

    # where to redirect when @login_required hits an anonymous user
    login_manager.login_view = 'login'

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with deadline_app.app_context():
        from app import routes, models
        db.create_all()

    return deadline_app
