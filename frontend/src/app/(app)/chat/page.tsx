"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useChatStream } from "@/hooks/useChatStream";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ConversationSidebar, upsertConversation } from "@/components/chat/ConversationSidebar";
import { QuotaIndicator, refreshQuota } from "@/components/chat/QuotaIndicator";

interface QuotaErrorBody {
  code: string;
  tier: string;
  used: number;
  limit: number;
  upgrade_url?: string;
}

export default function ChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const chat = useChatStream();
  const [input, setInput] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showQuotaModal, setShowQuotaModal] = useState(false);
  const [quotaError, setQuotaError] = useState<QuotaErrorBody | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load conversation from URL param + seed
  useEffect(() => {
    const id = searchParams.get("id");
    const seed = searchParams.get("seed");
    if (id) {
      chat.setConversationId(id);
      try {
        const raw = localStorage.getItem("chat:conv-messages:" + id);
        if (raw) {
          chat.setMessages(JSON.parse(raw));
          return; // loaded history — don't seed
        }
      } catch {
        // Ignore corrupt data
      }
    }
    // Pre-fill input from seed param (from patent page "Ask AI" button)
    if (seed) {
      setInput(seed);
    }
  }, [searchParams, chat.setConversationId, chat.setMessages]);

  // Persist messages to localStorage when they change
  useEffect(() => {
    if (chat.conversationId && chat.messages.length > 0) {
      localStorage.setItem(
        "chat:conv-messages:" + chat.conversationId,
        JSON.stringify(chat.messages)
      );
      // Update conversation list
      const lastMsg = chat.messages[chat.messages.length - 1];
      upsertConversation({
        id: chat.conversationId,
        title: chat.messages[0]?.content?.slice(0, 50) || "New conversation",
        lastMessage: lastMsg?.content?.slice(0, 80) || "",
        updatedAt: new Date().toISOString(),
      });
    }
  }, [chat.messages, chat.conversationId]);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat.messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || chat.isStreaming) return;

    setInput("");

    try {
      await chat.sendMessage(text, chat.conversationId);
      refreshQuota();
    } catch {
      if (chat.error) {
        try {
          const parsed = JSON.parse(chat.error);
          if (parsed.code === "quota_exceeded") {
            setQuotaError(parsed);
            setShowQuotaModal(true);
          }
        } catch {
          // Not a quota error
        }
      }
    }
  };

  const handleNewChat = () => {
    chat.clearMessages();
    router.replace("/chat");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)] -mx-6">
      {/* Sidebar — hidden on mobile, toggle with hamburger */}
      <div
        className={`${
          sidebarOpen ? "block" : "hidden"
        } md:block absolute md:relative z-30 h-full`}
      >
        <ConversationSidebar
          activeId={chat.conversationId}
          onNewChat={handleNewChat}
        />
        <QuotaIndicator />
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/50 z-20"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header */}
        <div className="md:hidden flex items-center gap-2 px-4 py-2 border-b border-[var(--border-subtle)]">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="text-sm font-medium text-[var(--text-secondary)]">Chat</span>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
          {chat.messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-md">
                <div className="text-4xl mb-4">💬</div>
                <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
                  Ask about patents
                </h2>
                <p className="text-sm text-[var(--text-muted)] mb-6">
                  Ask questions about patents, technologies, companies, or
                  competitive landscapes. The AI searches the database and
                  retrieves relevant patents to ground its answers.
                </p>
                <div className="grid grid-cols-1 gap-2">
                  {[
                    "What are the latest battery patents from Toyota?",
                    "Compare patent portfolios of Tesla and Rivian",
                    "Explain solid-state battery electrolyte innovations",
                  ].map((q) => (
                    <button
                      key={q}
                      onClick={() => {
                        setInput(q);
                        setTimeout(() => handleSend(), 50);
                      }}
                      className="text-left text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] px-3 py-2 rounded border border-[var(--border-subtle)] hover:bg-[var(--bg-surface)] transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {chat.messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-[var(--border-subtle)] px-4 py-3">
          <div className="flex items-end gap-2 max-w-3xl mx-auto">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about patents..."
              rows={1}
              className="flex-1 resize-none rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              disabled={chat.isStreaming}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || chat.isStreaming}
              className="flex-shrink-0 px-4 py-2.5 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-40 transition-opacity"
            >
              {chat.isStreaming ? (
                <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                "Send"
              )}
            </button>
          </div>
          <p className="text-[10px] text-[var(--text-muted)] text-center mt-2">
            {process.env.NEXT_PUBLIC_BRAND_NAME || "Invention Index 8"} chat · AI can make mistakes · Verify patent data at source
          </p>
        </div>
      </div>

      {/* Quota exceeded modal */}
      {showQuotaModal && quotaError && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-xl max-w-sm w-full p-6">
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
              Daily limit reached
            </h3>
            <p className="text-sm text-[var(--text-secondary)] mb-4">
              You&apos;ve used {quotaError.used} of {quotaError.limit} daily
              chats. Upgrade to Basic for 50/day, or come back tomorrow.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowQuotaModal(false)}
                className="flex-1 px-4 py-2 rounded-lg border border-[var(--border-subtle)] text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] transition-colors"
              >
                OK
              </button>
              <a
                href="/account/billing"
                className="flex-1 px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm text-center font-medium hover:opacity-90 transition-opacity"
              >
                Upgrade
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
