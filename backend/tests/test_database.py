from app.database import get_connection, get_or_create_board, initialize_database


def test_initialization_creates_the_schema(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "kanban.db"))

    initialize_database()

    with get_connection() as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    assert [table["name"] for table in tables] == ["boards", "cards", "columns", "users"]


def test_first_board_read_seeds_the_current_kanban(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "kanban.db"))

    board = get_or_create_board("user")

    assert [column["id"] for column in board["columns"]] == [
        "col-backlog",
        "col-discovery",
        "col-progress",
        "col-review",
        "col-done",
    ]
    assert board["columns"][0]["cardIds"] == ["card-1", "card-2"]
    assert board["cards"]["card-1"]["title"] == "Align roadmap themes"


def test_each_user_has_one_independent_seeded_board(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "kanban.db"))

    get_or_create_board("user")
    get_or_create_board("user")
    get_or_create_board("another-user")

    with get_connection() as connection:
        board_count = connection.execute("SELECT COUNT(*) FROM boards").fetchone()[0]
    assert board_count == 2