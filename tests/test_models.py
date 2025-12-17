import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask

# Make sure we can import the app files
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import db
from app.models import User, Assignment


# This sets up a tiny test version of the app and an empty database
@pytest.fixture
def app():
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


# This lets us use the database in the tests
@pytest.fixture
def session(app):
    return db.session

# ---------- TESTS ----------

def test_user_password_hashing_and_storage(app, session):
    """
    Test that a user can be created,
    saved in the database, and their password works.
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
    Test that two users can be saved separately.
    """
    u1 = User(username="alice", email="alice@example.com")
    u1.set_password("p1")
    u2 = User(username="bob", email="bob@example.com")
    u2.set_password("p2")

    session.add_all([u1, u2])
    session.commit()

    alice = User.query.filter_by(username="alice").first()
    bob = User.query.filter_by(username="bob").first()

    assert alice is not None
    assert bob is not None
    assert alice.id != bob.id


def test_assignment_creation_and_link_to_user(app, session):
    """
    Test that an assignment can be created
    and is connected to the right user.
    """
    user = User(username="bob", email="bob@example.com")
    user.set_password("password123")
    session.add(user)
    session.commit()

    now = datetime.now(timezone.utc)

    assignment = Assignment(
        title="HW1",
        description="Read chapter 1",
        due_date=now + timedelta(days=3),
        user=user,
    )

    session.add(assignment)
    session.commit()

    session.expire_all()

    saved = Assignment.query.filter_by(title="HW1").first()
    assert saved is not None
    assert saved.user_id == user.id
    assert saved.user.username == "bob"

    user_from_db = session.get(User, user.id)
    assert len(user_from_db.assignments) == 1
    assert user_from_db.assignments[0].title == "HW1"


def test_assignments_ordered_by_due_date(app, session):
    """
    Test that assignments can be sorted by due date.
    """
    user = User(username="charlie", email="charlie@example.com")
    user.set_password("pw")
    session.add(user)
    session.commit()

    now = datetime.now(timezone.utc)

    a1 = Assignment(
        title="Soon",
        description="Due sooner",
        due_date=now + timedelta(days=1),
        user=user,
    )
    a2 = Assignment(
        title="Later",
        description="Due later",
        due_date=now + timedelta(days=5),
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
    Test that an assignment's title or description
    can be changed and saved.
    """
    user = User(username="dana", email="dana@example.com")
    user.set_password("pw")
    session.add(user)
    session.commit()

    due_time = datetime.now(timezone.utc) + timedelta(days=4)
    assignment = Assignment(
        title="Draft HW",
        description="Old description",
        due_date=due_time,
        user=user,
    )
    session.add(assignment)
    session.commit()

    assignment.title = "Final HW"
    assignment.description = "Updated description"
    session.commit()

    saved = Assignment.query.filter_by(id=assignment.id).first()
    assert saved.title == "Final HW"
    assert saved.description == "Updated description"


def test_assignments_can_be_deleted(app, session):
    """
    Test that an assignment can be deleted.
    """
    user = User(username="eric", email="eric@example.com")
    user.set_password("pw")
    session.add(user)
    session.commit()

    due_time = datetime.now(timezone.utc) + timedelta(days=2)
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
    Test that assignments due soon (within 2 days) can be found.
    """
    user = User(username="fiona", email="fiona@example.com")
    user.set_password("pw")
    session.add(user)
    session.commit()

    now = datetime.now(timezone.utc) 
    urgent = Assignment(
        title="Urgent HW",
        description="Due soon",
        due_date=now + timedelta(days=1), 
        user=user,
    )
    not_urgent = Assignment(
        title="Future HW",
        description="Due later",
        due_date=now + timedelta(days=7), 
        user=user,
    )

    session.add_all([urgent, not_urgent])
    session.commit()

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
    Test that assignments far in the future are NOT counted as urgent.
    """
    user = User(username="gina", email="gina@example.com")
    user.set_password("pw")
    session.add(user)
    session.commit()

    now = datetime.now(timezone.utc)

    far_assignment = Assignment(
        title="Far HW",
        description="Due in 10 days",
        due_date=now + timedelta(days=10),
        user=user,
    )
    session.add(far_assignment)
    session.commit()

    urgent_cutoff = now + timedelta(days=2)

    urgent_results = (
        Assignment.query.filter(
            Assignment.user_id == user.id,
            Assignment.due_date <= urgent_cutoff,
        )
        .all()
    )

    assert urgent_results == []

def test_assignments_creation_timestamp(app, session):
    """
    Test that the app automatically saves a created_at timestamp.
    """
    now = datetime.now(timezone.utc)
    a = Assignment(title="Timestamp Test", due_date=now + timedelta(days=1))
    session.add(a)
    session.commit()
    
    assert a.created_at is not None

def test_assignments_can_be_sorted_alphabetically(app, session):
    """
    Test that assignments can be sorted by title.
    """
    user = User(username="henry", email="h@example.com", password_hash="...")
    session.add(user)
    now = datetime.now(timezone.utc)
    
    a1 = Assignment(title="B Task", due_date=now, user=user)
    a2 = Assignment(title="A Task", due_date=now, user=user)
    session.add_all([a1, a2])
    session.commit()

    results = Assignment.query.filter_by(user_id=user.id).order_by(Assignment.title).all()
    assert results[0].title == "A Task"
    assert results[1].title == "B Task"
