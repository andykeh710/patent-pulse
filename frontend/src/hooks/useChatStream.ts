"use client";

import { useCallback, useRef, useState } from "react";

// ── Types ────────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  citations?: { verified: string[]; unverified: string[] };
  sources?: SourcePatent[];
  toolCalls?: ToolCallRecord[];
  isStreaming?: boolean;
}

export interface SourcePatent {
  doc_id: string;
  title: string;
  abstract_excerpt: string;
  assignees: string[];
  publication_date: string;
}

export interface ToolCallRecord {
  name: string;
  input: Record<string, unknown>;
  result?: Record<string, unknown>;
  status: "pending" | "done";
}

interface ChatStreamState {
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;
  conversationId: string | null;
}

// ── Hook ──────────────────────────────────────────────────────────────

export function useChatStream() {
  const [state, setState] = useState<ChatStreamState>({
    messages: [],
    isStreaming: false,
    error: null,
    conversationId: null,
  });

  const abortRef = useRef<AbortController | null>(null);
  const msgIdRef = useRef(0);

  const _nextId = () => `msg-${++msgIdRef.current}-${Date.now()}`;

  const addMessage = useCallback((msg: ChatMessage) => {
    setState((prev) => ({ ...prev, messages: [...prev.messages, msg] }));
  }, []);

  const updateLastAssistant = useCallback(
    (updater: (msg: ChatMessage) => ChatMessage) => {
      setState((prev) => {
        const msgs = [...prev.messages];
        const last = msgs[msgs.length - 1];
        if (last && last.role === "assistant") {
          msgs[msgs.length - 1] = updater(last);
        }
        return { ...prev, messages: msgs };
      });
    },
    []
  );

  const sendMessage = useCallback(
    async (content: string, conversationId?: string | null) => {
      // Abort any in-flight stream
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const userMsg: ChatMessage = {
        id: _nextId(),
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };

      const assistantMsg: ChatMessage = {
        id: _nextId(),
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
        isStreaming: true,
        toolCalls: [],
      };

      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, userMsg, assistantMsg],
        isStreaming: true,
        error: null,
      }));

      try {
        const resp = await fetch("/api/v1/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: content,
            conversation_id: conversationId || null,
          }),
          signal: controller.signal,
          credentials: "include",
        });

        if (!resp.ok) {
          const body = await resp.json().catch(() => ({}));
          if (resp.status === 402) {
            // Quota exceeded — parse structured body
            setState((prev) => ({
              ...prev,
              isStreaming: false,
              error: JSON.stringify({
                code: "quota_exceeded",
                ...body.detail,
              }),
            }));
            return;
          }
          throw new Error(`Chat stream failed: ${resp.status}`);
        }

        if (!resp.body) throw new Error("No response body");

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith("data: ")) continue;

            try {
              const event = JSON.parse(trimmed.slice(6));

              switch (event.type) {
                case "meta":
                  setState((prev) => ({
                    ...prev,
                    conversationId: event.conversation_id || null,
                  }));
                  break;

                case "token":
                  updateLastAssistant((msg) => ({
                    ...msg,
                    content: msg.content + event.content,
                  }));
                  break;

                case "tool_call_start":
                  updateLastAssistant((msg) => ({
                    ...msg,
                    toolCalls: [
                      ...(msg.toolCalls || []),
                      {
                        name: event.name,
                        input: event.input,
                        status: "pending" as const,
                      },
                    ],
                  }));
                  break;

                case "tool_call_result":
                  updateLastAssistant((msg) => {
                    const calls = [...(msg.toolCalls || [])];
                    const last = calls[calls.length - 1];
                    if (last && last.status === "pending") {
                      calls[calls.length - 1] = {
                        ...last,
                        result: event.result,
                        status: "done" as const,
                      };
                    }
                    return { ...msg, toolCalls: calls };
                  });
                  break;

                case "citations":
                  updateLastAssistant((msg) => ({
                    ...msg,
                    citations: {
                      verified: event.verified || [],
                      unverified: event.unverified || [],
                    },
                  }));
                  break;

                case "sources":
                  updateLastAssistant((msg) => ({
                    ...msg,
                    sources: event.patents || [],
                  }));
                  break;

                case "warning":
                  updateLastAssistant((msg) => {
                    const content = msg.content;
                    const warning =
                      event.code === "uncited_or_invalid_doc_ids"
                        ? event.message
                        : event.message || "";
                    return {
                      ...msg,
                      content: warning
                        ? content + `\n\n> ⚠️ ${warning}`
                        : content,
                    };
                  });
                  break;

                case "done":
                  updateLastAssistant((msg) => ({
                    ...msg,
                    isStreaming: false,
                  }));
                  setState((prev) => ({ ...prev, isStreaming: false }));
                  break;

                case "error":
                  updateLastAssistant((msg) => ({
                    ...msg,
                    content: msg.content || event.message || "An error occurred",
                    isStreaming: false,
                  }));
                  setState((prev) => ({
                    ...prev,
                    isStreaming: false,
                    error: event.message || null,
                  }));
                  break;
              }
            } catch {
              // Skip malformed SSE lines
            }
          }
        }

        updateLastAssistant((msg) => ({ ...msg, isStreaming: false }));
        setState((prev) => ({ ...prev, isStreaming: false }));
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") return;
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: (err as Error).message || "Chat request failed",
        }));
      }
    },
    [updateLastAssistant]
  );

  const clearMessages = useCallback(() => {
    abortRef.current?.abort();
    setState({
      messages: [],
      isStreaming: false,
      error: null,
      conversationId: null,
    });
  }, []);

  const setMessages = useCallback((messages: ChatMessage[]) => {
    setState((prev) => ({ ...prev, messages }));
  }, []);

  const setConversationId = useCallback((id: string | null) => {
    setState((prev) => ({ ...prev, conversationId: id }));
  }, []);

  return {
    ...state,
    sendMessage,
    addMessage,
    clearMessages,
    setMessages,
    setConversationId,
  };
}
