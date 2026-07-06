"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Bot, Send, X, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useAssistant } from "@/lib/assistant/AssistantProvider";
import { useBodyScrollLock } from "@/lib/hooks/useBodyScrollLock";
import { useFocusTrap } from "@/lib/hooks/useFocusTrap";
import { cn } from "@/lib/utils/cn";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface ChatResponse {
  reply: string;
  provider: string;
  suggestions: string[];
}

function renderMarkdownLite(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={i} className="px-1 py-0.5 rounded bg-[var(--input-bg)] font-mono text-xs">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export function AIAssistantPanel() {
  const { open, setOpen, context, clearContext } = useAssistant();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();

  useBodyScrollLock(open);
  useFocusTrap(panelRef, open);

  const chatMutation = useMutation({
    mutationFn: (message: string) =>
      api<ChatResponse>("/api/v1/assistant/chat", {
        method: "POST",
        body: JSON.stringify({
          message,
          alert_id: context.alertId || null,
          offense_id: context.offenseId || null,
          siem_query: context.siemQuery || null,
        }),
      }),
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
    },
  });

  useEffect(() => {
    if (open && context.prefill && messages.length === 0) {
      setInput(context.prefill);
    }
  }, [open, context.prefill, messages.length]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, chatMutation.isPending]);

  const handleClose = useCallback(() => {
    setOpen(false);
    clearContext();
    setMessages([]);
    setInput("");
  }, [setOpen, clearContext]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") handleClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, handleClose]);

  function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || chatMutation.isPending) return;
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    chatMutation.mutate(trimmed);
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-full bg-accent text-accent-foreground shadow-lg hover:opacity-90 transition-opacity"
        aria-label="Open AI Assistant"
      >
        <Bot className="w-5 h-5" />
        <span className="text-sm font-medium hidden sm:inline">AI Assistant</span>
      </button>
    );
  }

  return (
    <div
      ref={panelRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="fixed bottom-6 right-6 z-50 w-[min(420px,calc(100vw-2rem))] flex flex-col rounded-xl border border-border bg-card shadow-2xl overflow-hidden max-h-[min(560px,calc(100vh-6rem))] animate-scale-in"
    >
      <header className="flex items-center justify-between px-4 py-3 border-b border-border-subtle bg-[var(--sidebar-hover)]">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-accent" aria-hidden />
          <div>
            <p id={titleId} className="text-sm font-semibold">AI Security Assistant</p>
            <p className="text-[10px] text-muted normal-case">
              {context.alertId ? "Alert context" : context.offenseId ? "Offense context" : "SOC copilot"}
            </p>
          </div>
        </div>
        <button type="button" onClick={handleClose} className="btn-ghost p-1.5" aria-label="Close assistant">
          <X className="w-4 h-4" />
        </button>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px]">
        {messages.length === 0 && (
          <div className="text-sm text-muted space-y-2">
            <p>Ask about alerts, investigation steps, SIEM queries, or offense triage.</p>
            <div className="flex flex-wrap gap-1.5">
              {[
                "Explain this alert",
                "Investigation steps",
                "Show failed logins from last hour",
              ].map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => sendMessage(s)}
                  className="btn-ghost text-xs py-1 px-2"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              "text-sm rounded-lg px-3 py-2 max-w-[95%] whitespace-pre-wrap",
              msg.role === "user"
                ? "ml-auto bg-accent/20 text-foreground"
                : "mr-auto bg-[var(--input-bg)] text-muted",
            )}
          >
            {msg.role === "assistant" ? renderMarkdownLite(msg.content) : msg.content}
          </div>
        ))}
        {chatMutation.isPending && (
          <div className="text-xs text-muted animate-pulse">Thinking…</div>
        )}
        {chatMutation.isError && (
          <p className="text-xs text-danger">{chatMutation.error.message}</p>
        )}
      </div>

      {chatMutation.data?.suggestions && chatMutation.data.suggestions.length > 0 && (
        <div className="px-3 pb-2 flex flex-wrap gap-1">
          {chatMutation.data.suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => sendMessage(s)}
              className="btn-ghost text-[10px] py-0.5 px-2"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <form
        className="flex gap-2 p-3 border-t border-border-subtle"
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the assistant…"
          className="input-siem flex-1 text-sm"
          disabled={chatMutation.isPending}
        />
        <button type="submit" className="btn-primary p-2" disabled={!input.trim() || chatMutation.isPending}>
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
