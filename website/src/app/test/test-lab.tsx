"use client";

import type { FormEvent, ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import {
  Activity,
  AudioLines,
  Bot,
  Clapperboard,
  Link2,
  LoaderCircle,
  RefreshCw,
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

type ActiveOperation = {
  id: string;
  title: string;
  detail: string | null;
  stageLabel: string;
  timeLabel: string;
  elapsedLabel: string | null;
  updatedLabel: string;
  tone: EntryTone;
};

const EVENT_TYPES = [
  "status",
  "log",
  "source_ingested",
  "producer_conversation_started",
  "producer_tool_called",
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
  const [connectionState, setConnectionState] = useState<"idle" | "connecting" | "streaming" | "reconnecting">("idle");
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [nowTick, setNowTick] = useState(() => Date.now());

  const eventSourceRef = useRef<EventSource | null>(null);
  const refreshTimerRef = useRef<number | null>(null);
  const batchPollRef = useRef<number | null>(null);
  const logStreamRef = useRef<HTMLDivElement | null>(null);

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
    };
  }, []);

  useEffect(() => {
    if (!activeBatchId) {
      eventSourceRef.current?.close();
      setConnectionState("idle");
      return;
    }

    void refreshBatch(activeBatchId, { silent: true });
    connectEventStream(activeBatchId);

    return () => {
      eventSourceRef.current?.close();
    };
  }, [activeBatchId]);

  useEffect(() => {
    if (!activeBatchId) {
      if (batchPollRef.current !== null) {
        window.clearInterval(batchPollRef.current);
        batchPollRef.current = null;
      }
      return;
    }

    batchPollRef.current = window.setInterval(() => {
      void refreshBatch(activeBatchId, { silent: true });
    }, 3000);

    return () => {
      if (batchPollRef.current !== null) {
        window.clearInterval(batchPollRef.current);
        batchPollRef.current = null;
      }
    };
  }, [activeBatchId]);

  useEffect(() => {
    if (!activeBatchId) {
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
    if (!logStreamRef.current) {
      return;
    }
    logStreamRef.current.scrollTo({
      top: logStreamRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [events.length]);

  async function checkHealth() {
    try {
      const response = await fetch("/api/brainrot/health", { cache: "no-store" });
      setBackendHealth(response.ok ? "ok" : "error");
    } catch {
      setBackendHealth("error");
    }
  }

  async function bootstrapAgents() {
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
      setIsRefreshing(true);
    }

    try {
      const response = await fetch(`/api/brainrot/batches/${batchId}`, { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) {
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
        const next = [...previous, parsed];
        return next.slice(-160);
      });
      setConnectionState("streaming");
      scheduleRefresh(batchId);
    };

    for (const type of EVENT_TYPES) {
      source.addEventListener(type, handleEvent as EventListener);
    }

    source.onmessage = handleEvent;
  }

  function scheduleRefresh(batchId: string) {
    if (refreshTimerRef.current !== null) {
      return;
    }

    refreshTimerRef.current = window.setTimeout(() => {
      refreshTimerRef.current = null;
      void refreshBatch(batchId, { silent: true });
    }, 250);
  }

  const items = batchEnvelope?.items ?? [];
  const batch = batchEnvelope?.batch ?? null;
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
  const latestLogAgeLabel = latestLogEvent
    ? `${Math.max(0, Math.floor((nowTick - new Date(latestLogEvent.created_at).getTime()) / 1000))}s ago`
    : "Waiting for first event";
  const isBatchSettled = batch ? ["completed", "partial_failed", "failed"].includes(batch.status) : false;
  const logEntries = logEvents.map(event => toLogEntry(event));

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
          <div className={styles.heroBadges}>
            <StatusBadge label={`Backend ${backendHealth}`} tone={backendHealth === "ok" ? "success" : backendHealth === "checking" ? "neutral" : "danger"} />
            <StatusBadge label={bootstrapSummary ?? "Agents not bootstrapped"} tone={bootstrapSummary ? "accent" : "neutral"} />
            <StatusBadge label={activeBatchId ? `Batch ${shortId(activeBatchId)}` : "No active batch"} tone={activeBatchId ? "accent" : "neutral"} />
          </div>
        </div>

        <div className={styles.strategyCard}>
          <div className={styles.strategyIcon}>
            <WandSparkles size={18} />
          </div>
          <h2 className={styles.strategyTitle}>Variation strategy</h2>
          <ul className={styles.strategyList}>
            <li>Guarantee multiple subtitle presets across a batch instead of a single repeated karaoke burn.</li>
            <li>Bias high-energy gameplay toward pop, punch, or comic treatments and calmer clips toward box or sweep captions.</li>
            <li>Expose the exact subtitle style, font, and gameplay asset path per item so you can verify the run, not trust it.</li>
          </ul>
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
            <MiniMetric label="Connection" value={connectionState} tone={connectionState === "streaming" ? "success" : connectionState === "reconnecting" ? "warning" : "neutral"} />
            <MiniMetric label="Last sync" value={lastSyncedAt ? formatClock(lastSyncedAt) : "—"} tone="neutral" />
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
            icon={<Bot size={16} />}
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
              <StatusBadge label={connectionState} tone={connectionState === "streaming" ? "success" : connectionState === "reconnecting" ? "warning" : "neutral"} />
              <StatusBadge label={`${activeOperations.length} active`} tone={activeOperations.length > 0 ? "warning" : "neutral"} />
              <StatusBadge label={`${logEntries.length} history`} tone="accent" />
            </div>
          </div>

          <div className={styles.liveLogSummary}>
            <span>{latestLogEvent ? `Last event ${latestLogAgeLabel}` : "Listening for backend work"}</span>
            <span>{latestLogEvent ? formatClock(latestLogEvent.created_at) : "No events yet"}</span>
          </div>

          <div className={styles.activeOpsPanel}>
            <div className={styles.activeOpsHeader}>
              <span>Active backend work</span>
              <span>{activeOperations.length > 0 ? `${activeOperations.length} live` : "Idle"}</span>
            </div>
            {activeOperations.length > 0 ? (
              <div className={styles.activeOpsList}>
                {activeOperations.map(operation => (
                  <div key={operation.id} className={styles.activeOpRow}>
                    <div className={styles.activeOpPulseWrap}>
                      <span className={`${styles.activeOpPulse} ${styles[`activeOpPulse-${operation.tone}`]}`} />
                    </div>
                    <div className={styles.activeOpCopy}>
                      <p className={styles.activeOpTitle}>{operation.title}</p>
                      {operation.detail ? <p className={styles.activeOpDetail}>{operation.detail}</p> : null}
                    </div>
                    <div className={styles.activeOpMeta}>
                      <span className={styles.activeOpStage}>{operation.stageLabel}</span>
                      <span className={styles.activeOpClock}>{operation.timeLabel}</span>
                      {operation.elapsedLabel ? (
                        <span className={styles.activeOpElapsed}>{operation.elapsedLabel}</span>
                      ) : null}
                      <span className={styles.activeOpUpdated}>{operation.updatedLabel}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className={styles.emptyState}>
                {activeBatchId && !isBatchSettled
                  ? "No long-running backend job is active right now. The next event will appear here immediately."
                  : "Attach a live batch to see active workstream timers here."}
              </p>
            )}
          </div>

          <div className={styles.thinkingLogCard}>
            {logEntries.length > 0 ? (
              <div className={styles.thinkingLogBody} ref={logStreamRef}>
                {logEntries.map((entry, index) => {
                  const isLast = index === logEntries.length - 1;
                  return (
                    <div key={entry.id} className={styles.thinkingLogStep}>
                      <div className={styles.thinkingLogBulletCol}>
                        <span className={`${styles.thinkingLogBullet} ${styles[`thinkingLogBullet-${entry.tone}`]}`} />
                        {!isLast && <span className={styles.thinkingLogLine} />}
                      </div>
                      <div className={styles.thinkingLogStepContent}>
                        <div className={styles.thinkingLogStepHead}>
                          <div className={styles.thinkingLogStepHeadMain}>
                            <p className={styles.thinkingLogStepTitle}>{entry.title}</p>
                            {entry.detail ? (
                              <p className={styles.thinkingLogStepDetail}>{entry.detail}</p>
                            ) : null}
                          </div>
                          <div className={styles.thinkingLogMetaCol}>
                            <span className={styles.thinkingLogStage}>{entry.stageLabel}</span>
                            <span className={styles.thinkingLogClock}>{entry.timeLabel}</span>
                            {entry.elapsedLabel ? (
                              <span className={styles.thinkingLogElapsed}>{entry.elapsedLabel}</span>
                            ) : null}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
                {!isBatchSettled && activeBatchId ? (
                  <div className={styles.thinkingSpinnerRow}>
                    <div className={styles.thinkingSpinnerIndent}>
                      <span className={styles.thinkingSpinner} />
                    </div>
                    <span className={styles.thinkingFinalizingText}>Listening for the next backend update…</span>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className={styles.emptyState}>Attach a batch to stream the event log here.</p>
            )}
          </div>
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

                    <div className={styles.itemDetails}>
                      <p>
                        <strong>Estimated:</strong>{" "}
                        {typeof item.script?.estimated_seconds === "number"
                          ? `${item.script.estimated_seconds.toFixed(1)}s`
                          : "Pending"}
                      </p>
                      <p>
                        <strong>Output:</strong>{" "}
                        {stringValue(item.output_url)?.startsWith("http") ? (
                          <a href={stringValue(item.output_url) ?? "#"} target="_blank" rel="noreferrer">
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

function shortId(value: string) {
  return value.slice(0, 8);
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
  if (event.type === "status" && stringValue(event.payload.status) === "queued") {
    return false;
  }
  if (event.type === "producer_conversation_started") {
    return false;
  }
  if (event.type === "log") {
    const message = stringValue(event.payload.message) ?? "";
    if (numberValue(event.payload.heartbeat) !== null) {
      return false;
    }
    if (message.startsWith("Source ingestion completed for ")) {
      return false;
    }
    if (message.startsWith("Narration started for item ")) {
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

function toLogEntry(event: BatchEventRecord) {
  const payload = event.payload;
  const elapsed = numberValue(payload.elapsed_seconds);
  const totalElapsed = numberValue(payload.total_elapsed_seconds);
  const base = {
    id: `${event.sequence}-${event.type}`,
    stageLabel: humanizeStage(stringValue(payload.stage) ?? event.type),
    timeLabel: formatClock(event.created_at),
    elapsedLabel:
      totalElapsed !== null
        ? `${totalElapsed.toFixed(1)}s total`
        : elapsed !== null
          ? `${elapsed.toFixed(1)}s`
          : null,
    tone: "accent" as EntryTone,
  };
  if (event.type === "log") {
    const validationSummary = summarizeValidationSummary(stringValue(payload.validation_summary));
    const detailParts = [
      stringValue(payload.source),
      payload.attempt ? `attempt ${payload.attempt}` : null,
      payload.heartbeat ? `heartbeat ${payload.heartbeat}` : null,
      stringValue(payload.model),
      validationSummary,
      payload.title_repairs ? `titles fixed ${payload.title_repairs}` : null,
      payload.hook_repairs ? `hooks fixed ${payload.hook_repairs}` : null,
      payload.fact_repairs ? `facts fixed ${payload.fact_repairs}` : null,
      payload.narration_repairs ? `scripts extended ${payload.narration_repairs}` : null,
      totalElapsed !== null && elapsed !== null && Math.abs(totalElapsed - elapsed) >= 0.1
        ? `step ${elapsed.toFixed(1)}s`
        : null,
      summarizeValidationSummary(stringValue(payload.error)),
    ].filter(Boolean);
    const title = stringValue(payload.message) ?? "Backend update";
    const lowerTitle = title.toLowerCase();
    return {
      ...base,
      tone: lowerTitle.includes("failed")
        ? ("danger" as const)
        : lowerTitle.includes("received") ||
            lowerTitle.includes("completed") ||
            lowerTitle.includes("finished") ||
            lowerTitle.includes("applied local script fixes")
          ? ("success" as const)
          : lowerTitle.includes("waiting")
            ? ("neutral" as const)
            : ("accent" as const),
      title,
      detail: detailParts.join(" · ") || null,
    };
  }
  if (event.type === "source_ingested") {
    return {
      ...base,
      tone: "success" as const,
      title: `Source ingested: ${stringValue(payload.title) ?? "source"}`,
      detail: `${payload.url_count ?? 0} URLs normalized.`,
    };
  }
  if (event.type === "producer_conversation_started") {
    return {
      ...base,
      title: "Producer started",
      detail: `${stringValue(payload.mode) ?? "unknown"} · ${stringValue(payload.model) ?? "default model"}`,
    };
  }
  if (event.type === "scripts_ready") {
    return {
      ...base,
      tone: "success" as const,
      title: `${payload.script_count ?? 0} scripts ready`,
      detail: `attempts ${payload.attempt_count ?? 0} · repairs ${payload.repair_count ?? 0}`,
    };
  }
  if (event.type === "producer_tool_called") {
    return {
      ...base,
      title: "Producer tool call received",
      detail: `${payload.script_count ?? 0} scripts · ${payload.angle_count ?? 0} angles`,
    };
  }
  if (event.type === "narrator_conversation_started") {
    return {
      ...base,
      title: `Narration started for item ${payload.item_id ?? "?"}`,
      detail: `run ${shortId(String(payload.run_id ?? "?"))}`,
    };
  }
  if (event.type === "narrator_audio_ready") {
    return {
      ...base,
      tone: "success" as const,
      title: `Narration audio ready for item ${payload.item_id ?? "?"}`,
      detail: shortPath(stringValue(payload.audio_path)) ?? "Audio stored",
    };
  }
  if (event.type === "alignment_ready") {
    return {
      ...base,
      tone: "success" as const,
      title: `Alignment ready for item ${payload.item_id ?? "?"}`,
      detail: `${payload.word_count ?? 0} words aligned`,
    };
  }
  if (event.type === "render_started") {
    return {
      ...base,
      title: `Rendering video ${(Number(payload.item_index) || 0) + 1}`,
      detail: `${stringValue(payload.subtitle_style_label) ?? "pending style"} · ${shortPath(stringValue(payload.gameplay_asset_path)) ?? "pending gameplay"}`,
    };
  }
  if (event.type === "item_completed") {
    return {
      ...base,
      tone: "success" as const,
      title: `Video ${(Number(payload.item_index) || 0) + 1} exported`,
      detail: shortPath(stringValue(payload.output_url)) ?? "Render uploaded",
    };
  }
  if (event.type === "batch_completed" || event.type === "done") {
    return {
      ...base,
      tone: stringValue(payload.status) === "failed" ? ("danger" as const) : ("success" as const),
      title: `Batch finished with status ${stringValue(payload.status) ?? "unknown"}`,
      detail: `uploaded ${payload.uploaded_count ?? 0} · failed ${payload.failed_count ?? 0}`,
    };
  }
  if (event.type === "error") {
    return {
      ...base,
      tone: "danger" as const,
      title: "Backend error",
      detail: stringValue(payload.message) ?? "Backend error",
    };
  }
  if (event.type === "status") {
    return {
      ...base,
      tone: "neutral" as const,
      title: `Batch status changed to ${stringValue(payload.status) ?? "unknown"}`,
      detail: "Status update",
    };
  }
  return {
    ...base,
    title: humanizeEventType(event.type),
    detail: JSON.stringify(payload),
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
  const liveElapsed = elapsed !== null ? `${(elapsed + secondsSinceUpdate).toFixed(1)}s live` : null;

  return {
    id: `${key}-${event.sequence}`,
    title: entry.title,
    detail: entry.detail,
    stageLabel: entry.stageLabel,
    timeLabel: entry.timeLabel,
    elapsedLabel: liveElapsed,
    updatedLabel: secondsSinceUpdate < 1 ? "just now" : `${Math.floor(secondsSinceUpdate)}s since update`,
    tone: entry.tone,
    updatedAtMs,
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
    shortScripts ? `${shortScripts} short` : null,
    ungroundedHooks ? `${ungroundedHooks} ungrounded hook` : null,
    malformedFacts ? `${malformedFacts} malformed fact` : null,
    genericHooks ? `${genericHooks} generic hook` : null,
    genericCopy ? `${genericCopy} generic copy` : null,
  ].filter(Boolean);

  if (summaryParts.length > 0) {
    return `${issues.length} issues · ${summaryParts.join(" · ")}`;
  }
  return issues.slice(0, 2).join(" · ");
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
