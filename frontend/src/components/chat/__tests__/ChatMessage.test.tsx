import { render, screen } from "@testing-library/react";

// Mock react-markdown (ESM module, can't be parsed by Jest)
jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }: { children: string }) => <>{children}</>,
}));

import { ChatMessage } from "../ChatMessage";

const makeMsg = (overrides = {}) => ({
  id: "msg-1",
  role: "user" as const,
  content: "Hello",
  timestamp: "2026-01-01T00:00:00Z",
  ...overrides,
});

describe("ChatMessage", () => {
  it("renders user message as plain text", () => {
    render(<ChatMessage message={makeMsg({ role: "user", content: "What is AI?" })} />);
    expect(screen.getByText("What is AI?")).toBeInTheDocument();
  });

  it("renders assistant message content", () => {
    render(
      <ChatMessage
        message={makeMsg({
          role: "assistant",
          content: "AI stands for Artificial Intelligence.",
        })}
      />
    );
    expect(screen.getByText(/Artificial Intelligence/)).toBeInTheDocument();
  });

  it("renders verified citation badge with accent styling", () => {
    render(
      <ChatMessage
        message={makeMsg({
          role: "assistant",
          content: "See [USPTO:US12345] for details.",
          citations: { verified: ["USPTO:US12345"], unverified: [] },
        })}
      />
    );
    const badge = screen.getByText("USPTO:US12345");
    expect(badge).toBeInTheDocument();
    expect(badge.closest("a")?.className).toContain("bg-[var(--accent-muted)]");
  });

  it("renders unverified citation with warning styling", () => {
    render(
      <ChatMessage
        message={makeMsg({
          role: "assistant",
          content: "Unknown [USPTO:US99999] reference.",
          citations: { verified: [], unverified: ["USPTO:US99999"] },
        })}
      />
    );
    const badge = screen.getByText("USPTO:US99999");
    expect(badge).toBeInTheDocument();
    expect(badge.closest("a")?.className).toContain("yellow");
  });

  it("shows streaming indicator when message is streaming and empty", () => {
    render(
      <ChatMessage
        message={makeMsg({
          role: "assistant",
          content: "",
          isStreaming: true,
        })}
      />
    );
    expect(screen.getByText("Thinking...")).toBeInTheDocument();
  });

  it("renders tool call cards when present", () => {
    render(
      <ChatMessage
        message={makeMsg({
          role: "assistant",
          content: "",
          toolCalls: [
            {
              name: "search_patents",
              input: { query: "batteries" },
              status: "pending" as const,
            },
          ],
        })}
      />
    );
    expect(screen.getByText("Searching patents")).toBeInTheDocument();
  });
});
