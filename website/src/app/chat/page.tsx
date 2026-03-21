"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { ArrowLeft, Sparkles, User, ChevronRight, Wand2 } from "lucide-react";
import { PromptInputBox, type PromptSendPayload, type ModeId } from "@/components/ui/ai-prompt-box";
import Navbar from "@/components/ui/navbar";
import styles from "./chat-page.module.css";

// ── Types ──────────────────────────────────────────────────────────────────────
interface ThinkingStep {
  title: string;
  detail: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  mode?: ModeId | "normal";
  thinkingSteps?: ThinkingStep[];
  thinkingDuration?: number;
}

interface MessageGroup {
  role: "user" | "assistant";
  messages: Message[];
}

// ── Constants ─────────────────────────────────────────────────────────────────
const TITLE_WORDS = ["Turn", "your", "content", "into", "brainrot."];

const easeOutExpo = [0.22, 1, 0.36, 1] as const;

const COMMON_THINKING_STEPS: ThinkingStep[] = [
  { title: "Receiving your question", detail: "The orchestrator accepted your message and prepared context from recent history." },
  { title: "Running question reader agent", detail: "Classifying question type and required depth with safety policy checks." },
  { title: "Running response agent", detail: "Generating a helpful, accurate answer using the selected response style." },
  { title: "Finalizing answer", detail: "Validating the final response and returning it to chat." },
];

const MOCK_RESPONSES: Record<string, string> = {
  normal: "That's a great question! Here's how I'd think about it: start by defining your core goal, then layer in the details. Keeping things simple at first gives you room to iterate and improve over time.",
  search: "Based on the latest information available, here's what I found: the topic you're asking about has several interesting dimensions. Let me break this down for you with the most relevant facts and current perspectives.",
};

function getSteps(_mode: ModeId | "normal"): ThinkingStep[] {
  return COMMON_THINKING_STEPS;
}

function groupMessages(messages: Message[]): MessageGroup[] {
  return messages.reduce<MessageGroup[]>((acc, msg) => {
    const last = acc[acc.length - 1];
    if (last && last.role === msg.role) last.messages.push(msg);
    else acc.push({ role: msg.role, messages: [msg] });
    return acc;
  }, []);
}

// ── Motion variants ───────────────────────────────────────────────────────────
const headingWordMotion = {
  hidden: { opacity: 0, y: 18 },
  show: (i: number) => ({ opacity: 1, y: 0, transition: { duration: 0.55, ease: easeOutExpo, delay: i * 0.07 } }),
};

const blockMotion = {
  hidden: { opacity: 0, y: 14 },
  show: (delay: number) => ({ opacity: 1, y: 0, transition: { duration: 0.5, ease: easeOutExpo, delay } }),
};

