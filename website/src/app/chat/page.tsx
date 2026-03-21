"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { ArrowLeft, Sparkles, User, ChevronRight, Play, Heart, MessageCircle, Share2, Bookmark, ExternalLink } from "lucide-react";
import { PromptInputBox, type PromptSendPayload, type ModeId } from "@/components/ui/ai-prompt-box";
import Navbar from "@/components/ui/navbar";
import styles from "./chat-page.module.css";

// ── Types ──────────────────────────────────────────────────────────────────────
interface ThinkingStep {
  title: string;
  detail: string;
}

interface GeneratedVideo {
  source: string;
  tag: string;
  facts: string[];
  bg: "subway" | "minecraft" | "satisfying" | "racing";
  accent: string;
  likes: string;
  comments: string;
  shares: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  mode?: ModeId | "normal";
  thinkingSteps?: ThinkingStep[];
  thinkingDuration?: number;
  generatedVideo?: GeneratedVideo;
}

interface MessageGroup {
  role: "user" | "assistant";
  messages: Message[];
}

// ── Constants ─────────────────────────────────────────────────────────────────
const TITLE_WORDS = ["Turn", "your", "content", "into", "brainrot."];

const easeOutExpo = [0.22, 1, 0.36, 1] as const;

const COMMON_THINKING_STEPS: ThinkingStep[] = [
  { title: "Scraping your content", detail: "Pulling the full page text, stripping ads and navigation noise, extracting only the core article body." },
  { title: "Running knowledge extraction", detail: "Identifying the 5–7 key facts, stats, and ideas that will land hardest in a 60-second format." },
  { title: "Generating brainrot script", detail: "Writing the punchy, high-retention script with hooks, quick cuts, and dopamine-triggering pacing." },
  { title: "Rendering video with overlay", detail: "Compositing gameplay background, voiceover, text cards, and progress bar into your final short." },
];

const BG_TYPES = ["subway", "minecraft", "satisfying", "racing"] as const;
const BG_LABELS: Record<string, string> = {
  subway: "🏃 Subway Surfers",
  minecraft: "⛏️ Minecraft Parkour",
  satisfying: "✨ Satisfying Clips",
  racing: "🏎️ Racing Highlights",
};
const ACCENTS = ["#5235ef", "#7c3aed", "#6d28d9", "#4f46e5"];
const TAGS = ["Research", "Study Notes", "Blog Post", "Article", "PDF", "Raw Text"];

