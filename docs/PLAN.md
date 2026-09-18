# Project Plan

This plan delivers the MVP in small, independently verifiable stages. Each stage is complete only when its checklist and success criteria are satisfied. Product decisions requiring approval are called out before the stage that depends on them.

## Part 1: Plan and Existing Frontend Documentation

- [x] Review the root requirements and the existing frontend demo.
- [x] Expand this implementation plan into checkable delivery stages with tests and success criteria.
- [x] Create `frontend/AGENTS.md` describing the current frontend architecture, commands, and test layout.
- [x] Obtain approval for this plan before starting scaffolding.

Tests:

- Review that every root requirement maps to a later stage.
- Verify the frontend documentation matches the current source structure and `package.json` scripts.

Success criteria:

- The plan is approved by the user.
- The existing frontend can be understood without treating it as the future backend contract.

## Part 2: Docker, Backend, and Scripts

- [x] Create the FastAPI application and its `uv` project metadata in `backend/`.
- [x] Add a Dockerfile and Docker configuration that installs Python dependencies with `uv` and serves the application locally.
- [x] Add cross-platform start and stop scripts under `scripts/` for macOS/Linux and Windows.
- [x] Serve a temporary static hello-world page at `/`.
- [x] Add a small backend API endpoint to prove the page can call the API.
- [x] Document the local run command and port in the minimal README.

Tests:

- Backend unit/API test: the health or example endpoint returns the expected JSON.
- Container smoke test: build the image, start it, load `/`, and call the example API endpoint.
- Run the appropriate script on the host platform.

Success criteria:

- One Docker container serves the static page and API locally.
- The scripts can start and stop the local container without manual Docker commands.

## Part 3: Serve the Existing Frontend

- [x] Configure the Next.js application for static export compatible with FastAPI static-file serving.
- [x] Build the frontend during the Docker image build and copy its output into the backend static directory.
- [x] Replace the temporary page with the existing Kanban demo at `/`.
- [x] Keep existing board behaviors: five initial columns, rename, card creation/deletion, and drag-and-drop movement.
- [x] Add card title and detail editing to complete the MVP interaction requirements.
- [x] Update browser-test configuration to exercise the container-served application rather than a separate Next dev server.

Tests:

- Run frontend unit tests with `npm run test:unit`.
- Run frontend browser tests with `npm run test:e2e` against the served app.
- Extend unit and browser tests to cover editing a card title and details.
- Container smoke test: `/` renders the Kanban heading and five columns.

Success criteria:

- The statically built frontend is served by FastAPI at `/`.
- Existing unit and browser behaviors remain covered and passing.

## Part 4: MVP Sign-In and Sign-Out

- [x] Add a login screen shown to unauthenticated visitors.
- [x] Validate only the MVP credentials: username `user`, password `password`.
- [x] Add a backend-managed authentication session and a logout action.
- [x] Protect board and future board API routes from unauthenticated requests.
- [x] Display the board only after successful sign-in.

Tests:

- Backend API tests for valid login, invalid login, logout, and unauthenticated rejection.
- Frontend tests for the login form, invalid credentials, successful login, and logout.
- Browser test that confirms a visitor cannot see the board until signed in.

Success criteria:

- A user can sign in and out with the specified credentials.
- Authentication state is enforced by the backend, not only hidden in the UI.

## Part 5: Database Design Approval

- [x] Propose a SQLite schema for users, the single board per user, columns, cards, and card ordering.
- [x] Document the schema, migration/initialization approach, ownership rules, and JSON representation in `docs/`.
- [x] Specify how the initial demo board is created for a new user.
- [x] Specify the Docker volume path for persistent SQLite storage.
- [ ] Obtain user approval before implementing persistence.

Tests:

- Review that the proposal supports multiple users while enforcing one board per user for the MVP.
- Review that column and card order can be read and updated without ambiguity.

Success criteria:

- The database document is approved.
- No persistence implementation begins before approval.

## Part 6: Persistent Kanban API

