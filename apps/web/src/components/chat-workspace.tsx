"use client";

import { useCallback, useEffect } from "react";
import { toast } from "sonner";

import {
  streamAssistantGenerate,
  streamIntakeChat,
  streamRefinementChat,
  streamReviewResume,
  getSession,
} from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { CV, ChatMessage, ReviewApprovalPayload } from "@/lib/types";

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
    pendingReviewApproval,
    setPendingReviewApproval,
    isAwaitingReviewApproval,
    setIsAwaitingReviewApproval,
    reviewDecisions,
    clearReviewDecisions,
    setArtifactTab,
    currentThreadId,
    setCurrentThreadId,
    setReviewSubmitHandler,
    activeSessionId,
    setActiveSessionId,
    setActiveSessionStatus,
    setRequiresApiKeyOnResume,
    setChatMessages,
  } = useAppStore();

  // Hydrate from session history when activeSessionId changes
  useEffect(() => {
    if (!activeSessionId) return;

    let cancelled = false;

    const hydrate = async () => {
      try {
        const detail = await getSession(activeSessionId);
        if (cancelled) return;

        // Restore messages
        const restoredMessages: ChatMessage[] = (detail.messages ?? []).map(
          (m: Record<string, unknown>) => ({
            id: (m.message_id ?? m.id ?? crypto.randomUUID()) as string,
            role: (m.role ?? "assistant") as "user" | "assistant" | "system",
            content: (m.content ?? "") as string,
            kind: (m.kind ?? "text") as "text" | "artifact",
            timestamp: new Date((m.timestamp as string) ?? new Date().toISOString()),
          })
        );
        setChatMessages(restoredMessages);

        // Restore CV data
        if (detail.cv_data) {
          setCvData(detail.cv_data as unknown as CV);
        }

        // Restore thread ID
        setCurrentThreadId(activeSessionId);
        setActiveSessionStatus(detail.status);
        setRequiresApiKeyOnResume(detail.requires_api_key_on_resume);

        // Determine chat phase from session state
        if (detail.status === "interrupted" && detail.pending_interrupt) {
          setPendingReviewApproval(detail.pending_interrupt as unknown as ReviewApprovalPayload);
          setIsAwaitingReviewApproval(true);
          setChatPhase("generation");
          setArtifactTab("reviews");
          setAssistantStatus("awaiting_input");
        } else if (detail.has_cv) {
          setChatPhase("refinement");
          setAssistantStatus("idle");
        } else {
          setChatPhase("intake");
          setAssistantStatus("idle");
        }
      } catch {
        toast.error("Failed to load session");
      }
    };

    void hydrate();
    return () => { cancelled = true; };
  }, [
    activeSessionId,
    setActiveSessionStatus,
    setAssistantStatus,
    setArtifactTab,
    setChatMessages,
    setChatPhase,
    setCurrentThreadId,
    setCvData,
    setIsAwaitingReviewApproval,
    setPendingReviewApproval,
    setRequiresApiKeyOnResume,
  ]);

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
            onThreadStarted: (data: unknown) => {
              const payload = data as { thread_id?: string };
              if (payload.thread_id) {
                setCurrentThreadId(payload.thread_id);
              }
            },
            onArtifactUpdate: (data: unknown) => {
              const payload = data as ArtifactPayload;
              if (!payload.cv_data) {
                return;
              }

              setCvData(payload.cv_data as CV);
            },
            onInterruptPending: (data: unknown) => {
              if (cancelled) {
                return;
              }

              const payload = data as ReviewApprovalPayload;
              setPendingReviewApproval(payload);
              setIsAwaitingReviewApproval(true);
              setArtifactTab("reviews");
              setAssistantStatus("awaiting_input");

              addChatMessage(
                createTextMessage(
                  "assistant",
                  "The review committee has finished evaluating your CV. Please review their recommendations in the Reviews tab and approve or reject each item."
                )
              );
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

              // Only auto-advance if we didn't hit an interrupt
              if (!isAwaitingReviewApproval) {
                setChatPhase("refinement");
                setAssistantStatus("idle");
                addChatMessage(
                  createTextMessage(
                    "assistant",
                    "Your tailored CV is ready! You can now ask me to refine any section."
                  )
                );
              }
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
    isAwaitingReviewApproval,
    jobDescription,
    resumeText,
    reviewMode,
    reviewModel,
    selectedModel,
    setArtifactTab,
    setAssistantStatus,
    setCurrentThreadId,
    setChatPhase,
    setCvData,
    setIntakeReady,
    setIsAwaitingReviewApproval,
    setPendingReviewApproval,
    userInstructions,
  ]);

  const handleReviewSubmit = useCallback(async () => {
    if (!currentThreadId || !reviewDecisions || Object.keys(reviewDecisions).length === 0) {
      return;
    }

    setIsAwaitingReviewApproval(true);
    setAssistantStatus("streaming");

    try {
      await streamReviewResume(
        currentThreadId,
        reviewDecisions,
        {
          onArtifactUpdate: (data: unknown) => {
            const payload = data as ArtifactPayload;
            if (payload.cv_data) {
              setCvData(payload.cv_data as CV);
            }
          },
          onComplete: () => {
            setChatPhase("refinement");
            setAssistantStatus("idle");
            clearReviewDecisions();
            setPendingReviewApproval(null);
            setIsAwaitingReviewApproval(false);
            addChatMessage(
              createTextMessage(
                "assistant",
                "Your CV has been finalized based on the approved recommendations!"
              )
            );
          },
          onError: (data: unknown) => {
            const payload = data as ErrorPayload;
            toast.error(payload.error || "Failed to resume generation");
            setAssistantStatus("idle");
            setIsAwaitingReviewApproval(false);
          },
        } as Parameters<typeof streamReviewResume>[2],
        apiKey.trim() || null,
        selectedModel.trim() || null
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to resume generation";
      toast.error(message);
      setAssistantStatus("idle");
      setIsAwaitingReviewApproval(false);
    }
  }, [
    currentThreadId,
    reviewDecisions,
    setIsAwaitingReviewApproval,
    setAssistantStatus,
    setCvData,
    setChatPhase,
    clearReviewDecisions,
    setPendingReviewApproval,
    addChatMessage,
    apiKey,
    selectedModel,
  ]);

  useEffect(() => {
    setReviewSubmitHandler(handleReviewSubmit);
  }, [handleReviewSubmit, setReviewSubmitHandler]);

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
