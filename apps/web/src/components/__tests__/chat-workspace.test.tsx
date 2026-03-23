import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ChatWorkspace } from "../chat-workspace";
import { useAppStore } from "@/lib/store";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  streamIntakeChat: vi.fn(),
  streamAssistantGenerate: vi.fn(),
  streamRefinementChat: vi.fn(),
}));

describe("ChatWorkspace", () => {
  beforeEach(() => {
    useAppStore.getState().reset();
    vi.clearAllMocks();
    useAppStore.setState({
      uiMode: "assistant",
      resumeText: "Sample resume",
      jobDescription: "Sample job description",
    });
  });

  it("renders intake composer initially", () => {
    useAppStore.setState({ chatPhase: "intake" });

    render(<ChatWorkspace />);

    expect(screen.getByPlaceholderText("Type your message...")).toBeInTheDocument();
    expect(useAppStore.getState().chatPhase).toBe("intake");
  });

  it("calls streamIntakeChat when sending message in intake phase", async () => {
    const mockStreamIntakeChat = vi.mocked(api.streamIntakeChat);
    mockStreamIntakeChat.mockResolvedValue(undefined);
    useAppStore.setState({
      chatPhase: "intake",
      chatInput: "What should I emphasize?",
    });

    render(<ChatWorkspace />);

    const input = screen.getByPlaceholderText("Type your message...");
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(mockStreamIntakeChat).toHaveBeenCalledOnce();
    });
    expect(useAppStore.getState().chatMessages.at(-1)?.content).toBe("What should I emphasize?");
  });

  it("auto-triggers generation when intakeReady becomes true", async () => {
    const mockStreamGenerate = vi.mocked(api.streamAssistantGenerate);
    mockStreamGenerate.mockResolvedValue(undefined);

    render(<ChatWorkspace />);

    act(() => {
      useAppStore.setState({ intakeReady: true, chatPhase: "intake" });
    });

    await waitFor(() => {
      expect(mockStreamGenerate).toHaveBeenCalledOnce();
      expect(useAppStore.getState().chatPhase).toBe("generation");
      expect(useAppStore.getState().assistantStatus).toBe("streaming");
    });
  });

  it("transitions generation to refinement on completion", async () => {
    const mockStreamGenerate = vi.mocked(api.streamAssistantGenerate);
    mockStreamGenerate.mockImplementation(async (...args) => {
      const handlers = args[3] as { onComplete?: () => void };
      handlers.onComplete?.();
    });

    render(<ChatWorkspace />);

    act(() => {
      useAppStore.setState({ intakeReady: true, chatPhase: "intake" });
    });

    await waitFor(() => {
      expect(useAppStore.getState().chatPhase).toBe("refinement");
      expect(useAppStore.getState().assistantStatus).toBe("idle");
    });

    expect(
      useAppStore
        .getState()
        .chatMessages.some((msg) => msg.content.includes("Your tailored CV is ready"))
    ).toBe(true);
  });

  it("calls streamRefinementChat when sending message in refinement phase", async () => {
    const mockStreamRefinementChat = vi.mocked(api.streamRefinementChat);
    mockStreamRefinementChat.mockResolvedValue(undefined);

    useAppStore.setState({
      chatPhase: "refinement",
      chatInput: "Please make the summary shorter.",
      cvData: { name: "Jane Doe", location: "NYC", sections: { Summary: ["x"], Skills: [], Education: [], Experience: [] } },
    });

    render(<ChatWorkspace />);

    const input = screen.getByPlaceholderText("Type your message...");
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(mockStreamRefinementChat).toHaveBeenCalledOnce();
    });
    expect(useAppStore.getState().chatMessages.at(-1)?.content).toBe(
      "Please make the summary shorter."
    );
  });

  it("disables input during generation phase", () => {
    useAppStore.setState({ chatPhase: "generation", assistantStatus: "streaming" });

    render(<ChatWorkspace />);

    const input = screen.getByPlaceholderText("Generating CV...");
    expect(input).toBeDisabled();
  });
});
