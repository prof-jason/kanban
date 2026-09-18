import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

DEFAULT_DATABASE_PATH = "/data/project_management.db"

INITIAL_COLUMNS = [
    ("col-backlog", "Backlog", ["card-1", "card-2"]),
    ("col-discovery", "Discovery", ["card-3"]),
    ("col-progress", "In Progress", ["card-4", "card-5"]),
    ("col-review", "Review", ["card-6"]),
    ("col-done", "Done", ["card-7", "card-8"]),
]

INITIAL_CARDS = {
    "card-1": ("Align roadmap themes", "Draft quarterly themes with impact statements and metrics."),
    "card-2": ("Gather customer signals", "Review support tags, sales notes, and churn feedback."),
    "card-3": ("Prototype analytics view", "Sketch initial dashboard layout and key drill-downs."),
    "card-4": ("Refine status language", "Standardize column labels and tone across the board."),
    "card-5": ("Design card layout", "Add hierarchy and spacing for scanning dense lists."),
    "card-6": ("QA micro-interactions", "Verify hover, focus, and loading states."),
    "card-7": ("Ship marketing page", "Final copy approved and asset pack delivered."),
    "card-8": ("Close onboarding sprint", "Document release notes and share internally."),
}


def get_database_path() -> Path:
    return Path(os.getenv("DATABASE_PATH", DEFAULT_DATABASE_PATH))


