"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  AudioLines,
  CheckCircle2,
  ChevronRight,
  Clapperboard,
  Globe,
  ShieldCheck,
} from "lucide-react";

import styles from "./chat-page.module.css";
import { buildChatShortsPath, saveChatBatchToStorage, type StoredChatBatch } from "@/lib/chat-run-storage";

export type BatchRecord = {
  id: string;
  source_url?: string | null;
  title_hint?: string | null;
  requested_count: number;
  status: string;
  error?: string | null;
  metadata?: Record<string, unknown>;
};

export type BatchItemRecord = {
  id: string;
  item_index: number;
  status: string;
  error?: string | null;
  output_url?: string | null;
  script?: {
    title?: string;
    narration_text?: string;
    estimated_seconds?: number;
  } | null;
  render_metadata?: Record<string, unknown>;
};

export type BatchEnvelope = {
  batch: BatchRecord;
  items: BatchItemRecord[];
};

export type BatchEventRecord = {
  sequence: number;
  type: string;
  created_at: string;
  payload: Record<string, unknown>;
};

export type LiveBatchSeed = {
  createdAt: string;
  chatId: string;
  batchId: string | null;
  initialEnvelope: BatchEnvelope | null;
  sourceLabel: string;
  error: string | null;
};

type ConnectionState = "idle" | "connecting" | "streaming" | "reconnecting" | "settled";
type EntryTone = "accent" | "success" | "warning" | "danger" | "neutral";
type LogIconKey = "firecrawl" | "openai" | "elevenlabs" | "ffmpeg" | "qa" | "backend" | "success" | "warning" | "danger";

type LogEntry = {
  id: string;
  title: string;
  detail: string | null;
  tone: EntryTone;
  iconKey: LogIconKey;
  providerLabel: string;
};

type ActiveOperation = {
  id: string;
  title: string;
  detail: string | null;
  liveLabel: string | null;
  tone: EntryTone;
  iconKey: LogIconKey;
  providerLabel: string;
  kind: "ingest" | "producer" | "narration" | "assets" | "render" | "backend";
};

type ActivitySummary = {
  title: string;
  detail: string | null;
  liveLabel: string | null;
  tone: EntryTone;
  iconKey: LogIconKey;
  providerLabel: string;
};

const EVENT_TYPES = [
  "status",
  "log",
  "source_ingested",
  "producer_conversation_started",
  "producer_tool_called",
  "section_planning_started",
  "section_planning_completed",
  "coverage_plan_ready",
  "slot_generation_started",
  "slot_generation_completed",
  "slot_generation_failed",
  "slot_repair_started",
  "slot_repair_completed",
  "producer_bundle_completed",
  "scripts_ready",
  "narrator_conversation_started",
  "narrator_audio_ready",
  "alignment_ready",
  "render_started",
  "item_completed",
  "batch_completed",
  "error",
  "done",
  "ping",
] as const;

