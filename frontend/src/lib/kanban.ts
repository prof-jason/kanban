export type Card = {
  id: string;
  title: string;
  details: string;
};

export type Column = {
  id: string;
  title: string;
  cardIds: string[];
};

export type BoardData = {
  columns: Column[];
  cards: Record<string, Card>;
};

export const initialData: BoardData = {
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
    { id: "col-discovery", title: "Discovery", cardIds: ["card-3"] },
    {
      id: "col-progress",
      title: "In Progress",
      cardIds: ["card-4", "card-5"],
    },
    { id: "col-review", title: "Review", cardIds: ["card-6"] },
    { id: "col-done", title: "Done", cardIds: ["card-7", "card-8"] },
  ],
  cards: {
    "card-1": {
      id: "card-1",
      title: "Align roadmap themes",
      details: "Draft quarterly themes with impact statements and metrics.",
    },
    "card-2": {
      id: "card-2",
      title: "Gather customer signals",
      details: "Review support tags, sales notes, and churn feedback.",
    },
    "card-3": {
      id: "card-3",
      title: "Prototype analytics view",
      details: "Sketch initial dashboard layout and key drill-downs.",
    },
    "card-4": {
      id: "card-4",
      title: "Refine status language",
      details: "Standardize column labels and tone across the board.",
    },
    "card-5": {
      id: "card-5",
      title: "Design card layout",
      details: "Add hierarchy and spacing for scanning dense lists.",
    },
    "card-6": {
      id: "card-6",
      title: "QA micro-interactions",
      details: "Verify hover, focus, and loading states.",
    },
    "card-7": {
      id: "card-7",
      title: "Ship marketing page",
      details: "Final copy approved and asset pack delivered.",
    },
    "card-8": {
      id: "card-8",
      title: "Close onboarding sprint",
      details: "Document release notes and share internally.",
    },
  },
};

// A drag id is either a column id (dropped on empty column space) or a card id.
const findColumn = (columns: Column[], id: string): Column | undefined =>
  columns.find((column) => column.id === id) ??
  columns.find((column) => column.cardIds.includes(id));

const withCardIds = (
  columns: Column[],
  cardIdsByColumnId: Record<string, string[]>
): Column[] =>
  columns.map((column) =>
    column.id in cardIdsByColumnId
      ? { ...column, cardIds: cardIdsByColumnId[column.id] }
      : column
  );

export const moveCard = (
  columns: Column[],
  activeId: string,
  overId: string
): Column[] => {
  const activeColumn = findColumn(columns, activeId);
  const overColumn = findColumn(columns, overId);

  if (!activeColumn || !overColumn) {
    return columns;
  }

  const droppedOnColumn = overColumn.id === overId;

  if (activeColumn.id === overColumn.id) {
    const nextCardIds = activeColumn.cardIds.filter(
      (cardId) => cardId !== activeId
    );

    if (droppedOnColumn) {
      nextCardIds.push(activeId);
      return withCardIds(columns, { [activeColumn.id]: nextCardIds });
    }

    const fromIndex = activeColumn.cardIds.indexOf(activeId);
    const toIndex = activeColumn.cardIds.indexOf(overId);
    if (fromIndex === -1 || toIndex === -1 || fromIndex === toIndex) {
      return columns;
    }

    nextCardIds.splice(toIndex, 0, activeId);
    return withCardIds(columns, { [activeColumn.id]: nextCardIds });
  }

  if (!activeColumn.cardIds.includes(activeId)) {
    return columns;
  }

  const nextActiveCardIds = activeColumn.cardIds.filter(
    (cardId) => cardId !== activeId
  );
  const overIndex = droppedOnColumn ? -1 : overColumn.cardIds.indexOf(overId);
  const nextOverCardIds = [...overColumn.cardIds];
  nextOverCardIds.splice(
    overIndex === -1 ? nextOverCardIds.length : overIndex,
    0,
    activeId
  );

  return withCardIds(columns, {
    [activeColumn.id]: nextActiveCardIds,
    [overColumn.id]: nextOverCardIds,
  });
};
