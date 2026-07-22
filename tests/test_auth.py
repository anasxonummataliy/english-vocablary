from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def api_client():
    with patch("api.main.start_bot", new_callable=AsyncMock):
        with patch("api.main.bot.close", new_callable=AsyncMock):
            from api.main import active_sessions, app

            active_sessions.clear()
            with TestClient(app, raise_server_exceptions=True) as client:
                yield client
            active_sessions.clear()


def test_login_page_returns_html(api_client):
    response = api_client.get("/login")
    assert response.status_code == 200
    assert "Admin Panel" in response.text


def test_index_redirects_without_session(api_client):
    response = api_client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_with_valid_credentials(api_client):
    response = api_client.post(
        "/login",
        data={"login": "anasxon", "password": "muslim1306"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert "session_token" in response.cookies


def test_login_with_invalid_credentials(api_client):
    response = api_client.post(
        "/login",
        data={"login": "wrong", "password": "wrong"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=1" in response.headers["location"]


def test_api_users_requires_auth(api_client):
    response = api_client.get("/api/users")
    assert response.status_code == 401


def test_logout_clears_session(api_client):
    login_response = api_client.post(
        "/login",
        data={"login": "anasxon", "password": "muslim1306"},
        follow_redirects=False,
    )
    token = login_response.cookies.get("session_token")

    logout_response = api_client.get(
        "/logout",
        cookies={"session_token": token},
        follow_redirects=False,
    )
    assert logout_response.status_code == 303

    users_response = api_client.get(
        "/api/users",
        cookies={"session_token": token},
    )
    assert users_response.status_code == 401
