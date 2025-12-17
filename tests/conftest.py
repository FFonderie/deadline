import pytest
from app import create_app, db
from app.models import User

# Create ONE app instance for the whole test session
flask_app = create_app()
flask_app.config.update(
    TESTING=True,
    WTF_CSRF_ENABLED=False,
    SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    SECRET_KEY="test-secret",
)

@pytest.fixture
def app():
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def user(app):
    with app.app_context():
        u = User(username="student1", email="student1@test.com")
        u.set_password("Password123!")
        db.session.add(u)
        db.session.commit()
        return u


