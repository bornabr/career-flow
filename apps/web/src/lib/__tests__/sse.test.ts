import { describe, it, expect, vi } from "vitest";
import { parseSSE, EventHandlers } from "../sse";

describe("parseSSE", () => {
  describe("single event parsing", () => {
    it("should parse a single event and call correct handler", async () => {
      const onRunStarted = vi.fn();
      const handlers: EventHandlers = { onRunStarted };

      const eventData = {
        type: "run.started",
        timestamp: "2026-03-16T10:00:00+00:00",
        data: { thread_id: "test-123", mode: "standard" },
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        { status: 200 }
      );

      await parseSSE(response, handlers);

      expect(onRunStarted).toHaveBeenCalledOnce();
      expect(onRunStarted).toHaveBeenCalledWith(eventData.data);
    });

    it("should parse step.started event", async () => {
      const onStepStarted = vi.fn();
      const handlers: EventHandlers = { onStepStarted };

      const eventData = {
        type: "step.started",
        timestamp: "2026-03-16T10:00:01+00:00",
        data: { step: "generation", description: "Tailoring CV..." },
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        { status: 200 }
      );

      await parseSSE(response, handlers);

      expect(onStepStarted).toHaveBeenCalledWith(eventData.data);
    });

    it("should parse step.completed event", async () => {
      const onStepCompleted = vi.fn();
      const handlers: EventHandlers = { onStepCompleted };

      const eventData = {
        type: "step.completed",
        timestamp: "2026-03-16T10:00:05+00:00",
        data: { step: "generation", duration_ms: 4500 },
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        { status: 200 }
      );

      await parseSSE(response, handlers);

      expect(onStepCompleted).toHaveBeenCalledWith(eventData.data);
    });

    it("should parse review.memo event", async () => {
      const onReviewMemo = vi.fn();
      const handlers: EventHandlers = { onReviewMemo };

      const reviewData = {
        reviewer: "hr",
        score: 8,
        summary: "Good alignment",
        suggestions: [],
      };

      const eventData = {
        type: "review.memo",
        timestamp: "2026-03-16T10:00:10+00:00",
        data: reviewData,
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        { status: 200 }
      );

      await parseSSE(response, handlers);

      expect(onReviewMemo).toHaveBeenCalledWith(reviewData);
    });

    it("should parse review.failed event", async () => {
      const onReviewFailed = vi.fn();
      const handlers: EventHandlers = { onReviewFailed };

      const eventData = {
        type: "review.failed",
        timestamp: "2026-03-16T10:00:15+00:00",
        data: { reviewer: "technical", error: "API timeout" },
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        { status: 200 }
      );

      await parseSSE(response, handlers);

      expect(onReviewFailed).toHaveBeenCalledWith(eventData.data);
    });

    it("should parse validation.completed event", async () => {
      const onValidationCompleted = vi.fn();
      const handlers: EventHandlers = { onValidationCompleted };

      const eventData = {
        type: "validation.completed",
        timestamp: "2026-03-16T10:00:20+00:00",
        data: {
          ats_issues: ["Missing keyword: python"],
          hallucination_warnings: [],
        },
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        { status: 200 }
      );

      await parseSSE(response, handlers);

      expect(onValidationCompleted).toHaveBeenCalledWith(eventData.data);
    });

    it("should parse result event", async () => {
      const onResult = vi.fn();
      const handlers: EventHandlers = { onResult };

      const resultData = {
        cv_data: { name: "John Doe", experience: [] },
        review_panel: null,
      };

      const eventData = {
        type: "result",
        timestamp: "2026-03-16T10:00:25+00:00",
        data: resultData,
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        { status: 200 }
      );

      await parseSSE(response, handlers);

      expect(onResult).toHaveBeenCalledWith(resultData);
    });

    it("should parse error event", async () => {
      const onError = vi.fn();
      const handlers: EventHandlers = { onError };

      const eventData = {
        type: "error",
        timestamp: "2026-03-16T10:00:30+00:00",
        data: { error: "LLM API error", details: "Rate limited" },
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        { status: 200 }
      );

      await parseSSE(response, handlers);

      expect(onError).toHaveBeenCalledWith(eventData.data);
    });

    it("should parse run.completed event", async () => {
      const onRunCompleted = vi.fn();
      const handlers: EventHandlers = { onRunCompleted };

      const eventData = {
        type: "run.completed",
        timestamp: "2026-03-16T10:00:35+00:00",
        data: { success: true, duration_ms: 35000 },
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        { status: 200 }
      );

      await parseSSE(response, handlers);

      expect(onRunCompleted).toHaveBeenCalledWith(eventData.data);
    });
  });

  describe("multiple event parsing", () => {
    it("should parse multiple events and call handlers in order", async () => {
      const onRunStarted = vi.fn();
      const onStepStarted = vi.fn();
      const onStepCompleted = vi.fn();

      const handlers: EventHandlers = {
        onRunStarted,
        onStepStarted,
        onStepCompleted,
      };

      const events = [
        {
          type: "run.started",
          timestamp: "2026-03-16T10:00:00+00:00",
          data: { thread_id: "test-123", mode: "standard" },
        },
        {
          type: "step.started",
          timestamp: "2026-03-16T10:00:01+00:00",
          data: { step: "generation", description: "Tailoring CV..." },
        },
        {
          type: "step.completed",
          timestamp: "2026-03-16T10:00:05+00:00",
          data: { step: "generation", duration_ms: 4500 },
        },
      ];

      const body = events
        .map((event) => `data: ${JSON.stringify(event)}`)
        .join("\n\n");

      const response = new Response(body + "\n\n", { status: 200 });

      await parseSSE(response, handlers);

      expect(onRunStarted).toHaveBeenCalledOnce();
      expect(onStepStarted).toHaveBeenCalledOnce();
      expect(onStepCompleted).toHaveBeenCalledOnce();
    });

    it("should parse review events from multiple reviewers", async () => {
      const onReviewMemo = vi.fn();
      const handlers: EventHandlers = { onReviewMemo };

      const events = [
        {
          type: "review.memo",
          timestamp: "2026-03-16T10:00:10+00:00",
          data: { reviewer: "hr", score: 8, summary: "Good alignment" },
        },
        {
          type: "review.memo",
          timestamp: "2026-03-16T10:00:12+00:00",
          data: { reviewer: "technical", score: 9, summary: "Strong skills" },
        },
        {
          type: "review.memo",
          timestamp: "2026-03-16T10:00:14+00:00",
          data: { reviewer: "ats", score: 7, summary: "Needs keywords" },
        },
      ];

      const body = events
        .map((event) => `data: ${JSON.stringify(event)}`)
        .join("\n\n");

      const response = new Response(body + "\n\n", { status: 200 });

      await parseSSE(response, handlers);

      expect(onReviewMemo).toHaveBeenCalledTimes(3);
      expect(onReviewMemo).toHaveBeenNthCalledWith(1, events[0].data);
      expect(onReviewMemo).toHaveBeenNthCalledWith(2, events[1].data);
      expect(onReviewMemo).toHaveBeenNthCalledWith(3, events[2].data);
    });

    it("should handle mixed event types", async () => {
      const onRunStarted = vi.fn();
      const onStepStarted = vi.fn();
      const onReviewMemo = vi.fn();
      const onError = vi.fn();
      const onRunCompleted = vi.fn();

      const handlers: EventHandlers = {
        onRunStarted,
        onStepStarted,
        onReviewMemo,
        onError,
        onRunCompleted,
      };

      const events = [
        {
          type: "run.started",
          timestamp: "2026-03-16T10:00:00+00:00",
          data: { thread_id: "test", mode: "review" },
        },
        {
          type: "step.started",
          timestamp: "2026-03-16T10:00:01+00:00",
          data: { step: "hr_review", description: "HR review..." },
        },
        {
          type: "review.memo",
          timestamp: "2026-03-16T10:00:05+00:00",
          data: { reviewer: "hr", score: 8 },
        },
        {
          type: "error",
          timestamp: "2026-03-16T10:00:10+00:00",
          data: { error: "Technical review failed" },
        },
        {
          type: "run.completed",
          timestamp: "2026-03-16T10:00:15+00:00",
          data: { success: false, duration_ms: 15000 },
        },
      ];

      const body = events
        .map((event) => `data: ${JSON.stringify(event)}`)
        .join("\n\n");

      const response = new Response(body + "\n\n", { status: 200 });

      await parseSSE(response, handlers);

      expect(onRunStarted).toHaveBeenCalledOnce();
      expect(onStepStarted).toHaveBeenCalledOnce();
      expect(onReviewMemo).toHaveBeenCalledOnce();
      expect(onError).toHaveBeenCalledOnce();
      expect(onRunCompleted).toHaveBeenCalledOnce();
    });
  });

  describe("error handling", () => {
    it("should skip empty events when split by double newline", async () => {
      const onStepStarted = vi.fn();
      const handlers: EventHandlers = { onStepStarted };

      const eventData = {
        type: "step.started",
        timestamp: "2026-03-16T10:00:01+00:00",
        data: { step: "generation" },
      };

      // Empty event followed by valid event - SSE spec: events separated by \n\n
      const body =
        `data: ${JSON.stringify(eventData)}\n\n` + // First valid event
        `\n\n` + // Empty event (will be empty string after split)
        `data: ${JSON.stringify(eventData)}\n\n`; // Second valid event

      const response = new Response(body, { status: 200 });

      await parseSSE(response, handlers);

      expect(onStepStarted).toHaveBeenCalledTimes(2);
    });

    it("should parse only valid data: prefixed events", async () => {
      const onStepStarted = vi.fn();
      const handlers: EventHandlers = { onStepStarted };

      const eventData = {
        type: "step.started",
        timestamp: "2026-03-16T10:00:01+00:00",
        data: { step: "generation" },
      };

      // In SSE, each event is ONE LINE starting with "data:"
      // Multiple headers before it don't matter - we only parse lines with "data:"
      const body =
        `event: step\nid: 123\ndata: ${JSON.stringify(eventData)}\n\n`;

      const response = new Response(body, { status: 200 });

      await parseSSE(response, handlers);

      // After split on \n\n, we get one chunk with multiple lines
      // Parser should only parse the one starting with "data:"
      expect(onStepStarted).toHaveBeenCalledOnce();
    });

    it("should handle invalid JSON gracefully", async () => {
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      const onStepStarted = vi.fn();
      const handlers: EventHandlers = { onStepStarted };

      const eventData = {
        type: "step.started",
        timestamp: "2026-03-16T10:00:01+00:00",
        data: { step: "generation" },
      };

      // Invalid JSON followed by valid event
      const body =
        `data: {invalid json}\n\n` +
        `data: ${JSON.stringify(eventData)}\n\n`;

      const response = new Response(body, { status: 200 });

      await parseSSE(response, handlers);

      // Should have logged error and continued
      expect(consoleSpy).toHaveBeenCalledWith(
        "Failed to parse SSE event JSON:",
        expect.any(Error)
      );
      expect(onStepStarted).toHaveBeenCalledOnce();

      consoleSpy.mockRestore();
    });

    it("should not crash on missing handler", async () => {
      // Create minimal handlers (no onStepStarted handler)
      const handlers: EventHandlers = {};

      const eventData = {
        type: "step.started",
        timestamp: "2026-03-16T10:00:01+00:00",
        data: { step: "generation" },
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        { status: 200 }
      );

      // Should not throw
      await expect(parseSSE(response, handlers)).resolves.toBeUndefined();
    });

    it("should handle empty stream gracefully", async () => {
      const handlers: EventHandlers = {
        onStepStarted: vi.fn(),
      };

      const response = new Response("", { status: 200 });

      await expect(parseSSE(response, handlers)).resolves.toBeUndefined();
      expect(handlers.onStepStarted).not.toHaveBeenCalled();
    });

    it("should handle stream with only whitespace", async () => {
      const handlers: EventHandlers = {
        onStepStarted: vi.fn(),
      };

      const response = new Response("\n\n   \n\n", { status: 200 });

      await expect(parseSSE(response, handlers)).resolves.toBeUndefined();
      expect(handlers.onStepStarted).not.toHaveBeenCalled();
    });

    it("should handle incomplete events", async () => {
      const onStepStarted = vi.fn();
      const handlers: EventHandlers = { onStepStarted };

      const incompleteEvent = {
        type: "step.started",
        timestamp: "2026-03-16T10:00:01+00:00",
        data: { step: "generation" },
      };

      // Event without trailing double newline
      const body = `data: ${JSON.stringify(incompleteEvent)}`;

      const response = new Response(body, { status: 200 });

      await parseSSE(response, handlers);

      // Should still parse the incomplete event
      expect(onStepStarted).toHaveBeenCalledOnce();
    });
  });

  describe("handler invocation", () => {
    it("should pass event data to handler", async () => {
      const onStepCompleted = vi.fn();
      const handlers: EventHandlers = { onStepCompleted };

      const stepData = { step: "generation", duration_ms: 5000 };
      const eventData = {
        type: "step.completed",
        timestamp: "2026-03-16T10:00:05+00:00",
        data: stepData,
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        { status: 200 }
      );

      await parseSSE(response, handlers);

      expect(onStepCompleted).toHaveBeenCalledWith(stepData);
    });

    it("should handle complex nested data structures", async () => {
      const onResult = vi.fn();
      const handlers: EventHandlers = { onResult };

      const complexData = {
        cv_data: {
          name: "John Doe",
          contact: {
            email: "john@example.com",
            phone: "+1234567890",
          },
          experience: [
            {
              title: "Engineer",
              company: "Acme",
              duration: "2 years",
              bullets: ["Built things", "Fixed bugs"],
            },
          ],
          skills: ["JavaScript", "Python", "Go"],
        },
        review_panel: {
          reviews: [
            { reviewer: "hr", score: 8 },
            { reviewer: "technical", score: 9 },
          ],
          consensus_score: 8.5,
        },
      };

      const eventData = {
        type: "result",
        timestamp: "2026-03-16T10:00:25+00:00",
        data: complexData,
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        { status: 200 }
      );

      await parseSSE(response, handlers);

      expect(onResult).toHaveBeenCalledWith(complexData);
    });
  });

  describe("type correctness", () => {
    it("should accept Response objects", async () => {
      const onStepStarted = vi.fn();
      const handlers: EventHandlers = { onStepStarted };

      const eventData = {
        type: "step.started",
        timestamp: "2026-03-16T10:00:01+00:00",
        data: { step: "generation" },
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        {
          status: 200,
          headers: { "content-type": "text/event-stream" },
        }
      );

      await parseSSE(response, handlers);

      expect(onStepStarted).toHaveBeenCalled();
    });

    it("should accept partial EventHandlers", async () => {
      const onRunStarted = vi.fn();
      const handlers: EventHandlers = { onRunStarted };
      // Note: Only onRunStarted provided, other handlers are undefined

      const eventData = {
        type: "run.started",
        timestamp: "2026-03-16T10:00:00+00:00",
        data: { thread_id: "test" },
      };

      const response = new Response(
        `data: ${JSON.stringify(eventData)}\n\n`,
        { status: 200 }
      );

      await parseSSE(response, handlers);

      expect(onRunStarted).toHaveBeenCalled();
    });
  });
});
