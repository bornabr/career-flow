/**
 * SSE (Server-Sent Events) Client
 * Parses text/event-stream format and calls handlers for each event type.
 *
 * Wire format:
 * data: {"type": "event.name", "timestamp": "ISO8601", "data": {...}}\n\n
 */

export interface SSEEvent {
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface EventHandlers {
  onRunStarted?: (data: unknown) => void;
  onStepStarted?: (data: unknown) => void;
  onStepCompleted?: (data: unknown) => void;
  onReviewMemo?: (data: unknown) => void;
  onReviewFailed?: (data: unknown) => void;
  onValidationCompleted?: (data: unknown) => void;
  onResult?: (data: unknown) => void;
  onError?: (data: unknown) => void;
  onRunCompleted?: (data: unknown) => void;
  onInterruptPending?: (data: unknown) => void;
  onThreadStarted?: (data: unknown) => void;
  onArtifactUpdate?: (data: unknown) => void;
  onMessage?: (data: unknown) => void;
  onIntakeReady?: (data: unknown) => void;
  onComplete?: (data: unknown) => void;
}

/**
 * Parse Server-Sent Events from response and call handlers
 * @param response - Response object from fetch (must have text() method)
 * @param handlers - Map of event type to handler function
 * @throws Error if response body cannot be read
 */
export async function parseSSE(
  response: Response,
  handlers: EventHandlers
): Promise<void> {
  const text = await response.text();

  // Split on double newline to separate event blocks
  const blocks = text.split("\n\n");

  for (const block of blocks) {
    // Skip empty blocks
    if (!block.trim()) {
      continue;
    }

    // Each block can have multiple lines (event:, id:, data:, etc.)
    // We only care about lines starting with 'data: '
    const lines = block.split("\n");

    for (const line of lines) {
      if (!line.startsWith("data: ")) {
        continue;
      }

      try {
        // Remove 'data: ' prefix
        const jsonString = line.slice(6);

        // Parse JSON
        const event: SSEEvent = JSON.parse(jsonString);

        // Call handler based on event type
        const handlerKey = `on${
          event.type
            .split(".")
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join("")
        }` as keyof EventHandlers;

        const handler = handlers[handlerKey];
        if (handler) {
          handler(event.data);
        }
      } catch (err) {
        // Log parse errors but continue processing remaining events
        if (err instanceof SyntaxError) {
          console.error("Failed to parse SSE event JSON:", err);
        } else {
          console.error("Error processing SSE event:", err);
        }
      }
    }
  }
}
