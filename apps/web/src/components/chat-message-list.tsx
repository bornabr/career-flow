import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/lib/types";

interface ChatMessageListProps {
  messages: ChatMessage[];
}

export function ChatMessageList({ messages }: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-4 text-center text-muted-foreground">
        <p>Start a conversation...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-3 overflow-y-auto p-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex flex-col ${
            message.role === "user" ? "items-end text-right" : "items-start text-left"
          }`}
        >
          <span
            className={`inline-block max-w-[85%] rounded-lg px-4 py-2 text-sm ${
              message.role === "user"
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-foreground"
            }`}
          >
            {message.content}
          </span>
          <span className="mt-1 text-xs text-muted-foreground">
            {new Intl.DateTimeFormat("en-US", {
              hour: "numeric",
              minute: "numeric",
            }).format(new Date(message.timestamp))}
          </span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
