import pytest

from app.database import (
    create_card,
    delete_card,
    get_chat_history,
    get_connection,
    get_or_create_board,
    initialize_database,
    move_card,
    rename_column,
    record_chat_messages,
    update_card,
)


def test_initialization_creates_the_schema(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "kanban.db"))

    initialize_database()

    with get_connection() as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    assert [table["name"] for table in tables] == [
        "boards",
        "cards",
        "chat_messages",
        "columns",
        "users",
    ]


def test_first_board_read_seeds_the_current_kanban(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "kanban.db"))

    board = get_or_create_board("user")

    assert [column["id"] for column in board["columns"]] == [
        "board-user-col-backlog",
        "board-user-col-discovery",
        "board-user-col-progress",
        "board-user-col-review",
        "board-user-col-done",
    ]
    assert board["columns"][0]["cardIds"] == ["board-user-card-1", "board-user-card-2"]
    assert board["cards"]["board-user-card-1"]["title"] == "Align roadmap themes"


def test_each_user_has_one_independent_seeded_board(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "kanban.db"))

    get_or_create_board("user")
    get_or_create_board("user")
    get_or_create_board("another-user")

    with get_connection() as connection:
        board_count = connection.execute("SELECT COUNT(*) FROM boards").fetchone()[0]
    assert board_count == 2


def test_board_mutations_preserve_the_json_contract(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "kanban.db"))
    board = get_or_create_board("user")
    backlog_id = board["columns"][0]["id"]
    review_id = board["columns"][3]["id"]
    first_card_id = board["columns"][0]["cardIds"][0]

    board = rename_column("user", backlog_id, "Ideas")
    assert board["columns"][0]["title"] == "Ideas"

    board = create_card("user", backlog_id, "New card", "New details")
    new_card_id = board["columns"][0]["cardIds"][-1]
    assert board["cards"][new_card_id]["title"] == "New card"

    board = update_card("user", new_card_id, "Edited card", "Edited details")
    assert board["cards"][new_card_id] == {
        "id": new_card_id,
        "title": "Edited card",
        "details": "Edited details",
    }

    board = move_card("user", first_card_id, review_id, 0)
    assert board["columns"][3]["cardIds"][0] == first_card_id
    assert first_card_id not in board["columns"][0]["cardIds"]

    board = delete_card("user", new_card_id)
    assert new_card_id not in board["cards"]
    assert new_card_id not in board["columns"][0]["cardIds"]


def test_card_can_be_reordered_within_its_column(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "kanban.db"))
    board = get_or_create_board("user")
    backlog_id = board["columns"][0]["id"]
    first_card_id = board["columns"][0]["cardIds"][0]

    board = move_card("user", first_card_id, backlog_id, 1)

    assert board["columns"][0]["cardIds"] == [
        "board-user-card-2",
        "board-user-card-1",
    ]


def test_board_mutations_cannot_cross_user_boundaries(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "kanban.db"))
    other_board = get_or_create_board("another-user")
    other_column_id = other_board["columns"][0]["id"]
    get_or_create_board("user")

    with pytest.raises(LookupError, match="Column not found"):
        rename_column("user", other_column_id, "Unauthorized change")


def test_chat_history_is_limited_to_the_latest_ten_messages(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "kanban.db"))
    get_or_create_board("user")
    record_chat_messages(
        "user",
        [{"role": "user", "content": f"Message {index}"} for index in range(12)],
    )

    history = get_chat_history("user")

    assert len(history) == 10
    assert history[0]["content"] == "Message 2"
    assert history[-1]["content"] == "Message 11"