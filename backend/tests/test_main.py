import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "kanban.db"))
    with TestClient(app) as test_client:
        yield test_client


def sign_in(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"username": "user", "password": "password"}
    )
    assert response.status_code == 204


def test_example_endpoint_returns_expected_message(client: TestClient) -> None:
    response = client.get("/api/example")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello from the API"}


def test_root_serves_static_page(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Project Management MVP" in response.text


def test_valid_login_creates_a_session(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"username": "user", "password": "password"}
    )

    assert response.status_code == 204
    assert client.get("/api/auth/session").json() == {
        "authenticated": True,
        "username": "user",
    }


def test_invalid_login_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"username": "user", "password": "incorrect"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."


def test_logout_clears_the_session(client: TestClient) -> None:
    sign_in(client)

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert client.get("/api/auth/session").json() == {
        "authenticated": False,
        "username": "",
    }


def test_board_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/board")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_board_api_reads_and_updates_the_authenticated_board(client: TestClient) -> None:
    sign_in(client)
    board = client.get("/api/board").json()
    backlog_id = board["columns"][0]["id"]
    review_id = board["columns"][3]["id"]
    first_card_id = board["columns"][0]["cardIds"][0]

    board = client.patch(
        f"/api/board/columns/{backlog_id}", json={"title": "Ideas"}
    ).json()
    assert board["columns"][0]["title"] == "Ideas"

    board = client.post(
        "/api/board/cards",
        json={"column_id": backlog_id, "title": "New card", "details": "New details"},
    ).json()
    new_card_id = board["columns"][0]["cardIds"][-1]

    board = client.patch(
        f"/api/board/cards/{new_card_id}",
        json={"title": "Edited card", "details": "Edited details"},
    ).json()
    assert board["cards"][new_card_id]["title"] == "Edited card"

    board = client.post(
        f"/api/board/cards/{first_card_id}/move",
        json={"column_id": review_id, "position": 0},
    ).json()
    assert board["columns"][3]["cardIds"][0] == first_card_id

    board = client.delete(f"/api/board/cards/{new_card_id}").json()
    assert new_card_id not in board["cards"]