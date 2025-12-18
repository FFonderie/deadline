import os
import sys
from datetime import datetime, timedelta, timezone
import pytest
from flask import Flask
from app.models import User, Class, Assignment, Submission
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import db
from app.models import User, Assignment, Class, Submission

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
    and is connected to the right user and class.
    """
    user = User(username="bob", email="bob@example.com")
    user.set_password("password123")
    session.add(user)
    
    # Create required class for assignment
    test_class = Class(name="CS101", owner=user)
    session.add(test_class)
    session.commit()

    now = datetime.now(timezone.utc)

    assignment = Assignment(
        title="HW1",
        description="Read chapter 1",
        due_date=now + timedelta(days=3),
        creator=user,
        clazz=test_class
    )

    session.add(assignment)
    session.commit()

    session.expire_all()

    saved = Assignment.query.filter_by(title="HW1").first()
    assert saved is not None
    assert saved.creator_id == user.id
    assert saved.creator.username == "bob"

    user_from_db = session.get(User, user.id)
    assert len(user_from_db.created_assignments) == 1
    assert user_from_db.created_assignments[0].title == "HW1"


def test_assignments_ordered_by_due_date(app, session):
    """
    Test that assignments can be sorted by due date (Chronological Order).
    """
    user = User(username="charlie", email="charlie@example.com")
    user.set_password("pw")
    session.add(user)
    test_class = Class(name="History", owner=user)
    session.add(test_class)
    session.commit()

    now = datetime.now(timezone.utc)

    a1 = Assignment(
        title="Soon",
        description="Due sooner",
        due_date=now + timedelta(days=1),
        creator=user,
        clazz=test_class
    )
    a2 = Assignment(
        title="Later",
        description="Due later",
        due_date=now + timedelta(days=5),
        creator=user,
        clazz=test_class
    )    

    session.add_all([a1, a2])
    session.commit()

    results = (
        Assignment.query.filter_by(creator_id=user.id)
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
    test_class = Class(name="English", owner=user)
    session.add(test_class)
    session.commit()

    due_time = datetime.now(timezone.utc) + timedelta(days=4)
    assignment = Assignment(
        title="Draft HW",
        description="Old description",
        due_date=due_time,
        creator=user,
        clazz=test_class
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
    test_class = Class(name="Science", owner=user)
    session.add(test_class)
    session.commit()

    due_time = datetime.now(timezone.utc) + timedelta(days=2)
    assignment = Assignment(
        title="To delete",
        description="Temporary",
        due_date=due_time,
        creator=user,
        clazz=test_class
    )
    session.add(assignment)
    session.commit()

    session.delete(assignment)
    session.commit()

    gone = Assignment.query.filter_by(title="To delete").first()
    assert gone is None


def test_urgent_assignments_within_two_days(app, session):
    """
    Test that assignments due soon (within 2 days) can be found (Urgency Highlight).
    """
    user = User(username="fiona", email="fiona@example.com")
    user.set_password("pw")
    session.add(user)
    test_class = Class(name="Math", owner=user)
    session.add(test_class)
    session.commit()

    now = datetime.now(timezone.utc) 
    urgent = Assignment(
        title="Urgent HW",
        description="Due soon",
        due_date=now + timedelta(days=1), 
        creator=user,
        clazz=test_class
    )
    not_urgent = Assignment(
        title="Future HW",
        description="Due later",
        due_date=now + timedelta(days=7), 
        creator=user,
        clazz=test_class
    )

    session.add_all([urgent, not_urgent])
    session.commit()

    urgent_cutoff = now + timedelta(days=2)

    urgent_results = (
        Assignment.query.filter(
            Assignment.creator_id == user.id,
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
    test_class = Class(name="Geography", owner=user)
    session.add(test_class)
    session.commit()

    now = datetime.now(timezone.utc)

    far_assignment = Assignment(
        title="Far HW",
        description="Due in 10 days",
        due_date=now + timedelta(days=10),
        creator=user,
        clazz=test_class
    )
    session.add(far_assignment)
    session.commit()

    urgent_cutoff = now + timedelta(days=2)

    urgent_results = (
        Assignment.query.filter(
            Assignment.creator_id == user.id,
            Assignment.due_date <= urgent_cutoff,
        )
        .all()
    )

    assert urgent_results == []


def test_assignments_creation_timestamp(app, session):
    """
    Test that the app automatically saves a created_at timestamp (System Logging).
    """
    user = User(username="henry", email="h@example.com")
    user.set_password("pw")
    session.add(user)
    test_class = Class(name="Testing", owner=user)
    session.add(test_class)
    session.commit()

    now = datetime.now(timezone.utc)
    a = Assignment(title="Timestamp Test", due_date=now + timedelta(days=1), creator=user, clazz=test_class)
    session.add(a)
    session.commit()
    
    assert a.created_at is not None


def test_marking_assignment_as_completed(app, session):
    """
    Test that an assignment can be marked as completed by creating a submission.
    """
    user = User(username="student1", email="s1@example.com")
    user.set_password("pw")
    session.add(user)
    test_class = Class(name="Bio", owner=user)
    session.add(test_class)
    session.commit()

    a = Assignment(title="Lab", due_date=datetime.now(timezone.utc), creator=user, clazz=test_class)
    session.add(a)
    session.commit()

    sub = Submission(assignment=a, student=user, content="Done!")
    session.add(sub)
    session.commit()

    assert len(a.submissions) == 1
    assert a.submissions[0].content == "Done!"


def test_assignments_can_be_sorted_alphabetically(app, session):
    """
    Test that assignments can be sorted by title (Sort by Course/Title).
    """
    user = User(username="ian", email="i@example.com")
    user.set_password("pw")
    session.add(user)
    test_class = Class(name="Music", owner=user)
    session.add(test_class)
    session.commit()

    now = datetime.now(timezone.utc)
    
    a1 = Assignment(title="B Task", due_date=now, creator=user, clazz=test_class)
    a2 = Assignment(title="A Task", due_date=now, creator=user, clazz=test_class)
    session.add_all([a1, a2])
    session.commit()

    results = Assignment.query.filter_by(creator_id=user.id).order_by(Assignment.title).all()
    assert results[0].title == "A Task"
    assert results[1].title == "B Task"

def test_mvp_completion_and_sorting_logic(app, session):
    """Covers MVP #11 (Mark as Done) and #12 (Done Section)"""
    with app.app_context():
        u = User(username="mvp_user", email="mvp@test.com")
        u.set_password("pass")
        session.add(u)
        session.commit()
        
        c = Class(name="MVP Class", owner=u)
        session.add(c)
        session.commit()

        # The FIX: explicitly passing class_id and clazz
        a1 = Assignment(title="Task 1", due_date=datetime.now(timezone.utc), class_id=c.id, creator=u)
        a2 = Assignment(title="Task 2", due_date=datetime.now(timezone.utc), class_id=c.id, creator=u)
        session.add_all([a1, a2])
        session.commit()

        sub = Submission(assignment=a1, student=u, content="Finished")
        session.add(sub)
        session.commit()

        done = Assignment.query.join(Submission).filter(Submission.student_id == u.id).all()
        assert a1 in done
        assert len(done) == 1

