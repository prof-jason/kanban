import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/lib/kanban";

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];
const boardResponse = (board = initialData) =>
  new Response(JSON.stringify(board), { status: 200 });

const copyBoard = () => structuredClone(initialData);

describe("KanbanBoard", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads the board from the API", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(boardResponse()));

    render(<KanbanBoard showChat={false} />);

    expect(screen.getByText("Loading board...")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Kanban Studio" })).toBeInTheDocument();
  });

  it("shows an error when the board cannot be loaded", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 500 })));

    render(<KanbanBoard showChat={false} />);

    expect(await screen.findByText("Unable to load the board.")).toBeInTheDocument();
  });

  it("shows an error when a board change cannot be saved", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 500 })));
    render(<KanbanBoard initialBoard={initialData} showChat={false} />);
    const column = getFirstColumn();

    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(column).getByPlaceholderText(/card title/i), "New card");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(await screen.findByText("Unable to save the board. Please try again.")).toBeInTheDocument();
  });

  it("renders five columns", () => {
    render(<KanbanBoard initialBoard={initialData} showChat={false} />);
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard initialBoard={initialData} showChat={false} />);
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    const afterAdd = copyBoard();
    afterAdd.cards["card-new"] = { id: "card-new", title: "New card", details: "Notes" };
    afterAdd.columns[0].cardIds.push("card-new");
    const afterDelete = copyBoard();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(boardResponse(afterAdd)).mockResolvedValueOnce(boardResponse(afterDelete))
    );
    render(<KanbanBoard initialBoard={initialData} showChat={false} />);
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    await waitFor(() => {
      expect(within(column).getByText("New card")).toBeInTheDocument();
    });

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    await waitFor(() => {
      expect(within(column).queryByText("New card")).not.toBeInTheDocument();
    });
  });

  it("edits a card", async () => {
    const afterEdit = copyBoard();
    afterEdit.cards["card-1"] = {
      id: "card-1",
      title: "Updated roadmap",
      details: "Updated details.",
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(boardResponse(afterEdit)));
    render(<KanbanBoard initialBoard={initialData} showChat={false} />);
    const card = screen.getByTestId("card-card-1");

    await userEvent.click(within(card).getByRole("button", { name: /edit align roadmap themes/i }));
    const titleInput = within(card).getByLabelText("Card title");
    const detailsInput = within(card).getByLabelText("Card details");
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Updated roadmap");
    await userEvent.clear(detailsInput);
    await userEvent.type(detailsInput, "Updated details.");
    await userEvent.click(within(card).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(within(card).getByText("Updated roadmap")).toBeInTheDocument();
      expect(within(card).getByText("Updated details.")).toBeInTheDocument();
    });
  });
});
