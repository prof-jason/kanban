# Code Review

Scope: the whole repository (backend, frontend, Docker and scripts, tests, docs) at the state after the card layout fix. Test status at review time: 14/14 Vitest, 28/28 pytest, 5/5 Playwright.

Findings are based on reading the code. Items marked "unverified" were not reproduced by running them.

## Remediation status

All high and medium priority items (H1-H3, M1-M7) were addressed. Low priority items and the Tests section were not.

- H1: AI operations now run in one `BEGIN IMMEDIATE` transaction (`apply_ai_operations`); any invalid operation rolls back the whole batch. Tests added at database and API level.
- H2: no default secret. `SESSION_SECRET` is read from the environment, otherwise a random key is generated per start. `SESSION_HTTPS_ONLY=1` enables secure cookies.
- H3: credentials compared with `secrets.compare_digest`; `MVP_USERNAME` / `MVP_PASSWORD` configurable (defaults unchanged).
- M1: `src/lib/api.ts` `apiFetch` reports 401 as `UnauthorizedError`; the board and chat return the user to the login form.
- M2: column titles save on blur only when changed and non-empty, and revert on failure; `maxLength` 200.
- M3: no per-call schema setup; board reads are two queries; reads no longer write.
- M4: REST models enforce the same 200 / 4000 limits as the AI contract.
- M5: operations are validated against current data inside the write transaction. Edits made during a model call can no longer apply against stale positions. Frontend edits are not locked while a chat request is in flight.
- M6: verified against the real OpenRouter endpoint. The strict schema is accepted and responses parse. The free model's answers are inconsistent (some responses were nonsense, such as a `move_card` or an unknown card id); these are rejected without changing the board.
- M7: one shared request helper, a 90 second timeout, and a total deadline. The real endpoint once held a request open past its per-read timeout, which the total deadline now covers; timeouts return a distinct message.

## Summary

The codebase is small, readable and consistent with the "keep it simple" standard. Board ownership checks are done correctly in SQL, and AI output is validated against a strict schema before any mutation. The main issues are that AI operations are not atomic (contradicting the documented guarantee), the session secret has an insecure default, and several places lack robustness around failed saves and expired sessions. Documentation in the frontend has drifted from the implementation.

## High priority

### H1. AI operations are not atomic; partial failure leaves the board changed
- Where: `backend/app/database.py` `apply_ai_operations`, `backend/app/main.py` `chat_with_ai`.
- Each operation calls a public function that opens its own connection and commits. `_validate_ai_operations` only checks IDs and positions, not the rules the mutators enforce. For example the schema allows a whitespace-only title (`min_length=1`), but `create_card`, `update_card` and `rename_column` strip and raise `ValueError` on empty titles.
- Failure scenario: the model returns `[create_card("Good"), create_card("   ")]`. The first card is committed, the second raises, the endpoint returns 502, and the chat messages are never recorded. The UI shows an error while the board has silently changed after a reload.
- This contradicts `docs/AI.md` ("Invalid or unavailable model output returns an error and no board change is recorded").
- Action: run all operations in one connection and one transaction (pass the connection into private `_apply_*` helpers, roll back on any error), and make the validator reject blank titles. Add a test for the mixed valid/invalid case.

### H2. Insecure default session secret
- Where: `backend/app/main.py` (`SESSION_SECRET` default `"local-development-session-secret"`).
- The default is public in the repo and `compose.yaml` does not set the variable, so every deployment signs cookies with a known key. Anyone can forge a `{"username": "user"}` session cookie without the password.
- Action: read the secret from the environment with no default (fail at startup), or generate a random one at startup for local use. Add it to `.env` and document it. Set `https_only=True` when not running on localhost.

### H3. Hardcoded credentials compared with `!=`
- Where: `backend/app/main.py` `login`.
- Acceptable for the stated MVP, but the check is not constant-time and there is no rate limiting. Combined with H2 this is the only barrier to the data.
- Action: use `secrets.compare_digest`, and move the credentials to environment variables with the current values as documented defaults only for local runs. Do this before any non-local use.

## Medium priority

### M1. Session expiry and API errors are not handled in the UI
- Where: `KanbanBoard.tsx` `saveBoard` and `loadBoard`, `ChatSidebar.tsx`.
- A 401 (expired or cleared cookie) shows a generic "Unable to save" message instead of returning the user to the login form. Non-OK responses from `/api/auth/session` are parsed as JSON without checking status.
- Action: centralize `fetch` in one small helper that treats 401 as "signed out" and lifts that state to `AuthGate`.

### M2. Column rename can leave the UI out of sync with the server
- Where: `KanbanBoard.tsx` `handleRenameColumn` / `handleSaveColumn`, `KanbanColumn.tsx`.
- Typing updates local state immediately; the save happens on blur. If the title is emptied the server returns 422, an error shows, but the input keeps the empty value (never reverted). A save also fires on every blur even when the title is unchanged.
- Action: skip the request when the title equals the last saved value, and reload or revert on failure. Add `maxLength` to the input.