- [ ] Initialize SQLite and create its schema when the database does not exist.
- [ ] Seed the authenticated user's initial board on first access.
- [ ] Add authenticated routes to read the board and update column names, card title/details, card locations/order, and card lifecycle.
- [ ] Validate request data and consistently scope all reads and writes to the authenticated user.
- [ ] Return a complete, ordered board representation suitable for the frontend.

Tests:

- Backend unit tests for schema initialization and first-board creation.
- API tests for board reads, column rename, card create/edit/delete, and card move/reorder.
- API authorization tests proving one user cannot access another user's board.

Success criteria:

- A missing database is initialized automatically.
- All board mutations persist and preserve a valid ordered board.

## Part 7: Connect the Frontend to the API

- [ ] Replace the frontend's initial in-memory board source with an authenticated API read.
- [ ] Persist each supported UI mutation through the API and update the UI from the returned board state.
- [ ] Add clear loading and request-error states without changing the existing Kanban interaction model.
- [ ] Confirm a reload shows persisted board changes.

Tests:

- Frontend unit tests for API-loading, success, and error states.
- Integration/browser tests for login, rename, card edit, create, delete, drag-and-drop, reload, and logout.
- Backend API tests remain part of the full test suite.

Success criteria:

- The board is backed by SQLite rather than page-local state.
- User changes survive a browser reload and container restart when the database volume is retained.

## Part 8: OpenRouter Connectivity

- [ ] Add a backend AI client configured from `OPENROUTER_API_KEY` and the required `nvidia/nemotron-3-ultra-550b-a55b:free` model.
- [ ] Keep the API key server-side and exclude it from logs and frontend assets.
- [ ] Add a narrow internal or development connectivity check that asks the model `2+2`.
- [ ] Provide actionable configuration errors when the key is absent.

Tests:

- Unit tests mock the OpenRouter client and cover success, missing configuration, and upstream failure handling.
- Manual, opt-in connectivity check verifies a configured key receives a valid `2+2` response.

Success criteria:

- The container can successfully make a real OpenRouter request with the supplied environment variable.
- Automated tests never require a real API key or external model call.

## Part 9: Structured AI Board Operations

- [ ] Define a versioned structured response contract containing assistant text and an optional complete board update or explicit operations.
- [ ] Send the authenticated user's current board JSON, chat history, and new question to the backend AI client.
- [ ] Validate the model response before returning it or persisting any proposed board changes.
- [ ] Ensure invalid or unavailable model output cannot corrupt the board.
- [ ] Define bounded conversation-history retention appropriate for the MVP.

Tests:

- Unit tests for structured response parsing and invalid-response rejection.
- API tests using mocked AI responses for chat-only, create, edit, move, and multiple-card operations.
- Tests proving validated AI updates persist only to the authenticated user's board.

Success criteria:

- AI responses always conform to the documented structured contract.
- The backend can safely return assistant text and an optional board update for a user request.

## Part 10: AI Chat Sidebar

- [ ] Add an accessible sidebar chat interface consistent with the existing Kanban visual language.
- [ ] Support message submission, pending state, response rendering, and request-error feedback.
- [ ] Send chat messages to the authenticated backend route.
- [ ] Apply a validated AI board update and refresh the board without a page reload.
- [ ] Add tests for both chat-only replies and replies that update one or multiple cards.

Tests:

- Frontend unit tests for chat states and board refresh after a mocked structured response.
- Browser tests for a chat response that changes the board and is immediately visible.
- Full container test covering sign-in, persistent board API, and a mocked AI chat workflow.

Success criteria:

- Users can chat from the board screen.
- AI-directed, validated board changes appear automatically and persist through the normal board API.

## Approval Items

The following product decisions have been confirmed:

- The board has five fixed columns. Users may rename them but may not add or delete columns.
- MVP authentication uses a backend cookie session that persists across browser refreshes.
- Validated AI-proposed board changes apply automatically.
- SQLite data uses a Docker volume and persists across container restarts.