// ── Component ─────────────────────────────────────────────────────────────────
export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [composerMode, setComposerMode] = useState<ModeId | null>(null);
  const [showAboutPanel, setShowAboutPanel] = useState(false);
  const [expandedThinking, setExpandedThinking] = useState<Set<string>>(new Set());
  // Live thinking card state
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([]);
  const [visibleSteps, setVisibleSteps] = useState(0);
  const [isThinkingActive, setIsThinkingActive] = useState(false);
  const [isClosingLogs, setIsClosingLogs] = useState(false);

  const scrollerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const isEmpty = messages.length === 0;
  const groups = groupMessages(messages);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    bottomRef.current?.scrollIntoView({ behavior, block: "end" });
  }, []);

  useEffect(() => { scrollToBottom("smooth"); }, [messages.length, isLoading, visibleSteps, scrollToBottom]);

  const toggleThinking = (msgId: string) => {
    setExpandedThinking(prev => {
      const next = new Set(prev);
      if (next.has(msgId)) next.delete(msgId);
      else next.add(msgId);
      return next;
    });
  };

  const handleSend = useCallback((payload: PromptSendPayload) => {
    const { message, mode } = payload;
    if (!message.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: message.trim(),
      timestamp: new Date(),
      mode: mode,
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    setShowAboutPanel(false);

    const steps = getSteps(mode);
    setThinkingSteps(steps);
    setVisibleSteps(0);
    setIsThinkingActive(true);
    setIsClosingLogs(false);

    // Reveal thinking steps progressively
    const STEP_DELAY = 600;
    steps.forEach((_, i) => {
      setTimeout(() => { setVisibleSteps(i + 1); }, 400 + i * STEP_DELAY);
    });

    // After all steps shown, close logs and show response
    const totalThinkingMs = 400 + steps.length * STEP_DELAY + 600;
    setTimeout(() => {
      setIsClosingLogs(true);
      setTimeout(() => {
        setIsThinkingActive(false);
        setIsClosingLogs(false);
        setVisibleSteps(0);
        const thinkingDuration = Math.round(totalThinkingMs / 1000);
        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: MOCK_RESPONSES[mode] ?? MOCK_RESPONSES.normal,
          timestamp: new Date(),
          mode: mode,
          thinkingSteps: steps,
          thinkingDuration,
        };
        setMessages(prev => [...prev, assistantMsg]);
        setIsLoading(false);
      }, 400);
    }, totalThinkingMs);
  }, [isLoading]);

  return (
    <div
      className={styles.page}
      style={{ display: "flex", flexDirection: "column", height: "100dvh", overflow: "hidden" }}
    >
      {/* Navbar — only on empty state */}
      {isEmpty && <Navbar />}

      {/* Back button — chat state */}
      {!isEmpty && (
        <Link href="/" className={styles.chatBackBtn}>
          <ArrowLeft size={12} />
          Back
        </Link>
      )}

      {/* "See the magic" button */}
      {!isEmpty && !showAboutPanel && (
        <div className={`${styles.aiPanelBtnOuter} ${isLoading ? styles.aiPanelBtnSpinning : ""}`}>
          <button
            type="button"
            onClick={() => setShowAboutPanel(true)}
            className={styles.aiPanelBtn}
            aria-label="See the magic"
          >
            <Wand2 size={13} />
            See the magic
          </button>
        </div>
      )}

      {/* Close panel × */}
      {!isEmpty && showAboutPanel && (
        <button
          type="button"
          onClick={() => setShowAboutPanel(false)}
          className={styles.aiPanelClose}
          aria-label="Close panel"
        >
          ×
        </button>
      )}

      {/* Main layout */}
      <div
        className={showAboutPanel && !isEmpty ? styles.splitRoot : undefined}
        style={
          showAboutPanel && !isEmpty
            ? { flex: 1, display: "flex", overflow: "hidden" }
            : { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }
        }
      >
        <div style={showAboutPanel && !isEmpty
          ? { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 }
          : { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }
        }>
          <AnimatePresence mode="wait">
            {isEmpty ? (
              /* ── Empty / landing state ── */
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
                  {TITLE_WORDS.map((word, i) => (
                    <motion.span
                      key={i}
                      className={styles.headingWord}
                      variants={headingWordMotion}
                      custom={i}
                      style={i >= 3 ? {
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
                  Paste a URL, upload your notes, or drop raw text. Draftr converts it into a short-form brainrot video — same addictive format, actual knowledge.
                </motion.p>

                <motion.div
                  variants={blockMotion}
                  custom={0.40}
                  initial="hidden"
                  animate="show"
                  style={{ position: "relative", width: "100%", maxWidth: 680 }}
                >
                  <div style={{
                    pointerEvents: "none", position: "absolute", bottom: -48, left: "50%",
                    transform: "translateX(-50%)", width: 880, height: 340, borderRadius: "50%",
                    background: "radial-gradient(ellipse at top, rgba(82,53,239,0.07) 0%, rgba(109,91,255,0.03) 44%, transparent 68%)",
                    filter: "blur(40px)", zIndex: 0,
                  }} />
                  <div style={{ position: "relative", zIndex: 1 }}>
                    <PromptInputBox
                      onSend={handleSend}
                      isLoading={isLoading}
                      placeholder="Paste a URL, describe your content, or ask anything..."
                      mode={composerMode}
                      onModeChange={setComposerMode}
                    />
                  </div>
                </motion.div>
              </motion.div>

            ) : (
              /* ── Chat state ── */
              <motion.div
                key="chat"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                className={styles.chatRoot}
              >
                <div className={styles.chatScroller} ref={scrollerRef}>
                  <div className={styles.chatScrollInner}>

                    <AnimatePresence initial={false}>
                      {groups.map((group, gi) => (
                        <motion.div
                          key={`group-${gi}`}
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

                          <div className={`${styles.bubbleStack} ${group.role === "user" ? styles.bubbleStackUser : ""}`}>
                            {group.role === "user" && (
                              <div className={`${styles.senderLabel} ${styles.senderLabelUser}`}>You</div>
                            )}


                            {/* Thought summary */}
                            {group.role === "assistant" && group.messages[0].thinkingSteps && (
                              <div className={styles.thoughtSummaryWrap}>
                                <button
                                  className={styles.thoughtSummary}
                                  onClick={() => toggleThinking(group.messages[0].id)}
                                >
                                  Thought for {group.messages[0].thinkingDuration}s
                                  <ChevronRight
                                    size={11}
                                    className={expandedThinking.has(group.messages[0].id) ? styles.chevronOpen : styles.chevronClosed}
                                  />
                                </button>

                                <AnimatePresence>
                                  {expandedThinking.has(group.messages[0].id) && (
                                    <motion.div
                                      initial={{ height: 0, opacity: 0 }}
                                      animate={{ height: "auto", opacity: 1 }}
                                      exit={{ height: 0, opacity: 0 }}
                                      transition={{ duration: 0.22, ease: easeOutExpo }}
                                      style={{ overflow: "hidden" }}
                                    >
                                      <div className={styles.thoughtLogPanel}>
                                        <p className={styles.thoughtLogTitle}>Logs</p>
                                        {group.messages[0].thinkingSteps.map((step, si) => {
                                          const isLast = si === group.messages[0].thinkingSteps!.length - 1;
                                          return (
                                            <div key={si} className={styles.thoughtLogStep}>
                                              <div className={styles.thoughtLogBulletCol}>
                                                <span className={styles.thoughtLogBullet} />
                                                {!isLast && <span className={styles.thoughtLogLine} />}
                                              </div>
                                              <div className={styles.thoughtLogStepContent}>
                                                <div className={styles.thoughtLogStepHead}>
                                                  <div className={styles.thoughtLogStepHeadMain}>
                                                    <p className={styles.thoughtLogStepTitle}>{step.title}</p>
                                                    <p className={styles.thoughtLogStepDetail}>{step.detail}</p>
                                                  </div>
                                                </div>
                                              </div>
                                            </div>
                                          );
                                        })}
                                      </div>
                                    </motion.div>
                                  )}
                                </AnimatePresence>
                              </div>
                            )}

                            {/* Bubbles */}
                            {group.messages.map((msg, mi) => {
                              const isFirst = mi === 0;
                              const isLast = mi === group.messages.length - 1;
                              let radiusClass = "";
                              if (msg.role === "assistant") {
                                if (!isFirst && isLast) radiusClass = styles.bubbleAiLast;
                                else if (isFirst && !isLast) radiusClass = styles.bubbleAiFirst;
                              } else {
                                if (!isFirst && isLast) radiusClass = styles.bubbleUserLast;
                                else if (isFirst && !isLast) radiusClass = styles.bubbleUserFirst;
                              }
                              return (
                                <motion.div
                                  key={msg.id}
                                  initial={{ opacity: 0, y: 8 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  transition={{ duration: 0.32, ease: easeOutExpo }}
                                  className={`${styles.bubble} ${msg.role === "assistant" ? styles.bubbleAi : styles.bubbleUser} ${radiusClass}`}
                                >
                                  {msg.content}
                                </motion.div>
                              );
                            })}

                            <div className={`${styles.bubbleTime} ${group.role === "user" ? styles.bubbleTimeUser : ""}`}>
                              {group.messages[group.messages.length - 1].timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </AnimatePresence>

                    {/* Live thinking card */}
                    <AnimatePresence>
                      {isThinkingActive && (
                        <motion.div
                          key="thinking"
                          initial={{ opacity: 0, y: 16 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -8 }}
                          transition={{ duration: 0.3, ease: easeOutExpo }}
                          className={`${styles.thinkingCard} ${isClosingLogs ? styles.thinkingCardClosing : ""}`}
                        >
                          <div className={styles.thinkingCardHeader}>
                            <div className={styles.thinkingCardAvatar}>
                              <Sparkles size={11} />
                            </div>
                            <span className={styles.thinkingCardTitle}>Draftr is thinking…</span>
                          </div>
                          <div className={styles.thinkingCardBody}>
                            <AnimatePresence initial={false}>
                              {thinkingSteps.slice(0, visibleSteps).map((step, i) => {
                                const isLastVisible = i === visibleSteps - 1;
                                const hasMore = visibleSteps < thinkingSteps.length;
                                const showLine = !isLastVisible || hasMore;
                                return (
                                  <motion.div
                                    key={i}
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.32, ease: easeOutExpo }}
                                    className={styles.thinkingStep}
                                  >
                                    <div className={styles.thinkingBulletCol}>
                                      <span className={styles.thinkingBullet} />
                                      {showLine && <span className={styles.thinkingLine} />}
                                    </div>
                                    <div className={styles.thinkingStepContent}>
                                      <p className={styles.thinkingStepTitle}>{step.title}</p>
                                      <p className={styles.thinkingStepDetail}>{step.detail}</p>
                                    </div>
                                  </motion.div>
                                );
                              })}
                            </AnimatePresence>

                            {!isClosingLogs && (
                              <div className={styles.thinkingSpinnerRow}>
                                <div className={styles.thinkingSpinnerIndent}>
                                  <span className={styles.thinkingSpinner} />
                                </div>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    <div ref={bottomRef} style={{ height: isLoading ? 72 : 12 }} />
                  </div>
                </div>

                {/* Input footer */}
                <div className={styles.inputFooter}>
                  <div className={styles.inputGlow} />
                  <div className={styles.inputInner}>
                    <PromptInputBox
                      onSend={handleSend}
                      isLoading={isLoading}
                      placeholder="Ask another question..."
                      mode={composerMode}
                      onModeChange={setComposerMode}
                    />
                    <p className={styles.inputDisclaimer}>
                      Draftr AI responses are for creative and educational assistance only.
                    </p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* About panel — split view */}
        <AnimatePresence>
          {showAboutPanel && !isEmpty && (
            <motion.div
              key="about-panel"
              initial={{ opacity: 0, x: 32 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 32 }}
              transition={{ duration: 0.38, ease: [0.22, 1, 0.36, 1] }}
              className={styles.aboutPanel}
            >
              <iframe
                src="/about"
                className={styles.aboutPanelFrame}
                title="About Draftr"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
