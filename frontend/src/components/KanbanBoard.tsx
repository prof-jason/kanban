"use client";

import { useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { ChatSidebar } from "@/components/ChatSidebar";
import { apiFetch, UnauthorizedError } from "@/lib/api";
import { moveCard, type BoardData } from "@/lib/kanban";

type KanbanBoardProps = {
  onLogout?: () => void;
  onUnauthorized?: () => void;
  initialBoard?: BoardData;
  showChat?: boolean;
};

export const KanbanBoard = ({
  onLogout,
  onUnauthorized,
  initialBoard,
  showChat = true,
}: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData | null>(initialBoard ?? null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  useEffect(() => {
    if (initialBoard) {
      return;
    }

    const loadBoard = async () => {
      try {
        const response = await apiFetch("/api/board");
        if (!response.ok) {
          throw new Error("Unable to load the board.");
        }
        setBoard((await response.json()) as BoardData);
      } catch (error) {
        if (error instanceof UnauthorizedError) {
          onUnauthorized?.();
          return;
        }
        setError("Unable to load the board.");
      }
    };

    void loadBoard();
  }, [initialBoard, onUnauthorized]);

  const cardsById = useMemo(() => board?.cards ?? {}, [board]);

  const saveBoard = async (path: string, options: RequestInit): Promise<boolean> => {
    setError("");
    try {
      const response = await apiFetch(path, options);
      if (!response.ok) {
        throw new Error("Unable to save the board.");
      }
      setBoard((await response.json()) as BoardData);
      return true;
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        onUnauthorized?.();
      } else {
        setError("Unable to save the board. Please try again.");
      }
      return false;
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    if (!board) {
      return;
    }

    const cardId = active.id as string;
    const nextColumns = moveCard(board.columns, cardId, over.id as string);
    const targetColumn = nextColumns.find((column) => column.cardIds.includes(cardId));
    if (!targetColumn) {
      return;
    }

    void saveBoard(`/api/board/cards/${cardId}/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        column_id: targetColumn.id,
        position: targetColumn.cardIds.indexOf(cardId),
      }),
    });
  };

  const handleSaveColumn = (columnId: string, title: string) =>
    saveBoard(`/api/board/columns/${columnId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });

  const handleAddCard = (columnId: string, title: string, details: string) => {
    void saveBoard("/api/board/cards", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ column_id: columnId, title, details }),
    });
  };

  const handleDeleteCard = (_columnId: string, cardId: string) => {
    void saveBoard(`/api/board/cards/${cardId}`, {
      method: "DELETE",
    });
  };

  const handleEditCard = (cardId: string, title: string, details: string) => {
    void saveBoard(`/api/board/cards/${cardId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, details }),
    });
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  if (!board) {
    return (
      <main className="p-6 text-[var(--gray-text)]">
        {error || "Loading board..."}
      </main>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
            </div>
            {onLogout && (
              <button
                type="button"
                onClick={onLogout}
                className="rounded-xl border border-[var(--stroke)] px-4 py-3 text-sm font-semibold text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)]"
              >
                Log out
              </button>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        {error && <p className="text-sm text-red-700">{error}</p>}

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="grid gap-6 lg:grid-cols-5">
              {board.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  onSaveColumn={handleSaveColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                  onEditCard={handleEditCard}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
          {showChat && <ChatSidebar onBoardUpdate={setBoard} onUnauthorized={onUnauthorized} />}
        </div>
      </main>
    </div>
  );
};
