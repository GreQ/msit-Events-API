"""Unit tests for the models and API tests for the routes.

Each test gets a fresh app backed by an in-memory SQLite database.
Run with:  .venv/Scripts/python.exe -m pytest
"""
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

import config

config.Config.SQLALCHEMY_DATABASE_URI = "sqlite://"  # must be set before create_app()

from app import create_app  # noqa: E402
from models import RSVP, Event, User, db  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures and helpers
# --------------------------------------------------------------------------- #

@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, username="alice", password="secret123"):
    return client.post("/api/auth/register", json={"username": username, "password": password})


def login(client, username="alice", password="secret123"):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def auth_header(client, username, password="secret123"):
    register(client, username, password)
    token = login(client, username, password).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client):
    # The first registered user becomes admin.
    return auth_header(client, "admin")


@pytest.fixture
def user_headers(client, admin_headers):
    # Depends on admin_headers so this user is never the first (admin) one.
    return auth_header(client, "bob")


def make_event(client, headers, **overrides):
    payload = {"title": "Meetup", "date": "2030-01-15T18:00:00", **overrides}
    resp = client.post("/api/events", json=payload, headers=headers)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def make_user(username="u", password="pw"):
    user = User(username=username)
    user.set_password(password)
    return user


# --------------------------------------------------------------------------- #
# Model unit tests
# --------------------------------------------------------------------------- #

class TestUserModel:
    def test_password_is_hashed_and_verifiable(self, app):
        user = make_user(password="pw")
        assert user.password_hash != "pw"
        assert user.check_password("pw")
        assert not user.check_password("wrong")

    def test_defaults_and_to_dict(self, app):
        user = make_user()
        db.session.add(user)
        db.session.commit()

        data = user.to_dict()
        assert data["id"] == user.id
        assert data["username"] == "u"
        assert data["is_admin"] is False
        assert data["created_at"] is not None
        assert "password_hash" not in data

    def test_username_is_unique(self, app):
        db.session.add_all([make_user("dup"), make_user("dup")])
        with pytest.raises(IntegrityError):
            db.session.commit()


class TestEventModel:
    def test_defaults(self, app):
        event = Event(title="E", date=datetime(2030, 1, 1, 12, 0))
        db.session.add(event)
        db.session.commit()
        assert event.is_public is True
        assert event.requires_admin is False
        assert event.capacity is None
        assert event.created_at is not None

    def test_to_dict_counts_and_attendees(self, app):
        user = make_user()
        event = Event(title="E", date=datetime(2030, 1, 1, 12, 0), creator=user)
        db.session.add_all([
            event,
            RSVP(event=event, user=user, attending=True),
            RSVP(event=event, user=None, attending=True),   # anonymous
            RSVP(event=event, user=None, attending=False),  # not going
        ])
        db.session.commit()

        data = event.to_dict()
        assert data["date"] == "2030-01-01T12:00:00"
        assert data["created_by"] == user.id
        assert data["rsvp_count"] == 3
        # Only attending, non-anonymous RSVPs are listed as attendees.
        assert data["attendees"] == [user.id]

    def test_deleting_event_cascades_to_rsvps(self, app):
        event = Event(title="E", date=datetime(2030, 1, 1))
        event.rsvps.append(RSVP())
        db.session.add(event)
        db.session.commit()

        db.session.delete(event)
        db.session.commit()
        assert db.session.scalar(db.select(db.func.count()).select_from(RSVP)) == 0

    def test_relationships_are_bidirectional(self, app):
        user = make_user()
        event = Event(title="E", date=datetime(2030, 1, 1), creator=user)
        rsvp = RSVP(event=event, user=user)
        db.session.add_all([user, event, rsvp])
        db.session.commit()
        assert user.events == [event]
        assert user.rsvps == [rsvp]
        assert event.rsvps == [rsvp]