def get_connection() -> sqlite3.Connection:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY,
              username TEXT NOT NULL UNIQUE,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS boards (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS columns (
              id TEXT PRIMARY KEY,
              board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
              title TEXT NOT NULL,
              position INTEGER NOT NULL,
              UNIQUE (board_id, position)
            );

            CREATE TABLE IF NOT EXISTS cards (
              id TEXT PRIMARY KEY,
              column_id TEXT NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
              title TEXT NOT NULL,
              details TEXT NOT NULL,
              position INTEGER NOT NULL,
              UNIQUE (column_id, position)
            );

            CREATE INDEX IF NOT EXISTS cards_by_column_position
            ON cards(column_id, position);

            PRAGMA user_version = 1;
            """
        )


def get_or_create_board(username: str) -> dict[str, object]:
    initialize_database()
    with get_connection() as connection:
        user_id = f"user-{username}"
        now = datetime.now(UTC).isoformat()
        connection.execute(
            "INSERT OR IGNORE INTO users (id, username, created_at) VALUES (?, ?, ?)",
            (user_id, username, now),
        )
        board = connection.execute(
            "SELECT id FROM boards WHERE user_id = ?", (user_id,)
        ).fetchone()

        if board is None:
            board_id = f"board-{username}"
            connection.execute(
                "INSERT INTO boards (id, user_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (board_id, user_id, now, now),
            )
            _seed_board(connection, board_id)

        return _read_board(connection, user_id)


def _seed_board(connection: sqlite3.Connection, board_id: str) -> None:
    for column_position, (seed_column_id, title, seed_card_ids) in enumerate(INITIAL_COLUMNS):
        column_id = f"{board_id}-{seed_column_id}"
        connection.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (column_id, board_id, title, column_position),
        )
        for card_position, seed_card_id in enumerate(seed_card_ids):
            card_id = f"{board_id}-{seed_card_id}"
            title, details = INITIAL_CARDS[seed_card_id]
            connection.execute(
                "INSERT INTO cards (id, column_id, title, details, position) VALUES (?, ?, ?, ?, ?)",
                (card_id, column_id, title, details, card_position),
            )


def _read_board(connection: sqlite3.Connection, user_id: str) -> dict[str, object]:
    board = connection.execute(
        "SELECT id FROM boards WHERE user_id = ?", (user_id,)
    ).fetchone()
    if board is None:
        raise LookupError("Board not found")

    columns = connection.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position", (board["id"],)
    ).fetchall()
    column_data = []
    cards: dict[str, dict[str, str]] = {}

    for column in columns:
        card_rows = connection.execute(
            "SELECT id, title, details FROM cards WHERE column_id = ? ORDER BY position",
            (column["id"],),
        ).fetchall()
        card_ids = [card["id"] for card in card_rows]
        column_data.append(
            {"id": column["id"], "title": column["title"], "cardIds": card_ids}
        )
        cards.update(
            {
                card["id"]: {
                    "id": card["id"],
                    "title": card["title"],
                    "details": card["details"],
                }
                for card in card_rows
            }
        )

    return {"columns": column_data, "cards": cards}


def rename_column(username: str, column_id: str, title: str) -> dict[str, object]:
    title = title.strip()
    if not title:
        raise ValueError("Column title cannot be empty")

    with get_connection() as connection:
        user_id, board_id = _get_board_ids(connection, username)
        result = connection.execute(
            "UPDATE columns SET title = ? WHERE id = ? AND board_id = ?",
            (title, column_id, board_id),
        )
        if result.rowcount == 0:
            raise LookupError("Column not found")
        _touch_board(connection, board_id)
        return _read_board(connection, user_id)


def create_card(
    username: str, column_id: str, title: str, details: str
) -> dict[str, object]:
    title = title.strip()
    if not title:
        raise ValueError("Card title cannot be empty")

    with get_connection() as connection:
        user_id, board_id = _get_board_ids(connection, username)
        _require_column(connection, board_id, column_id)
        position = connection.execute(
            "SELECT COUNT(*) FROM cards WHERE column_id = ?", (column_id,)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO cards (id, column_id, title, details, position) VALUES (?, ?, ?, ?, ?)",
            (f"card-{uuid4().hex}", column_id, title, details.strip(), position),
        )
        _touch_board(connection, board_id)
        return _read_board(connection, user_id)


def update_card(
    username: str, card_id: str, title: str, details: str
) -> dict[str, object]:
    title = title.strip()
    if not title:
        raise ValueError("Card title cannot be empty")

    with get_connection() as connection:
        user_id, board_id = _get_board_ids(connection, username)
        result = connection.execute(
            """
            UPDATE cards
            SET title = ?, details = ?
            WHERE id = ?
              AND column_id IN (SELECT id FROM columns WHERE board_id = ?)
            """,
            (title, details.strip(), card_id, board_id),
        )
        if result.rowcount == 0:
            raise LookupError("Card not found")
        _touch_board(connection, board_id)
        return _read_board(connection, user_id)


def delete_card(username: str, card_id: str) -> dict[str, object]:
    with get_connection() as connection:
        user_id, board_id = _get_board_ids(connection, username)
        card = _require_card(connection, board_id, card_id)
        connection.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        _renumber_column(connection, card["column_id"])
        _touch_board(connection, board_id)
        return _read_board(connection, user_id)


def move_card(
    username: str, card_id: str, target_column_id: str, target_position: int
) -> dict[str, object]:
    with get_connection() as connection:
        user_id, board_id = _get_board_ids(connection, username)
        card = _require_card(connection, board_id, card_id)
        _require_column(connection, board_id, target_column_id)
        source_column_id = card["column_id"]
        target_card_ids = [
            row["id"]
            for row in connection.execute(
                "SELECT id FROM cards WHERE column_id = ? ORDER BY position",
                (target_column_id,),
            )
        ]
        if source_column_id == target_column_id:
            target_card_ids.remove(card_id)

        if target_position < 0 or target_position > len(target_card_ids):
            raise ValueError("Target position is outside the column")

        source_card_ids = [
            row["id"]
            for row in connection.execute(
                "SELECT id FROM cards WHERE column_id = ? ORDER BY position",
                (source_column_id,),
            )
            if row["id"] != card_id
        ]
        target_card_ids.insert(target_position, card_id)

        _temporarily_clear_positions(connection, source_column_id)
        if source_column_id == target_column_id:
            _set_positions(connection, source_column_id, target_card_ids)
        else:
            _temporarily_clear_positions(connection, target_column_id)
            connection.execute(
                "UPDATE cards SET column_id = ?, position = ? WHERE id = ?",
                (target_column_id, -(len(target_card_ids) + 1), card_id),
            )
            _set_positions(connection, source_column_id, source_card_ids)
            _set_positions(connection, target_column_id, target_card_ids)
        _touch_board(connection, board_id)
        return _read_board(connection, user_id)


def _get_board_ids(connection: sqlite3.Connection, username: str) -> tuple[str, str]:
    row = connection.execute(
        """
        SELECT users.id AS user_id, boards.id AS board_id
        FROM users JOIN boards ON boards.user_id = users.id
        WHERE users.username = ?
        """,
        (username,),
    ).fetchone()
    if row is None:
        raise LookupError("Board not found")
    return row["user_id"], row["board_id"]


def _require_column(
    connection: sqlite3.Connection, board_id: str, column_id: str
) -> sqlite3.Row:
    column = connection.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?", (column_id, board_id)
    ).fetchone()
    if column is None:
        raise LookupError("Column not found")
    return column


def _require_card(
    connection: sqlite3.Connection, board_id: str, card_id: str
) -> sqlite3.Row:
    card = connection.execute(
        """
        SELECT cards.id, cards.column_id
        FROM cards JOIN columns ON columns.id = cards.column_id
        WHERE cards.id = ? AND columns.board_id = ?
        """,
        (card_id, board_id),
    ).fetchone()
    if card is None:
        raise LookupError("Card not found")
    return card


def _temporarily_clear_positions(connection: sqlite3.Connection, column_id: str) -> None:
    connection.execute(
        "UPDATE cards SET position = -position - 1 WHERE column_id = ?", (column_id,)
    )


def _renumber_column(connection: sqlite3.Connection, column_id: str) -> None:
    card_ids = [
        row["id"]
        for row in connection.execute(
            "SELECT id FROM cards WHERE column_id = ? ORDER BY position", (column_id,)
        )
    ]
    _temporarily_clear_positions(connection, column_id)
    _set_positions(connection, column_id, card_ids)


def _set_positions(
    connection: sqlite3.Connection, column_id: str, card_ids: list[str]
) -> None:
    for position, card_id in enumerate(card_ids):
        connection.execute(
            "UPDATE cards SET position = ? WHERE id = ? AND column_id = ?",
            (position, card_id, column_id),
        )


def _touch_board(connection: sqlite3.Connection, board_id: str) -> None:
    connection.execute(
        "UPDATE boards SET updated_at = ? WHERE id = ?",
        (datetime.now(UTC).isoformat(), board_id),
    )