# Database Design

## Decision

Use a relational SQLite database. The API will return and accept the Kanban board as JSON, matching the frontend's `BoardData` shape. SQLite rows remain the source of truth rather than storing one opaque JSON board blob; this preserves foreign-key ownership and makes ordered card updates straightforward.

The database file will be `/data/project_management.db` in the container. Docker Compose will mount the named volume `kanban-data` at `/data`, so the file survives container restarts.

## Schema

```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);

CREATE TABLE boards (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE columns (
  id TEXT PRIMARY KEY,
  board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  position INTEGER NOT NULL,
  UNIQUE (board_id, position)
);

CREATE TABLE cards (
  id TEXT PRIMARY KEY,
  column_id TEXT NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  details TEXT NOT NULL,
  position INTEGER NOT NULL,
  UNIQUE (column_id, position)
);

CREATE INDEX cards_by_column_position ON cards(column_id, position);

CREATE TABLE chat_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX chat_messages_by_board ON chat_messages(board_id, id);
```

`boards.user_id` is unique, enforcing one board per user. A card belongs to its board through its column, so a user can only read or change it after the request is scoped through `boards.user_id`.

Columns and cards use globally unique string IDs. Seeded IDs are scoped to the board, such as `board-user-col-backlog` and `board-user-card-1`; later-created records use server-generated IDs. This lets every future user receive the same initial board without primary-key collisions.

## JSON Contract

The board endpoint returns the existing frontend shape. Columns are ordered by `columns.position`; each `cardIds` list is ordered by `cards.position`.

```json
{
  "columns": [
    {
      "id": "board-user-col-backlog",
      "title": "Backlog",
      "cardIds": ["board-user-card-1", "board-user-card-2"]
    }
  ],
  "cards": {
    "board-user-card-1": {
      "id": "board-user-card-1",
      "title": "Align roadmap themes",
      "details": "Draft quarterly themes with impact statements and metrics."
    }
  }
}
```

The map key in `cards` must equal the nested card `id`. Each card ID must appear exactly once in the `cardIds` lists. Column IDs are fixed after seed creation; only their titles can change in the MVP.

## Initialization and Seed Data

On application startup, the database layer enables foreign keys and runs the idempotent `CREATE TABLE IF NOT EXISTS` statements above. The schema version is recorded with `PRAGMA user_version`; the current version is `2`, which adds `chat_messages`. A future schema change will increment that version and apply a small ordered migration in code.

The fixed MVP user is represented by a `users` row keyed to username `user`. On the first authenticated board read, the backend will create that user's one board if missing and seed the current five-column demo board, including its eight cards and positions. It will not overwrite an existing board.

## Ownership and Updates

Every board operation starts by resolving the authenticated session username to `users.id`, then its `boards.id`. All queries and mutations include that board scope. Card moves and reorders update positions transactionally: compact the source column positions, insert at the target position, and renumber affected cards without duplicate positions.

The Part 6 API will validate that titles are nonempty, card IDs exist within the authenticated board, and each returned board satisfies the JSON contract above.

Chat messages belong to a board and are deleted with it. The AI request uses the latest 10 messages in chronological order.

## Approval Needed

Approval of this document authorizes Part 6 implementation: SQLite initialization, the `kanban-data` volume, board seeding, and authenticated board API routes. No persistence code has been added in this stage.