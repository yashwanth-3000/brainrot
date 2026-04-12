"use client";

import type { FormEvent, ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  AudioLines,
  Bot,
  CheckCircle2,
  ChevronRight,
  Clapperboard,
  Globe,
  Link2,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  WandSparkles,
} from "lucide-react";

import styles from "./test-page.module.css";

type BatchRecord = {
  id: string;
  source_url?: string | null;
  title_hint?: string | null;
  requested_count: number;
  status: string;
  error?: string | null;
  metadata?: Record<string, unknown>;
};

type BatchItemRecord = {
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

type BatchEnvelope = {
  batch: BatchRecord;
  items: BatchItemRecord[];
};

type BatchEventRecord = {
  sequence: number;
  type: string;
  created_at: string;
  payload: Record<string, unknown>;
};

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

type DemoTraceMode = "live" | "snapshot" | "playback";

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

const DEMO_TRACE_SEQUENCE: LogEntry[] = [
  {
    id: "demo-01",
    providerLabel: "ElevenLabs Agent",
    iconKey: "elevenlabs",
    tone: "accent",
    title: "An ElevenLabs narrator agent conversation started for video 2a8e6720",
    detail:
      "The approved script is now being injected into a live ElevenLabs agent conversation so subtitle timing can be built from real audio. 15:08:41",
  },
  {
    id: "demo-02",
    providerLabel: "FFmpeg",
    iconKey: "ffmpeg",
    tone: "accent",
    title: "FFmpeg is still rendering video 1",
    detail:
      "Gameplay, narration, and ASS subtitles are still being composited into the final MP4 artifact. 15:08:39 · 12.5s",
  },
  {
    id: "demo-03",
    providerLabel: "FFmpeg",
    iconKey: "ffmpeg",
    tone: "accent",
    title: "FFmpeg is still rendering video 2",
    detail:
      "Gameplay, narration, and ASS subtitles are still being composited into the final MP4 artifact. 15:08:40 · 12.5s",
  },
  {
    id: "demo-04",
    providerLabel: "FFmpeg",
    iconKey: "ffmpeg",
    tone: "accent",
    title: "FFmpeg is still rendering video 3",
    detail:
      "Gameplay, narration, and ASS subtitles are still being composited into the final MP4 artifact. 15:08:40 · 12.5s",
  },
  {
    id: "demo-05",
    providerLabel: "FFmpeg",
    iconKey: "ffmpeg",
    tone: "accent",
    title: "FFmpeg is still rendering video 4",
    detail:
      "Gameplay, narration, and ASS subtitles are still being composited into the final MP4 artifact. 15:08:40 · 12.5s",
  },
  {
    id: "demo-06",
    providerLabel: "FFmpeg",
    iconKey: "success",
    tone: "success",
    title: "video 1 is fully exported",
    detail:
      "…b0d/d669f47e-35dd-44c2-877a-1b59d0ed12fb.mp4 is ready for review or upload. 15:08:41",
  },
  {
    id: "demo-07",
    providerLabel: "FFmpeg",
    iconKey: "success",
    tone: "success",
    title: "video 2 is fully exported",
    detail:
      "…b0d/cbd8e32d-272c-47fd-9c8e-ce44dde736b9.mp4 is ready for review or upload. 15:08:47",
  },
  {
    id: "demo-08",
    providerLabel: "FFmpeg",
    iconKey: "success",
    tone: "success",
    title: "video 4 is fully exported",
    detail:
      "…b0d/851c67d7-7f81-4e95-8ceb-94089106faeb.mp4 is ready for review or upload. 15:08:48",
  },
  {
    id: "demo-09",
    providerLabel: "ElevenLabs Agent",
    iconKey: "elevenlabs",
    tone: "accent",
    title: "The ElevenLabs narrator agent is still speaking video 2a8e6720",
    detail:
      "A live ElevenLabs agent conversation is still producing speech audio for this script before forced alignment can begin. 15:08:49 · 7.5s",
  },
  {
    id: "demo-10",
    providerLabel: "FFmpeg",
    iconKey: "success",
    tone: "success",
    title: "video 3 is fully exported",
    detail:
      "…b0d/4c6f60e6-b0fd-4c03-b0d9-2998e46dca7f.mp4 is ready for review or upload. 15:08:49",
  },
  {
    id: "demo-11",
    providerLabel: "ElevenLabs Agent",
    iconKey: "elevenlabs",
    tone: "accent",
    title: "The ElevenLabs narrator agent is still speaking video 2a8e6720",
    detail:
      "A live ElevenLabs agent conversation is still producing speech audio for this script before forced alignment can begin. 15:09:11 · 30.0s",
  },
  {
    id: "demo-12",
    providerLabel: "ElevenLabs Alignment",
    iconKey: "success",
    tone: "success",
    title: "ElevenLabs forced alignment finished for video 2a8e6720",
    detail:
      "Mapped 189 spoken words to timestamps so subtitles can animate against the real narration instead of estimated text timing. 15:09:14",
  },
  {
    id: "demo-13",
    providerLabel: "Backend",
    iconKey: "backend",
    tone: "accent",
    title: "video 5 is selecting gameplay and subtitle assets",
    detail:
      "The backend is matching this approved script with gameplay footage, subtitle treatment, and optional music before FFmpeg render begins. 15:09:14 · 0.0s",
  },
  {
    id: "demo-14",
    providerLabel: "FFmpeg",
    iconKey: "ffmpeg",
    tone: "accent",
    title: "FFmpeg render started for video 5",
    detail:
      "Combining Single Word Pop subtitles with gameplay/minecraft/minecraft_clip_04.mp4 and narration audio. 15:09:14",
  },
  {
    id: "demo-15",
    providerLabel: "FFmpeg",
    iconKey: "ffmpeg",
    tone: "accent",
    title: "FFmpeg is still rendering video 5",
    detail:
      "Gameplay, narration, and ASS subtitles are still being composited into the final MP4 artifact. 15:09:21 · 7.5s",
  },
  {
    id: "demo-16",
    providerLabel: "FFmpeg",
    iconKey: "success",
    tone: "success",
    title: "video 5 finished FFmpeg assembly",
    detail:
      "The final frame burn is done and the backend is uploading the MP4 artifact now. 15:09:22 · 8.5s",
  },
  {
    id: "demo-17",
    providerLabel: "FFmpeg",
    iconKey: "success",
    tone: "success",
    title: "video 5 is fully exported",
    detail:
      "…b0d/2a8e6720-de4f-4cf3-ad2d-ba95de7db598.mp4 is ready for review or upload. 15:09:22",
  },
  {
    id: "demo-18",
    providerLabel: "Backend",
    iconKey: "success",
    tone: "success",
    title: "Batch finished successfully",
    detail: "5 videos exported. 15:09:22",
  },
];

const DEMO_TRACE_SUMMARY: ActivitySummary = {
  providerLabel: "Backend",
  iconKey: "success",
  tone: "success",
  liveLabel: "Finished at 15:09:22",
  title: "The batch has finished successfully",
  detail:
    "The backend has finished Firecrawl ingest, script generation, narration, alignment, and FFmpeg export for this run.",
};

export function TestLab() {
  const [sourceUrl, setSourceUrl] = useState("https://devpost.com/software/content-hub-9zbp5w");
  const [titleHint, setTitleHint] = useState("Devpost benchmark");
  const [count, setCount] = useState("10");
  const [premiumAudio, setPremiumAudio] = useState(false);
  const [batchIdInput, setBatchIdInput] = useState("");
  const [batchEnvelope, setBatchEnvelope] = useState<BatchEnvelope | null>(null);
  const [events, setEvents] = useState<BatchEventRecord[]>([]);
  const [backendHealth, setBackendHealth] = useState<"checking" | "ok" | "error">("checking");
  const [bootstrapSummary, setBootstrapSummary] = useState<string | null>(null);
  const [connectionState, setConnectionState] = useState<"idle" | "connecting" | "streaming" | "reconnecting" | "settled">("idle");
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [logsExpanded, setLogsExpanded] = useState(true);
  const [demoTraceMode, setDemoTraceMode] = useState<DemoTraceMode>("live");
  const [demoTraceCursor, setDemoTraceCursor] = useState(0);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [nowTick, setNowTick] = useState(() => Date.now());

  const eventSourceRef = useRef<EventSource | null>(null);
  const refreshTimerRef = useRef<number | null>(null);
  const batchPollRef = useRef<number | null>(null);
  const demoPlaybackRef = useRef<number | null>(null);
  const logStreamRef = useRef<HTMLDivElement | null>(null);
  const logStickToTopRef = useRef(true);
  const logScrollHeightRef = useRef(0);
  const batch = batchEnvelope?.batch ?? null;
  const activeBatchStatus = batch && batch.id === activeBatchId ? batch.status : null;
  const isBatchSettled = isSettledStatus(activeBatchStatus);
  const demoLogEntries =
    demoTraceMode === "live"
      ? []
      : DEMO_TRACE_SEQUENCE.slice(0, demoTraceMode === "snapshot" ? DEMO_TRACE_SEQUENCE.length : demoTraceCursor).reverse();
  const showingDemoTrace = demoTraceMode !== "live";

  useEffect(() => {
    void checkHealth();
    return () => {
      eventSourceRef.current?.close();
      if (refreshTimerRef.current !== null) {
        window.clearTimeout(refreshTimerRef.current);
      }
      if (batchPollRef.current !== null) {
        window.clearInterval(batchPollRef.current);
      }
      if (demoPlaybackRef.current !== null) {
        window.clearInterval(demoPlaybackRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (demoTraceMode !== "playback") {
      if (demoPlaybackRef.current !== null) {
        window.clearInterval(demoPlaybackRef.current);
        demoPlaybackRef.current = null;
      }
      return;
    }

    if (demoTraceCursor >= DEMO_TRACE_SEQUENCE.length) {
      setDemoTraceMode("snapshot");
      return;
    }

    demoPlaybackRef.current = window.setInterval(() => {
      setDemoTraceCursor(previous => {
        if (previous >= DEMO_TRACE_SEQUENCE.length) {
          if (demoPlaybackRef.current !== null) {
            window.clearInterval(demoPlaybackRef.current);
            demoPlaybackRef.current = null;
          }
          return previous;
        }
        return previous + 1;
      });
    }, 180);

    return () => {
      if (demoPlaybackRef.current !== null) {
        window.clearInterval(demoPlaybackRef.current);
        demoPlaybackRef.current = null;
      }
    };
  }, [demoTraceMode, demoTraceCursor]);

  useEffect(() => {
    if (!activeBatchId) {
      eventSourceRef.current?.close();
      if (refreshTimerRef.current !== null) {
        window.clearTimeout(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
      setConnectionState("idle");
      return;
    }

    void refreshBatch(activeBatchId, { silent: true });
    logStickToTopRef.current = true;
  }, [activeBatchId]);

  useEffect(() => {
    if (!activeBatchId || isBatchSettled) {
      eventSourceRef.current?.close();
      if (isBatchSettled && activeBatchId) {
        setConnectionState("settled");
      }
      return;
    }

    connectEventStream(activeBatchId);

    return () => {
      eventSourceRef.current?.close();
    };
  }, [activeBatchId, isBatchSettled]);

  useEffect(() => {
    if (!activeBatchId || isBatchSettled) {
      return;
    }
    const intervalId = window.setInterval(() => {
      setNowTick(Date.now());
    }, 1000);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [activeBatchId]);

  useEffect(() => {
    if (!logStreamRef.current || !logsExpanded) {
      return;
    }
    if (logStickToTopRef.current) {
      logStreamRef.current.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    } else {
      const delta = logStreamRef.current.scrollHeight - logScrollHeightRef.current;
      if (delta > 0) {
        logStreamRef.current.scrollTop += delta;
      }
    }
    logScrollHeightRef.current = logStreamRef.current.scrollHeight;
  }, [events.length, demoLogEntries.length, logsExpanded]);

  async function checkHealth() {
    try {
      const response = await fetch("/api/brainrot/health", { cache: "no-store" });
      setBackendHealth(response.ok ? "ok" : "error");
    } catch {
      setBackendHealth("error");
    }
  }

  async function bootstrapAgents() {
    setDemoTraceMode("live");
    setDemoTraceCursor(0);
    setIsBootstrapping(true);
    setPageError(null);
    setStatusMessage(null);
    try {
      const response = await fetch("/api/brainrot/agents/bootstrap", { method: "POST" });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail ?? "Failed to bootstrap agents.");
      }
      const agents = Array.isArray(payload.agents) ? payload.agents : [];
      setBootstrapSummary(`${agents.length} agents active`);
      setStatusMessage("Agents bootstrapped.");
      void checkHealth();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Failed to bootstrap agents.");
    } finally {
      setIsBootstrapping(false);
    }
  }

  async function createBatch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDemoTraceMode("live");
    setDemoTraceCursor(0);
    setIsCreating(true);
    setPageError(null);
    setStatusMessage(null);

    try {
      const formData = new FormData();
      formData.append("source_url", sourceUrl.trim());
      formData.append("count", count);
      if (titleHint.trim()) {
        formData.append("title_hint", titleHint.trim());
      }
      formData.append("premium_audio", String(premiumAudio));

      const response = await fetch("/api/brainrot/batches", {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail ?? "Failed to create batch.");
      }

      setEvents([]);
      setBatchEnvelope(payload);
      setBatchIdInput(payload.batch.id);
      setActiveBatchId(payload.batch.id);
      setStatusMessage(`Batch ${payload.batch.id} created.`);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Failed to create batch.");
    } finally {
      setIsCreating(false);
    }
  }

  async function attachBatch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextBatchId = batchIdInput.trim();
    if (!nextBatchId) {
      return;
    }

    setDemoTraceMode("live");
    setDemoTraceCursor(0);
    setPageError(null);
    setStatusMessage(null);
    setEvents([]);
    setActiveBatchId(nextBatchId);

    const success = await refreshBatch(nextBatchId, { silent: false });
    if (success) {
      setStatusMessage(`Attached to batch ${nextBatchId}.`);
    }
  }

  async function refreshBatch(batchId: string, options: { silent: boolean }) {
    if (!options.silent) {
      setDemoTraceMode("live");
      setDemoTraceCursor(0);
      setIsRefreshing(true);
    }

    try {
      const response = await fetch(`/api/brainrot/batches/${batchId}`, { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) {
        if (response.status === 404 && activeBatchId === batchId) {
          eventSourceRef.current?.close();
          if (batchPollRef.current !== null) {
            window.clearInterval(batchPollRef.current);
            batchPollRef.current = null;
          }
          setActiveBatchId(null);
          setConnectionState("idle");
        }
        throw new Error(payload?.detail ?? "Failed to load batch.");
      }
      setBatchEnvelope(payload);
      setLastSyncedAt(new Date().toISOString());
      setPageError(null);
      return true;
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Failed to load batch.");
      return false;
    } finally {
      if (!options.silent) {
        setIsRefreshing(false);
      }
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
    if (isBatchSettled && activeBatchId === batchId) {
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

  const items = batchEnvelope?.items ?? [];
  const statusCounts = {
    queued: 0,
    narrating: 0,
    selecting_assets: 0,
    rendering: 0,
    uploaded: 0,
    failed: 0,
  };

  for (const item of items) {
    if (item.status in statusCounts) {
      statusCounts[item.status as keyof typeof statusCounts] += 1;
    }
  }

  const liveMetadataByItem: Record<string, Record<string, unknown>> = {};
  for (const event of events) {
    const itemId = typeof event.payload.item_id === "string" ? event.payload.item_id : null;
    if (!itemId) {
      continue;
    }
    if (event.type === "render_started") {
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
  }

  const styleDistribution = new Map<
    string,
    { label: string; animation: string; font: string; count: number }
  >();
  for (const item of items) {
    const meta = {
      ...(liveMetadataByItem[item.id] ?? {}),
      ...(item.render_metadata ?? {}),
    };
    const styleId = stringValue(meta.subtitle_style_id);
    if (!styleId) {
      continue;
    }
    const existing = styleDistribution.get(styleId);
    if (existing) {
      existing.count += 1;
      continue;
    }
    styleDistribution.set(styleId, {
      label: stringValue(meta.subtitle_style_label) ?? styleId,
      animation: stringValue(meta.subtitle_animation) ?? "n/a",
      font: stringValue(meta.subtitle_font_name) ?? "n/a",
      count: 1,
    });
  }

  const producerMetrics = batch?.metadata?.producer_metrics as Record<string, unknown> | undefined;
  const streamEvents = events.filter(event => event.type !== "ping" && event.type !== "done");
  const logEvents = compactLogEvents(streamEvents);
  const activeOperations = buildActiveOperations(streamEvents, nowTick);
  const latestLogEvent = streamEvents.at(-1) ?? null;
  const logEntries = logEvents.map(event => toLogEntry(event)).reverse();
  const thinkingDurationLabel = formatThinkingDuration(streamEvents, nowTick, isBatchSettled);
  const activitySummary = buildActivitySummary(activeOperations, latestLogEvent, batch, nowTick, isBatchSettled);
  const traceEntries = showingDemoTrace ? demoLogEntries : logEntries;
  const traceSummary = showingDemoTrace ? DEMO_TRACE_SUMMARY : activitySummary;
  const traceThinkingDuration = showingDemoTrace ? "1m 41s" : thinkingDurationLabel;
  const traceConnectionState = showingDemoTrace ? (demoTraceMode === "playback" ? "streaming" : "settled") : connectionState;
  const traceModeLabel = showingDemoTrace
    ? demoTraceMode === "playback"
      ? "Playing sample trace"
      : "Showing sample trace"
    : "Live backend SSE";

  function handleLogScroll() {
    if (!logStreamRef.current) {
      return;
    }
    const { scrollTop } = logStreamRef.current;
    logStickToTopRef.current = scrollTop < 56;
  }

  function useLiveTrace() {
    setDemoTraceMode("live");
    setDemoTraceCursor(0);
  }

  function loadSampleTrace() {
    logStickToTopRef.current = true;
    setLogsExpanded(true);
    setDemoTraceCursor(DEMO_TRACE_SEQUENCE.length);
    setDemoTraceMode("snapshot");
  }

  function playSampleTrace() {
    logStickToTopRef.current = true;
    setLogsExpanded(true);
    setDemoTraceCursor(1);
    setDemoTraceMode("playback");
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <div className={styles.kicker}>
            <span className={styles.kickerDot} />
            Internal test lab
          </div>
          <h1 className={styles.heroTitle}>
            Watch subtitle styles, gameplay variation, and backend stages in real time.
          </h1>
          <p className={styles.heroCopyText}>
            This console is built to verify that a batch does not feel templated. Faster gameplay can
            take louder single-word or stacked caption treatments, while slower or darker clips can take
            cleaner boxed or karaoke subtitles so a ten-video run still feels intentionally varied.
          </p>
          <div className={styles.heroSignalGrid}>
            <HeroSignal
              label="Backend"
              value={backendHealth === "ok" ? "Online" : backendHealth === "checking" ? "Checking" : "Offline"}
              detail={bootstrapSummary ?? "Agents have not been bootstrapped yet."}
              tone={backendHealth === "ok" ? "success" : backendHealth === "checking" ? "neutral" : "danger"}
            />
            <HeroSignal
              label="Stream"
              value={humanizeConnectionState(connectionState)}
              detail={lastSyncedAt ? `Last sync ${formatClock(lastSyncedAt)}` : "Waiting for the first backend sync."}
              tone={connectionState === "streaming" || connectionState === "settled" ? "success" : connectionState === "reconnecting" ? "warning" : "neutral"}
            />
            <HeroSignal
              label="Active batch"
              value={activeBatchId ? shortId(activeBatchId) : "No batch"}
              detail={batch ? `${batch.requested_count} items / ${batch.status}` : "Start or attach a run to inspect it live."}
              tone={activeBatchId ? "accent" : "neutral"}
            />
            <HeroSignal
              label="Exports"
              value={`${statusCounts.uploaded}/${items.length || batch?.requested_count || 0}`}
              detail={items.length > 0 ? `${statusCounts.rendering} rendering / ${statusCounts.failed} failed` : "No items have reached rendering yet."}
              tone={statusCounts.uploaded > 0 ? "success" : statusCounts.rendering > 0 ? "warning" : "neutral"}
            />
          </div>
        </div>

        <div className={styles.strategyCard}>
          <div className={styles.strategyIcon}>
            <WandSparkles size={18} />
          </div>
          <p className={styles.strategyEyebrow}>Live stack</p>
          <h2 className={styles.strategyTitle}>What this run is proving</h2>
          <p className={styles.strategyLead}>
            Firecrawl prepares the source, OpenAI writes the scripts, ElevenLabs narrator agents create
            the voiceovers, ElevenLabs alignment times the captions, and FFmpeg assembles the final reels.
          </p>
          <div className={styles.stackList}>
            <StackRow
              icon={<Globe size={15} />}
              title="Firecrawl ingest"
              detail="Turns the source URL into clean markdown, metadata, and normalized links."
            />
            <StackRow
              icon={<OpenAIIcon size={15} />}
              title="OpenAI scripts"
              detail="Generates the reel scripts that then go through local backend QA and repair."
            />
            <StackRow
              icon={<AudioLines size={15} />}
              title="ElevenLabs narrator agent"
              detail="Speaks the approved script inside a live agent conversation to create the voiceover."
            />
            <StackRow
              icon={<ShieldCheck size={15} />}
              title="ElevenLabs forced alignment"
              detail="Maps every spoken word to the real audio so subtitle timing stays accurate."
            />
            <StackRow
              icon={<Clapperboard size={15} />}
              title="FFmpeg final render"
              detail="Combines gameplay, voiceover, and animated subtitles into the final MP4."
            />
          </div>
        </div>
      </section>

      <section className={styles.dashboardGrid}>
        <article className={styles.card}>
          <div className={styles.cardHeader}>
            <div>
              <p className={styles.eyebrow}>Run a batch</p>
              <h2 className={styles.cardTitle}>Launch a live test</h2>
            </div>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => void bootstrapAgents()}
              disabled={isBootstrapping}
            >
              {isBootstrapping ? <LoaderCircle size={15} className={styles.spin} /> : <Bot size={15} />}
              Bootstrap agents
            </button>
          </div>

          <form className={styles.form} onSubmit={createBatch}>
            <label className={styles.field}>
              <span>Source URL</span>
              <div className={styles.inputShell}>
                <Link2 size={15} />
                <input value={sourceUrl} onChange={event => setSourceUrl(event.target.value)} />
              </div>
            </label>

            <div className={styles.fieldRow}>
              <label className={styles.field}>
                <span>Title hint</span>
                <input value={titleHint} onChange={event => setTitleHint(event.target.value)} />
              </label>
              <label className={styles.field}>
                <span>Count</span>
                <input
                  type="number"
                  min={5}
                  max={15}
                  value={count}
                  onChange={event => setCount(event.target.value)}
                />
              </label>
            </div>

            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={premiumAudio}
                onChange={event => setPremiumAudio(event.target.checked)}
              />
              <span>Use premium narration audio</span>
            </label>

            <button type="submit" className={styles.primaryButton} disabled={isCreating}>
              {isCreating ? <LoaderCircle size={15} className={styles.spin} /> : <Sparkles size={15} />}
              Start test batch
            </button>
          </form>
        </article>

        <article className={styles.card}>
          <div className={styles.cardHeader}>
            <div>
              <p className={styles.eyebrow}>Attach or refresh</p>
              <h2 className={styles.cardTitle}>Inspect an existing run</h2>
            </div>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => activeBatchId && void refreshBatch(activeBatchId, { silent: false })}
              disabled={!activeBatchId || isRefreshing}
            >
              {isRefreshing ? <LoaderCircle size={15} className={styles.spin} /> : <RefreshCw size={15} />}
              Refresh batch
            </button>
          </div>

          <form className={styles.form} onSubmit={attachBatch}>
            <label className={styles.field}>
              <span>Batch ID</span>
              <input value={batchIdInput} onChange={event => setBatchIdInput(event.target.value)} />
            </label>
            <button type="submit" className={styles.secondaryButton}>
              <Activity size={15} />
              Attach stream
            </button>
          </form>

          <div className={styles.systemGrid}>
            <MiniMetric label="Connection" value={humanizeConnectionState(connectionState)} tone={connectionState === "streaming" || connectionState === "settled" ? "success" : connectionState === "reconnecting" ? "warning" : "neutral"} />
            <MiniMetric label="Last sync" value={lastSyncedAt ? formatClock(lastSyncedAt) : "Not synced yet"} tone="neutral" />
            <MiniMetric label="Producer mode" value={stringValue(producerMetrics?.mode) ?? "direct_openai"} tone="accent" />
            <MiniMetric label="Repairs" value={String(numberValue(producerMetrics?.repair_count) ?? 0)} tone="neutral" />
          </div>

          {statusMessage ? <p className={styles.inlineNote}>{statusMessage}</p> : null}
          {pageError ? <p className={styles.errorNote}>{pageError}</p> : null}
        </article>
      </section>

      <section className={styles.pipelineSection}>
        <div className={styles.sectionHeader}>
          <div>
            <p className={styles.eyebrow}>Pipeline state</p>
            <h2 className={styles.sectionTitle}>Batch-level verification</h2>
          </div>
          {batch ? (
            <div className={styles.sectionMeta}>
              <span>{batch.status}</span>
              <span>{batch.requested_count} items requested</span>
            </div>
          ) : null}
        </div>

        <div className={styles.pipelineGrid}>
          <StepCard
            icon={<Link2 size={16} />}
            title="Ingest"
            value={eventSeen(events, "source_ingested") ? "Source captured" : batch?.status === "ingesting" ? "Running" : "Pending"}
            detail={batch?.source_url ?? "No source attached"}
            tone={eventSeen(events, "source_ingested") ? "success" : batch?.status === "ingesting" ? "accent" : "neutral"}
          />
          <StepCard
            icon={<OpenAIIcon size={16} />}
            title="Producer"
            value={eventSeen(events, "scripts_ready") ? `${items.length || batch?.requested_count || 0} scripts ready` : batch?.status === "scripting" ? "Generating" : "Pending"}
            detail={producerMetrics ? `${numberValue(producerMetrics.elapsed_seconds) ?? 0}s · ${numberValue(producerMetrics.attempt_count) ?? 0} attempts` : "Waiting for script metrics"}
            tone={eventSeen(events, "scripts_ready") ? "success" : batch?.status === "scripting" ? "accent" : "neutral"}
          />
          <StepCard
            icon={<AudioLines size={16} />}
            title="Narration"
            value={`${statusCounts.narrating + statusCounts.selecting_assets + statusCounts.rendering + statusCounts.uploaded}/${items.length || batch?.requested_count || 0} touched`}
            detail={`${countEvents(events, "narrator_audio_ready")} audio-ready events · ${countEvents(events, "alignment_ready")} aligned`}
            tone={statusCounts.narrating > 0 ? "accent" : countEvents(events, "alignment_ready") > 0 ? "success" : "neutral"}
          />
          <StepCard
            icon={<Clapperboard size={16} />}
            title="Render"
            value={`${statusCounts.uploaded}/${items.length || batch?.requested_count || 0} exported`}
            detail={`${statusCounts.rendering} rendering · ${statusCounts.failed} failed`}
            tone={statusCounts.uploaded > 0 ? "success" : statusCounts.rendering > 0 ? "accent" : "neutral"}
          />
        </div>
      </section>

      <section className={styles.contentGrid}>
        <article className={styles.card}>
          <div className={styles.cardHeader}>
            <div>
              <p className={styles.eyebrow}>Subtitle mix</p>
              <h2 className={styles.cardTitle}>Variation across the batch</h2>
            </div>
            <StatusBadge
              label={`${styleDistribution.size} styles seen`}
              tone={styleDistribution.size >= 3 ? "success" : styleDistribution.size > 0 ? "accent" : "neutral"}
            />
          </div>

          <div className={styles.distributionList}>
            {Array.from(styleDistribution.values()).length > 0 ? (
              Array.from(styleDistribution.values()).map(style => (
                <div key={`${style.label}-${style.font}`} className={styles.distributionRow}>
                  <div>
                    <p className={styles.distributionLabel}>{style.label}</p>
                    <p className={styles.distributionMeta}>{style.animation} · {style.font}</p>
                  </div>
                  <span className={styles.distributionCount}>{style.count}</span>
                </div>
              ))
            ) : (
              <p className={styles.emptyState}>Once rendering starts, the subtitle style distribution will appear here.</p>
            )}
          </div>
        </article>

        <article className={`${styles.card} ${styles.logCard}`}>
          <div className={styles.cardHeader}>
            <div>
              <p className={styles.eyebrow}>Realtime log stream</p>
              <h2 className={styles.cardTitle}>Live backend thinking</h2>
            </div>
            <div className={styles.logHeaderMeta}>
              <div className={styles.logHeaderStat}>
                <span>Stream</span>
                <strong>{humanizeConnectionState(traceConnectionState)}</strong>
              </div>
              <div className={styles.logHeaderStat}>
                <span>Events</span>
                <strong>{traceEntries.length}</strong>
              </div>
            </div>
          </div>

          <div className={styles.traceDemoBar}>
            <div className={styles.traceDemoCopy}>
              <span className={styles.traceDemoLabel}>Trace source</span>
              <p className={styles.traceDemoText}>{traceModeLabel}</p>
            </div>
            <div className={styles.traceDemoActions}>
              <button type="button" className={styles.traceButton} onClick={useLiveTrace}>
                Live stream
              </button>
              <button type="button" className={styles.traceButton} onClick={loadSampleTrace}>
                Load sample
              </button>
              <button type="button" className={styles.traceButton} onClick={playSampleTrace}>
                Play sample
              </button>
            </div>
          </div>

          <div className={styles.thoughtSummaryWrap}>
            <button
              type="button"
              className={styles.thoughtSummary}
              onClick={() => setLogsExpanded(previous => !previous)}
            >
              <div className={styles.thoughtSummaryCopy}>
                <span className={styles.thoughtSummaryLabel}>Backend trace</span>
                <span className={styles.thoughtSummaryMeta}>
                  {showingDemoTrace ? "UI simulation mode" : logsExpanded ? "Hide timeline" : "Show timeline"}
                </span>
              </div>
              <div className={styles.thoughtSummaryInfo}>
                <span className={styles.thoughtSummaryDuration}>{traceThinkingDuration}</span>
                <ChevronRight
                  size={11}
                  className={logsExpanded ? styles.chevronOpen : styles.chevronClosed}
                />
              </div>
            </button>
          </div>

          <AnimatePresence initial={false}>
            {logsExpanded ? (
              <motion.div
                key="backend-thinking-history"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.22 }}
                style={{ overflow: "hidden" }}
              >
                <div className={styles.thoughtLogPanel}>
                  <div className={styles.thoughtLogHeader}>
                    <div className={styles.thoughtLogHeaderTop}>
                      <div className={`${styles.thoughtLogStatusDot} ${styles[`statusDot-${traceSummary.tone}`]}`} />
                      <span className={`${styles.thoughtLogHeaderBadge} ${styles[`tagTone-${traceSummary.tone}`]}`}>
                        <span className={`${styles.logEntryIcon} ${styles[`iconTone-${traceSummary.tone}`]}`}>
                          <LogIcon iconKey={traceSummary.iconKey} />
                        </span>
                        {traceSummary.providerLabel}
                      </span>
                      {traceSummary.liveLabel ? (
                        <span className={styles.thoughtLogHeaderTime}>{traceSummary.liveLabel}</span>
                      ) : null}
                    </div>
                    <p className={styles.thoughtLogTitle}>{traceSummary.title}</p>
                    {traceSummary.detail ? (
                      <p className={styles.thoughtLogSubtitle}>{traceSummary.detail}</p>
                    ) : null}
                  </div>
                  {traceEntries.length > 0 ? (
                    <div className={styles.thoughtLogBody} ref={logStreamRef} onScroll={handleLogScroll}>
                      <AnimatePresence initial={false}>
                        {traceEntries.map((entry, index) => {
                          const isLast = index === traceEntries.length - 1;
                          return (
                            <motion.div
                              key={entry.id}
                              className={styles.thoughtLogStep}
                              initial={{ opacity: 0, y: -6, scale: 0.98 }}
                              animate={{ opacity: 1, y: 0, scale: 1 }}
                              exit={{ opacity: 0, y: 4 }}
                              transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
                            >
                              <div className={styles.thoughtLogBulletCol}>
                                <motion.span
                                  className={`${styles.thoughtLogBullet} ${styles[`bulletTone-${entry.tone}`]}`}
                                  initial={{ scale: 0, opacity: 0 }}
                                  animate={{ scale: 1, opacity: 1 }}
                                  transition={{ delay: 0.1, duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                                />
                                {!isLast && (
                                  <motion.span
                                    className={styles.thoughtLogLine}
                                    initial={{ scaleY: 0, originY: 0 }}
                                    animate={{ scaleY: 1 }}
                                    transition={{ delay: 0.18, duration: 0.3, ease: "easeOut" }}
                                    style={{ transformOrigin: "top" }}
                                  />
                                )}
                              </div>
                              <div className={styles.thoughtLogStepContent}>
                                <motion.div
                                  className={styles.logEntrySourceRow}
                                  initial={{ opacity: 0 }}
                                  animate={{ opacity: 1 }}
                                  transition={{ delay: 0.06, duration: 0.2 }}
                                >
                                  <span className={`${styles.logEntryIcon} ${styles[`iconTone-${entry.tone}`]}`}>
                                    <LogIcon iconKey={entry.iconKey} />
                                  </span>
                                  <span className={styles.logEntryProvider}>{entry.providerLabel}</span>
                                </motion.div>
                                <motion.p
                                  className={styles.thoughtLogStepTitle}
                                  initial={{ opacity: 0, x: -8 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: 0.1, duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
                                >
                                  {entry.title}
                                </motion.p>
                                {entry.detail ? (
                                  <motion.p
                                    className={styles.thoughtLogStepDetail}
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ delay: 0.2, duration: 0.28 }}
                                  >
                                    {entry.detail}
                                  </motion.p>
                                ) : null}
                              </div>
                            </motion.div>
                          );
                        })}
                      </AnimatePresence>
                    </div>
                  ) : (
                    <p className={styles.emptyState}>Attach a batch to stream the event log here.</p>
                  )}
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </article>
      </section>

      <section className={styles.itemsSection}>
        <div className={styles.sectionHeader}>
          <div>
            <p className={styles.eyebrow}>Per-item detail</p>
            <h2 className={styles.sectionTitle}>Video-by-video verification</h2>
          </div>
          <div className={styles.sectionMeta}>
            <span>{statusCounts.uploaded} complete</span>
            <span>{statusCounts.failed} failed</span>
          </div>
        </div>

        <div className={styles.itemsGrid}>
          {items.length > 0 ? (
            items
              .slice()
              .sort((left, right) => left.item_index - right.item_index)
              .map(item => {
                const meta = {
                  ...(liveMetadataByItem[item.id] ?? {}),
                  ...(item.render_metadata ?? {}),
                };
                const videoPreviewUrl = batch ? `/api/brainrot/batches/${batch.id}/items/${item.id}/video` : null;
                const hasVideo = item.status === "uploaded" && Boolean(item.output_url) && Boolean(videoPreviewUrl);
                return (
                  <article key={item.id} className={styles.itemCard}>
                    <div className={styles.itemHeader}>
                      <div>
                        <p className={styles.itemIndex}>Video {item.item_index + 1}</p>
                        <h3 className={styles.itemTitle}>{item.script?.title ?? "Script pending"}</h3>
                      </div>
                      <StatusBadge label={item.status} tone={toneForItemStatus(item.status)} />
                    </div>

                    <div className={styles.itemMetaGrid}>
                      <ItemMeta label="Subtitle style" value={stringValue(meta.subtitle_style_label) ?? "Pending"} />
                      <ItemMeta label="Animation" value={stringValue(meta.subtitle_animation) ?? "Pending"} />
                      <ItemMeta label="Font" value={stringValue(meta.subtitle_font_name) ?? "Pending"} />
                      <ItemMeta label="Gameplay" value={shortPath(stringValue(meta.gameplay_asset_path)) ?? "Pending"} />
                    </div>

                    {hasVideo ? (
                      <div className={styles.itemVideoWrap}>
                        <video
                          key={videoPreviewUrl ?? item.id}
                          className={styles.itemVideo}
                          controls
                          preload="metadata"
                          playsInline
                          src={videoPreviewUrl ?? undefined}
                        />
                      </div>
                    ) : (
                      <div className={styles.itemVideoPlaceholder}>
                        <Clapperboard size={18} />
                        <span>
                          {item.status === "failed"
                            ? "This video failed before export."
                            : "The MP4 preview will appear here as soon as rendering finishes."}
                        </span>
                      </div>
                    )}

                    <div className={styles.itemDetails}>
                      <p>
                        <strong>Estimated:</strong>{" "}
                        {typeof item.script?.estimated_seconds === "number"
                          ? `${item.script.estimated_seconds.toFixed(1)}s`
                          : "Pending"}
                      </p>
                      <p>
                        <strong>Output:</strong>{" "}
                        {hasVideo ? (
                          <a href={videoPreviewUrl ?? "#"} target="_blank" rel="noreferrer">
                            Open render
                          </a>
                        ) : (
                          shortPath(stringValue(item.output_url)) ?? "Pending"
                        )}
                      </p>
                      {item.error ? (
                        <p className={styles.itemError}>
                          <strong>Error:</strong> {item.error}
                        </p>
                      ) : null}
                    </div>
                  </article>
                );
              })
          ) : (
            <article className={styles.card}>
              <p className={styles.emptyState}>No batch items yet. Start or attach a run to inspect its subtitle and gameplay choices.</p>
            </article>
          )}
        </div>
      </section>
    </main>
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

function humanizeEventType(value: string) {
  return value.replaceAll("_", " ");
}

function humanizeStage(value: string) {
  return value.replaceAll("_", " ");
}

function formatClock(value: string) {
  return new Date(value).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function countEvents(events: BatchEventRecord[], type: string) {
  return events.filter(event => event.type === type).length;
}

function eventSeen(events: BatchEventRecord[], type: string) {
  return events.some(event => event.type === type);
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
    return {
      ...base,
      iconKey: "openai",
      providerLabel: "CrewAI",
      title: "CrewAI is planning article coverage",
      detail: withEventMeta(
        "The source markdown is being split into meaningful article sections before any scripts are written.",
        event,
      ),
    };
  }
  if (event.type === "section_planning_completed") {
    return {
      ...base,
      tone: "success" as const,
      iconKey: "success",
      providerLabel: "CrewAI",
      title: "CrewAI finished section planning",
      detail: withEventMeta(
        `${payload.section_count ?? 0} article sections were extracted for coverage planning.`,
        event,
      ),
    };
  }
  if (event.type === "coverage_plan_ready") {
    return {
      ...base,
      iconKey: "openai",
      providerLabel: "CrewAI",
      title: "CrewAI coverage plan is ready",
      detail: withEventMeta(
        `${payload.slot_count ?? 0} section-based script slots were planned from ${payload.section_count ?? 0} extracted sections.`,
        event,
      ),
    };
  }
  if (event.type === "slot_generation_started") {
    return {
      ...base,
      iconKey: "openai",
      providerLabel: "CrewAI",
      title: `CrewAI is writing slot ${Number(payload.slot_index ?? 0) + 1} from the ${stringValue(payload.section_heading) ? `"${stringValue(payload.section_heading)}"` : "assigned"} section`,
      detail: withEventMeta(
        `This slot is covering a different article section with the ${stringValue(payload.angle_family) ?? "assigned"} angle family.`,
        event,
      ),
    };
  }
  if (event.type === "slot_generation_completed") {
    return {
      ...base,
      tone: "success" as const,
      iconKey: "success",
      providerLabel: "CrewAI",
      title: `CrewAI finished slot ${Number(payload.slot_index ?? 0) + 1}`,
      detail: withEventMeta(
        `The section draft for ${stringValue(payload.section_heading) ?? "this slot"} is ready for bundle QA.`,
        event,
      ),
    };
  }
  if (event.type === "slot_generation_failed") {
    return {
      ...base,
      tone: "danger" as const,
      iconKey: "danger",
      providerLabel: "CrewAI",
      title: `CrewAI failed slot ${Number(payload.slot_index ?? 0) + 1}`,
      detail: withEventMeta(stringValue(payload.error) ?? "CrewAI could not complete this slot.", event),
    };
  }
  if (event.type === "slot_repair_started") {
    return {
      ...base,
      iconKey: "qa",
      providerLabel: "CrewAI Repair",
      title: `CrewAI is repairing slot ${Number(payload.slot_index ?? 0) + 1}`,
      detail: withEventMeta(
        "This slot is being rewritten to remove overlap and fix grounding issues without losing section coverage.",
        event,
      ),
    };
  }
  if (event.type === "slot_repair_completed") {
    return {
      ...base,
      tone: "success" as const,
      iconKey: "success",
      providerLabel: "CrewAI Repair",
      title: `CrewAI repaired slot ${Number(payload.slot_index ?? 0) + 1}`,
      detail: withEventMeta(
        "The corrected slot now fits the coverage plan and can move back into QA.",
        event,
      ),
    };
  }
  if (event.type === "producer_bundle_completed") {
    return {
      ...base,
      tone: "success" as const,
      iconKey: "success",
      providerLabel: "CrewAI",
      title: "CrewAI coverage bundle is complete",
      detail: withEventMeta(
        `${payload.slot_count ?? 0} section-based scripts are ready for final backend QA.`,
        event,
      ),
    };
  }
  if (event.type === "log") {
    const validationSummary = summarizeValidationSummary(stringValue(payload.validation_summary));
    const title = stringValue(payload.message) ?? "Backend update";
    if (title.startsWith("Starting source ingestion.")) {
      return {
        ...base,
        iconKey: "firecrawl",
        providerLabel: "Firecrawl",
        title: "Source ingest pipeline started",
        detail: withEventMeta(
          "The backend is preparing the incoming URL for Firecrawl so the article can be turned into clean markdown.",
          event,
        ),
      };
    }
    if (title.startsWith("Starting Firecrawl ingest for ")) {
      return {
        ...base,
        iconKey: "firecrawl",
        providerLabel: "Firecrawl",
        title: "Firecrawl ingest session started",
        detail: withEventMeta(
          "Firecrawl is opening the source so the backend can pull a normalized markdown brief from the page.",
          event,
        ),
      };
    }
    if (title.startsWith("Scraping ") && title.includes(" via Firecrawl.")) {
      const sourceUrl = title.replace("Scraping ", "").replace(" via Firecrawl.", "");
      return {
        ...base,
        iconKey: "firecrawl",
        providerLabel: "Firecrawl",
        title: "Firecrawl is scraping the source URL",
        detail: withEventMeta(
          `${sourceUrl} is being converted into clean page content, metadata, and normalized links for the rest of the pipeline.`,
          event,
        ),
      };
    }
    if (title.startsWith("Scrape completed for ")) {
      return {
        ...base,
        tone: "success" as const,
        iconKey: "success",
        providerLabel: "Firecrawl",
        title: "Firecrawl returned the article content",
        detail: withEventMeta(
          `Captured ${title.replace("Scrape completed for ", "").replace(".", "")} and handed the cleaned result back to the backend.`,
          event,
        ),
      };
    }
    if (title.startsWith("Firecrawl scrape request is still running.")) {
      return {
        ...base,
        iconKey: "firecrawl",
        providerLabel: "Firecrawl",
        title: "Firecrawl is still scraping the source URL",
        detail: withEventMeta(
          "The scrape request is still in flight, so the backend is waiting for Firecrawl to return clean page content.",
          event,
        ),
      };
    }
    if (title.startsWith("Firecrawl site mapping request is still running.")) {
      return {
        ...base,
        iconKey: "firecrawl",
        providerLabel: "Firecrawl",
        title: "Firecrawl is still mapping the site",
        detail: withEventMeta(
          "The mapping request is still selecting which URLs belong in this source before content extraction continues.",
          event,
        ),
      };
    }
    if (title.startsWith("Waiting for OpenAI producer response on attempt ")) {
      const mode = stringValue(payload.mode);
      return {
        ...base,
        iconKey: "openai",
        providerLabel: producerProviderLabel(mode),
        title: `OpenAI script pass ${payload.attempt ?? "?"}/3 is still running`,
        detail: withEventMeta(
          `${producerStageCopy(mode, stringValue(payload.model))} The current pass is still generating scripts from the Firecrawl brief.`,
          event,
        ),
      };
    }
    if (title.startsWith("Waiting for producer repair response on attempt ")) {
      const mode = stringValue(payload.mode);
      return {
        ...base,
        iconKey: "openai",
        providerLabel: producerProviderLabel(mode),
        title: `${mode === "elevenlabs_native" ? "ElevenLabs producer-agent repair pass" : "OpenAI repair pass"} ${payload.attempt ?? "?"}/3 is still running`,
        detail: withEventMeta(
          `${producerStageCopy(mode, stringValue(payload.model))} The repair pass is still rewriting the rejected scripts so the batch can recover without a full restart.`,
          event,
        ),
      };
    }
    if (title.startsWith("Waiting for ElevenLabs narration audio for item ")) {
      const mode = stringValue(payload.mode);
      const copy = narrationInFlightCopy(mode, payload);
      return {
        ...base,
        iconKey: "elevenlabs",
        providerLabel: copy.providerLabel,
        title: copy.title,
        detail: withEventMeta(copy.detail, event),
      };
    }
    if (title.startsWith("Waiting for ElevenLabs TTS audio for item ")) {
      const copy = narrationInFlightCopy("elevenlabs_tts", payload);
      return {
        ...base,
        iconKey: "elevenlabs",
        providerLabel: copy.providerLabel,
        title: copy.title,
        detail: withEventMeta(copy.detail, event),
      };
    }
    if (title.startsWith("FFmpeg still rendering item ")) {
      return {
        ...base,
        iconKey: "ffmpeg",
        providerLabel: "FFmpeg",
        title: `FFmpeg is still rendering ${videoLabelFromPayload(payload)}`,
        detail: withEventMeta(
          "Gameplay, narration, and ASS subtitles are still being composited into the final MP4 artifact.",
          event,
        ),
      };
    }
    if (title.startsWith("Mapping website URLs with Firecrawl.")) {
      return {
        ...base,
        iconKey: "firecrawl",
        providerLabel: "Firecrawl",
        title: "Firecrawl is mapping site URLs",
        detail: withEventMeta(
          "The crawler is deciding which pages belong in the source set before content extraction begins.",
          event,
        ),
      };
    }
    if (title.startsWith("Starting Firecrawl crawl job for selected URLs.")) {
      return {
        ...base,
        iconKey: "firecrawl",
        providerLabel: "Firecrawl",
        title: "Firecrawl crawl job started",
        detail: withEventMeta(
          "Firecrawl is walking the selected URLs and collecting markdown from each page in the set.",
          event,
        ),
      };
    }
    if (title.startsWith("Firecrawl crawl completed with ")) {
      return {
        ...base,
        tone: "success" as const,
        iconKey: "success",
        providerLabel: "Firecrawl",
        title: "Firecrawl crawl job completed",
        detail: withEventMeta(
          title.replace("Firecrawl ", ""),
          event,
        ),
      };
    }
    if (title.startsWith("Producer started")) {
      const mode = stringValue(payload.mode);
      const model = stringValue(payload.model) ?? "default model";
      return {
        ...base,
        iconKey: mode === "direct_openai" ? "openai" : "elevenlabs",
        providerLabel: producerProviderLabel(mode),
        title: "Script generation pipeline started",
        detail: withEventMeta(
          producerStageCopy(mode, model),
          event,
        ),
      };
    }
    if (title.startsWith("Producer attempt ")) {
      const mode = stringValue(payload.mode);
      return {
        ...base,
        iconKey: mode === "elevenlabs_native" ? "elevenlabs" : "openai",
        providerLabel: producerProviderLabel(mode),
        title: `${mode === "elevenlabs_native" ? "Starting ElevenLabs producer-agent pass" : "Starting OpenAI script pass"} ${payload.attempt ?? "?"}/3`,
        detail: withEventMeta(
          "The backend is opening a fresh generation attempt because the previous pass did not return a final accepted bundle.",
          event,
        ),
      };
    }
    if (title.startsWith("OpenAI request started for producer attempt ")) {
      const mode = stringValue(payload.mode);
      return {
        ...base,
        iconKey: "openai",
        providerLabel: producerProviderLabel(mode),
        title: `OpenAI script request ${payload.attempt ?? "?"}/3 was sent`,
        detail: withEventMeta(
          `${producerStageCopy(mode, stringValue(payload.model))} The returned scripts will be checked by local backend QA before they can reach video generation.`,
          event,
        ),
      };
    }
    if (title.startsWith("Producer submitted script bundle. Validating scripts now.")) {
      const mode = stringValue(payload.mode);
      return {
        ...base,
        iconKey: "qa",
        providerLabel: "Backend QA",
        title: mode === "elevenlabs_native" ? "The ElevenLabs producer agent returned a script bundle" : "OpenAI returned a script bundle",
        detail: withEventMeta(
          "The backend is now running local QA to check word count, hook grounding, duplicate ideas, and fact quality before any script can reach video generation.",
          event,
        ),
      };
    }
    if (title.startsWith("Validation failed on attempt ")) {
      return {
        ...base,
        tone: "warning" as const,
        iconKey: "warning",
        providerLabel: "Backend QA",
        title: `Local QA rejected script pass ${payload.attempt ?? "?"}/3`,
        detail: withEventMeta(
          `${validationSummary ?? "The current bundle did not meet the batch rules"}. The backend is sending only the failed issues back for repair instead of stopping the run.`,
          event,
        ),
      };
    }
    if (title.startsWith("Repair request started for attempt ")) {
      const mode = stringValue(payload.mode);
      return {
        ...base,
        iconKey: mode === "elevenlabs_native" ? "elevenlabs" : "openai",
        providerLabel: producerProviderLabel(mode),
        title: `${mode === "elevenlabs_native" ? "ElevenLabs producer-agent repair pass" : "OpenAI repair pass"} ${payload.attempt ?? "?"}/3 started`,
        detail: withEventMeta(
          `${validationSummary ?? "The failed scripts are being rewritten"}. ${mode === "elevenlabs_native" ? "The active ElevenLabs producer agent" : "OpenAI"} is focusing on broken hooks, facts, and pacing issues.`,
          event,
        ),
      };
    }
    if (title.startsWith("Repair succeeded on attempt ")) {
      return {
        ...base,
        tone: "success" as const,
        iconKey: "success",
        providerLabel: "Backend QA",
        title: `Repair pass ${payload.attempt ?? "?"}/3 fixed the rejected scripts`,
        detail: withEventMeta(
          "The repaired scripts cleared local QA and can now move forward to narration and rendering.",
          event,
        ),
      };
    }
    if (title.startsWith("Repair failed on attempt ")) {
      return {
        ...base,
        tone: "danger" as const,
        iconKey: "danger",
        providerLabel: "Backend QA",
        title: `Repair pass ${payload.attempt ?? "?"}/3 still failed QA`,
        detail: withEventMeta(
          `${summarizeValidationSummary(stringValue(payload.error)) ?? "Some script issues were still unresolved"}. The backend will try another full generation pass.`,
          event,
        ),
      };
    }
    if (title.startsWith("Applied local script fixes after ")) {
      const repairParts = [
        numberValue(payload.title_repairs) ? `${payload.title_repairs} title cleanup` : null,
        numberValue(payload.hook_repairs) ? `${payload.hook_repairs} hook cleanup` : null,
        numberValue(payload.fact_repairs) ? `${payload.fact_repairs} fact cleanup` : null,
        numberValue(payload.narration_repairs) ? `${payload.narration_repairs} narration extension` : null,
      ].filter(Boolean);
      return {
        ...base,
        tone: "success" as const,
        iconKey: "qa",
        providerLabel: "Backend QA",
        title: "Backend normalization cleaned the script bundle",
        detail: withEventMeta(
          repairParts.length > 0
            ? `${repairParts.join(", ")} were applied before QA so formatting issues do not block the batch.`
            : "The backend applied local cleanup so formatting issues do not block the batch.",
          event,
        ),
      };
    }
    if (title.startsWith("Accepted ")) {
      return {
        ...base,
        tone: "success" as const,
        iconKey: "success",
        providerLabel: "Backend",
        title: "Approved scripts are already moving into production",
        detail: withEventMeta(
          `${stringValue(payload.source) ?? "This slice"} passed QA, so the backend started asset selection, ElevenLabs narrator-agent conversations, and rendering immediately instead of waiting for the full batch.`,
          event,
        ),
      };
    }
    if (title.startsWith("Render completed for item ")) {
      return {
        ...base,
        tone: "success" as const,
        iconKey: "success",
        providerLabel: "FFmpeg",
        title: `${videoLabelFromPayload(payload)} finished FFmpeg assembly`,
        detail: withEventMeta(
          "The final frame burn is done and the backend is uploading the MP4 artifact now.",
          event,
        ),
      };
    }
    if (title.startsWith("Producer request failed on attempt ")) {
      const mode = stringValue(payload.mode);
      return {
        ...base,
        tone: "warning" as const,
        iconKey: "warning",
        providerLabel: producerProviderLabel(mode),
        title: `${mode === "elevenlabs_native" ? "ElevenLabs producer-agent pass" : "OpenAI script pass"} ${payload.attempt ?? "?"}/3 failed to return cleanly`,
        detail: withEventMeta(
          `${summarizeValidationSummary(stringValue(payload.error)) ?? "The request failed"}. The backend is retrying automatically.`,
          event,
        ),
      };
    }
    if (title.startsWith("Producer failed")) {
      const mode = stringValue(payload.mode);
      return {
        ...base,
        tone: "danger" as const,
        iconKey: "danger",
        providerLabel: producerProviderLabel(mode),
        title: "Script generation failed",
        detail: withEventMeta(
          `${summarizeValidationSummary(stringValue(payload.error)) ?? "The producer could not deliver a valid bundle after all retries"}.`,
          event,
        ),
      };
    }
    if (title.startsWith("Staging assets for item ")) {
      return {
        ...base,
        iconKey: "backend",
        providerLabel: "Backend",
        title: `${videoLabelFromPayload(payload)} is selecting gameplay and subtitle assets`,
        detail: withEventMeta(
          "The backend is matching this approved script with gameplay footage, subtitle treatment, and optional music before FFmpeg render begins.",
          event,
        ),
      };
    }
    return {
      ...base,
      title,
      detail: withEventMeta(summarizeValidationSummary(stringValue(payload.error)) ?? validationSummary, event),
    };
  }
  if (event.type === "source_ingested") {
    return {
      ...base,
      tone: "success" as const,
      iconKey: "success",
      providerLabel: "Firecrawl",
      title: "Firecrawl finished ingesting the source",
      detail: withEventMeta(
        `Captured "${stringValue(payload.title) ?? "source"}" as clean markdown with ${payload.url_count ?? 0} normalized source URL${Number(payload.url_count) === 1 ? "" : "s"}.`,
        event,
      ),
    };
  }
  if (event.type === "scripts_ready") {
    const mode = stringValue(payload.mode);
    return {
      ...base,
      tone: "success" as const,
      iconKey: "success",
      providerLabel: producerProviderLabel(mode),
      title: "Script generation is complete",
      detail: withEventMeta(
        `${payload.script_count ?? 0} scripts cleared local QA after ${payload.attempt_count ?? 0} generation attempt${Number(payload.attempt_count) === 1 ? "" : "s"} and ${payload.repair_count ?? 0} repair pass${Number(payload.repair_count) === 1 ? "" : "es"}. ${mode === "elevenlabs_native" ? "These scripts came from the ElevenLabs producer agent." : `${payload.section_count ?? payload.script_count ?? 0} article sections were planned into ${payload.planned_count ?? payload.script_count ?? 0} section-based script slots through the CrewAI producer.`}`,
        event,
      ),
    };
  }
  if (event.type === "narrator_conversation_started") {
    const mode = stringValue(payload.mode);
    const copy = narrationStartedCopy(mode, payload);
    return {
      ...base,
      iconKey: "elevenlabs",
      providerLabel: copy.providerLabel,
      title: copy.title,
      detail: withEventMeta(copy.detail, event),
    };
  }
  if (event.type === "alignment_ready") {
    return {
      ...base,
      tone: "success" as const,
      iconKey: "success",
      providerLabel: "ElevenLabs Alignment",
      title: `ElevenLabs forced alignment finished for ${videoLabelFromPayload(payload)}`,
      detail: withEventMeta(
        `Mapped ${payload.word_count ?? 0} spoken words to timestamps so subtitles can animate against the real narration instead of estimated text timing.`,
        event,
      ),
    };
  }
  if (event.type === "render_started") {
    return {
      ...base,
      iconKey: "ffmpeg",
      providerLabel: "FFmpeg",
      title: `FFmpeg render started for ${videoLabelFromPayload(payload)}`,
      detail: withEventMeta(
        `Combining ${stringValue(payload.subtitle_style_label) ?? "subtitle style"} subtitles with ${shortPath(stringValue(payload.gameplay_asset_path)) ?? "the selected gameplay clip"} and narration audio.`,
        event,
      ),
    };
  }
  if (event.type === "item_completed") {
    return {
      ...base,
      tone: "success" as const,
      iconKey: "success",
      providerLabel: "FFmpeg",
      title: `${videoLabelFromPayload(payload)} is fully exported`,
      detail: withEventMeta(
        `${shortPath(stringValue(payload.output_url)) ?? "The final MP4"} is ready for review or upload.`,
        event,
      ),
    };
  }
  if (event.type === "batch_completed" || event.type === "done") {
    return {
      ...base,
      tone: stringValue(payload.status) === "failed" ? ("danger" as const) : ("success" as const),
      iconKey: stringValue(payload.status) === "failed" ? ("danger" as const) : ("success" as const),
      providerLabel: "Backend",
      title: stringValue(payload.status) === "failed" ? "Batch failed" : "Batch finished successfully",
      detail: withEventMeta(
        `${payload.uploaded_count ?? 0} videos exported${Number(payload.failed_count) ? `, ${payload.failed_count} failed` : ""}.`,
        event,
      ),
    };
  }
  if (event.type === "error") {
    return {
      ...base,
      tone: "danger" as const,
      iconKey: "danger",
      providerLabel: "Backend",
      title: "Backend error",
      detail: withEventMeta(stringValue(payload.message) ?? "Backend error", event),
    };
  }
  return {
    ...base,
    title: humanizeEventType(event.type),
    detail: withEventMeta(JSON.stringify(payload), event),
  };
}

function buildActiveOperations(events: BatchEventRecord[], nowTick: number): ActiveOperation[] {
  const operations = new Map<string, BatchEventRecord>();

  for (const event of events) {
    clearResolvedOperations(operations, event);
    const key = activeOperationKey(event);
    if (!key) {
      continue;
    }
    operations.set(key, event);
  }

  return Array.from(operations.entries())
    .map(([key, event]) => toActiveOperation(key, event, nowTick))
    .sort((left, right) => right.updatedAtMs - left.updatedAtMs)
    .map(({ updatedAtMs: _updatedAtMs, ...operation }) => operation);
}

function clearResolvedOperations(operations: Map<string, BatchEventRecord>, event: BatchEventRecord) {
  const itemId = stringValue(event.payload.item_id);
  const slotId = stringValue(event.payload.slot_id);
  const status = stringValue(event.payload.status);
  const stage = stringValue(event.payload.stage);

  if (
    event.type === "source_ingested" ||
    status === "scripting" ||
    status === "completed" ||
    status === "failed" ||
    status === "partial_failed"
  ) {
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

function toActiveOperation(key: string, event: BatchEventRecord, nowTick: number) {
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
    updatedAtMs,
  };
}

function activeOperationKind(key: string): ActiveOperation["kind"] {
  if (key === "ingest") {
    return "ingest";
  }
  if (key === "producer" || key.startsWith("producer:")) {
    return "producer";
  }
  if (key.startsWith("narration:")) {
    return "narration";
  }
  if (key.startsWith("assets:")) {
    return "assets";
  }
  if (key.startsWith("render:")) {
    return "render";
  }
  return "backend";
}

function buildActivitySummary(
  activeOperations: ActiveOperation[],
  latestLogEvent: BatchEventRecord | null,
  batch: BatchRecord | null,
  nowTick: number,
  isBatchSettled: boolean,
): ActivitySummary {
  if (activeOperations.length === 0) {
    if (isBatchSettled) {
      const failed = batch?.status === "failed" || batch?.status === "partial_failed";
      return {
        title: failed ? "The batch has finished with failures" : "The batch has finished successfully",
        detail: failed
          ? "Generation has stopped. Use the log history below to inspect exactly where the backend failed."
          : "The backend has finished Firecrawl ingest, script generation, narration, alignment, and FFmpeg export for this run.",
        liveLabel: latestLogEvent ? `Finished at ${formatClock(latestLogEvent.created_at)}` : null,
        tone: failed ? "danger" : "success",
        iconKey: failed ? "danger" : "success",
        providerLabel: "Backend",
      };
    }

    const latestEntry = latestLogEvent ? toLogEntry(latestLogEvent) : null;
    return {
      title: latestEntry?.title ?? "Waiting for the next backend stage",
      detail:
        latestEntry?.detail ??
        "The SSE stream is open. The next Firecrawl, OpenAI, ElevenLabs, or FFmpeg update will appear here as soon as the backend publishes it.",
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
    {
      ingest: 0,
      producer: 0,
      narration: 0,
      assets: 0,
      render: 0,
      backend: 0,
    },
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
  const issues = value
    .split(";")
    .map(item => item.trim())
    .filter(Boolean);
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
  const metaParts = [
    formatClock(event.created_at),
    eventElapsedLabel(event.payload),
  ].filter(Boolean);
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

function humanizeConnectionState(value: "idle" | "connecting" | "streaming" | "reconnecting" | "settled") {
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
  if (status === "uploaded") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  if (status === "rendering") {
    return "warning";
  }
  if (status === "narrating" || status === "selecting_assets") {
    return "accent";
  }
  return "neutral";
}

function HeroSignal({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  tone: "success" | "danger" | "accent" | "warning" | "neutral";
}) {
  return (
    <div className={`${styles.heroSignal} ${styles[`heroSignal-${tone}`]}`}>
      <span className={styles.heroSignalLabel}>{label}</span>
      <strong className={styles.heroSignalValue}>{value}</strong>
      <span className={styles.heroSignalDetail}>{detail}</span>
    </div>
  );
}

function StackRow({
  icon,
  title,
  detail,
}: {
  icon: ReactNode;
  title: string;
  detail: string;
}) {
  return (
    <div className={styles.stackRow}>
      <span className={styles.stackRowIcon}>{icon}</span>
      <div className={styles.stackRowCopy}>
        <p className={styles.stackRowTitle}>{title}</p>
        <p className={styles.stackRowDetail}>{detail}</p>
      </div>
    </div>
  );
}

function StepCard({
  icon,
  title,
  value,
  detail,
  tone,
}: {
  icon: ReactNode;
  title: string;
  value: string;
  detail: string;
  tone: "success" | "accent" | "neutral";
}) {
  return (
    <article className={styles.stepCard}>
      <div className={styles.stepIcon}>{icon}</div>
      <p className={styles.stepTitle}>{title}</p>
      <p className={styles.stepValue}>{value}</p>
      <p className={styles.stepDetail}>{detail}</p>
      <span className={`${styles.stepTone} ${styles[`tone-${tone}`]}`} />
    </article>
  );
}

function MiniMetric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "success" | "accent" | "neutral" | "warning";
}) {
  return (
    <div className={styles.metricCard}>
      <span className={styles.metricLabel}>{label}</span>
      <span className={`${styles.metricValue} ${styles[`metric-${tone}`]}`}>{value}</span>
    </div>
  );
}

function ItemMeta({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.itemMeta}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StatusBadge({
  label,
  tone,
}: {
  label: string;
  tone: "success" | "danger" | "accent" | "warning" | "neutral";
}) {
  return <span className={`${styles.statusBadge} ${styles[`badge-${tone}`]}`}>{label}</span>;
}
