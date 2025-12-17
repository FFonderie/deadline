def login(client, username="student1", password="Password123!"):
    return client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "remember_me": "y",
        },
        follow_redirects=False,
    )


def test_routes_exist_in_app(client):
    """
   Sanity check: confirm that the test client is connected to an app instance that contains the main routes.
    """
    rules = [rule.rule for rule in client.application.url_map.iter_rules()]

    assert "/" in rules
    assert "/login" in rules
    assert "/timeline" in rules


def test_home_page_renders(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Deadline" in res.data or b"deadline" in res.data


def test_protected_route_redirects_when_logged_out(client):
    """
    Edge case: if a user is not logged in and tries to visit a protected route,
    they should be sent to the login page
    """
    res = client.get("/timeline", follow_redirects=False)
    assert res.status_code in (302, 303)
    assert "/login" in res.headers.get("Location", "")


def test_login_post_redirects_on_success(client, user):
    """
    Integration test for POST /login
    """
    res = login(client)
    assert res.status_code in (302, 303)


def test_login_then_timeline_page_renders(client, user):
    """
    Logged-in user should be able to access /timeline
    """
    login(client)
    res = client.get("/timeline")
    assert res.status_code == 200
