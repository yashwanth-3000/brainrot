"use client";

import React, { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, Minus, Plus, Sparkles, User } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { PromptInputBox, type PromptSendPayload, type ModeId } from "@/components/ui/ai-prompt-box";
import Navbar from "@/components/ui/navbar";

import { LiveBatchMessage, type BatchEnvelope, type LiveBatchSeed } from "./live-batch-message";
import styles from "./chat-page.module.css";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  mode?: ModeId | "normal";
  liveBatch?: LiveBatchSeed;
};

type MessageGroup = {
  role: "user" | "assistant";
  messages: Message[];
};

const TITLE_WORDS = ["Turn", "your", "content", "into", "brainrot."];
const CHAT_BATCH_COUNT_STORAGE_KEY = "draftr:chat-batch-count";
const MIN_CHAT_BATCH_COUNT = 5;
const MAX_CHAT_BATCH_COUNT = 15;
const DEFAULT_CHAT_BATCH_COUNT = 5;
const easeOutExpo = [0.22, 1, 0.36, 1] as const;

const headingWordMotion = {
  hidden: { opacity: 0, y: 18 },
  show: (i: number) => ({ opacity: 1, y: 0, transition: { duration: 0.55, ease: easeOutExpo, delay: i * 0.07 } }),
};

const blockMotion = {
  hidden: { opacity: 0, y: 14 },
  show: (delay: number) => ({ opacity: 1, y: 0, transition: { duration: 0.5, ease: easeOutExpo, delay } }),
};

export default function ChatPage() {
  return (
    <Suspense fallback={<ChatPageFallback />}>
      <ChatPageContent />
    </Suspense>
  );
}

function ChatPageFallback() {
  return <ChatPageInner requestedChatId={null} prefillPrompt="" authError={false} />;
}

function ChatPageContent() {
  const searchParams = useSearchParams();
  return (
    <ChatPageInner
      requestedChatId={searchParams.get("chat")}
      prefillPrompt={searchParams.get("prefill") ?? ""}
      authError={searchParams.get("auth") === "error"}
    />
  );
}