class TestRSVPModel:
    def test_defaults_and_to_dict(self, app):
        event = Event(title="E", date=datetime(2030, 1, 1))
        rsvp = RSVP(event=event)
        db.session.add(rsvp)
        db.session.commit()

        data = rsvp.to_dict()
        assert data["attending"] is True
        assert data["event_id"] == event.id
        assert data["user_id"] is None
        assert data["created_at"] is not None


# --------------------------------------------------------------------------- #
# General endpoints
# --------------------------------------------------------------------------- #

class TestGeneralRoutes:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Evently API"

    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "healthy"}

    def test_openapi_spec_is_served(self, client):
        resp = client.get("/api/openapi.yaml")
        assert resp.status_code == 200
        assert b"openapi" in resp.data


# --------------------------------------------------------------------------- #
# Auth routes
# --------------------------------------------------------------------------- #

class TestAuthRoutes:
    def test_first_user_is_admin_second_is_not(self, client):
        first = register(client, "first")
        second = register(client, "second")
        assert first.status_code == 201
        assert first.get_json()["user"]["is_admin"] is True
        assert second.status_code == 201
        assert second.get_json()["user"]["is_admin"] is False

    @pytest.mark.parametrize("payload", [
        {},
        {"username": "x"},
        {"password": "x"},
        {"username": "", "password": "x"},
    ])
    def test_register_requires_username_and_password(self, client, payload):
        resp = client.post("/api/auth/register", json=payload)
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_register_duplicate_username(self, client):
        register(client, "alice")
        resp = register(client, "alice")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Username already exists"

    def test_login_success_returns_token(self, client):
        register(client, "alice")
        resp = login(client, "alice")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["access_token"]
        assert body["user"]["username"] == "alice"

    def test_login_wrong_password(self, client):
        register(client, "alice")
        resp = login(client, "alice", "nope")
        assert resp.status_code == 401
        assert resp.get_json()["error"] == "Invalid credentials"

    def test_login_unknown_user(self, client):
        assert login(client, "ghost").status_code == 401

    def test_login_requires_fields(self, client):
        assert client.post("/api/auth/login", json={}).status_code == 400


# --------------------------------------------------------------------------- #
# Event routes
# --------------------------------------------------------------------------- #

