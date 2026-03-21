"use client";

import type { FormEvent, ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  AudioLines,
  Clapperboard,
  LoaderCircle,
  MonitorPlay,
  Sparkles,
  Type,
  WandSparkles,
} from "lucide-react";

import styles from "./video-edit-page.module.css";

type AssetRecord = {
  id: string;
  path: string;
  tags: string[];
};

type SubtitlePresetOption = {
  id: string;
  label: string;
  animation: string;
  font_name: string;
  preferred_tags: string[];
};

type OptionsEnvelope = {
  gameplay_assets: AssetRecord[];
  subtitle_presets: SubtitlePresetOption[];
};

type BatchRecord = {
  id: string;
  status: string;
  title_hint?: string | null;
};

type BatchItemRecord = {
  id: string;
  status: string;
  output_url?: string | null;
  error?: string | null;
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

const DEFAULT_TITLE = "Content Hub Subtitle Preview";
const DEFAULT_NARRATION =
  "Content Hub plugs into Adobe Express so one idea can turn into tailored captions for X, Instagram, and LinkedIn. Thinking Mode helps shape the copy, the editor keeps every line adjustable, and the whole point is faster social publishing without flattening your voice into generic AI filler.";

const NARRATION_PRESETS = [
  {
    id: "balanced",
    label: "Balanced product explainer",
    title: "Content Hub Balanced Preview",
    narration:
      "Content Hub plugs into Adobe Express so one idea can turn into tailored captions for X, Instagram, and LinkedIn. Thinking Mode helps shape the copy, the editor keeps every line adjustable, and the whole point is faster social publishing without flattening your voice into generic AI filler.",
  },
  {
    id: "dense",
    label: "Dense detail stress test",
    title: "Content Hub Dense Preview",
    narration:
      "Content Hub starts with a single prompt, then routes that idea through Thinking Mode, channel-aware caption generation, and a live editor inside Adobe Express. The useful part is not just writing faster. It keeps the copy adaptable for X, Instagram, and LinkedIn while leaving every line editable, so a team can test variations, tighten hooks, and publish without restarting the workflow from zero every time.",
  },
  {
    id: "punchy",
    label: "Punchy caption rhythm",
    title: "Content Hub Punchy Preview",
    narration:
      "One idea in. Multiple social posts out. Content Hub uses Thinking Mode to shape the angle, rewrites for each platform, and keeps the draft editable inside Adobe Express. That means faster hooks, cleaner captions, and fewer dead-end AI drafts when you still need the final post to sound like your team actually wrote it.",
  },
];

const EVENT_TYPES = [
  "status",
  "log",
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

export function VideoEditLab() {
  const [options, setOptions] = useState<OptionsEnvelope | null>(null);
  const [title, setTitle] = useState(DEFAULT_TITLE);
  const [narrationText, setNarrationText] = useState(DEFAULT_NARRATION);
  const [selectedGameplayId, setSelectedGameplayId] = useState("");
  const [selectedPresetId, setSelectedPresetId] = useState("");
  const [premiumAudio, setPremiumAudio] = useState(false);
  const [batchEnvelope, setBatchEnvelope] = useState<BatchEnvelope | null>(null);
  const [events, setEvents] = useState<BatchEventRecord[]>([]);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [connectionState, setConnectionState] = useState<"idle" | "connecting" | "streaming" | "reconnecting">("idle");
  const [pageError, setPageError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [nowTick, setNowTick] = useState(() => Date.now());

  const eventSourceRef = useRef<EventSource | null>(null);
  const refreshTimerRef = useRef<number | null>(null);

  useEffect(() => {
    void loadOptions();
    return () => {
      eventSourceRef.current?.close();
      if (refreshTimerRef.current !== null) {
        window.clearTimeout(refreshTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!activeBatchId) {
      eventSourceRef.current?.close();
      setConnectionState("idle");
      return;
    }
    void refreshBatch(activeBatchId);
    connectEventStream(activeBatchId);
    const intervalId = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => {
      eventSourceRef.current?.close();
      window.clearInterval(intervalId);
    };
  }, [activeBatchId]);

  async function loadOptions() {
    try {
      const response = await fetch("/api/brainrot/video-edit/options", { cache: "no-store" });
      const payload = (await response.json()) as OptionsEnvelope;
      if (!response.ok) {
        throw new Error("Failed to load video edit options.");
      }
      setOptions(payload);
      if (payload.gameplay_assets[0] && !selectedGameplayId) {
        setSelectedGameplayId(payload.gameplay_assets[0].id);
      }
      if (payload.subtitle_presets[0] && !selectedPresetId) {
        setSelectedPresetId(payload.subtitle_presets[0].id);
      }
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Failed to load options.");
    }
  }

  async function createPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedGameplayId || !selectedPresetId) {
      setPageError("Choose a gameplay clip and a subtitle style first.");
      return;
    }

    setIsSubmitting(true);
    setPageError(null);
    setStatusMessage(null);
    setEvents([]);

    try {
      const response = await fetch("/api/brainrot/video-edit/previews", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title,
          narration_text: narrationText,
          gameplay_asset_id: selectedGameplayId,
          subtitle_preset_id: selectedPresetId,
          premium_audio: premiumAudio,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail ?? "Failed to start preview render.");
      }
      setBatchEnvelope({ batch: payload.batch, items: [payload.item] });
      setActiveBatchId(payload.batch.id);
      setStatusMessage(`Preview batch ${payload.batch.id} started.`);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Failed to start preview render.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function refreshBatch(batchId: string) {
    try {
      const response = await fetch(`/api/brainrot/batches/${batchId}`, { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) {
        if (response.status === 404 && activeBatchId === batchId) {
          eventSourceRef.current?.close();
          setActiveBatchId(null);
          setConnectionState("idle");
        }
        throw new Error(payload?.detail ?? "Failed to refresh preview batch.");
      }
      setBatchEnvelope(payload);
      return true;
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Failed to refresh preview batch.");
      return false;
    }
  }

  function connectEventStream(batchId: string) {
    eventSourceRef.current?.close();
    setConnectionState("connecting");
    const source = new EventSource(`/api/brainrot/batches/${batchId}/events`);
    eventSourceRef.current = source;

    source.onopen = () => setConnectionState("streaming");
    source.onerror = () => setConnectionState("reconnecting");

    const handleEvent = (rawEvent: MessageEvent<string>) => {
      const parsed = parseEvent(rawEvent.data, rawEvent.type);
      if (!parsed) {
        return;
      }
      if (parsed.type === "ping") {
        setConnectionState("streaming");
        return;
      }
      setEvents(previous => [...previous, parsed].slice(-80));
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
      void refreshBatch(batchId);
    }, 250);
  }

  const item = batchEnvelope?.items[0] ?? null;
  const activePreset = options?.subtitle_presets.find(preset => preset.id === selectedPresetId) ?? null;
  const activeGameplay = options?.gameplay_assets.find(asset => asset.id === selectedGameplayId) ?? null;
  const compactLogs = useMemo(
    () => events.filter(event => event.type !== "ping" && !(event.type === "log" && typeof event.payload.heartbeat === "number")),
    [events],
  );
  const latestEvent = compactLogs.at(-1) ?? null;
  const liveStage = buildLiveStage(events, nowTick);
  const previewVideoUrl = activeBatchId && item?.status === "uploaded"
    ? `/api/brainrot/video-edit/previews/${activeBatchId}/video`
    : null;
  const renderMetadata = item?.render_metadata ?? null;

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <div className={styles.kicker}>
            <span className={styles.kickerDot} />
            Video edit lab
          </div>
          <h1 className={styles.heroTitle}>Tune subtitle animation, placement, and pacing on one real render.</h1>
          <p className={styles.heroCopyText}>
            This page is for visual iteration, not batch generation. Pick a gameplay clip, lock a subtitle treatment,
            change the narration, and run one actual ElevenLabs plus FFmpeg preview so you can judge placement and motion
            before shipping it into the wider pipeline.
          </p>
        </div>

        <div className={styles.previewSignalCard}>
          <div className={styles.previewSignalIcon}>
            <WandSparkles size={18} />
          </div>
          <h2 className={styles.previewSignalTitle}>Preview rules</h2>
          <ul className={styles.previewSignalList}>
            <li>One video only, so subtitle placement problems are obvious instead of hidden inside a batch.</li>
            <li>Uses the same ElevenLabs narration and FFmpeg burn path as production renders.</li>
            <li>Lets you compare fonts and animation styles against a fixed clip without wasting a full run.</li>
          </ul>
        </div>
      </section>

      <section className={styles.layoutGrid}>
        <article className={styles.card}>
          <div className={styles.cardHeader}>
            <div>
              <p className={styles.eyebrow}>Controls</p>
              <h2 className={styles.cardTitle}>Build one preview</h2>
            </div>
            <StatusBadge label={connectionState} tone={connectionState === "streaming" ? "success" : connectionState === "reconnecting" ? "warning" : "neutral"} />
          </div>

          <form className={styles.form} onSubmit={createPreview}>
            <label className={styles.field}>
              <span>Preview title</span>
              <input value={title} onChange={event => setTitle(event.target.value)} />
            </label>

            <label className={styles.field}>
              <span>Narration text</span>
              <textarea value={narrationText} onChange={event => setNarrationText(event.target.value)} rows={8} />
            </label>

            <div className={styles.presetRail}>
              {NARRATION_PRESETS.map(preset => (
                <button
                  key={preset.id}
                  type="button"
                  className={styles.presetChip}
                  onClick={() => {
                    setTitle(preset.title);
                    setNarrationText(preset.narration);
                  }}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            <label className={styles.field}>
              <span>Gameplay clip</span>
              <select value={selectedGameplayId} onChange={event => setSelectedGameplayId(event.target.value)}>
                {(options?.gameplay_assets ?? []).map(asset => (
                  <option key={asset.id} value={asset.id}>
                    {asset.path}
                  </option>
                ))}
              </select>
            </label>

            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={premiumAudio}
                onChange={event => setPremiumAudio(event.target.checked)}
              />
              <span>Use premium narration audio</span>
            </label>

            <button type="submit" className={styles.primaryButton} disabled={isSubmitting}>
              {isSubmitting ? <LoaderCircle size={15} className={styles.spin} /> : <Sparkles size={15} />}
              Render preview
            </button>
          </form>

          {statusMessage ? <p className={styles.inlineNote}>{statusMessage}</p> : null}
          {pageError ? <p className={styles.errorNote}>{pageError}</p> : null}
        </article>

        <article className={styles.card}>
          <div className={styles.cardHeader}>
            <div>
              <p className={styles.eyebrow}>Subtitle styles</p>
              <h2 className={styles.cardTitle}>Animation presets</h2>
            </div>
            <StatusBadge label={`${options?.subtitle_presets.length ?? 0} styles`} tone="accent" />
          </div>
          <div className={styles.styleGrid}>
            {(options?.subtitle_presets ?? []).map(preset => {
              const selected = preset.id === selectedPresetId;
              return (
                <button
                  key={preset.id}
                  type="button"
                  className={`${styles.styleCard} ${selected ? styles.styleCardSelected : ""}`}
                  onClick={() => setSelectedPresetId(preset.id)}
                >
                  <p className={styles.styleLabel}>{preset.label}</p>
                  <p className={styles.styleMeta}>{preset.animation} · {preset.font_name}</p>
                  <p className={styles.styleTags}>{preset.preferred_tags.slice(0, 4).join(" · ")}</p>
                </button>
              );
            })}
          </div>
        </article>
      </section>

      <section className={styles.previewGrid}>
        <article className={`${styles.card} ${styles.playerCard}`}>
          <div className={styles.cardHeader}>
            <div>
              <p className={styles.eyebrow}>Rendered output</p>
              <h2 className={styles.cardTitle}>See the actual subtitle burn</h2>
            </div>
            <div className={styles.metaStack}>
              <StatusBadge label={batchEnvelope?.batch.status ?? "idle"} tone={item?.status === "uploaded" ? "success" : batchEnvelope ? "warning" : "neutral"} />
              {activeBatchId ? <StatusBadge label={activeBatchId.slice(0, 8)} tone="accent" /> : null}
            </div>
          </div>

          <div className={styles.playerShell}>
            {previewVideoUrl ? (
              <video key={previewVideoUrl} src={previewVideoUrl} controls playsInline className={styles.previewVideo} />
            ) : (
              <div className={styles.playerPlaceholder}>
                <MonitorPlay size={24} />
                <p>Start a preview render to inspect subtitle placement and animation.</p>
              </div>
            )}
          </div>

          <div className={styles.metricGrid}>
            <MetricCard icon={<Type size={15} />} label="Style" value={activePreset?.label ?? "Not selected"} />
            <MetricCard icon={<Sparkles size={15} />} label="Animation" value={activePreset?.animation ?? "Not selected"} />
            <MetricCard icon={<AudioLines size={15} />} label="Font" value={activePreset?.font_name ?? "Not selected"} />
            <MetricCard icon={<Clapperboard size={15} />} label="Gameplay" value={activeGameplay?.path ?? "Not selected"} />
          </div>

          {renderMetadata ? (
            <div className={styles.metricGrid}>
              <MetricCard
                icon={<Type size={15} />}
                label="Burned style"
                value={stringValue(renderMetadata.subtitle_style_label) ?? activePreset?.label ?? "Pending"}
              />
              <MetricCard
                icon={<Sparkles size={15} />}
                label="Burned animation"
                value={stringValue(renderMetadata.subtitle_animation) ?? activePreset?.animation ?? "Pending"}
              />
              <MetricCard
                icon={<AudioLines size={15} />}
                label="Subtitle words"
                value={String(numberValue(renderMetadata.subtitle_word_count) ?? "Pending")}
              />
              <MetricCard
                icon={<Clapperboard size={15} />}
                label="Selected clip"
                value={stringValue(renderMetadata.gameplay_asset_path) ?? activeGameplay?.path ?? "Pending"}
              />
            </div>
          ) : null}
        </article>

        <article className={styles.card}>
          <div className={styles.cardHeader}>
            <div>
              <p className={styles.eyebrow}>Live backend state</p>
              <h2 className={styles.cardTitle}>What the preview is doing</h2>
            </div>
            <StatusBadge
              label={liveStage?.stage ?? "idle"}
              tone={item?.status === "uploaded" ? "success" : activeBatchId ? "warning" : "neutral"}
            />
          </div>

          <div className={styles.activeBox}>
            <p className={styles.activeTitle}>{liveStage?.message ?? "No preview job running yet."}</p>
            <p className={styles.activeMeta}>
              {latestEvent ? `${formatClock(latestEvent.created_at)} · ${liveStage?.elapsedLabel ?? "waiting"}` : "Waiting for first preview event"}
            </p>
          </div>

          <div className={styles.historyList}>
            {compactLogs.length > 0 ? compactLogs.slice(-18).map(event => (
              <div key={`${event.sequence}-${event.type}`} className={styles.historyRow}>
                <div>
                  <p className={styles.historyTitle}>{eventTitle(event)}</p>
                  <p className={styles.historyDetail}>{eventDetail(event)}</p>
                </div>
                <span className={styles.historyClock}>{formatClock(event.created_at)}</span>
              </div>
            )) : (
              <p className={styles.emptyState}>The preview history will appear here once a render starts.</p>
            )}
          </div>
        </article>
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

function stringValue(value: unknown) {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function numberValue(value: unknown) {
  return typeof value === "number" ? value : null;
}

function formatClock(value: string) {
  return new Date(value).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function eventTitle(event: BatchEventRecord) {
  if (event.type === "log") {
    return stringValue(event.payload.message) ?? "Backend update";
  }
  if (event.type === "render_started") {
    return "Render started";
  }
  if (event.type === "item_completed") {
    return "Preview exported";
  }
  if (event.type === "batch_completed") {
    return "Preview batch finished";
  }
  return event.type.replaceAll("_", " ");
}

function eventDetail(event: BatchEventRecord) {
  if (event.type === "render_started") {
    return `${stringValue(event.payload.subtitle_style_label) ?? "style"} · ${stringValue(event.payload.gameplay_asset_path) ?? "gameplay"}`;
  }
  if (event.type === "item_completed") {
    return stringValue(event.payload.output_url) ?? "Video uploaded";
  }
  if (event.type === "batch_completed") {
    return `status ${stringValue(event.payload.status) ?? "unknown"}`;
  }
  return [
    stringValue(event.payload.source),
    stringValue(event.payload.error),
    stringValue(event.payload.validation_summary),
  ].filter(Boolean).join(" · ") || "Live backend event";
}

function buildLiveStage(events: BatchEventRecord[], nowTick: number) {
  const terminalEvent = [...events]
    .reverse()
    .find(event => event.type === "batch_completed" || event.type === "done" || event.type === "item_completed");

  if (terminalEvent) {
    const secondsSinceUpdate = Math.max(0, (nowTick - new Date(terminalEvent.created_at).getTime()) / 1000);
    if (terminalEvent.type === "item_completed") {
      return {
        stage: "completed",
        message: "Preview exported",
        elapsedLabel: `${Math.floor(secondsSinceUpdate)}s ago`,
      };
    }

    return {
      stage: stringValue(terminalEvent.payload.status) ?? "completed",
      message: "Preview batch finished",
      elapsedLabel: `${Math.floor(secondsSinceUpdate)}s ago`,
    };
  }

  const liveEvent = [...events]
    .reverse()
    .find(event => event.type === "log" || event.type === "render_started" || event.type === "narrator_conversation_started");

  if (!liveEvent) {
    return null;
  }

  const elapsedSeconds = numberValue(liveEvent.payload.total_elapsed_seconds) ?? numberValue(liveEvent.payload.elapsed_seconds);
  const secondsSinceUpdate = Math.max(0, (nowTick - new Date(liveEvent.created_at).getTime()) / 1000);
  return {
    stage: stringValue(liveEvent.payload.stage) ?? liveEvent.type.replaceAll("_", " "),
    message: eventTitle(liveEvent),
    elapsedLabel: elapsedSeconds !== null ? `${(elapsedSeconds + secondsSinceUpdate).toFixed(1)}s live` : `${Math.floor(secondsSinceUpdate)}s since update`,
  };
}

function StatusBadge({
  label,
  tone,
}: {
  label: string;
  tone: "success" | "warning" | "accent" | "neutral";
}) {
  return <span className={`${styles.statusBadge} ${styles[`badge-${tone}`]}`}>{label}</span>;
}

function MetricCard({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className={styles.metricCard}>
      <div className={styles.metricIcon}>{icon}</div>
      <div>
        <p className={styles.metricLabel}>{label}</p>
        <p className={styles.metricValue}>{value}</p>
      </div>
    </div>
  );
}
