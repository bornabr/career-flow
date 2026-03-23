import { describe, it, expect, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatMessageList } from "../chat-message-list";
import type { ChatMessage } from "@/lib/types";

describe("ChatMessageList", () => {
  beforeAll(() => {
    window.HTMLElement.prototype.scrollIntoView = function() {};
  });

  it("renders empty state when there are no messages", () => {
    render(<ChatMessageList messages={[]} />);
    expect(screen.getByText("Start a conversation...")).toBeInTheDocument();
  });

  it("renders messages with correct alignment and styling", () => {
    const messages: ChatMessage[] = [
      {
        id: "1",
        role: "user",
        content: "Hello assistant",
        kind: "text",
        timestamp: new Date("2024-01-01T10:00:00Z"),
      },
      {
        id: "2",
        role: "assistant",
        content: "Hello user",
        kind: "text",
        timestamp: new Date("2024-01-01T10:01:00Z"),
      },
    ];

    const { container } = render(<ChatMessageList messages={messages} />);
    
    expect(screen.getByText("Hello assistant")).toBeInTheDocument();
    expect(screen.getByText("Hello user")).toBeInTheDocument();

    const userMessageContainer = screen.getByText("Hello assistant").parentElement;
    expect(userMessageContainer).toHaveClass("items-end", "text-right");

    const assistantMessageContainer = screen.getByText("Hello user").parentElement;
    expect(assistantMessageContainer).toHaveClass("items-start", "text-left");
  });

  it("displays timestamps in human-readable format", () => {
    const date = new Date("2024-01-01T10:00:00Z");
    const messages: ChatMessage[] = [
      {
        id: "1",
        role: "user",
        content: "Test message",
        kind: "text",
        timestamp: date,
      },
    ];

    render(<ChatMessageList messages={messages} />);
    
    const formattedTime = new Intl.DateTimeFormat("en-US", {
      hour: "numeric",
      minute: "numeric",
    }).format(date);

    expect(screen.getByText(formattedTime)).toBeInTheDocument();
  });
});