class TestEventRoutes:
    def test_list_events_empty(self, client):
        resp = client.get("/api/events")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_create_event(self, client, user_headers):
        event = make_event(client, user_headers, description="desc", location="Room 1",
                           capacity=10, is_public=False, requires_admin=True)
        assert event["title"] == "Meetup"
        assert event["description"] == "desc"
        assert event["location"] == "Room 1"
        assert event["date"] == "2030-01-15T18:00:00"
        assert event["capacity"] == 10
        assert event["is_public"] is False
        assert event["requires_admin"] is True
        assert event["rsvp_count"] == 0

    def test_create_event_requires_auth(self, client):
        resp = client.post("/api/events", json={"title": "x", "date": "2030-01-01T00:00:00"})
        assert resp.status_code == 401

    @pytest.mark.parametrize("payload, message", [
        ({"date": "2030-01-01T00:00:00"}, "Title is required"),
        ({"title": "x"}, "Date is required"),
    ])
    def test_create_event_missing_fields(self, client, user_headers, payload, message):
        resp = client.post("/api/events", json=payload, headers=user_headers)
        assert resp.status_code == 400
        assert resp.get_json()["error"] == message

    @pytest.mark.parametrize("bad_date", ["not-a-date", "2030-13-01", 12345])
    def test_create_event_invalid_date(self, client, user_headers, bad_date):
        resp = client.post("/api/events", json={"title": "x", "date": bad_date}, headers=user_headers)
        assert resp.status_code == 400
        assert "Invalid date format" in resp.get_json()["error"]

    def test_create_event_accepts_z_suffix(self, client, user_headers):
        event = make_event(client, user_headers, date="2030-01-15T18:00:00Z")
        assert event["date"].startswith("2030-01-15T18:00:00")

    def test_get_and_list_events(self, client, user_headers):
        created = make_event(client, user_headers)
        resp = client.get(f"/api/events/{created['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["id"] == created["id"]
        assert len(client.get("/api/events").get_json()) == 1

    def test_get_missing_event_404(self, client):
        assert client.get("/api/events/999").status_code == 404


# --------------------------------------------------------------------------- #
# RSVP routes
# --------------------------------------------------------------------------- #

class TestRSVPRoutes:
    def test_anonymous_rsvp_to_public_event(self, client, user_headers):
        event = make_event(client, user_headers)
        resp = client.post(f"/api/rsvps/event/{event['id']}", json={})
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["user_id"] is None
        assert body["attending"] is True

    def test_private_event_requires_auth(self, client, user_headers):
        event = make_event(client, user_headers, is_public=False)
        url = f"/api/rsvps/event/{event['id']}"
        assert client.post(url, json={}).status_code == 401
        assert client.post(url, json={}, headers=user_headers).status_code == 201

    def test_admin_event_access(self, client, admin_headers, user_headers):
        event = make_event(client, admin_headers, requires_admin=True)
        url = f"/api/rsvps/event/{event['id']}"
        assert client.post(url, json={}).status_code == 401
        assert client.post(url, json={}, headers=user_headers).status_code == 403
        assert client.post(url, json={}, headers=admin_headers).status_code == 201

    def test_rsvp_updates_existing(self, client, user_headers):
        event = make_event(client, user_headers)
        url = f"/api/rsvps/event/{event['id']}"
        first = client.post(url, json={"attending": True}, headers=user_headers)
        second = client.post(url, json={"attending": False}, headers=user_headers)
        assert first.status_code == 201
        assert second.status_code == 200
        assert second.get_json()["id"] == first.get_json()["id"]
        assert second.get_json()["attending"] is False

    def test_capacity_is_enforced(self, client, user_headers):
        event = make_event(client, user_headers, capacity=1)
        url = f"/api/rsvps/event/{event['id']}"
        assert client.post(url, json={}).status_code == 201
        resp = client.post(url, json={})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Event is at full capacity"

    def test_not_attending_rsvps_do_not_use_capacity(self, client, user_headers):
        event = make_event(client, user_headers, capacity=1)
        url = f"/api/rsvps/event/{event['id']}"
        assert client.post(url, json={"attending": False}).status_code == 201
        assert client.post(url, json={}).status_code == 201

    @pytest.mark.xfail(strict=True, reason="Known bug: capacity check runs before the "
                                           "existing-RSVP lookup (see CLAUDE.md)")
    def test_user_can_change_rsvp_when_event_full(self, client, user_headers):
        event = make_event(client, user_headers, capacity=1)
        url = f"/api/rsvps/event/{event['id']}"
        client.post(url, json={}, headers=user_headers)
        resp = client.post(url, json={"attending": False}, headers=user_headers)
        assert resp.status_code == 200

    @pytest.mark.xfail(strict=True, reason="Bug: openapi.yaml says the RSVP body is optional, "
                                           "but request.get_json() returns 415 without one")
    def test_rsvp_without_body(self, client, user_headers):
        event = make_event(client, user_headers)
        resp = client.post(f"/api/rsvps/event/{event['id']}")
        assert resp.status_code == 201

    def test_rsvp_missing_event_404(self, client):
        assert client.post("/api/rsvps/event/999").status_code == 404
        assert client.get("/api/rsvps/event/999").status_code == 404

    def test_get_rsvps_stats(self, client, user_headers):
        event = make_event(client, user_headers)
        url = f"/api/rsvps/event/{event['id']}"
        client.post(url, json={}, headers=user_headers)
        client.post(url, json={})
        client.post(url, json={"attending": False})

        resp = client.get(url)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["event"]["id"] == event["id"]
        assert len(body["rsvps"]) == 3
        assert body["stats"] == {"attending": 2, "not_attending": 1, "total": 3}
