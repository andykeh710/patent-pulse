"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface ConversationMeta {
  id: string;
  title: string;
  lastMessage: string;
  updatedAt: string;
}

const STORAGE_KEY = "chat:conversations";

function loadConversations(): ConversationMeta[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveConversations(convs: ConversationMeta[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(convs));
}

export function upsertConversation(meta: ConversationMeta) {
  const convs = loadConversations();
  const idx = convs.findIndex((c) => c.id === meta.id);
  if (idx >= 0) {
    convs[idx] = { ...convs[idx], ...meta };
  } else {
    convs.unshift(meta);
  }
  // Keep max 50
  saveConversations(convs.slice(0, 50));
}

function groupByDate(convs: ConversationMeta[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);

  const groups: { label: string; items: ConversationMeta[] }[] = [];
  const todayItems: ConversationMeta[] = [];
  const yesterdayItems: ConversationMeta[] = [];
  const olderItems: ConversationMeta[] = [];

  for (const c of convs) {
    const d = new Date(c.updatedAt);
    if (d >= today) {
      todayItems.push(c);
    } else if (d >= yesterday) {
      yesterdayItems.push(c);
    } else {
      olderItems.push(c);
    }
  }

  if (todayItems.length) groups.push({ label: "Today", items: todayItems });
  if (yesterdayItems.length) groups.push({ label: "Yesterday", items: yesterdayItems });
  if (olderItems.length) groups.push({ label: "Older", items: olderItems });

  return groups;
}

export function ConversationSidebar({
  activeId,
  onNewChat,
}: {
  activeId: string | null;
  onNewChat: () => void;
}) {
  const router = useRouter();
  const [convs, setConvs] = useState<ConversationMeta[]>([]);

  useEffect(() => {
    setConvs(loadConversations());
    const onStorage = () => setConvs(loadConversations());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const groups = groupByDate(convs);

  return (
    <div className="w-64 flex-shrink-0 border-r border-[var(--border-subtle)] bg-[var(--bg-elevated)] h-full overflow-y-auto">
      {/* New chat button */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-[var(--border-subtle)] hover:bg-[var(--bg-surface)] transition-colors text-sm text-[var(--text-primary)]"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New chat
        </button>
      </div>

      {/* Conversation list */}
      <div className="px-3 pb-3">
        {groups.map((group) => (
          <div key={group.label} className="mb-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] px-1 mb-1">
              {group.label}
            </div>
            {group.items.map((conv) => (
              <button
                key={conv.id}
                onClick={() => router.push(`/chat?id=${conv.id}`)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors mb-0.5 ${
                  activeId === conv.id
                    ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]"
                }`}
              >
                <div className="font-medium truncate">{conv.title || "New conversation"}</div>
                <div className="text-[var(--text-muted)] truncate mt-0.5">
                  {conv.lastMessage || "No messages yet"}
                </div>
              </button>
            ))}
          </div>
        ))}

        {convs.length === 0 && (
          <div className="text-xs text-[var(--text-muted)] px-1 py-2">
            No conversations yet. Start one above.
          </div>
        )}
      </div>
    </div>
  );
}
