import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

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
    for column_position, (column_id, title, card_ids) in enumerate(INITIAL_COLUMNS):
        connection.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (column_id, board_id, title, column_position),
        )
        for card_position, card_id in enumerate(card_ids):
            title, details = INITIAL_CARDS[card_id]
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