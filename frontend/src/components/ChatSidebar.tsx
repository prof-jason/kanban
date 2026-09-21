"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiFetch, UnauthorizedError } from "@/lib/api";
import type { BoardData } from "@/lib/kanban";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type ChatSidebarProps = {
  onBoardUpdate: (board: BoardData) => void;
  onUnauthorized?: () => void;
};

export const ChatSidebar = ({ onBoardUpdate, onUnauthorized }: ChatSidebarProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const response = await apiFetch("/api/ai/history");
        if (!response.ok) {
          throw new Error("Unable to load chat history.");
        }
        const data = (await response.json()) as { messages: ChatMessage[] };
        setMessages(data.messages);
      } catch (error) {
        if (error instanceof UnauthorizedError) {
          onUnauthorized?.();
        } else {
          setError("Unable to load chat history.");
        }
      } finally {
        setIsLoading(false);
      }
    };

    void loadHistory();
  }, [onUnauthorized]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      return;
    }

    setError("");
    setIsSubmitting(true);
    try {
      const response = await apiFetch("/api/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmedQuestion }),
      });
      if (!response.ok) {
        throw new Error("Unable to send your message.");
      }
      const data = (await response.json()) as { response: string; board: BoardData };
      setMessages((currentMessages) => [
        ...currentMessages,
        { role: "user", content: trimmedQuestion },
        { role: "assistant", content: data.response },
      ]);
      setQuestion("");
      onBoardUpdate(data.board);
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        onUnauthorized?.();
      } else {
        setError("Unable to send your message. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <aside className="flex min-h-[520px] flex-col border border-[var(--stroke)] bg-white p-5 shadow-[var(--shadow)] xl:sticky xl:top-6 xl:max-h-[calc(100vh-3rem)]">
      <div className="border-b border-[var(--stroke)] pb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--primary-blue)]">
          AI workspace
        </p>
        <h2 className="mt-2 font-display text-xl font-semibold text-[var(--navy-dark)]">Project assistant</h2>
      </div>

      <div className="flex flex-1 flex-col gap-3 overflow-y-auto py-5" aria-live="polite">
        {isLoading && <p className="text-sm text-[var(--gray-text)]">Loading conversation...</p>}
        {!isLoading && messages.length === 0 && (
          <p className="text-sm leading-6 text-[var(--gray-text)]">What would you like to change?</p>
        )}
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={
              message.role === "user"
                ? "self-end bg-[var(--navy-dark)] px-3 py-2 text-sm text-white"
                : "border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm leading-6 text-[var(--navy-dark)]"
            }
          >
            {message.content}
          </div>
        ))}
        {isSubmitting && <p className="text-sm text-[var(--gray-text)]">Working...</p>}
      </div>

      <form onSubmit={handleSubmit} className="border-t border-[var(--stroke)] pt-4">
        <label className="sr-only" htmlFor="ai-question">Message the project assistant</label>
        <textarea
          id="ai-question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about your board"
          rows={3}
          disabled={isSubmitting}
          className="w-full resize-none border border-[var(--stroke)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] disabled:opacity-60"
        />
        {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
        <button
          type="submit"
          disabled={isSubmitting || !question.trim()}
          className="mt-3 w-full bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-60"
        >
          {isSubmitting ? "Sending..." : "Send"}
        </button>
      </form>
    </aside>
  );
};