function buildGeneratedVideo(msg: string): GeneratedVideo {
  const hash = msg.split("").reduce((a, c) => a + c.charCodeAt(0), 0);
  return {
    source: msg.length > 60 ? msg.slice(0, 57) + "..." : msg,
    tag: TAGS[hash % TAGS.length],
    facts: [
      "Key insight extracted from your content — structured for maximum retention in under 30 seconds.",
      "Supporting fact #2 — distilled from your source material with context that makes it stick.",
      "The core takeaway — the one thing your brain will actually remember after watching.",
    ],
    bg: BG_TYPES[hash % BG_TYPES.length],
    accent: ACCENTS[hash % ACCENTS.length],
    likes: `${((hash % 40) + 10)}.${hash % 9}K`,
    comments: `${(hash % 900) + 100}`,
    shares: `${((hash % 8) + 1)}.${hash % 9}K`,
  };
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

// ── Generated video card ───────────────────────────────────────────────────────
function GameplayBg({ type }: { type: GeneratedVideo["bg"] }) {
  const colors: Record<string, string[]> = {
    subway: ["#1a0a2e", "#2d1b69", "#1a0a2e", "#3b1f7a"],
    minecraft: ["#1a2e1a", "#2d4a1e", "#1a3a1a", "#3b5e22"],
    satisfying: ["#0a1a2e", "#1b3a5e", "#0a2a3e", "#1f4a7a"],
    racing: ["#2e1a0a", "#5e3a1b", "#3e2a0a", "#7a4e1f"],
  };
  const cols = colors[type];
  return (
    <div className={styles.vidBg}>
      <div className={styles.vidGrid}>
        {Array.from({ length: 24 }).map((_, i) => (
          <div key={i} className={styles.vidCell} style={{ background: cols[i % cols.length] }} />
        ))}
      </div>
      <div className={styles.vidScanline} />
      <div className={styles.vidBgLabel}>{BG_LABELS[type]}</div>
    </div>
  );
}

function GeneratedVideoCard({ video, msgId }: { video: GeneratedVideo; msgId: string }) {
  const [liked, setLiked] = useState(false);
  const [saved, setSaved] = useState(false);
  const [factIdx, setFactIdx] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setFactIdx(i => (i + 1) % video.facts.length), 3000);
    return () => clearInterval(t);
  }, [video.facts.length]);

  return (
    <div className={styles.genCard}>
      {/* Header */}
      <div className={styles.genCardHeader}>
        <div className={styles.genCardHeaderLeft}>
          <div className={styles.genCardAvatar} style={{ background: `linear-gradient(135deg, ${video.accent}, #9b87ff)` }}>
            <Sparkles size={12} />
          </div>
          <div>
            <p className={styles.genCardTitle}>Video generated</p>
            <p className={styles.genCardSub}>Draftr AI · brainrot format</p>
          </div>
        </div>
        <span className={styles.genCardTag} style={{ background: video.accent + "22", color: video.accent === "#5235ef" ? "#8a73ff" : "#c4b5fd", borderColor: video.accent + "55" }}>
          {video.tag}
        </span>
      </div>

      {/* Video preview */}
      <div className={styles.genPreview}>
        <GameplayBg type={video.bg} />

        {/* Overlay */}
        <div className={styles.genOverlay} />

        {/* Source chip */}
        <div className={styles.genSource}>
          <span>🔗</span>
          <span className={styles.genSourceText}>{video.source}</span>
        </div>

        {/* Fact card */}
        <div className={styles.genFactWrap}>
          {video.facts.map((fact, i) => (
            <div
              key={i}
              className={`${styles.genFact} ${i === factIdx ? styles.genFactActive : ""}`}
            >
              <p className={styles.genFactText}>{fact}</p>
              <div className={styles.genFactDots}>
                {video.facts.map((_, di) => (
                  <span
                    key={di}
                    className={`${styles.genFactDot} ${di === factIdx ? styles.genFactDotActive : ""}`}
                    style={di === factIdx ? { background: video.accent } : {}}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Progress bar */}
        <div className={styles.genProgress}>
          <div className={styles.genProgressFill} style={{ width: `${((factIdx + 1) / video.facts.length) * 100}%`, background: video.accent }} />
        </div>

        {/* Play button */}
        <div className={styles.genPlayBtn}>
          <Play size={18} fill="white" color="white" />
        </div>

        {/* Stats strip */}
        <div className={styles.genStats}>
          <span>❤️ {video.likes}</span>
          <span>💬 {video.comments}</span>
          <span>↗️ {video.shares}</span>
        </div>
      </div>

      {/* Actions */}
      <div className={styles.genActions}>
        <button
          className={`${styles.genActionBtn} ${liked ? styles.genActionBtnLiked : ""}`}
          onClick={() => setLiked(l => !l)}
        >
          <Heart size={14} fill={liked ? "#ef4444" : "none"} color={liked ? "#ef4444" : "currentColor"} />
          {liked ? "Liked" : "Like"}
        </button>
        <button className={styles.genActionBtn} onClick={() => setSaved(s => !s)}>
          <Bookmark size={14} fill={saved ? "currentColor" : "none"} />
          {saved ? "Saved" : "Save"}
        </button>
        <button className={styles.genActionBtn}>
          <Share2 size={14} />
          Share
        </button>
        <Link href="/shorts" className={`${styles.genActionBtn} ${styles.genActionBtnPrimary}`} style={{ background: video.accent, borderColor: video.accent }}>
          <ExternalLink size={13} />
          View in Shorts
        </Link>
      </div>

      {/* Regenerate nudge */}
      <div className={styles.genNudge}>
        <MessageCircle size={11} />
        Not quite right? Reply to regenerate with different gameplay or style.
      </div>
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [composerMode, setComposerMode] = useState<ModeId | null>(null);
  const [expandedThinking, setExpandedThinking] = useState<Set<string>>(new Set());
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
      mode,
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    const steps = COMMON_THINKING_STEPS;
    setThinkingSteps(steps);
    setVisibleSteps(0);
    setIsThinkingActive(true);
    setIsClosingLogs(false);

    const STEP_DELAY = 700;
    steps.forEach((_, i) => {
      setTimeout(() => { setVisibleSteps(i + 1); }, 400 + i * STEP_DELAY);
    });

    const totalThinkingMs = 400 + steps.length * STEP_DELAY + 600;
    setTimeout(() => {
      setIsClosingLogs(true);
      setTimeout(() => {
        setIsThinkingActive(false);
        setIsClosingLogs(false);
        setVisibleSteps(0);
        const thinkingDuration = Math.round(totalThinkingMs / 1000);
        const generatedVideo = buildGeneratedVideo(message.trim());
        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "",
          timestamp: new Date(),
          mode,
          thinkingSteps: steps,
          thinkingDuration,
          generatedVideo,
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

                        <div className={`${styles.bubbleStack} ${group.role === "user" ? styles.bubbleStackUser : ""} ${group.role === "assistant" ? styles.bubbleStackAi : ""}`}>
                          {group.role === "user" && (
                            <div className={`${styles.senderLabel} ${styles.senderLabelUser}`}>You</div>
                          )}

                          {/* Thought summary pill */}
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
                                      <p className={styles.thoughtLogTitle}>Generation log</p>
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

                          {/* User bubbles */}
                          {group.role === "user" && group.messages.map((msg, mi) => {
                            const isFirst = mi === 0;
                            const isLast = mi === group.messages.length - 1;
                            let radiusClass = "";
                            if (!isFirst && isLast) radiusClass = styles.bubbleUserLast;
                            else if (isFirst && !isLast) radiusClass = styles.bubbleUserFirst;
                            return (
                              <motion.div
                                key={msg.id}
                                initial={{ opacity: 0, y: 8 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.32, ease: easeOutExpo }}
                                className={`${styles.bubble} ${styles.bubbleUser} ${radiusClass}`}
                              >
                                {msg.content}
                              </motion.div>
                            );
                          })}

                          {/* AI: generated video card */}
                          {group.role === "assistant" && group.messages[0].generatedVideo && (
                            <motion.div
                              initial={{ opacity: 0, y: 12 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ duration: 0.4, ease: easeOutExpo }}
                            >
                              <GeneratedVideoCard
                                video={group.messages[0].generatedVideo}
                                msgId={group.messages[0].id}
                              />
                            </motion.div>
                          )}

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
                          <span className={styles.thinkingCardTitle}>Generating your video…</span>
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
                    placeholder="Paste another URL or describe your next video..."
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
    </div>
  );
}
