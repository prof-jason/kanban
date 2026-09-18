# Frontend Demo

## Purpose

This directory contains the Next.js Kanban UI. Authentication and board state are handled through the FastAPI API; board data persists in SQLite. The AI chat sidebar is implemented.

## Stack and Commands

- Next.js 16 with React 19 and TypeScript.
- Tailwind CSS 4 for styling, with project colors defined in `src/app/globals.css`.
- `@dnd-kit` provides card drag-and-drop.
- Vitest and Testing Library provide unit/component coverage.
- Playwright provides browser coverage.

From this directory, use:

- `npm run dev` to start the demo locally.
- `npm run build` to produce the production build.
- `npm run lint` for ESLint.
- `npm run test:unit` for Vitest.
- `npm run test:e2e` for Playwright; it starts or reuses the Docker Compose service on port 8000.
- `npm run test:all` for the unit and browser suites.

## Current Architecture

- `src/app/page.tsx` renders `AuthGate` as the home page.
- `src/components/AuthGate.tsx` checks the backend session, renders the login form for signed-out users, and renders the board only after authentication.
- `src/components/KanbanBoard.tsx` loads `BoardData` from `/api/board`, renders loading/error states, and sends each board mutation to the API.
- `src/components/ChatSidebar.tsx` loads persisted chat history, sends messages to `/api/ai/chat`, renders request states, and supplies the returned board to `KanbanBoard` for immediate refresh.
- `src/components/KanbanColumn.tsx` renders a droppable column, editable column title, sortable cards, and the new-card form.
- `src/components/KanbanCard.tsx` renders one sortable card and its delete action.
- `src/components/KanbanCardPreview.tsx` renders the drag overlay preview.
- `src/components/NewCardForm.tsx` contains the card-create form.
- `src/lib/api.ts` provides `apiFetch`, which reports a 401 as `UnauthorizedError`; components call `onUnauthorized` to return to the login form.
- `src/lib/kanban.ts` defines `Card`, `Column`, and `BoardData`, supplies the initial five-column sample board, and implements pure card-movement and ID helpers.

The demo starts with five columns: Backlog, Discovery, In Progress, Review, and Done. Users can rename their titles, add and remove cards, and drag cards within or between columns.

## Testing Conventions

- Place component tests beside the component, following `KanbanBoard.test.tsx`.
- `ChatSidebar.test.tsx` mocks history and chat API responses to cover history, errors, and an AI board update.
- Test pure board behavior beside `src/lib/kanban.ts`, following `kanban.test.ts`.
- Place browser workflows in `tests/`.
- Existing stable selectors use `data-testid` values such as `column-col-backlog` and `card-card-1`; preserve or deliberately update tests when changing them.

## Integration Direction

FastAPI serves the static frontend build from the Docker image. Keep browser-only state limited to presentational and request state. Treat API responses as the source of truth for the authenticated user's board, and route all persistent mutations through the backend.