import os
import sys
from datetime import datetime, timedelta

import pytest
from flask import Flask

# --- Make sure project root is on sys.path so we can import app.models ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import db
from app.models import User, Assignment


# ---------- FIXTURE: minimal Flask app + in-memory DB ----------

@pytest.fixture
def app():
    """
    Create a minimal Flask app just for testing models + DB.
    We don't rely on the real app instance here.
    """
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SECRET_KEY="test-secret-key",
        WTF_CSRF_ENABLED=False,
    )

    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def session(app):
    """Shortcut to the DB session inside an app context."""
    return db.session


# ---------- TESTS (map to MVP bullets) ----------

def test_user_password_hashing_and_storage(app, session):
    """
    MVP:
    - User can create an account (username + password)
    - App stores user accounts in a local database
    """
    u = User(username="alice", email="alice@example.com")
    u.set_password("supersecret")

    session.add(u)
    session.commit()

    user = User.query.filter_by(username="alice").first()
    assert user is not None
    assert user.email == "alice@example.com"
    assert user.check_password("supersecret")
    assert not user.check_password("wrongpassword")


def test_second_user_is_independent(app, session):
    """
    Extra coverage for account creation & uniqueness.
    Still supports:
    - User accounts stored correctly & independently.
    """
    u1 = User(username="alice", email="alice@example.com")
    u1.set_password("p1")
    u2 = User(username="bob", email="bob@example.com")
    u2.set_password("p2")

    session.add_all([u1, u2])
    session.commit()

    alice = User.query.filter_by(username="alice").first()
    bob = User.query.filter_by(username="bob").first()

    assert alice is not None and bob is not None
    assert alice.id != bob.id
    assert alice.check_password("p1")
    assert bob.check_password("p2")


def test_assignment_creation_and_link_to_user(app, session):
    """
    MVP:
    - Users can add assignments in the database
    - App saves assignments in the database
    """
    user = User(username="bob", email="bob@example.com")
    user.set_password("password123")
    session.add(user)
    session.commit()

    due_time = datetime.utcnow() + timedelta(days=3)

    assignment = Assignment(
        title="HW1",
        description="Read chapter 1",
        due_date=due_time,
        user=user,
    )

    session.add(assignment)
    session.commit()

    saved = Assignment.query.filter_by(title="HW1").first()
    assert saved is not None
    assert saved.user_id == user.id
    assert saved.user.username == "bob"


def test_assignments_ordered_by_due_date(app, session):
    """
    MVP:
    - Dashboard shows all user’s assignments in chronological order
    (simulated here by ordering query on due_date).
    """
    user = User(username="charlie", email="charlie@example.com")
    user.set_password("pw")
    session.add(user)
    session.commit()

    a1 = Assignment(
        title="Soon",
        description="Due sooner",
        due_date=datetime.utcnow() + timedelta(days=1),
        user=user,
    )
    a2 = Assignment(
        title="Later",
        description="Due later",
        due_date=datetime.utcnow() + timedelta(days=5),
        user=user,
    )

    session.add_all([a1, a2])
    session.commit()

    results = (
        Assignment.query.filter_by(user_id=user.id)
        .order_by(Assignment.due_date)
        .all()
    )

    assert len(results) == 2
    assert results[0].title == "Soon"
    assert results[1].title == "Later"


def test_assignments_can_be_updated(app, session):
    """
    MVP:
    - Users can edit assignments.
    (Here we simulate editing title/description in the DB.)
    """
    user = User(username="dana", email="dana@example.com")
    user.set_password("pw")
    session.add(user)
    session.commit()

    due_time = datetime.utcnow() + timedelta(days=4)
    assignment = Assignment(
        title="Draft HW",
        description="Old description",
        due_date=due_time,
        user=user,
    )
    session.add(assignment)
    session.commit()

    # simulate editing
    assignment.title = "Final HW"
    assignment.description = "Updated description"
    session.commit()

    saved = Assignment.query.filter_by(id=assignment.id).first()
    assert saved.title == "Final HW"
    assert saved.description == "Updated description"


def test_assignments_can_be_deleted(app, session):
    """
    MVP:
    - Users can delete assignments.
    (We simulate deletion in the DB.)
    """
    user = User(username="eric", email="eric@example.com")
    user.set_password("pw")
    session.add(user)
    session.commit()

    due_time = datetime.utcnow() + timedelta(days=2)
    assignment = Assignment(
        title="To delete",
        description="Temporary",
        due_date=due_time,
        user=user,
    )
    session.add(assignment)
    session.commit()

    session.delete(assignment)
    session.commit()

    gone = Assignment.query.filter_by(title="To delete").first()
    assert gone is None


def test_urgent_assignments_within_two_days(app, session):
    """
    MVP:
    - App highlights urgent assignments (due within 2 days).
    Here we simulate 'urgent' as due_date within next 2 days.
    """
    user = User(username="fiona", email="fiona@example.com")
    user.set_password("pw")
    session.add(user)
    session.commit()

    urgent = Assignment(
        title="Urgent HW",
        description="Due soon",
        due_date=datetime.utcnow() + timedelta(days=1),
        user=user,
    )
    not_urgent = Assignment(
        title="Future HW",
        description="Due later",
        due_date=datetime.utcnow() + timedelta(days=7),
        user=user,
    )

    session.add_all([urgent, not_urgent])
    session.commit()

    now = datetime.utcnow()
    urgent_cutoff = now + timedelta(days=2)

    urgent_results = (
        Assignment.query.filter(
            Assignment.user_id == user.id,
            Assignment.due_date <= urgent_cutoff,
        )
        .order_by(Assignment.due_date)
        .all()
    )

    assert len(urgent_results) == 1
    assert urgent_results[0].title == "Urgent HW"


def test_non_urgent_assignments_excluded_from_urgent_query(app, session):
    """
    Extra coverage for urgent filter logic:
    Checks that far future assignments are not considered urgent.
    """
    user = User(username="gina", email="gina@example.com")
    user.set_password("pw")
    session.add(user)
    session.commit()

    far_assignment = Assignment(
        title="Far HW",
        description="Due in 10 days",
        due_date=datetime.utcnow() + timedelta(days=10),
        user=user,
    )
    session.add(far_assignment)
    session.commit()

    now = datetime.utcnow()
    urgent_cutoff = now + timedelta(days=2)

    urgent_results = (
        Assignment.query.filter(
            Assignment.user_id == user.id,
            Assignment.due_date <= urgent_cutoff,
        )
        .all()
    )

    assert urgent_results == []