### M3. `get_or_create_board` re-runs schema setup and writes on every call
- Where: `backend/app/database.py`.
- `initialize_database()` (an `executescript`) runs on every board read, chat history read and AI operation, on top of the lifespan call. `GET /api/board` also performs an `INSERT OR IGNORE`. `apply_ai_operations` then re-reads the full board per operation, and `_read_board` issues one query per column.
- Not a problem at MVP scale, but it is unneeded work and the `executescript` commits implicitly.
- Action: drop the per-call `initialize_database()`; create the user/board in one place (login or startup); fetch cards in one query.

### M4. No request-size limits on REST card and column fields
- Where: `backend/app/main.py` `ColumnUpdate`, `CardCreate`, `CardUpdate`.
- The AI contract caps titles at 200 and details at 4000, but the REST models accept unbounded strings. These are also serialized into every AI prompt.
- Action: apply the same `Field(max_length=...)` limits to the REST models so the two paths agree.

### M5. Concurrent updates race
- Where: `chat_with_ai` reads the board, waits up to 30 s on the model, then applies operations validated against that older snapshot.
- If the user edits or moves a card during the model call, operations use stale positions. The frontend then replaces its whole board with the AI response, discarding any local unsaved rename.
- Action: with H1's single transaction, re-validate inside the transaction. Optionally disable board edits while a chat request is in flight.

### M6. OpenRouter strict schema compatibility is unverified
- Where: `backend/app/openrouter.py`, `ai_contract.py`.
- `response_schema()` sends the Pydantic schema with `$defs`, `$ref` and a `oneOf` discriminated union under `strict: True`. Providers differ in which of these they accept, and the tests mock the HTTP call. The real endpoint (unverified) may reject the schema or ignore it.
- Action: run one real request through `/api/ai/chat` and record the result. If rejected, inline the refs or use a flat operation object.

### M7. Long-running blocking call and no retry
- Where: `answer_board_question` uses synchronous `httpx.post` with a 30 s timeout inside a sync endpoint. This runs in the threadpool, which is fine, but a free-tier model can exceed 30 s and the user just gets a 502.
- Action: consider a longer timeout and a distinct message for timeouts. Deduplicate the two near-identical request blocks (`answer_two_plus_two`, `answer_board_question`) into one helper.

## Low priority

- L1. Dead code and duplication: `createId` in `frontend/src/lib/kanban.ts` is unused by the app; `initialData` is used only by tests and duplicates the backend seed data. `GET /api/example` is a leftover smoke endpoint. Remove or move test fixtures into the test folder.
- L2. Duplicated header chips: the board header renders the column titles a second time (`KanbanBoard.tsx`), which duplicates text and can confuse `getByText` selectors.
- L3. Responsive layout: columns use `lg:grid-cols-5` inside an `xl` two-column grid with the sidebar, so at 1280px each column is ~154px wide. The card fix stops the overflow, but the columns remain cramped. Consider horizontal scrolling or a narrower sidebar.
- L4. Docker: the image runs as root, has no `HEALTHCHECK`, and uses `ghcr.io/astral-sh/uv:latest` (unpinned). Pin the uv tag and add a non-root user.
- L5. `SessionMiddleware` defaults to a 14-day cookie; state the intended lifetime explicitly.
- L6. Minor code style: unsorted imports in `main.py`, `# type: ignore` in `_validate_ai_operations` (use a typed board `TypedDict`), inconsistent indentation inside the schema SQL in `initialize_database`.
- L7. `AuthGate.handleLogout` does not handle a failed logout request; `ChatSidebar` does not scroll to the newest message.

## Tests

- Coverage is reasonable for the happy paths (28 backend, 14 unit, 5 e2e).
- Gaps: no test for partial AI failure (H1), blank AI titles, REST field limits, concurrency, 401 handling in the UI, or column rename revert (M2).
- The e2e suite runs against the real persistent `kanban-data` volume, so data accumulates ("Playwright card ..." entries) and the "first card" tests depend on prior state. Use a separate Compose project or volume for tests, or reset the DB before the run.
- `playwright.config.ts` starts `docker compose up` in the foreground as the web server and never tears it down; the run leaves the container up unless stopped manually.
- `frontend/test-results/.last-run.json` is tracked in git although it is a generated artifact; add `test-results` to `frontend/.gitignore` and `git rm --cached` it.
- The real AI path is never exercised end to end (mocked in both pytest and Playwright); see M6.

## Documentation

- `frontend/AGENTS.md` is stale: it says "AI chat is not yet implemented" and "Card editing is not yet implemented", but both exist. Update it.
- `CLAUDE.md` and `README.md` are consistent with the code. Consider documenting `SESSION_SECRET` and the local test workflow (Docker required; `uv` is not assumed on the host).

## Suggested order of work

1. H1 (transactional AI operations) with tests.
2. H2 and H3 (secret and credential handling).
3. M1, M2, M4 (UI and validation robustness).
4. M6 (verify the real AI call), then M3, M5, M7.
5. Test isolation and cleanup items (Tests section, L1, L2, L4, L6).
6. Update `frontend/AGENTS.md`.
