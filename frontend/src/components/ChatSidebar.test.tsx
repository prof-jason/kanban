import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ChatSidebar } from "@/components/ChatSidebar";
import { initialData } from "@/lib/kanban";

const jsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status });

describe("ChatSidebar", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads history and refreshes the board after an AI response", async () => {
    const onBoardUpdate = vi.fn();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ messages: [{ role: "assistant", content: "How can I help?" }] })
      )
      .mockResolvedValueOnce(
        jsonResponse({ response: "I added the task.", board: initialData })
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<ChatSidebar onBoardUpdate={onBoardUpdate} />);

    expect(await screen.findByText("How can I help?")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Message the project assistant"), "Add a task");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("I added the task.")).toBeInTheDocument();
    expect(onBoardUpdate).toHaveBeenCalledWith(initialData);
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/ai/chat",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("shows an error when a chat request fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse({ messages: [] }))
        .mockResolvedValueOnce(new Response(null, { status: 502 }))
    );

    render(<ChatSidebar onBoardUpdate={vi.fn()} />);
    await screen.findByText("What would you like to change?");
    await userEvent.type(screen.getByLabelText("Message the project assistant"), "Add a task");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => {
      expect(screen.getByText("Unable to send your message. Please try again.")).toBeInTheDocument();
    });
  });
});