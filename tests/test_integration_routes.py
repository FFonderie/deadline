import pytest
from app.models import User, Class, Assignment
from datetime import datetime, timedelta

def test_home_page_renders(client):
    res = client.get("/")
    assert res.status_code == 200

def test_login_logout_flow(client, session, app):
    with app.app_context():
        u = User(username="testuser", email="test@test.com")
        u.set_password("Password123!")
        session.add(u)
        session.commit()

    res = client.post("/login", data={
        "username": "testuser",
        "password": "Password123!"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Logout" in res.data 

    res = client.get("/logout", follow_redirects=True)
    assert res.status_code == 200

def test_instructor_page_access_edge_case(client, session, app):
    with app.app_context():
        teacher = User(username="teacher", email="t@t.com")
        teacher.set_password("pass")
        student = User(username="student", email="s@t.com")
        student.set_password("pass")
        session.add_all([teacher, student])
        session.commit()

        c = Class(name="CS50", owner=teacher)
        session.add(c)
        session.commit()
        # FIX: Save the ID here so we don't need the 'c' object later
        c_id = c.id

    client.post("/login", data={"username": "student", "password": "pass"})
    # Use the saved c_id
    res = client.get(f"/classes/{c_id}/assignments/new")
    assert res.status_code == 403

def test_timeline_renders_with_data(client, session, app):
    with app.app_context():
        u = User(username="user1", email="u1@test.com")
        u.set_password("pass")
        session.add(u)
        c = Class(name="Bio101", owner=u)
        c.members.append(u)
        session.add(c)
        session.commit()
        a = Assignment(title="Bio Lab", due_date=datetime.now() + timedelta(days=1), creator=u, clazz=c)
        session.add(a)
        session.commit()

    client.post("/login", data={"username": "user1", "password": "pass"})
    res = client.get("/timeline")
    assert res.status_code == 200
    assert b"Bio Lab" in res.data
