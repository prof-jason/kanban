# AI Chat Contract

`POST /api/ai/chat` is an authenticated backend-only endpoint. It reads the current board and the latest 10 saved messages, sends them with the new question to OpenRouter, and returns assistant text with the resulting board. `GET /api/ai/history` returns the persisted history for the authenticated board.

The model must return this versioned JSON shape:

```json
{
  "version": "1",
  "response": "I added the launch task to Backlog.",
  "operations": [
    {
      "type": "create_card",
      "column_id": "board-user-col-backlog",
      "title": "Plan launch",
      "details": "Outline milestones."
    }
  ]
}
```

`operations` is always present. An empty list means chat only. Supported operations are:

- `rename_column`: `column_id`, `title`
- `create_card`: `column_id`, `title`, `details`
- `update_card`: `card_id`, `title`, `details`
- `move_card`: `card_id`, `column_id`, `position`
- `delete_card`: `card_id`

OpenRouter receives a strict JSON Schema derived from this contract. The backend parses the returned content before performing any mutation. It checks every referenced column, card, and target position against the current authenticated board before applying operations. All operations in a response are applied in one database transaction: if any operation is invalid (unknown id, bad position, blank title), none are applied and no board change or chat message is recorded.

Conversation history is stored in SQLite `chat_messages`, associated with the board. The request supplies the latest 10 messages in chronological order. After a successful chat request, the user question and assistant response are stored. Schema version 2 adds this table and its board/id index.

The frontend chat sidebar loads this history on the board screen. It renders each response and replaces the displayed board with the `board` object returned from a successful chat request, so valid AI operations appear without a page reload.