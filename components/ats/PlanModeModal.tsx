"use client";

import { useEffect, useRef, useState } from "react";
import { ChatMessage, PlanModeResponse, WeakBullet } from "./types";

type Props = {
  isOpen: boolean;
  bullet: WeakBullet | null;
  currentBullet: string;
  jobDescription: string;
  messages: ChatMessage[];
  options: string[];
  loading: boolean;
  onClose: () => void;
  onMessagesChange: (messages: ChatMessage[]) => void;
  onOptionsChange: (options: string[]) => void;
  onCurrentBulletChange: (value: string) => void;
  onApplyOption: (value: string) => void;
};

const THINKING_PLACEHOLDER = "__thinking__";

function ThinkingText() {
  const [dots, setDots] = useState("");

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => {
        if (prev === "...") return "";
        return prev + ".";
      });
    }, 400);

    return () => clearInterval(interval);
  }, []);

  return (
    <p className="whitespace-pre-wrap leading-6 text-slate-500">
      Thinking{dots}
    </p>
  );
}

export default function PlanModeModal({
  isOpen,
  bullet,
  currentBullet,
  jobDescription,
  messages,
  options,
  loading,
  onClose,
  onMessagesChange,
  onOptionsChange,
  onCurrentBulletChange,
  onApplyOption,
}: Props) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, options, loading]);

  if (!isOpen || !bullet) return null;

  function refreshChat() {
    onMessagesChange([]);
    onOptionsChange([]);
    setInput("");
  }

  async function sendMessage(messageText?: string) {
    const userText = (messageText ?? input).trim();
    if (!userText || loading) return;

    const userMessage: ChatMessage = { role: "user", content: userText };
    const thinkingMessage: ChatMessage = {
      role: "assistant",
      content: THINKING_PLACEHOLDER,
    };

    onMessagesChange([...messages, userMessage, thinkingMessage]);
    onOptionsChange([]);
    setInput("");

    try {
      const res = await fetch("http://127.0.0.1:8000/plan-mode/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          bullet_id: bullet?.id,
          bullet_text: bullet?.text,
          current_bullet: currentBullet,
          bullet_reasons: bullet?.reasons,
          job_description: jobDescription,
          user_message: userText,
          conversation_history: [...messages, userMessage],
        }),
      });

      if (!res.ok) {
        throw new Error(`Plan mode failed: ${res.status}`);
      }

      const data: PlanModeResponse = await res.json();

      const assistantText =
        data.mode === "question" && data.question
          ? `${data.reply}\n\n${data.question}`
          : data.reply;

      onMessagesChange([
        ...messages,
        userMessage,
        { role: "assistant", content: assistantText },
      ]);
      onOptionsChange(data.options ?? []);
      onCurrentBulletChange(data.current_bullet);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Something went wrong in plan mode.";

      onMessagesChange([
        ...messages,
        userMessage,
        { role: "assistant", content: `Error: ${message}` },
      ]);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
      <div className="flex h-[90vh] w-full max-w-6xl flex-col overflow-hidden rounded-3xl bg-white shadow-2xl">
        <div className="shrink-0 border-b border-slate-200 px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
                Plan mode
              </p>
              <h2 className="mt-1 text-xl font-bold text-slate-900">
                Improve weak bullet
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              Close
            </button>
          </div>
        </div>

        <div className="grid min-h-0 flex-1 gap-0 md:grid-cols-[1fr_1.3fr]">
          <div className="min-h-0 overflow-y-auto border-r border-slate-200 p-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Original bullet
            </p>
            <p className="mt-2 rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
              {bullet.text}
            </p>

            <p className="mt-5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Current draft
            </p>
            <p className="mt-2 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-slate-800">
              {currentBullet}
            </p>

            <p className="mt-5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Why it was flagged
            </p>
            <ul className="mt-2 space-y-2">
              {bullet.reasons.map((reason) => (
                <li
                  key={reason}
                  className="rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800"
                >
                  {reason}
                </li>
              ))}
            </ul>
          </div>

          <div className="flex min-h-0 flex-col bg-slate-50/40">
            <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
              <div className="mx-auto flex w-full max-w-3xl flex-col gap-3">
                {messages.length === 0 && (
                  <div className="rounded-2xl bg-white p-4 text-sm text-slate-600 shadow-sm ring-1 ring-slate-200">
                    Start by asking for a rewrite, or answer with more detail so
                    the model can strengthen this bullet.
                  </div>
                )}

                {messages.map((msg, idx) => {
                  const isThinking =
                    msg.role === "assistant" &&
                    msg.content === THINKING_PLACEHOLDER;

                  return (
                    <div
                      key={`${msg.role}-${idx}`}
                      className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
                        msg.role === "user"
                          ? "ml-auto bg-slate-900 text-white"
                          : "mr-auto bg-white text-slate-800 ring-1 ring-slate-200"
                      }`}
                    >
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wide opacity-70">
                        {msg.role}
                      </p>

                      {isThinking ? (
                        <ThinkingText />
                      ) : (
                        <p className="whitespace-pre-wrap leading-6">
                          {msg.content}
                        </p>
                      )}
                    </div>
                  );
                })}

                {options.length > 0 && (
                  <div className="space-y-3 pt-2">
                    <p className="text-sm font-semibold text-slate-900">
                      Suggested options
                    </p>
                    {options.map((option, idx) => (
                      <div
                        key={`${option}-${idx}`}
                        className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200"
                      >
                        <p className="text-sm leading-6 text-slate-800">
                          {option}
                        </p>
                        <button
                          type="button"
                          onClick={() => onApplyOption(option)}
                          className="mt-3 rounded-xl bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800"
                        >
                          Use this version
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            <div className="shrink-0 border-t border-slate-200 bg-white px-6 py-4">
              <div className="mx-auto w-full max-w-3xl space-y-3">
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      sendMessage("Please help me improve this bullet.")
                    }
                    className="rounded-full bg-slate-100 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-200"
                  >
                    Improve this bullet
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      sendMessage("Ask me the most important question first.")
                    }
                    className="rounded-full bg-slate-100 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-200"
                  >
                    Ask a question
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      sendMessage(
                        "Make this more results-driven and ATS-friendly.",
                      )
                    }
                    className="rounded-full bg-slate-100 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-200"
                  >
                    Make it stronger
                  </button>
                </div>

                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Add more detail, tools used, impact, metrics, scope..."
                  className="max-h-40 min-h-[110px] w-full resize-none rounded-2xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-500"
                />

                <div className="flex justify-between">
                  <button
                    type="button"
                    onClick={refreshChat}
                    disabled={loading}
                    className="rounded-2xl border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Refresh
                  </button>

                  <button
                    type="button"
                    onClick={() => sendMessage()}
                    disabled={loading || !input.trim()}
                    className="rounded-2xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {loading ? "Thinking..." : "Send"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
