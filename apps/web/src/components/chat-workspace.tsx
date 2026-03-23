"use client";

import { useCallback, useEffect } from "react";
import { toast } from "sonner";

import {
  streamAssistantGenerate,
  streamIntakeChat,
  streamRefinementChat,
} from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { CV, ChatMessage } from "@/lib/types";

type IntakeMessagePayload = { assistant_reply?: string };
type IntakeReadyPayload = {
  ready_to_generate?: boolean;
  extracted_constraints?: string[];
};
type ArtifactPayload = { cv_data?: unknown };
type ErrorPayload = { error?: string };

function createTextMessage(role: "user" | "assistant", content: string): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    kind: "text",
    timestamp: new Date(),
  };
}

export function ChatWorkspace() {
  const {
    uiMode,
    chatPhase,
    chatMessages,
    chatInput,
    assistantStatus,
    intakeReady,
    resumeText,
    jobDescription,
    userInstructions,
    apiKey,
    selectedModel,
    reviewMode,
    reviewModel,
    cvData,
    addChatMessage,
    setChatPhase,
    setAssistantStatus,
    setIntakeReady,
    setCvData,
    setChatInput,
  } = useAppStore();

  const handleSendMessage = useCallback(async () => {
    const trimmedInput = chatInput.trim();
    if (!trimmedInput) {
      return;
    }

    if (chatPhase !== "intake" && chatPhase !== "refinement") {
      return;
    }

    const userMessage = createTextMessage("user", trimmedInput);
    const nextMessages = [...chatMessages, userMessage];

    addChatMessage(userMessage);
    setChatInput("");
    setAssistantStatus("thinking");

    if (chatPhase === "intake") {
      let intakeSignaledReady = false;

      try {
        await streamIntakeChat(
          nextMessages,
          resumeText,
          jobDescription,
          userInstructions.trim() || null,
          {
            onMessage: (data: unknown) => {
              const payload = data as IntakeMessagePayload;
              if (!payload.assistant_reply) {
                return;
              }

              addChatMessage(createTextMessage("assistant", payload.assistant_reply));
            },
            onIntakeReady: (data: unknown) => {
              const payload = data as IntakeReadyPayload;
              const isReady = Boolean(payload.ready_to_generate);

              setIntakeReady(isReady);
              if (isReady) {
                intakeSignaledReady = true;
                setAssistantStatus("awaiting_input");
              }
            },
            onError: (data: unknown) => {
              const payload = data as ErrorPayload;
              toast.error(payload.error || "Intake chat failed.");
              setAssistantStatus("idle");
            },
            onComplete: () => {
              if (!intakeSignaledReady) {
                setAssistantStatus("idle");
              }
            },
          } as Parameters<typeof streamIntakeChat>[4],
          apiKey.trim() || null,
          selectedModel.trim() || null
        );
      } catch (error) {
        const message = error instanceof Error ? error.message : "Intake chat failed.";
        toast.error(message);
        setAssistantStatus("idle");
      }

      return;
    }

    try {
      await streamRefinementChat(
        nextMessages,
        (cvData ?? {}) as Record<string, unknown>,
        resumeText,
        jobDescription,
        userMessage.content,
        {
          onMessage: (data: unknown) => {
            const payload = data as IntakeMessagePayload;
            if (!payload.assistant_reply) {
              return;
            }

            addChatMessage(createTextMessage("assistant", payload.assistant_reply));
          },
          onArtifactUpdate: (data: unknown) => {
            const payload = data as ArtifactPayload;
            if (!payload.cv_data) {
              return;
            }

            setCvData(payload.cv_data as CV);
          },
          onError: (data: unknown) => {
            const payload = data as ErrorPayload;
            toast.error(payload.error || "Refinement failed.");
            setAssistantStatus("idle");
          },
          onComplete: () => {
            setAssistantStatus("idle");
          },
        } as Parameters<typeof streamRefinementChat>[5],
        apiKey.trim() || null,
        selectedModel.trim() || null
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Refinement failed.";
      toast.error(message);
      setAssistantStatus("idle");
    }
  }, [
    addChatMessage,
    apiKey,
    chatInput,
    chatMessages,
    chatPhase,
    cvData,
    jobDescription,
    resumeText,
    selectedModel,
    setAssistantStatus,
    setChatInput,
    setCvData,
    setIntakeReady,
    userInstructions,
  ]);

  useEffect(() => {
    if (!intakeReady || chatPhase !== "intake") {
      return;
    }

    let cancelled = false;

    const runGeneration = async () => {
      setChatPhase("generation");
      setAssistantStatus("streaming");
      setIntakeReady(false);

      const extractedConstraints: string[] = [];

      try {
        await streamAssistantGenerate(
          resumeText,
          jobDescription,
          extractedConstraints,
          {
            onArtifactUpdate: (data: unknown) => {
              const payload = data as ArtifactPayload;
              if (!payload.cv_data) {
                return;
              }

              setCvData(payload.cv_data as CV);
            },
            onError: (data: unknown) => {
              const payload = data as ErrorPayload;
              toast.error(payload.error || "Generation failed.");
              if (!cancelled) {
                setAssistantStatus("idle");
                setChatPhase("intake");
              }
            },
            onComplete: () => {
              if (cancelled) {
                return;
              }

              setChatPhase("refinement");
              setAssistantStatus("idle");
              addChatMessage(
                createTextMessage(
                  "assistant",
                  "Your tailored CV is ready! You can now ask me to refine any section."
                )
              );
            },
          } as Parameters<typeof streamAssistantGenerate>[3],
          userInstructions.trim() || null,
          apiKey.trim() || null,
          selectedModel.trim() || null,
          reviewMode,
          reviewModel.trim() || null
        );
      } catch (error) {
        const message = error instanceof Error ? error.message : "Generation failed.";
        toast.error(message);
        if (!cancelled) {
          setAssistantStatus("idle");
          setChatPhase("intake");
        }
      }
    };

    void runGeneration();

    return () => {
      cancelled = true;
    };
  }, [
    addChatMessage,
    apiKey,
    chatPhase,
    intakeReady,
    jobDescription,
    resumeText,
    reviewMode,
    reviewModel,
    selectedModel,
    setAssistantStatus,
    setChatPhase,
    setCvData,
    setIntakeReady,
    userInstructions,
  ]);

  return (
    <div className="flex h-full flex-col" data-ui-mode={uiMode}>
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {chatMessages.map((message) => (
          <div key={message.id} className={message.role === "user" ? "text-right" : "text-left"}>
            <span className="inline-block max-w-[85%] rounded-lg bg-muted px-4 py-2 text-sm">
              {message.content}
            </span>
          </div>
        ))}
        {assistantStatus === "thinking" && (
          <p className="text-sm text-muted-foreground">Assistant is thinking...</p>
        )}
      </div>

      <div className="border-t p-4">
        <input
          type="text"
          value={chatInput}
          onChange={(event) => setChatInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void handleSendMessage();
            }
          }}
          disabled={chatPhase === "generation" || assistantStatus !== "idle"}
          placeholder={chatPhase === "generation" ? "Generating CV..." : "Type your message..."}
          className="w-full rounded-lg border bg-background px-4 py-2 text-sm"
        />
      </div>
    </div>
  );
}
