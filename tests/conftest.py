import pytest
import importlib
from app import create_app, db

@pytest.fixture
def app():
    _app = create_app()
    _app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SERVER_NAME": "localhost"
    })

    with _app.app_context():
        import app.routes
        # Only reload if the 'home' route isn't registered yet
        if 'home' not in _app.view_functions:
            importlib.reload(app.routes)
        
        db.create_all()
        yield _app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def session(app):
    return db.session