function ChatPageInner({
  requestedChatId,
  prefillPrompt,
  authError,
}: {
  requestedChatId: string | null;
  prefillPrompt: string;
  authError: boolean;
}) {
  const auth = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [composerMode, setComposerMode] = useState<ModeId | null>(null);
  const [chatSessionId, setChatSessionId] = useState<string | null>(requestedChatId);
  const [batchCount, setBatchCount] = useState(DEFAULT_CHAT_BATCH_COUNT);
  const [isBatchCountHydrated, setIsBatchCountHydrated] = useState(false);
  const [draftMessage, setDraftMessage] = useState(prefillPrompt);

  const bottomRef = useRef<HTMLDivElement>(null);
  const isEmpty = messages.length === 0;
  const groups = groupMessages(messages);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    bottomRef.current?.scrollIntoView({ behavior, block: "end" });
  }, []);

  useEffect(() => {
    scrollToBottom("smooth");
  }, [messages.length, scrollToBottom]);

  useEffect(() => {
    setChatSessionId(requestedChatId);
  }, [requestedChatId]);

  useEffect(() => {
    setDraftMessage(prefillPrompt);
  }, [prefillPrompt]);

  useEffect(() => {
    setChatSessionId(requestedChatId);
    setMessages([]);
  }, [auth.scopeKey, requestedChatId]);

  useEffect(() => {
    setBatchCount(readStoredBatchCount());
    setIsBatchCountHydrated(true);
  }, []);

  useEffect(() => {
    if (!isBatchCountHydrated || typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(CHAT_BATCH_COUNT_STORAGE_KEY, String(batchCount));
  }, [batchCount, isBatchCountHydrated]);

  const handleSend = useCallback(async (payload: PromptSendPayload) => {
    if (isLoading) {
      return;
    }

    const trimmedMessage = payload.message.trim();
    const createdAt = new Date();
    const sourceLabel = inferSourceLabel(payload);
    const userMessageId = crypto.randomUUID();
    const assistantMessageId = crypto.randomUUID();

    const userMsg: Message = {
      id: userMessageId,
      role: "user",
      content: trimmedMessage || sourceLabel,
      timestamp: createdAt,
      mode: payload.mode,
    };

    const assistantMsg: Message = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      mode: payload.mode,
      liveBatch: {
        createdAt: createdAt.toISOString(),
        chatId: chatSessionId ?? "",
        batchId: null,
        initialEnvelope: null,
        sourceLabel,
        error: null,
      },
    };

    setMessages(previous => [...previous, userMsg, assistantMsg]);
    setDraftMessage("");
    setIsLoading(true);

    try {
      const canonicalChatId = await ensureChatSession({
        existingChatId: chatSessionId,
        sourceLabel,
        sourceUrl: extractRequestSourceUrl(payload),
      });
      setChatSessionId(canonicalChatId);

      updateAssistantMessage(assistantMessageId, current => ({
        ...current,
        chatId: canonicalChatId,
      }));

      const { formData, resolvedSourceLabel } = prepareBatchRequest(payload, batchCount, canonicalChatId);
      updateAssistantMessage(assistantMessageId, current => ({
        ...current,
        sourceLabel: resolvedSourceLabel,
      }));

      try {
        await fetch("/api/brainrot/agents/bootstrap", { method: "POST" });
      } catch {
        // Batch creation is the real gate. If bootstrap fails transiently, let the create call decide.
      }

      const response = await fetch("/api/brainrot/batches", {
        method: "POST",
        body: formData,
      });
      const batchPayload = (await response.json()) as BatchEnvelope & { detail?: string };
      if (!response.ok) {
        throw new Error(batchPayload?.detail ?? "Failed to create live generation batch.");
      }

      updateAssistantMessage(assistantMessageId, current => ({
        ...current,
        batchId: batchPayload.batch.id,
        initialEnvelope: batchPayload,
        chatId: canonicalChatId,
        error: null,
      }));
    } catch (error) {
      updateAssistantMessage(assistantMessageId, current => ({
        ...current,
        error: error instanceof Error ? error.message : "Failed to start live generation.",
      }));
    } finally {
      setIsLoading(false);
    }
  }, [batchCount, chatSessionId, isLoading]);

  function updateAssistantMessage(messageId: string, updater: (current: LiveBatchSeed) => LiveBatchSeed) {
    setMessages(previous =>
      previous.map(message => {
        if (message.id !== messageId || !message.liveBatch) {
          return message;
        }
        return {
          ...message,
          liveBatch: updater(message.liveBatch),
        };
      }),
    );
  }

  return (
    <div
      className={styles.page}
      style={{ display: "flex", flexDirection: "column", height: "100dvh", overflow: "hidden" }}
    >
      {isEmpty && <Navbar />}

      {!isEmpty && (
        <Link href="/" className={styles.chatBackBtn}>
          <ArrowLeft size={12} />
          Back
        </Link>
      )}

      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <AnimatePresence mode="wait">
          {isEmpty ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.28 }}
              className={styles.emptyRoot}
            >
              <motion.h1
                className={styles.heroTitle}
                initial="hidden"
                animate="show"
                style={{ marginBottom: 14 }}
              >
                {TITLE_WORDS.map((word, index) => (
                  <motion.span
                    key={index}
                    className={styles.headingWord}
                    variants={headingWordMotion}
                    custom={index}
                    style={index >= 3 ? {
                      background: "linear-gradient(90deg, #5235ef 0%, #8a73ff 100%)",
                      WebkitBackgroundClip: "text",
                      WebkitTextFillColor: "transparent",
                      backgroundClip: "text",
                    } : undefined}
                  >
                    {word}{" "}
                  </motion.span>
                ))}
              </motion.h1>

              <motion.p
                className={styles.heroCopy}
                variants={blockMotion}
                custom={0.30}
                initial="hidden"
                animate="show"
                style={{ marginBottom: 34 }}
              >
                Paste a URL or upload a PDF. The chat page now runs the real backend pipeline and streams live Firecrawl,
                OpenAI, ElevenLabs, and FFmpeg activity directly in the conversation.
              </motion.p>

              <motion.div
                variants={blockMotion}
                custom={0.40}
                initial="hidden"
                animate="show"
                style={{ position: "relative", width: "100%", maxWidth: 680 }}
              >
                {!auth.isAuthenticated ? (
                  <div
                    style={{
                      marginBottom: 16,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 10,
                      borderRadius: 999,
                      border: "1px solid rgba(255,255,255,0.12)",
                      background: "rgba(16,12,28,0.62)",
                      padding: "10px 14px",
                      color: "#d9d5ea",
                      fontSize: 13,
                    }}
                  >
                    <span style={{ fontWeight: 700, color: "#f0ecff" }}>{auth.libraryLabel}</span>
                    <span>
                      Skip login and generate into the shared general library, or sign in with Google for your own
                      library.
                    </span>
                  </div>
                ) : null}
                {authError ? (
                  <div
                    style={{
                      marginBottom: 16,
                      borderRadius: 18,
                      border: "1px solid rgba(255,145,113,0.35)",
                      background: "rgba(95,36,28,0.55)",
                      padding: "12px 14px",
                      color: "#ffd8cf",
                      fontSize: 13,
                    }}
                  >
                    Google sign-in did not complete. Try the login flow again, and if it still fails, reopen the login page and retry from there.
                  </div>
                ) : null}
                <div
                  style={{
                    pointerEvents: "none",
                    position: "absolute",
                    bottom: -48,
                    left: "50%",
                    transform: "translateX(-50%)",
                    width: 880,
                    height: 340,
                    borderRadius: "50%",
                    background: "radial-gradient(ellipse at top, rgba(82,53,239,0.07) 0%, rgba(109,91,255,0.03) 44%, transparent 68%)",
                    filter: "blur(40px)",
                    zIndex: 0,
                  }}
                />
                <div style={{ position: "relative", zIndex: 1 }}>
                  <PromptInputBox
                    onSend={handleSend}
                    isLoading={isLoading}
                    placeholder="Paste a URL, upload a PDF, or add a title hint..."
                    mode={composerMode}
                    onModeChange={setComposerMode}
                    value={draftMessage}
                    onValueChange={setDraftMessage}
                    footerAccessory={<BatchCountAccessory value={batchCount} onChange={setBatchCount} disabled={isLoading} />}
                  />
                </div>
              </motion.div>
            </motion.div>
          ) : (
            <motion.div
              key="chat"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
              className={styles.chatRoot}
            >
              <div className={styles.chatScroller}>
                <div className={styles.chatScrollInner}>
                  <AnimatePresence initial={false}>
                    {groups.map((group, groupIndex) => (
                      <motion.div
                        key={`group-${groupIndex}`}
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.32, ease: easeOutExpo }}
                        className={`${styles.messageGroup} ${group.role === "user" ? styles.messageGroupUser : ""}`}
                      >
                        {group.role === "assistant" ? (
                          <div className={styles.aiAvatar}><Sparkles size={13} /></div>
                        ) : (
                          <div className={styles.userAvatar}><User size={12} /></div>
                        )}

                        <div className={`${styles.bubbleStack} ${group.role === "user" ? styles.bubbleStackUser : ""} ${group.role === "assistant" ? styles.bubbleStackAi : ""}`}>
                          {group.role === "user" ? (
                            <>
                              <div className={`${styles.senderLabel} ${styles.senderLabelUser}`}>You</div>
                              {group.messages.map((message, index) => {
                                const isFirst = index === 0;
                                const isLast = index === group.messages.length - 1;
                                let radiusClass = "";
                                if (!isFirst && isLast) radiusClass = styles.bubbleUserLast;
                                else if (isFirst && !isLast) radiusClass = styles.bubbleUserFirst;
                                return (
                                  <motion.div
                                    key={message.id}
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.32, ease: easeOutExpo }}
                                    className={`${styles.bubble} ${styles.bubbleUser} ${radiusClass}`}
                                  >
                                    {message.content}
                                  </motion.div>
                                );
                              })}
                            </>
                          ) : (
                            <>
                              {group.messages.map(message => (
                                <motion.div
                                  key={message.id}
                                  initial={{ opacity: 0, y: 12 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  transition={{ duration: 0.36, ease: easeOutExpo }}
                                >
                                  {message.liveBatch ? (
                                    <LiveBatchMessage seed={message.liveBatch} />
                                  ) : (
                                    <div className={`${styles.bubble} ${styles.bubbleAi}`}>{message.content}</div>
                                  )}
                                </motion.div>
                              ))}
                            </>
                          )}

                          <div className={`${styles.bubbleTime} ${group.role === "user" ? styles.bubbleTimeUser : ""}`}>
                            {group.messages[group.messages.length - 1].timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>

                  <div ref={bottomRef} style={{ height: 12 }} />
                </div>
              </div>

              <div className={styles.inputFooter}>
                <div className={styles.inputGlow} />
                <div className={styles.inputInner}>
                  <PromptInputBox
                    onSend={handleSend}
                    isLoading={isLoading}
                    placeholder="Paste another URL or upload another PDF..."
                    mode={composerMode}
                    onModeChange={setComposerMode}
                    value={draftMessage}
                    onValueChange={setDraftMessage}
                    footerAccessory={<BatchCountAccessory value={batchCount} onChange={setBatchCount} disabled={isLoading} />}
                  />
                  <p className={styles.inputDisclaimer}>
                    {auth.isAuthenticated
                      ? "Live chat generation saves to your account library."
                      : "Live chat generation saves to the general guest library until you sign in."}
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function groupMessages(messages: Message[]): MessageGroup[] {
  return messages.reduce<MessageGroup[]>((accumulator, message) => {
    const last = accumulator[accumulator.length - 1];
    if (last && last.role === message.role) {
      last.messages.push(message);
    } else {
      accumulator.push({ role: message.role, messages: [message] });
    }
    return accumulator;
  }, []);
}

function inferSourceLabel(payload: PromptSendPayload) {
  const pdfFile = payload.files?.find(file => /\.pdf$/i.test(file.name));
  if (pdfFile) {
    return pdfFile.name;
  }
  const explicitUrl = payload.searchUrl?.trim() || extractFirstUrl(payload.message);
  if (explicitUrl) {
    return explicitUrl;
  }
  if (payload.rawContent?.trim()) {
    return "Raw text input";
  }
  if (payload.files?.length) {
    return payload.files[0].name;
  }
  return "Chat request";
}

function extractRequestSourceUrl(payload: PromptSendPayload) {
  return payload.searchUrl?.trim() || extractFirstUrl(payload.message);
}

async function ensureChatSession({
  existingChatId,
  sourceLabel,
  sourceUrl,
}: {
  existingChatId: string | null;
  sourceLabel: string;
  sourceUrl: string | null;
}) {
  if (existingChatId) {
    return existingChatId;
  }
  const response = await fetch("/api/brainrot/chats", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title: sourceLabel,
      source_label: sourceLabel,
      source_url: sourceUrl,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload?.detail ?? "Failed to create chat session.");
  }
  const createdChatId = payload?.chat?.id;
  if (typeof createdChatId !== "string" || createdChatId.length === 0) {
    throw new Error("The backend did not return a valid chat id.");
  }
  return createdChatId;
}

function prepareBatchRequest(payload: PromptSendPayload, batchCount: number, chatId: string) {
  const formData = new FormData();
  const pdfFile = payload.files?.find(file => /\.pdf$/i.test(file.name)) ?? null;
  const sourceUrl = payload.searchUrl?.trim() || extractFirstUrl(payload.message);
  const strippedMessage = stripFirstUrl(payload.message).trim();

  if (pdfFile) {
    formData.append("file", pdfFile);
  } else if (sourceUrl) {
    formData.append("source_url", sourceUrl);
  } else if (payload.rawContent?.trim() || payload.files?.length) {
    throw new Error("Live generation in chat currently supports source URLs and PDF uploads. Raw text, TXT, DOC, and DOCX are not wired into the backend batch pipeline yet.");
  } else {
    throw new Error("Paste a source URL or upload a PDF to run the live backend pipeline from chat.");
  }

  formData.append("count", String(clampBatchCount(batchCount)));
  formData.append("chat_id", chatId);

  if (strippedMessage) {
    formData.append("title_hint", strippedMessage);
  }

  return {
    formData,
    resolvedSourceLabel: pdfFile ? pdfFile.name : sourceUrl ?? "Chat request",
  };
}

function extractFirstUrl(value: string) {
  const match = value.match(/https?:\/\/[^\s]+/i);
  return match?.[0] ?? null;
}

function stripFirstUrl(value: string) {
  return value.replace(/https?:\/\/[^\s]+/i, "").replace(/\s+/g, " ").trim();
}

function BatchCountAccessory({
  value,
  onChange,
  disabled,
}: {
  value: number;
  onChange: (value: number) => void;
  disabled: boolean;
}) {
  return (
    <div className={styles.batchCountAccessory}>
      <div className={styles.batchCountAccessoryMeta}>
        <label className={styles.batchCountAccessoryLabel} htmlFor="chat-batch-count">
          Videos
        </label>
        <span className={styles.batchCountAccessoryHint}>
          {MIN_CHAT_BATCH_COUNT} to {MAX_CHAT_BATCH_COUNT}
        </span>
      </div>
      <div className={styles.batchCountAccessoryFieldWrap}>
        <button
          type="button"
          className={styles.batchCountAccessoryStepperButton}
          onClick={() => onChange(clampBatchCount(value - 1))}
          disabled={disabled || value <= MIN_CHAT_BATCH_COUNT}
          aria-label="Decrease number of videos"
        >
          <Minus size={13} strokeWidth={2.4} />
        </button>
        <input
          id="chat-batch-count"
          type="number"
          min={MIN_CHAT_BATCH_COUNT}
          max={MAX_CHAT_BATCH_COUNT}
          inputMode="numeric"
          disabled={disabled}
          value={value}
          onChange={event => onChange(clampBatchCount(Number(event.target.value)))}
          className={styles.batchCountAccessoryField}
        />
        <button
          type="button"
          className={styles.batchCountAccessoryStepperButton}
          onClick={() => onChange(clampBatchCount(value + 1))}
          disabled={disabled || value >= MAX_CHAT_BATCH_COUNT}
          aria-label="Increase number of videos"
        >
          <Plus size={13} strokeWidth={2.4} />
        </button>
      </div>
    </div>
  );
}

function clampBatchCount(value: number) {
  if (!Number.isFinite(value)) {
    return DEFAULT_CHAT_BATCH_COUNT;
  }
  return Math.min(MAX_CHAT_BATCH_COUNT, Math.max(MIN_CHAT_BATCH_COUNT, Math.round(value)));
}

function readStoredBatchCount() {
  if (typeof window === "undefined") {
    return DEFAULT_CHAT_BATCH_COUNT;
  }
  const rawValue = window.localStorage.getItem(CHAT_BATCH_COUNT_STORAGE_KEY);
  return clampBatchCount(Number(rawValue));
}
