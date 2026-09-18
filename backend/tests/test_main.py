from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_example_endpoint_returns_expected_message() -> None:
    response = client.get("/api/example")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello from the API"}


def test_root_serves_static_page() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Project Management MVP" in response.text


def test_valid_login_creates_a_session() -> None:
    response = client.post(
        "/api/auth/login", json={"username": "user", "password": "password"}
    )

    assert response.status_code == 204
    assert client.get("/api/auth/session").json() == {
        "authenticated": True,
        "username": "user",
    }


def test_invalid_login_is_rejected() -> None:
    response = client.post(
        "/api/auth/login", json={"username": "user", "password": "incorrect"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."


def test_logout_clears_the_session() -> None:
    client.post("/api/auth/login", json={"username": "user", "password": "password"})

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert client.get("/api/auth/session").json() == {
        "authenticated": False,
        "username": "",
    }