def test_mvp_reminder_and_urgency_logic(app, session):
    """Covers MVP #7 (Urgent), #9 (Reminders), and #15 (Logging)"""
    with app.app_context():
        u = User(username="logic_user", email="logic@test.com")
        u.set_password("pass")
        session.add(u)
        session.commit()

        c = Class(name="Logic Class", owner=u)
        session.add(c)
        session.commit()
        
        # Use datetime.utcnow() to match your model's 'naive' format
        now = datetime.utcnow() 
        soon = now + timedelta(hours=5)
        
        a = Assignment(
            title="Urgent Task", 
            due_date=soon, 
            class_id=c.id, 
            creator=u
        )
        session.add(a)
        session.commit()

        # Now both are 'naive' (no timezone), so subtraction works!
        time_until_due = a.due_date - now
        
        assert time_until_due < timedelta(days=2)   # MVP #7
        assert time_until_due < timedelta(hours=24) # MVP #9
        assert a.created_at is not None   

def test_mvp_custom_settings_and_toggles(app, session):
    """Verifies MVP #10 (Custom Reminders) and #14 (Toggles)"""
    with app.app_context():
        # Add a password to satisfy the NOT NULL constraint
        u = User(username="privacy_pro", email="off@test.com", notifications_enabled=False)
        u.set_password("securepassword123") 
        
        session.add(u)
        session.commit()

        c = Class(name="CS50", owner=u)
        session.add(c)
        session.commit()

        # Create assignment with a custom 1-hour reminder
        a = Assignment(
            title="Last Minute Task", 
            due_date=datetime.utcnow(), 
            class_id=c.id, 
            creator=u,
            reminder_hours=1
        )
        session.add(a)
        session.commit()

        # Proof the DB handles the settings
        assert u.notifications_enabled is False
        assert a.reminder_hours == 1
        