export function LiveBatchMessage({ seed }: { seed: LiveBatchSeed }) {
  const router = useRouter();
  const [batchEnvelope, setBatchEnvelope] = useState<BatchEnvelope | null>(seed.initialEnvelope);
  const [events, setEvents] = useState<BatchEventRecord[]>([]);
  const [connectionState, setConnectionState] = useState<ConnectionState>(seed.batchId ? "connecting" : "idle");
  const [expanded, setExpanded] = useState(true);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(seed.error);
  const [nowTick, setNowTick] = useState(() => Date.now());

  const eventSourceRef = useRef<EventSource | null>(null);
  const refreshTimerRef = useRef<number | null>(null);
  const logStreamRef = useRef<HTMLDivElement | null>(null);
  const logStickToTopRef = useRef(true);
  const logScrollHeightRef = useRef(0);

  useEffect(() => {
    setLocalError(seed.error);
  }, [seed.error]);

  useEffect(() => {
    if (seed.initialEnvelope) {
      setBatchEnvelope(seed.initialEnvelope);
    }
  }, [seed.initialEnvelope]);

  const batch = batchEnvelope?.batch ?? null;
  const items = batchEnvelope?.items ?? [];
  const isBatchSettled = isSettledStatus(batch?.status) || Boolean(localError);

  useEffect(() => {
    if (!seed.batchId) {
      eventSourceRef.current?.close();
      if (refreshTimerRef.current !== null) {
        window.clearTimeout(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
      if (!localError) {
        setConnectionState("idle");
      }
      return;
    }

    void refreshBatch(seed.batchId, { silent: true });
    logStickToTopRef.current = true;
  }, [seed.batchId]);

  useEffect(() => {
    if (!seed.batchId || isBatchSettled) {
      eventSourceRef.current?.close();
      if (isBatchSettled && seed.batchId) {
        setConnectionState("settled");
      }
      return;
    }

    connectEventStream(seed.batchId);
    return () => {
      eventSourceRef.current?.close();
    };
  }, [seed.batchId, isBatchSettled]);

  useEffect(() => {
    if (isBatchSettled) {
      return;
    }
    const intervalId = window.setInterval(() => {
      setNowTick(Date.now());
    }, 1000);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [isBatchSettled]);

  const streamEvents = useMemo(
    () => events.filter(event => event.type !== "ping" && event.type !== "done"),
    [events],
  );
  const logEvents = useMemo(() => compactLogEvents(streamEvents), [streamEvents]);
  const activeOperations = useMemo(() => buildActiveOperations(streamEvents, nowTick), [streamEvents, nowTick]);
  const latestLogEvent = streamEvents.at(-1) ?? null;
  const logEntries = useMemo(() => logEvents.map(event => toLogEntry(event)).reverse(), [logEvents]);

  useEffect(() => {
    if (!logStreamRef.current || !expanded) {
      return;
    }
    if (logStickToTopRef.current) {
      logStreamRef.current.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      const delta = logStreamRef.current.scrollHeight - logScrollHeightRef.current;
      if (delta > 0) {
        logStreamRef.current.scrollTop += delta;
      }
    }
    logScrollHeightRef.current = logStreamRef.current.scrollHeight;
  }, [logEntries.length, expanded]);

  async function refreshBatch(batchId: string, options: { silent: boolean }) {
    try {
      const response = await fetch(`/api/brainrot/batches/${batchId}`, { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail ?? "Failed to load batch.");
      }
      setBatchEnvelope(payload);
      setLastSyncedAt(new Date().toISOString());
      setLocalError(null);
      return true;
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "Failed to load batch.");
      return false;
    }
  }

  function connectEventStream(batchId: string) {
    eventSourceRef.current?.close();
    setConnectionState("connecting");

    const source = new EventSource(`/api/brainrot/batches/${batchId}/events`);
    eventSourceRef.current = source;

    source.onopen = () => {
      setConnectionState("streaming");
    };

    source.onerror = () => {
      setConnectionState("reconnecting");
    };

    const handleEvent = (rawEvent: MessageEvent<string>) => {
      const parsed = parseEvent(rawEvent.data, rawEvent.type);
      if (!parsed) {
        return;
      }
      if (parsed.type === "ping") {
        setConnectionState("streaming");
        return;
      }

      setEvents(previous => {
        if (previous.some(event => event.sequence === parsed.sequence && event.type === parsed.type)) {
          return previous;
        }
        return [...previous, parsed];
      });
      setConnectionState("streaming");
      if (shouldRefreshBatchForEvent(parsed)) {
        scheduleRefresh(batchId);
      }
    };

    for (const type of EVENT_TYPES) {
      source.addEventListener(type, handleEvent as EventListener);
    }
    source.onmessage = handleEvent;
  }

  function scheduleRefresh(batchId: string) {
    if (isBatchSettled) {
      return;
    }
    if (refreshTimerRef.current !== null) {
      return;
    }

    refreshTimerRef.current = window.setTimeout(() => {
      refreshTimerRef.current = null;
      void refreshBatch(batchId, { silent: true });
    }, 250);
  }

  function handleLogScroll() {
    if (!logStreamRef.current) {
      return;
    }
    logStickToTopRef.current = logStreamRef.current.scrollTop < 56;
  }

  const sortedItems = items.slice().sort((left, right) => left.item_index - right.item_index);
  const uploadedCount = sortedItems.filter(item => item.status === "uploaded").length;
  const failedCount = sortedItems.filter(item => item.status === "failed").length;
  const requestedCount = batch?.requested_count ?? seed.initialEnvelope?.batch.requested_count ?? 0;

  const traceSummary = localError
    ? {
        title: "The live generation run failed",
        detail: localError,
        liveLabel: lastSyncedAt ? `Last sync ${formatClock(lastSyncedAt)}` : null,
        tone: "danger" as const,
        iconKey: "danger" as const,
        providerLabel: "Backend",
      }
    : !seed.batchId
      ? {
          title: "Preparing the live batch",
          detail: "The chat page is bootstrapping agents and creating a backend batch for this request.",
          liveLabel: `Started ${formatDurationLabel(Math.max(0, Math.round((nowTick - new Date(seed.createdAt).getTime()) / 1000)))} ago`,
        tone: "accent" as const,
        iconKey: "backend" as const,
        providerLabel: "Backend",
      }
      : buildActivitySummary(activeOperations, latestLogEvent, batch, nowTick, isBatchSettled, uploadedCount, requestedCount);

  const traceThinkingDuration =
    events.length > 0
      ? formatThinkingDuration(streamEvents, nowTick, isBatchSettled)
      : formatDurationLabel(Math.max(0, Math.round((nowTick - new Date(seed.createdAt).getTime()) / 1000)));

  const liveMetadataByItem: Record<string, Record<string, unknown>> = {};
  for (const event of events) {
    const itemId = typeof event.payload.item_id === "string" ? event.payload.item_id : null;
    if (!itemId || event.type !== "render_started") {
      continue;
    }
    liveMetadataByItem[itemId] = {
      ...(liveMetadataByItem[itemId] ?? {}),
      gameplay_asset_path: event.payload.gameplay_asset_path,
      music_asset_path: event.payload.music_asset_path,
      subtitle_style_id: event.payload.subtitle_style_id,
      subtitle_style_label: event.payload.subtitle_style_label,
      subtitle_animation: event.payload.subtitle_animation,
      subtitle_font_name: event.payload.subtitle_font_name,
    };
  }
  const canOpenShorts = isBatchSettled && uploadedCount > 0 && Boolean(batch?.id);

  useEffect(() => {
    if (!canOpenShorts || !batch?.id) {
      return;
    }

    const storedBatch: StoredChatBatch = {
      chatId: seed.chatId,
      batchId: batch.id,
      status: batch.status,
      sourceLabel: seed.sourceLabel,
      sourceUrl: batch.source_url ?? null,
      createdAt: seed.createdAt,
      updatedAt: new Date().toISOString(),
      uploadedCount,
      requestedCount,
      failedCount,
      items: sortedItems
        .filter(item => item.status === "uploaded")
        .map(item => {
          const meta = {
            ...(liveMetadataByItem[item.id] ?? {}),
            ...(item.render_metadata ?? {}),
          };
          const previewUrl = resolveBatchItemVideoUrl(batch.id, item);
          return {
            itemId: item.id,
            batchId: batch.id,
            itemIndex: item.item_index,
            title: item.script?.title ?? `Video ${item.item_index + 1}`,
            sourceLabel: seed.sourceLabel,
            sourceUrl: batch.source_url ?? null,
            status: item.status,
            outputUrl: item.output_url ?? null,
            previewUrl,
            thumbnailUrl: stringValue(meta.thumbnail_url),
            subtitleStyleLabel: stringValue(meta.subtitle_style_label),
            subtitleAnimation: stringValue(meta.subtitle_animation),
            subtitleFontName: stringValue(meta.subtitle_font_name),
            gameplayAssetPath: stringValue(meta.gameplay_asset_path),
            estimatedSeconds: typeof item.script?.estimated_seconds === "number" ? item.script.estimated_seconds : null,
            narrationText: item.script?.narration_text ?? null,
            createdAt: seed.createdAt,
          };
        }),
    };

    saveChatBatchToStorage(seed.chatId, storedBatch);
  }, [batch?.id, batch?.source_url, batch?.status, canOpenShorts, failedCount, liveMetadataByItem, requestedCount, seed.chatId, seed.createdAt, seed.sourceLabel, sortedItems, uploadedCount]);

  async function openInShorts() {
    if (!batch?.id || uploadedCount === 0) {
      return;
    }

    router.push(buildChatShortsPath(seed.chatId));
  }

  return (
    <div className={styles.liveBatchWrap}>
      <div className={styles.thoughtSummaryWrap}>
        <button
          type="button"
          className={styles.thoughtSummary}
          onClick={() => setExpanded(previous => !previous)}
        >
          Thought for {traceThinkingDuration}
          <ChevronRight size={11} className={expanded ? styles.chevronOpen : styles.chevronClosed} />
        </button>
      </div>

      <AnimatePresence initial={false}>
        {expanded ? (
          <motion.div
            key="live-batch-stack"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            style={{ overflow: "hidden" }}
          >
            <div className={styles.liveTracePanel}>
              <div className={styles.liveTraceSummary}>
                <div className={styles.liveTraceSummaryTop}>
                  <div className={`${styles.liveTraceStatusDot} ${styles[`liveTraceStatusDot-${traceSummary.tone}`]}`} />
                  <span className={`${styles.liveTraceProviderBadge} ${styles[`liveTraceProviderBadge-${traceSummary.tone}`]}`}>
                    <span className={`${styles.liveTraceProviderIcon} ${styles[`liveTraceProviderIcon-${traceSummary.tone}`]}`}>
                      <LogIcon iconKey={traceSummary.iconKey} />
                    </span>
                    {traceSummary.providerLabel}
                  </span>
                  {traceSummary.liveLabel ? (
                    <span className={styles.liveTraceTime}>{traceSummary.liveLabel}</span>
                  ) : null}
                </div>
                <p className={styles.liveTraceTitle}>{traceSummary.title}</p>
                {traceSummary.detail ? (
                  <p className={styles.liveTraceDetail}>{traceSummary.detail}</p>
                ) : null}
              </div>

              {logEntries.length > 0 ? (
                <div className={styles.liveTraceBody} ref={logStreamRef} onScroll={handleLogScroll}>
                  {logEntries.map((entry, index) => {
                    const isLast = index === logEntries.length - 1;
                    return (
                      <div key={entry.id} className={styles.thoughtLogStep}>
                        <div className={styles.thoughtLogBulletCol}>
                          <span className={`${styles.thoughtLogBullet} ${styles[`thoughtLogBullet-${entry.tone}`]}`} />
                          {!isLast ? <span className={styles.thoughtLogLine} /> : null}
                        </div>
                        <div className={styles.thoughtLogStepContent}>
                          <div className={styles.liveTraceEntryProviderRow}>
                            <span className={`${styles.liveTraceProviderIcon} ${styles[`liveTraceProviderIcon-${entry.tone}`]}`}>
                              <LogIcon iconKey={entry.iconKey} />
                            </span>
                            <span className={styles.liveTraceEntryProvider}>{entry.providerLabel}</span>
                          </div>
                          <p className={styles.thoughtLogStepTitle}>{entry.title}</p>
                          {entry.detail ? <p className={styles.thoughtLogStepDetail}>{entry.detail}</p> : null}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className={styles.liveTraceEmptyState}>
                  <span className={styles.liveTraceEmptyIcon}>
                    {seed.batchId ? <Activity size={14} /> : <CheckCircle2 size={14} />}
                  </span>
                  <p>{seed.batchId ? "Streaming live backend updates..." : "Waiting for the backend batch to be created..."}</p>
                </div>
              )}
            </div>

            <div className={styles.chatBatchCard}>
              <div className={styles.chatBatchHeader}>
                <div className={styles.chatBatchHeaderLeft}>
                  <div className={styles.chatBatchAvatar}>
                    <Clapperboard size={13} />
                  </div>
                  <div>
                    <p className={styles.chatBatchHeaderTitle}>Live generation</p>
                    <p className={styles.chatBatchHeaderSub}>
                      {seed.sourceLabel}
                      {batch ? ` · ${shortId(batch.id)}` : ""}
                    </p>
                  </div>
                </div>
                <span className={`${styles.chatBatchStatusBadge} ${styles[`chatBatchStatusBadge-${toneForItemStatus(batch?.status ?? (localError ? "failed" : "queued"))}`]}`}>
                  {localError ? "failed" : batch?.status ?? humanizeConnectionState(connectionState)}
                </span>
              </div>

              <div className={styles.chatBatchMetaRow}>
                <span>{uploadedCount}/{batch?.requested_count ?? seed.initialEnvelope?.batch.requested_count ?? 0} exported</span>
                <span>{lastSyncedAt ? `Last sync ${formatClock(lastSyncedAt)}` : humanizeConnectionState(connectionState)}</span>
              </div>

              {canOpenShorts ? (
                <div className={styles.chatBatchActionRow}>
                  <button type="button" className={styles.chatBatchPrimaryButton} onClick={openInShorts}>
                    Open generated shorts
                  </button>
                </div>
              ) : null}

              {sortedItems.length > 0 ? (
                <div className={styles.chatBatchCarousel}>
                  {sortedItems.map(item => {
                    const meta = {
                      ...(liveMetadataByItem[item.id] ?? {}),
                      ...(item.render_metadata ?? {}),
                    };
                    const videoPreviewUrl = batch ? resolveBatchItemVideoUrl(batch.id, item) : null;
                    const hasVideo = item.status === "uploaded" && Boolean(item.output_url) && Boolean(videoPreviewUrl);
                    return (
                      <article key={item.id} className={styles.chatBatchItemCard}>
                        <div className={styles.chatBatchItemHeader}>
                          <div>
                            <p className={styles.chatBatchItemKicker}>Video {item.item_index + 1}</p>
                            <h3 className={styles.chatBatchItemTitle}>{item.script?.title ?? "Script pending"}</h3>
                          </div>
                          <span className={`${styles.chatBatchItemStatus} ${styles[`chatBatchItemStatus-${toneForItemStatus(item.status)}`]}`}>
                            {item.status}
                          </span>
                        </div>

                        {hasVideo ? (
                          <video
                            key={videoPreviewUrl ?? item.id}
                            className={styles.chatBatchVideo}
                            controls
                            preload="metadata"
                            playsInline
                            src={videoPreviewUrl ?? undefined}
                          />
                        ) : (
                          <div className={styles.chatBatchVideoPlaceholder}>
                            <Clapperboard size={16} />
                            <span>
                              {item.status === "failed"
                                ? "This video failed before export."
                                : "The MP4 preview will appear here as soon as rendering finishes."}
                            </span>
                          </div>
                        )}

                        <div className={styles.chatBatchItemMeta}>
                          <span>{stringValue(meta.subtitle_style_label) ?? "Subtitle pending"}</span>
                          <span>{stringValue(meta.subtitle_font_name) ?? "Font pending"}</span>
                          <span>{shortPath(stringValue(meta.gameplay_asset_path)) ?? "Gameplay pending"}</span>
                        </div>

                        <div className={styles.chatBatchItemFooter}>
                          <span>
                            {typeof item.script?.estimated_seconds === "number"
                              ? `${item.script.estimated_seconds.toFixed(1)}s est.`
                              : "Timing pending"}
                          </span>
                          {hasVideo ? (
                            <a href={videoPreviewUrl ?? "#"} target="_blank" rel="noreferrer">
                              Open render
                            </a>
                          ) : null}
                        </div>

                        {item.error ? <p className={styles.chatBatchItemError}>{item.error}</p> : null}
                      </article>
                    );
                  })}
                </div>
              ) : (
                <div className={styles.chatBatchPlaceholder}>
                  <Clapperboard size={16} />
                  <p>
                    {seed.batchId
                      ? "The batch exists. Videos and per-item status will appear here as narration and rendering start."
                      : "The batch card will populate once the backend accepts this chat request."}
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function parseEvent(data: string, fallbackType: string): BatchEventRecord | null {
  try {
    const parsed = JSON.parse(data) as Partial<BatchEventRecord>;
    return {
      sequence: parsed.sequence ?? 0,
      created_at: parsed.created_at ?? new Date().toISOString(),
      payload: parsed.payload ?? {},
      type: parsed.type ?? fallbackType,
    };
  } catch {
    return null;
  }
}

function shouldRefreshBatchForEvent(event: BatchEventRecord) {
  if (
    event.type === "status" ||
    event.type === "source_ingested" ||
    event.type === "scripts_ready" ||
    event.type === "narrator_conversation_started" ||
    event.type === "alignment_ready" ||
    event.type === "render_started" ||
    event.type === "item_completed" ||
    event.type === "batch_completed" ||
    event.type === "error" ||
    event.type === "done"
  ) {
    return true;
  }

  if (event.type !== "log") {
    return false;
  }

  const message = stringValue(event.payload.message) ?? "";
  return (
    message.startsWith("Accepted ") ||
    message.startsWith("Staging assets for item ") ||
    message.startsWith("Render completed for item ") ||
    message.startsWith("Producer failed")
  );
}

function shortId(value: string) {
  return value.slice(0, 8);
}

function resolveBatchItemVideoUrl(batchId: string, item: BatchItemRecord) {
  if (item.output_url && item.output_url.startsWith("http")) {
    return item.output_url;
  }
  return `/api/brainrot/batches/${batchId}/items/${item.id}/video`;
}

function OpenAIIcon({ size = 13 }: { size?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 256 260"
      aria-hidden="true"
      fill="currentColor"
    >
      <path d="M239.184 106.203a64.716 64.716 0 0 0-5.576-53.103C219.452 28.459 191 15.784 163.213 21.74A65.586 65.586 0 0 0 52.096 45.22a64.716 64.716 0 0 0-43.23 31.36c-14.31 24.602-11.061 55.634 8.033 76.74a64.665 64.665 0 0 0 5.525 53.102c14.174 24.65 42.644 37.324 70.446 31.36a64.72 64.72 0 0 0 48.754 21.744c28.481.025 53.714-18.361 62.414-45.481a64.767 64.767 0 0 0 43.229-31.36c14.137-24.558 10.875-55.423-8.083-76.483Zm-97.56 136.338a48.397 48.397 0 0 1-31.105-11.255l1.535-.87 51.67-29.825a8.595 8.595 0 0 0 4.247-7.367v-72.85l21.845 12.636c.218.111.37.32.409.563v60.367c-.056 26.818-21.783 48.545-48.601 48.601Zm-104.466-44.61a48.345 48.345 0 0 1-5.781-32.589l1.534.921 51.722 29.826a8.339 8.339 0 0 0 8.441 0l63.181-36.425v25.221a.87.87 0 0 1-.358.665l-52.335 30.184c-23.257 13.398-52.97 5.431-66.404-17.803ZM23.549 85.38a48.499 48.499 0 0 1 25.58-21.333v61.39a8.288 8.288 0 0 0 4.195 7.316l62.874 36.272-21.845 12.636a.819.819 0 0 1-.767 0L41.353 151.53c-23.211-13.454-31.171-43.144-17.804-66.405v.256Zm179.466 41.695-63.08-36.63L161.73 77.86a.819.819 0 0 1 .768 0l52.233 30.184a48.6 48.6 0 0 1-7.316 87.635v-61.391a8.544 8.544 0 0 0-4.4-7.213Zm21.742-32.69-1.535-.922-51.619-30.081a8.39 8.39 0 0 0-8.492 0L99.98 99.808V74.587a.716.716 0 0 1 .307-.665l52.233-30.133a48.652 48.652 0 0 1 72.236 50.391v.205ZM88.061 139.097l-21.845-12.585a.87.87 0 0 1-.41-.614V65.685a48.652 48.652 0 0 1 79.757-37.346l-1.535.87-51.67 29.825a8.595 8.595 0 0 0-4.246 7.367l-.051 72.697Zm11.868-25.58 28.138-16.217 28.188 16.218v32.434l-28.086 16.218-28.188-16.218-.052-32.434Z" />
    </svg>
  );
}

function LogIcon({ iconKey }: { iconKey: LogIconKey }) {
  switch (iconKey) {
    case "firecrawl":
      return <Globe size={13} />;
    case "openai":
      return <OpenAIIcon size={13} />;
    case "elevenlabs":
      return <AudioLines size={13} />;
    case "ffmpeg":
      return <Clapperboard size={13} />;
    case "qa":
      return <ShieldCheck size={13} />;
    case "success":
      return <CheckCircle2 size={13} />;
    case "warning":
      return <AlertTriangle size={13} />;
    case "danger":
      return <AlertTriangle size={13} />;
    default:
      return <Activity size={13} />;
  }
}

function producerProviderLabel(mode: string | null) {
  return mode === "elevenlabs_native" ? "ElevenLabs Agent" : "CrewAI + OpenAI";
}

function narrationProviderLabel(mode: string | null) {
  return mode === "elevenlabs_agent" ? "ElevenLabs Agent" : "ElevenLabs Voice API";
}

function narrationInFlightCopy(mode: string | null, payload: Record<string, unknown>) {
  if (mode === "elevenlabs_agent") {
    return {
      providerLabel: "ElevenLabs Agent",
      title: `The ElevenLabs narrator agent is still speaking ${videoLabelFromPayload(payload)}`,
      detail: "A live ElevenLabs agent conversation is still producing speech audio for this script before forced alignment can begin.",
    };
  }
  return {
    providerLabel: "ElevenLabs Voice API",
    title: `ElevenLabs is still generating voiceover audio for ${videoLabelFromPayload(payload)}`,
    detail: "The backend is generating direct ElevenLabs speech audio with the selected voice before subtitle timing can begin.",
  };
}

function narrationStartedCopy(mode: string | null, payload: Record<string, unknown>) {
  if (mode === "elevenlabs_agent") {
    return {
      providerLabel: "ElevenLabs Agent",
      title: `An ElevenLabs narrator agent conversation started for ${videoLabelFromPayload(payload)}`,
      detail: "The approved script is now being injected into a live ElevenLabs agent conversation so subtitle timing can be built from real audio.",
    };
  }
  return {
    providerLabel: "ElevenLabs Voice API",
    title: `ElevenLabs voice generation started for ${videoLabelFromPayload(payload)}`,
    detail: "The approved script is now being sent directly to the ElevenLabs speech API so real voice audio can be generated for this reel.",
  };
}

function producerStageCopy(mode: string | null, model: string | null) {
  if (mode === "elevenlabs_native") {
    return `An ElevenLabs producer agent is generating scripts with its configured model${model ? ` (${model})` : ""} and can return the bundle through the submit_script_bundle server tool.`;
  }
  return `CrewAI is planning article coverage and using OpenAI ${model ?? "model"} to write one section-based script per slot.`;
}

function formatClock(value: string) {
  return new Date(value).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function numberValue(value: unknown) {
  return typeof value === "number" ? value : null;
}

function stringValue(value: unknown) {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function shortPath(value: string | null) {
  if (!value) {
    return null;
  }
  if (value.length <= 44) {
    return value;
  }
  return `…${value.slice(-44)}`;
}

function compactLogEvents(events: BatchEventRecord[]) {
  const compacted: BatchEventRecord[] = [];
  for (const event of events) {
    if (!shouldShowEvent(event)) {
      continue;
    }
    const previous = compacted.at(-1);
    if (previous && canMergeHeartbeatEvent(previous, event)) {
      compacted[compacted.length - 1] = event;
      continue;
    }
    compacted.push(event);
  }
  return compacted;
}

function shouldShowEvent(event: BatchEventRecord) {
  if (event.type === "status") {
    return false;
  }
  if (event.type === "producer_conversation_started" || event.type === "producer_tool_called" || event.type === "narrator_audio_ready") {
    return false;
  }
  if (event.type === "log") {
    const message = stringValue(event.payload.message) ?? "";
    if (message.startsWith("Source ingestion completed for ")) {
      return false;
    }
    if (message.startsWith("OpenAI producer response received")) {
      return false;
    }
    if (message.startsWith("Repair response received")) {
      return false;
    }
    if (message.startsWith("Producer validation passed")) {
      return false;
    }
    if (message.startsWith("Producer finished and scripts are ready")) {
      return false;
    }
    if (message.startsWith("Narration started for item ")) {
      return false;
    }
    if (message.startsWith("Narration audio received for item ")) {
      return false;
    }
    if (message.startsWith("Render started for item ")) {
      return false;
    }
  }
  return true;
}

function canMergeHeartbeatEvent(previous: BatchEventRecord, next: BatchEventRecord) {
  if (previous.type !== "log" || next.type !== "log") {
    return false;
  }
  const previousHeartbeat = numberValue(previous.payload.heartbeat);
  const nextHeartbeat = numberValue(next.payload.heartbeat);
  if (previousHeartbeat === null || nextHeartbeat === null) {
    return false;
  }
  return (
    stringValue(previous.payload.stage) === stringValue(next.payload.stage) &&
    stringValue(previous.payload.message) === stringValue(next.payload.message) &&
    stringValue(previous.payload.item_id) === stringValue(next.payload.item_id) &&
    numberValue(previous.payload.attempt) === numberValue(next.payload.attempt) &&
    stringValue(previous.payload.model) === stringValue(next.payload.model)
  );
}

function toLogEntry(event: BatchEventRecord): LogEntry {
  const payload = event.payload;
  const base = {
    id: `${event.sequence}-${event.type}`,
    tone: "accent" as EntryTone,
    iconKey: "backend" as LogIconKey,
    providerLabel: "Backend",
  };

  if (event.type === "section_planning_started") {
    return { ...base, iconKey: "openai", providerLabel: "CrewAI", title: "CrewAI is planning article coverage", detail: withEventMeta("The source markdown is being split into meaningful article sections before any scripts are written.", event) };
  }
  if (event.type === "section_planning_completed") {
    return { ...base, tone: "success", iconKey: "success", providerLabel: "CrewAI", title: "CrewAI finished section planning", detail: withEventMeta(`${payload.section_count ?? 0} article sections were extracted for coverage planning.`, event) };
  }
  if (event.type === "coverage_plan_ready") {
    return { ...base, iconKey: "openai", providerLabel: "CrewAI", title: "CrewAI coverage plan is ready", detail: withEventMeta(`${payload.slot_count ?? 0} section-based script slots were planned from ${payload.section_count ?? 0} extracted sections.`, event) };
  }
  if (event.type === "slot_generation_started") {
    return { ...base, iconKey: "openai", providerLabel: "CrewAI", title: `CrewAI is writing slot ${Number(payload.slot_index ?? 0) + 1} from the ${stringValue(payload.section_heading) ? `"${stringValue(payload.section_heading)}"` : "assigned"} section`, detail: withEventMeta(`This slot is covering a different article section with the ${stringValue(payload.angle_family) ?? "assigned"} angle family.`, event) };
  }
  if (event.type === "slot_generation_completed") {
    return { ...base, tone: "success", iconKey: "success", providerLabel: "CrewAI", title: `CrewAI finished slot ${Number(payload.slot_index ?? 0) + 1}`, detail: withEventMeta(`The section draft for ${stringValue(payload.section_heading) ?? "this slot"} is ready for bundle QA.`, event) };
  }
  if (event.type === "slot_generation_failed") {
    return { ...base, tone: "danger", iconKey: "danger", providerLabel: "CrewAI", title: `CrewAI failed slot ${Number(payload.slot_index ?? 0) + 1}`, detail: withEventMeta(stringValue(payload.error) ?? "CrewAI could not complete this slot.", event) };
  }
  if (event.type === "slot_repair_started") {
    return { ...base, iconKey: "qa", providerLabel: "CrewAI Repair", title: `CrewAI is repairing slot ${Number(payload.slot_index ?? 0) + 1}`, detail: withEventMeta("This slot is being rewritten to remove overlap and fix grounding issues without losing section coverage.", event) };
  }
  if (event.type === "slot_repair_completed") {
    return { ...base, tone: "success", iconKey: "success", providerLabel: "CrewAI Repair", title: `CrewAI repaired slot ${Number(payload.slot_index ?? 0) + 1}`, detail: withEventMeta("The corrected slot now fits the coverage plan and can move back into QA.", event) };
  }
  if (event.type === "producer_bundle_completed") {
    return { ...base, tone: "success", iconKey: "success", providerLabel: "CrewAI", title: "CrewAI coverage bundle is complete", detail: withEventMeta(`${payload.slot_count ?? 0} section-based scripts are ready for final backend QA.`, event) };
  }

  if (event.type === "log") {
    const validationSummary = summarizeValidationSummary(stringValue(payload.validation_summary));
    const title = stringValue(payload.message) ?? "Backend update";
    if (title.startsWith("Starting source ingestion.")) {
      return { ...base, iconKey: "firecrawl", providerLabel: "Firecrawl", title: "Source ingest pipeline started", detail: withEventMeta("The backend is preparing the incoming URL for Firecrawl so the article can be turned into clean markdown.", event) };
    }
    if (title.startsWith("Starting Firecrawl ingest for ")) {
      return { ...base, iconKey: "firecrawl", providerLabel: "Firecrawl", title: "Firecrawl ingest session started", detail: withEventMeta("Firecrawl is opening the source so the backend can pull a normalized markdown brief from the page.", event) };
    }
    if (title.startsWith("Scraping ") && title.includes(" via Firecrawl.")) {
      const sourceUrl = title.replace("Scraping ", "").replace(" via Firecrawl.", "");
      return { ...base, iconKey: "firecrawl", providerLabel: "Firecrawl", title: "Firecrawl is scraping the source URL", detail: withEventMeta(`${sourceUrl} is being converted into clean page content, metadata, and normalized links for the rest of the pipeline.`, event) };
    }
    if (title.startsWith("Scrape completed for ")) {
      return { ...base, tone: "success", iconKey: "success", providerLabel: "Firecrawl", title: "Firecrawl returned the article content", detail: withEventMeta(`Captured ${title.replace("Scrape completed for ", "").replace(".", "")} and handed the cleaned result back to the backend.`, event) };
    }
    if (title.startsWith("Firecrawl scrape request is still running.")) {
      return { ...base, iconKey: "firecrawl", providerLabel: "Firecrawl", title: "Firecrawl is still scraping the source URL", detail: withEventMeta("The scrape request is still in flight, so the backend is waiting for Firecrawl to return clean page content.", event) };
    }
    if (title.startsWith("Firecrawl site mapping request is still running.")) {
      return { ...base, iconKey: "firecrawl", providerLabel: "Firecrawl", title: "Firecrawl is still mapping the site", detail: withEventMeta("The mapping request is still selecting which URLs belong in this source before content extraction continues.", event) };
    }
    if (title.startsWith("CrewAI slot generation is still running.")) {
      const activeSlotCount = numberValue(payload.active_slot_count) ?? 0;
      const activeSlots = Array.isArray(payload.active_slots)
        ? payload.active_slots.filter((value): value is number => typeof value === "number")
        : [];
      const slotLabel = activeSlots.length > 0 ? `Slots ${activeSlots.join(", ")} are still waiting on OpenAI responses.` : "CrewAI is still waiting for the active slot writers to return.";
      return { ...base, iconKey: "openai", providerLabel: "CrewAI + OpenAI", title: `CrewAI is still writing ${activeSlotCount || activeSlots.length || "the active"} slot${(activeSlotCount || activeSlots.length || 1) === 1 ? "" : "s"}`, detail: withEventMeta(slotLabel, event) };
    }
    if (title.startsWith("CrewAI slot repair is still running.")) {
      const activeSlotCount = numberValue(payload.active_slot_count) ?? 0;
      const activeSlots = Array.isArray(payload.active_slots)
        ? payload.active_slots.filter((value): value is number => typeof value === "number")
        : [];
      const slotLabel = activeSlots.length > 0 ? `Repair is still running for slots ${activeSlots.join(", ")}.` : "CrewAI repair is still waiting for the active slot writers to finish.";
      return { ...base, iconKey: "qa", providerLabel: "CrewAI Repair", title: `CrewAI repair is still running for ${activeSlotCount || activeSlots.length || "the active"} slot${(activeSlotCount || activeSlots.length || 1) === 1 ? "" : "s"}`, detail: withEventMeta(slotLabel, event) };
    }
    if (title.startsWith("Waiting for OpenAI producer response on attempt ")) {
      const mode = stringValue(payload.mode);
      return { ...base, iconKey: "openai", providerLabel: producerProviderLabel(mode), title: `OpenAI script pass ${payload.attempt ?? "?"}/3 is still running`, detail: withEventMeta(`${producerStageCopy(mode, stringValue(payload.model))} The current pass is still generating scripts from the Firecrawl brief.`, event) };
    }
    if (title.startsWith("Waiting for producer repair response on attempt ")) {
      const mode = stringValue(payload.mode);
      return { ...base, iconKey: "openai", providerLabel: producerProviderLabel(mode), title: `${mode === "elevenlabs_native" ? "ElevenLabs producer-agent repair pass" : "OpenAI repair pass"} ${payload.attempt ?? "?"}/3 is still running`, detail: withEventMeta(`${producerStageCopy(mode, stringValue(payload.model))} The repair pass is still rewriting the rejected scripts so the batch can recover without a full restart.`, event) };
    }
    if (title.startsWith("Waiting for ElevenLabs narration audio for item ")) {
      const mode = stringValue(payload.mode);
      const copy = narrationInFlightCopy(mode, payload);
      return { ...base, iconKey: "elevenlabs", providerLabel: copy.providerLabel, title: copy.title, detail: withEventMeta(copy.detail, event) };
    }
    if (title.startsWith("Waiting for ElevenLabs TTS audio for item ")) {
      const copy = narrationInFlightCopy("elevenlabs_tts", payload);
      return { ...base, iconKey: "elevenlabs", providerLabel: copy.providerLabel, title: copy.title, detail: withEventMeta(copy.detail, event) };
    }
    if (title.startsWith("FFmpeg still rendering item ")) {
      return { ...base, iconKey: "ffmpeg", providerLabel: "FFmpeg", title: `FFmpeg is still rendering ${videoLabelFromPayload(payload)}`, detail: withEventMeta("Gameplay, narration, and ASS subtitles are still being composited into the final MP4 artifact.", event) };
    }
    if (title.startsWith("Producer started")) {
      const mode = stringValue(payload.mode);
      const model = stringValue(payload.model) ?? "default model";
      return { ...base, iconKey: mode === "direct_openai" ? "openai" : "elevenlabs", providerLabel: producerProviderLabel(mode), title: "Script generation pipeline started", detail: withEventMeta(producerStageCopy(mode, model), event) };
    }
    if (title.startsWith("Producer attempt ")) {
      const mode = stringValue(payload.mode);
      return { ...base, iconKey: mode === "elevenlabs_native" ? "elevenlabs" : "openai", providerLabel: producerProviderLabel(mode), title: `${mode === "elevenlabs_native" ? "Starting ElevenLabs producer-agent pass" : "Starting OpenAI script pass"} ${payload.attempt ?? "?"}/3`, detail: withEventMeta("The backend is opening a fresh generation attempt because the previous pass did not return a final accepted bundle.", event) };
    }
    if (title.startsWith("OpenAI request started for producer attempt ")) {
      const mode = stringValue(payload.mode);
      return { ...base, iconKey: "openai", providerLabel: producerProviderLabel(mode), title: `OpenAI script request ${payload.attempt ?? "?"}/3 was sent`, detail: withEventMeta(`${producerStageCopy(mode, stringValue(payload.model))} The returned scripts will be checked by local backend QA before they can reach video generation.`, event) };
    }
    if (title.startsWith("Producer submitted script bundle. Validating scripts now.")) {
      const mode = stringValue(payload.mode);
      return { ...base, iconKey: "qa", providerLabel: "Backend QA", title: mode === "elevenlabs_native" ? "The ElevenLabs producer agent returned a script bundle" : "OpenAI returned a script bundle", detail: withEventMeta("The backend is now running local QA to check word count, hook grounding, duplicate ideas, and fact quality before any script can reach video generation.", event) };
    }
    if (title.startsWith("Validation failed on attempt ")) {
      return { ...base, tone: "warning", iconKey: "warning", providerLabel: "Backend QA", title: `Local QA rejected script pass ${payload.attempt ?? "?"}/3`, detail: withEventMeta(`${validationSummary ?? "The current bundle did not meet the batch rules"}. The backend is sending only the failed issues back for repair instead of stopping the run.`, event) };
    }
    if (title.startsWith("Repair request started for attempt ")) {
      const mode = stringValue(payload.mode);
      return { ...base, iconKey: mode === "elevenlabs_native" ? "elevenlabs" : "openai", providerLabel: producerProviderLabel(mode), title: `${mode === "elevenlabs_native" ? "ElevenLabs producer-agent repair pass" : "OpenAI repair pass"} ${payload.attempt ?? "?"}/3 started`, detail: withEventMeta(`${validationSummary ?? "The failed scripts are being rewritten"}. ${mode === "elevenlabs_native" ? "The active ElevenLabs producer agent" : "OpenAI"} is focusing on broken hooks, facts, and pacing issues.`, event) };
    }
    if (title.startsWith("Repair succeeded on attempt ")) {
      return { ...base, tone: "success", iconKey: "success", providerLabel: "Backend QA", title: `Repair pass ${payload.attempt ?? "?"}/3 fixed the rejected scripts`, detail: withEventMeta("The repaired scripts cleared local QA and can now move forward to narration and rendering.", event) };
    }
    if (title.startsWith("Repair failed on attempt ")) {
      return { ...base, tone: "danger", iconKey: "danger", providerLabel: "Backend QA", title: `Repair pass ${payload.attempt ?? "?"}/3 still failed QA`, detail: withEventMeta(`${summarizeValidationSummary(stringValue(payload.error)) ?? "Some script issues were still unresolved"}. The backend will try another full generation pass.`, event) };
    }
    if (title.startsWith("Applied local script fixes after ")) {
      const repairParts = [
        numberValue(payload.title_repairs) ? `${payload.title_repairs} title cleanup` : null,
        numberValue(payload.hook_repairs) ? `${payload.hook_repairs} hook cleanup` : null,
        numberValue(payload.fact_repairs) ? `${payload.fact_repairs} fact cleanup` : null,
        numberValue(payload.narration_repairs) ? `${payload.narration_repairs} narration extension` : null,
      ].filter(Boolean);
      return { ...base, tone: "success", iconKey: "qa", providerLabel: "Backend QA", title: "Backend normalization cleaned the script bundle", detail: withEventMeta(repairParts.length > 0 ? `${repairParts.join(", ")} were applied before QA so formatting issues do not block the batch.` : "The backend applied local cleanup so formatting issues do not block the batch.", event) };
    }
    if (title.startsWith("Accepted ")) {
      return { ...base, tone: "success", iconKey: "success", providerLabel: "Backend", title: "Approved scripts are already moving into production", detail: withEventMeta(`${stringValue(payload.source) ?? "This slice"} passed QA, so the backend started asset selection, ElevenLabs narrator-agent conversations, and rendering immediately instead of waiting for the full batch.`, event) };
    }
    if (title.startsWith("Render completed for item ")) {
      return { ...base, tone: "success", iconKey: "success", providerLabel: "FFmpeg", title: `${videoLabelFromPayload(payload)} finished FFmpeg assembly`, detail: withEventMeta("The final frame burn is done and the backend is uploading the MP4 artifact now.", event) };
    }
    if (title.startsWith("Producer request failed on attempt ")) {
      const mode = stringValue(payload.mode);
      return { ...base, tone: "warning", iconKey: "warning", providerLabel: producerProviderLabel(mode), title: `${mode === "elevenlabs_native" ? "ElevenLabs producer-agent pass" : "OpenAI script pass"} ${payload.attempt ?? "?"}/3 failed to return cleanly`, detail: withEventMeta(`${summarizeValidationSummary(stringValue(payload.error)) ?? "The request failed"}. The backend is retrying automatically.`, event) };
    }
    if (title.startsWith("Producer failed")) {
      const mode = stringValue(payload.mode);
      return { ...base, tone: "danger", iconKey: "danger", providerLabel: producerProviderLabel(mode), title: "Script generation failed", detail: withEventMeta(`${summarizeValidationSummary(stringValue(payload.error)) ?? "The producer could not deliver a valid bundle after all retries"}.`, event) };
    }
    if (title.startsWith("Staging assets for item ")) {
      return { ...base, iconKey: "backend", providerLabel: "Backend", title: `${videoLabelFromPayload(payload)} is selecting gameplay and subtitle assets`, detail: withEventMeta("The backend is matching this approved script with gameplay footage, subtitle treatment, and optional music before FFmpeg render begins.", event) };
    }

    return { ...base, title, detail: withEventMeta(summarizeValidationSummary(stringValue(payload.error)) ?? validationSummary, event) };
  }

  if (event.type === "source_ingested") {
    return { ...base, tone: "success", iconKey: "success", providerLabel: "Firecrawl", title: "Firecrawl finished ingesting the source", detail: withEventMeta(`Captured "${stringValue(payload.title) ?? "source"}" as clean markdown with ${payload.url_count ?? 0} normalized source URL${Number(payload.url_count) === 1 ? "" : "s"}.`, event) };
  }
  if (event.type === "scripts_ready") {
    const mode = stringValue(payload.mode);
    return { ...base, tone: "success", iconKey: "success", providerLabel: producerProviderLabel(mode), title: "Script generation is complete", detail: withEventMeta(`${payload.script_count ?? 0} scripts cleared local QA after ${payload.attempt_count ?? 0} generation attempt${Number(payload.attempt_count) === 1 ? "" : "s"} and ${payload.repair_count ?? 0} repair pass${Number(payload.repair_count) === 1 ? "" : "es"}. ${mode === "elevenlabs_native" ? "These scripts came from the ElevenLabs producer agent." : `${payload.section_count ?? payload.script_count ?? 0} article sections were planned into ${payload.planned_count ?? payload.script_count ?? 0} section-based script slots through the CrewAI producer.`}`, event) };
  }
  if (event.type === "narrator_conversation_started") {
    const mode = stringValue(payload.mode);
    const copy = narrationStartedCopy(mode, payload);
    return { ...base, iconKey: "elevenlabs", providerLabel: copy.providerLabel, title: copy.title, detail: withEventMeta(copy.detail, event) };
  }
  if (event.type === "alignment_ready") {
    return { ...base, tone: "success", iconKey: "success", providerLabel: "ElevenLabs Alignment", title: `ElevenLabs forced alignment finished for ${videoLabelFromPayload(payload)}`, detail: withEventMeta(`Mapped ${payload.word_count ?? 0} spoken words to timestamps so subtitles can animate against the real narration instead of estimated text timing.`, event) };
  }
  if (event.type === "render_started") {
    return { ...base, iconKey: "ffmpeg", providerLabel: "FFmpeg", title: `FFmpeg render started for ${videoLabelFromPayload(payload)}`, detail: withEventMeta(`Combining ${stringValue(payload.subtitle_style_label) ?? "subtitle style"} subtitles with ${shortPath(stringValue(payload.gameplay_asset_path)) ?? "the selected gameplay clip"} and narration audio.`, event) };
  }
  if (event.type === "item_completed") {
    return { ...base, tone: "success", iconKey: "success", providerLabel: "FFmpeg", title: `${videoLabelFromPayload(payload)} is fully exported`, detail: withEventMeta(`${shortPath(stringValue(payload.output_url)) ?? "The final MP4"} is ready for review or upload.`, event) };
  }
  if (event.type === "batch_completed" || event.type === "done") {
    const uploadedCount = numberValue(payload.uploaded_count) ?? 0;
    const failedCount = numberValue(payload.failed_count) ?? 0;
    const requestedCount = uploadedCount + failedCount;
    const ratio = requestedCount > 0 ? uploadedCount / requestedCount : 0;
    const completion = completionCopyFromRatio(ratio, uploadedCount);
    return {
      ...base,
      tone: completion.tone,
      iconKey: completion.iconKey,
      providerLabel: "Backend",
      title: completion.title === "The batch has finished successfully"
        ? "Batch finished successfully"
        : completion.title === "The batch partially succeeded"
          ? "Batch partially succeeded"
          : "Batch failed",
      detail: withEventMeta(
        uploadedCount > 0
          ? `${uploadedCount} videos exported${failedCount > 0 ? `, ${failedCount} did not finish` : ""}`
          : "No videos were exported",
        event,
      ),
    };
  }
  if (event.type === "error") {
    return { ...base, tone: "danger", iconKey: "danger", providerLabel: "Backend", title: "Backend error", detail: withEventMeta(stringValue(payload.message) ?? "Backend error", event) };
  }

  return { ...base, title: event.type.replaceAll("_", " "), detail: withEventMeta(JSON.stringify(payload), event) };
}

function buildActiveOperations(events: BatchEventRecord[], nowTick: number): ActiveOperation[] {
  const operations = new Map<string, BatchEventRecord>();
  for (const event of events) {
    clearResolvedOperations(operations, event);
    const key = activeOperationKey(event);
    if (key) {
      operations.set(key, event);
    }
  }
  return Array.from(operations.entries())
    .map(([key, event]) => toActiveOperation(key, event, nowTick))
    .sort((left, right) => {
      const leftMs = left.liveLabel ? 1 : 0;
      const rightMs = right.liveLabel ? 1 : 0;
      return rightMs - leftMs;
    });
}

function clearResolvedOperations(operations: Map<string, BatchEventRecord>, event: BatchEventRecord) {
  const itemId = stringValue(event.payload.item_id);
  const slotId = stringValue(event.payload.slot_id);
  const status = stringValue(event.payload.status);
  const stage = stringValue(event.payload.stage);
  if (event.type === "source_ingested" || status === "scripting" || status === "completed" || status === "failed" || status === "partial_failed") {
    operations.delete("ingest");
  }
  if (event.type === "section_planning_completed" || event.type === "coverage_plan_ready") {
    operations.delete("producer:planning");
  }
  if ((event.type === "slot_generation_completed" || event.type === "slot_generation_failed" || event.type === "slot_repair_completed") && slotId) {
    operations.delete(`producer:${slotId}`);
  }
  if (event.type === "scripts_ready" || event.type === "batch_completed" || (event.type === "error" && stage === "producer")) {
    operations.delete("producer");
    deleteOperationsByPrefix(operations, "producer:");
  }
  if (event.type === "render_started" && itemId) {
    operations.delete(`assets:${itemId}`);
  }
  if ((event.type === "narrator_audio_ready" || event.type === "alignment_ready") && itemId) {
    operations.delete(`narration:${itemId}`);
  }
  if (event.type === "item_completed" && itemId) {
    operations.delete(`narration:${itemId}`);
    operations.delete(`assets:${itemId}`);
    operations.delete(`render:${itemId}`);
  }
  if (event.type === "error" && itemId) {
    operations.delete(`narration:${itemId}`);
    operations.delete(`assets:${itemId}`);
    operations.delete(`render:${itemId}`);
  }
  if (event.type === "batch_completed") {
    operations.clear();
  }
}

function deleteOperationsByPrefix(operations: Map<string, BatchEventRecord>, prefix: string) {
  for (const key of operations.keys()) {
    if (key.startsWith(prefix)) {
      operations.delete(key);
    }
  }
}

function activeOperationKey(event: BatchEventRecord) {
  const stage = stringValue(event.payload.stage);
  const itemId = stringValue(event.payload.item_id);
  const slotId = stringValue(event.payload.slot_id);
  if (event.type === "section_planning_started") {
    return "producer:planning";
  }
  if ((event.type === "slot_generation_started" || event.type === "slot_repair_started") && slotId) {
    return `producer:${slotId}`;
  }
  if (event.type === "narrator_conversation_started" && itemId) {
    return `narration:${itemId}`;
  }
  if (event.type === "render_started" && itemId) {
    return `render:${itemId}`;
  }
  if (event.type !== "log" || !stage) {
    return null;
  }
  if (stage === "ingest") {
    return "ingest";
  }
  if (stage === "producer") {
    return "producer";
  }
  if ((stage === "narration" || stage === "assets" || stage === "render") && itemId) {
    return `${stage}:${itemId}`;
  }
  return null;
}

function toActiveOperation(key: string, event: BatchEventRecord, nowTick: number): ActiveOperation {
  const entry = toLogEntry(event);
  const updatedAtMs = new Date(event.created_at).getTime();
  const secondsSinceUpdate = Math.max(0, (nowTick - updatedAtMs) / 1000);
  const elapsed = numberValue(event.payload.total_elapsed_seconds) ?? numberValue(event.payload.elapsed_seconds);
  const liveElapsed = elapsed !== null
    ? `Live for ${(elapsed + secondsSinceUpdate).toFixed(1)}s · last backend update ${secondsSinceUpdate < 1 ? "just now" : `${Math.floor(secondsSinceUpdate)}s ago`}`
    : secondsSinceUpdate < 1
      ? "Last backend update just now"
      : `Last backend update ${Math.floor(secondsSinceUpdate)}s ago`;

  return {
    id: `${key}-${event.sequence}`,
    title: entry.title,
    detail: entry.detail,
    liveLabel: liveElapsed,
    tone: entry.tone,
    iconKey: entry.iconKey,
    providerLabel: entry.providerLabel,
    kind: activeOperationKind(key),
  };
}

function activeOperationKind(key: string): ActiveOperation["kind"] {
  if (key === "ingest") return "ingest";
  if (key === "producer" || key.startsWith("producer:")) return "producer";
  if (key.startsWith("narration:")) return "narration";
  if (key.startsWith("assets:")) return "assets";
  if (key.startsWith("render:")) return "render";
  return "backend";
}

function buildActivitySummary(
  activeOperations: ActiveOperation[],
  latestLogEvent: BatchEventRecord | null,
  batch: BatchRecord | null,
  nowTick: number,
  isBatchSettled: boolean,
  uploadedCount: number,
  requestedCount: number,
): ActivitySummary {
  if (activeOperations.length === 0) {
    if (isBatchSettled) {
      const ratio = requestedCount > 0 ? uploadedCount / requestedCount : 0;
      const completion = completionCopyFromRatio(ratio, uploadedCount);
      return {
        title: completion.title,
        detail: completion.detail,
        liveLabel: latestLogEvent ? `Finished at ${formatClock(latestLogEvent.created_at)}` : null,
        tone: completion.tone,
        iconKey: completion.iconKey,
        providerLabel: "Backend",
      };
    }

    const latestEntry = latestLogEvent ? toLogEntry(latestLogEvent) : null;
    return {
      title: latestEntry?.title ?? "Waiting for the next backend stage",
      detail: latestEntry?.detail ?? "The SSE stream is open. The next Firecrawl, OpenAI, ElevenLabs, or FFmpeg update will appear here as soon as the backend publishes it.",
      liveLabel: latestLogEvent
        ? `${Math.max(0, Math.floor((nowTick - new Date(latestLogEvent.created_at).getTime()) / 1000))}s since the last backend update`
        : "Listening for backend work",
      tone: latestEntry?.tone ?? "neutral",
      iconKey: latestEntry?.iconKey ?? "backend",
      providerLabel: latestEntry?.providerLabel ?? "Backend",
    };
  }

  const primary = activeOperations[0];
  const countsByKind = activeOperations.reduce<Record<ActiveOperation["kind"], number>>(
    (accumulator, operation) => {
      accumulator[operation.kind] += 1;
      return accumulator;
    },
    { ingest: 0, producer: 0, narration: 0, assets: 0, render: 0, backend: 0 },
  );

  const mixedSegments = [
    countsByKind.producer ? `${countsByKind.producer} CrewAI producer ${countsByKind.producer === 1 ? "job" : "jobs"}` : null,
    countsByKind.narration ? `${countsByKind.narration} ElevenLabs narration ${countsByKind.narration === 1 ? "job" : "jobs"}` : null,
    countsByKind.render ? `${countsByKind.render} FFmpeg render ${countsByKind.render === 1 ? "job" : "jobs"}` : null,
    countsByKind.assets ? `${countsByKind.assets} asset planning ${countsByKind.assets === 1 ? "step" : "steps"}` : null,
  ].filter(Boolean);

  if (countsByKind.ingest > 0 && activeOperations.length === countsByKind.ingest) {
    return {
      title: "Firecrawl is still ingesting the source",
      detail: "The backend is waiting for Firecrawl to finish turning the source into clean markdown, metadata, and normalized links.",
      liveLabel: primary.liveLabel,
      tone: primary.tone,
      iconKey: "firecrawl",
      providerLabel: "Firecrawl",
    };
  }
  if (countsByKind.producer > 0 && activeOperations.length === countsByKind.producer) {
    return {
      title: "CrewAI is planning and writing section-based scripts",
      detail: "CrewAI is covering different parts of the article and using OpenAI to write one short per slot while backend QA checks grounding, overlap, and uniqueness.",
      liveLabel: primary.liveLabel,
      tone: primary.tone,
      iconKey: "openai",
      providerLabel: "CrewAI",
    };
  }
  if (countsByKind.narration > 0 && activeOperations.length === countsByKind.narration) {
    const narrationProvider = primary.providerLabel;
    return {
      title: narrationProvider === "ElevenLabs Agent"
        ? `ElevenLabs narrator-agent conversations are live for ${countsByKind.narration} ${countsByKind.narration === 1 ? "video" : "videos"}`
        : `ElevenLabs voice generation is running for ${countsByKind.narration} ${countsByKind.narration === 1 ? "video" : "videos"}`,
      detail: narrationProvider === "ElevenLabs Agent"
        ? "Approved scripts are being spoken inside live ElevenLabs agent conversations, then ElevenLabs forced alignment timestamps every spoken word from the real audio."
        : "Approved scripts are being turned into direct ElevenLabs speech, then timing data is used to sync subtitles against the real voiceover.",
      liveLabel: primary.liveLabel,
      tone: primary.tone,
      iconKey: "elevenlabs",
      providerLabel: narrationProvider,
    };
  }
  if (countsByKind.narration > 0) {
    return {
      title: "The backend is running multiple stages in parallel",
      detail: `${mixedSegments.join(" · ")} are active. New events are inserted at the top of the log history below.`,
      liveLabel: primary.liveLabel,
      tone: "accent",
      iconKey: "elevenlabs",
      providerLabel: primary.providerLabel,
    };
  }
  if (countsByKind.render > 0 && activeOperations.length === countsByKind.render) {
    return {
      title: `FFmpeg is rendering ${countsByKind.render} ${countsByKind.render === 1 ? "video" : "videos"} right now`,
      detail: "Gameplay, voiceover, and animated subtitles are being burned into final MP4 exports.",
      liveLabel: primary.liveLabel,
      tone: primary.tone,
      iconKey: "ffmpeg",
      providerLabel: "FFmpeg",
    };
  }
  return {
    title: "The backend is running multiple stages in parallel",
    detail: `${mixedSegments.join(" · ")} are active. New events are inserted at the top of the log history below.`,
    liveLabel: primary.liveLabel,
    tone: "accent",
    iconKey: primary.iconKey,
    providerLabel: primary.providerLabel,
  };
}

function summarizeValidationSummary(value: string | null) {
  if (!value) {
    return null;
  }
  const issues = value.split(";").map(item => item.trim()).filter(Boolean);
  if (issues.length === 0) {
    return value;
  }
  const shortScripts = issues.filter(issue => issue.includes("words")).length;
  const ungroundedHooks = issues.filter(issue => issue.includes("hook is not grounded")).length;
  const malformedFacts = issues.filter(issue => issue.includes("malformed source_facts_used")).length;
  const genericHooks = issues.filter(issue => issue.includes("generic hook starter")).length;
  const genericCopy = issues.filter(issue => issue.includes("generic marketing phrasing")).length;
  const summaryParts = [
    shortScripts ? `${shortScripts} script${shortScripts === 1 ? "" : "s"} too short` : null,
    ungroundedHooks ? `${ungroundedHooks} hook${ungroundedHooks === 1 ? "" : "s"} not grounded in source facts` : null,
    malformedFacts ? `${malformedFacts} malformed fact list${malformedFacts === 1 ? "" : "s"}` : null,
    genericHooks ? `${genericHooks} generic hook${genericHooks === 1 ? "" : "s"}` : null,
    genericCopy ? `${genericCopy} generic marketing phrase${genericCopy === 1 ? "" : "s"}` : null,
  ].filter(Boolean);
  if (summaryParts.length > 0) {
    return `${summaryParts.join("; ")}.`;
  }
  return issues.slice(0, 2).join(" · ");
}

function withEventMeta(detail: string | null, event: BatchEventRecord) {
  const metaParts = [formatClock(event.created_at), eventElapsedLabel(event.payload)].filter(Boolean);
  const normalizedDetail = detail?.trim().replace(/[. ]+$/, "") ?? null;
  if (!normalizedDetail) {
    return metaParts.length > 0 ? metaParts.join(" · ") : null;
  }
  return metaParts.length > 0 ? `${normalizedDetail}. ${metaParts.join(" · ")}` : `${normalizedDetail}.`;
}

function eventElapsedLabel(payload: Record<string, unknown>) {
  const totalElapsed = numberValue(payload.total_elapsed_seconds);
  if (totalElapsed !== null) {
    return `${totalElapsed.toFixed(1)}s total`;
  }
  const elapsed = numberValue(payload.elapsed_seconds);
  if (elapsed !== null) {
    return `${elapsed.toFixed(1)}s`;
  }
  return null;
}

function videoLabelFromPayload(payload: Record<string, unknown>) {
  const itemIndex = numberValue(payload.item_index);
  if (itemIndex !== null) {
    return `video ${itemIndex + 1}`;
  }
  const itemId = stringValue(payload.item_id);
  if (itemId) {
    return `video ${shortId(itemId)}`;
  }
  return "this video";
}

function isSettledStatus(status: string | null | undefined) {
  return status === "completed" || status === "partial_failed" || status === "failed";
}

function formatThinkingDuration(events: BatchEventRecord[], nowTick: number, isSettled: boolean) {
  if (events.length === 0) {
    return "0s";
  }
  const startedAt = new Date(events[0].created_at).getTime();
  const endedAt = isSettled ? new Date(events.at(-1)?.created_at ?? events[0].created_at).getTime() : nowTick;
  return formatDurationLabel(Math.max(0, Math.round((endedAt - startedAt) / 1000)));
}

function formatDurationLabel(totalSeconds: number) {
  if (totalSeconds < 60) {
    return `${totalSeconds}s`;
  }
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) {
    return `${minutes}m ${seconds}s`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m ${seconds}s`;
}

function completionCopyFromRatio(ratio: number, uploadedCount: number) {
  if (uploadedCount <= 0) {
    return {
      title: "The batch could not export any videos",
      detail: "No final MP4s were exported for this run. Use the log history below to inspect the stopping point.",
      tone: "danger" as const,
      iconKey: "danger" as const,
    };
  }
  if (ratio >= 0.75) {
    return {
      title: "The batch has finished successfully",
      detail: "The backend has finished Firecrawl ingest, script generation, narration, alignment, and FFmpeg export for this run.",
      tone: "success" as const,
      iconKey: "success" as const,
    };
  }
  return {
    title: "The batch partially succeeded",
    detail: "Some videos were exported successfully, and the completed renders are ready for review in Shorts.",
    tone: "warning" as const,
    iconKey: "warning" as const,
  };
}

function humanizeConnectionState(value: ConnectionState) {
  switch (value) {
    case "connecting":
      return "connecting";
    case "streaming":
      return "streaming";
    case "reconnecting":
      return "reconnecting";
    case "settled":
      return "complete";
    default:
      return "idle";
  }
}

function toneForItemStatus(status: string): "success" | "danger" | "accent" | "warning" | "neutral" {
  if (status === "uploaded" || status === "completed") {
    return "success";
  }
  if (status === "failed" || status === "partial_failed") {
    return "danger";
  }
  if (status === "rendering") {
    return "warning";
  }
  if (status === "narrating" || status === "selecting_assets" || status === "scripting") {
    return "accent";
  }
  return "neutral";
}
