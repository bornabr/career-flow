"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { listSessions } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import type { SessionSummary } from "@/lib/types";

function statusColor(status: string): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "completed":
      return "default";
    case "running":
      return "secondary";
    case "interrupted":
      return "outline";
    case "failed":
      return "destructive";
    default:
      return "secondary";
  }
}

function statusIcon(status: string): string {
  switch (status) {
    case "completed":
      return "✓";
    case "running":
      return "●";
    case "interrupted":
      return "⏸";
    case "failed":
      return "✕";
    default:
      return "?";
  }
}

function SessionItem({
  session,
  isActive,
  onSelect,
}: {
  session: SessionSummary;
  isActive: boolean;
  onSelect: (threadId: string) => void;
}) {
  return (
    <button
      onClick={() => onSelect(session.thread_id)}
      className={`w-full rounded-lg border p-3 text-left text-sm transition-colors hover:bg-accent ${
        isActive ? "border-primary bg-accent" : ""
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate font-medium">{session.title}</span>
        <Badge variant={statusColor(session.status)} className="shrink-0 text-xs">
          {statusIcon(session.status)} {session.status}
        </Badge>
      </div>
      {session.latest_assistant_message && (
        <p className="mt-1 truncate text-xs text-muted-foreground">
          {session.latest_assistant_message}
        </p>
      )}
      <p className="mt-1 text-xs text-muted-foreground">
        {new Date(session.updated_at).toLocaleString()}
      </p>
    </button>
  );
}

function SessionList({
  onSelect,
  onNewSession,
}: {
  onSelect: (threadId: string) => void;
  onNewSession: () => void;
}) {
  const {
    sessionSummaries,
    setSessionSummaries,
    activeSessionId,
    sessionCursor,
    setSessionCursor,
  } = useAppStore();
  const [isLoading, setIsLoading] = useState(false);

  const fetchSessions = useCallback(
    async (cursor?: string | null) => {
      setIsLoading(true);
      try {
        const response = await listSessions(20, cursor);
        if (cursor) {
          setSessionSummaries([...sessionSummaries, ...response.items]);
        } else {
          setSessionSummaries(response.items);
        }
        setSessionCursor(response.next_cursor);
      } catch {
        toast.error("Failed to load sessions");
      } finally {
        setIsLoading(false);
      }
    },
    [sessionSummaries, setSessionSummaries, setSessionCursor]
  );

  useEffect(() => {
    void fetchSessions();
    // Only fetch on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b p-3">
        <Button onClick={onNewSession} variant="outline" className="w-full" size="sm">
          + New Session
        </Button>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {sessionSummaries.map((session) => (
          <SessionItem
            key={session.thread_id}
            session={session}
            isActive={session.thread_id === activeSessionId}
            onSelect={onSelect}
          />
        ))}
        {sessionSummaries.length === 0 && !isLoading && (
          <p className="py-8 text-center text-sm text-muted-foreground">No sessions yet</p>
        )}
        {isLoading && (
          <p className="py-4 text-center text-sm text-muted-foreground">Loading...</p>
        )}
        {sessionCursor && !isLoading && (
          <Button
            variant="ghost"
            size="sm"
            className="w-full"
            onClick={() => void fetchSessions(sessionCursor)}
          >
            Load more
          </Button>
        )}
      </div>
    </div>
  );
}

export function SessionHistorySidebar() {
  const { setActiveSessionId, reset } = useAppStore();

  const handleSelect = useCallback(
    (threadId: string) => {
      setActiveSessionId(threadId);
    },
    [setActiveSessionId]
  );

  const handleNewSession = useCallback(() => {
    reset();
  }, [reset]);

  return (
    <>
      {/* Desktop: inline sidebar */}
      <div className="hidden h-full w-full border-r md:block">
        <SessionList onSelect={handleSelect} onNewSession={handleNewSession} />
      </div>

      {/* Mobile: dialog-based drawer */}
      <div className="md:hidden">
        <Dialog>
          <DialogTrigger
            render={<Button variant="outline" size="sm" />}
          >
            History
          </DialogTrigger>
          <DialogContent className="max-h-[80vh] overflow-y-auto sm:max-w-[400px]">
            <SessionList onSelect={handleSelect} onNewSession={handleNewSession} />
          </DialogContent>
        </Dialog>
      </div>
    </>
  );
}
