'use client'

import { Suspense, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import styles from './shorts-page.module.css'
import { useAuth } from '@/components/auth/auth-provider'
import Navbar from '@/components/ui/navbar'
import { buildChatShortsPath, loadChatShorts, type StoredChatShort } from '@/lib/chat-run-storage'

// ─── Types ──────────────────────────────────────────────────────────────────

type ChatSummary = {
  id: string
  title: string
  created_at: string
  updated_at: string
  last_source_label: string | null
  last_source_url: string | null
  total_runs: number
  total_exported: number
  total_failed: number
  last_status: string | null
  cover_batch_id: string | null
  cover_item_id: string | null
  cover_output_url: string | null
  metadata?: {
    cover_thumbnail_url?: string | null
  }
}

type ChatEnvelope = { chat: ChatSummary }
type ChatListResponse = { items: ChatSummary[] }

type ChatGeneratedAsset = {
  chat_id: string
  batch_id: string
  batch_status: string
  batch_created_at: string
  batch_updated_at: string
  source_url: string | null
  title_hint: string | null
  item_id: string
  item_index: number
  item_status: string
  output_url: string | null
  render_metadata: {
    subtitle_style_label?: string | null
    subtitle_animation?: string | null
    subtitle_font_name?: string | null
    gameplay_asset_path?: string | null
    thumbnail_url?: string | null
  }
  script: { title?: string | null; estimated_seconds?: number | null } | null
  created_at: string
  updated_at: string
}

type ChatGeneratedAssetsResponse = {
  chat_id: string
  chat: ChatSummary | null
  items: ChatGeneratedAsset[]
}

type RecommendationInsight = {
  key: string
  label: string
  score: number
  sample_size: number
  avg_completion_ratio: number
  avg_watch_time_seconds: number
  positive_action_rate: number
}

type ReelRetentionSummary = {
  reel_number: number
  item_id: string
  title: string
  watch_time_seconds: number
  max_progress_seconds: number
  completion_ratio: number
  estimated_seconds: number | null
  replay_count: number
  subtitle_style: string | null
  subtitle_font: string | null
  gameplay_label: string | null
}

type ChatRecommendationResponse = {
  chat_id: string
  chat: ChatSummary | null
  session_id: string | null
  has_enough_data: boolean
  min_reels_required: number
  reels_tracked: number
  total_sessions: number
  total_watch_time_seconds: number
  unique_viewers: number
  high_retention_sessions: number
  recommendation_title: string | null
  recommendation_body: string | null
  generation_prompt: string | null
  top_gameplay: RecommendationInsight[]
  top_caption_styles: RecommendationInsight[]
  top_text_styles: RecommendationInsight[]
  retention_summary: ReelRetentionSummary[]
  winning_profile: Record<string, unknown>
}

type GeneratedShort = {
  id: string
  title: string
  source: string
  sourceUrl: string
  batchId: string
  itemId: string
  videoUrl: string
  thumbnailUrl: string | null
  updatedAt: string
  estimatedSeconds: number | null
  subtitleStyle: string | null
  subtitleFont: string | null
  gameplayAsset: string | null
}

type ShortEngagementPayload = {
  batch_id: string
  item_id: string
  viewer_id: string
  session_id: string
  watch_time_seconds: number
  completion_ratio: number
  max_progress_seconds: number
  replay_count: number
  unmuted: boolean
  info_opened: boolean
  open_clicked: boolean
  liked: boolean
  skipped_early: boolean
  metadata: Record<string, unknown>
}

const SHORTS_VIEWER_ID_STORAGE_KEY = 'draftr:viewer-id'
const INSIGHTS_OPEN_STORAGE_KEY = 'draftr:shorts-insights-open'
const INSIGHTS_WIDTH_STORAGE_KEY = 'draftr:shorts-insights-width'

// ─── Page root ───────────────────────────────────────────────────────────────

export default function ShortsPage() {
  return (
    <Suspense fallback={<ShortsPageFallback />}>
      <ShortsPageContent />
    </Suspense>
  )
}

function ShortsPageFallback() {
  return (
    <ShortsShell
      chats={[]} selectedChat={null} selectedChatId={null}
      recommendation={null}
      shorts={[]} libraryState="loading" shortsState="idle"
      error={null} onSelectChat={() => {}}
      libraryLabel="General library"
      isAuthenticated={false}
      authError={false}
      sessionScopeId={null}
      onRetentionUpdate={() => {}}
    />
  )
}

// ─── Data-fetching layer ──────────────────────────────────────────────────────

function ShortsPageContent() {
  const auth = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const requestedChatId = searchParams.get('chat')
  const authError = searchParams.get('auth') === 'error'
  const buildScopedShortsPath = (chatId: string) =>
    authError ? `${buildChatShortsPath(chatId)}&auth=error` : buildChatShortsPath(chatId)

  const [chats, setChats] = useState<ChatSummary[]>([])
  const [selectedChatId, setSelectedChatId] = useState<string | null>(requestedChatId)
  const [selectedChat, setSelectedChat] = useState<ChatSummary | null>(null)
  const [shorts, setShorts] = useState<GeneratedShort[]>([])
  const [recommendation, setRecommendation] = useState<ChatRecommendationResponse | null>(null)
  const [recommendationSession, setRecommendationSession] = useState<{ chatId: string; id: string } | null>(null)
  const [recommendationVersion, setRecommendationVersion] = useState(0)
  const [libraryState, setLibraryState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [shortsState, setShortsState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const origins = Array.from(
      new Set(
        [
          selectedChat?.cover_output_url ?? null,
          ...shorts.slice(0, 2).map(short => short.videoUrl),
        ]
          .filter((value): value is string => Boolean(value && value.startsWith('http')))
          .map(value => {
            try {
              return new URL(value).origin
            } catch {
              return null
            }
          })
          .filter((value): value is string => Boolean(value)),
      ),
    )

    const createdLinks = origins.flatMap(origin => {
      const preconnect = document.createElement('link')
      preconnect.rel = 'preconnect'
      preconnect.href = origin
      preconnect.crossOrigin = 'anonymous'
      document.head.appendChild(preconnect)

      const dnsPrefetch = document.createElement('link')
      dnsPrefetch.rel = 'dns-prefetch'
      dnsPrefetch.href = origin
      document.head.appendChild(dnsPrefetch)

      return [preconnect, dnsPrefetch]
    })

    return () => {
      createdLinks.forEach(link => link.remove())
    }
  }, [selectedChat?.cover_output_url, shorts])

  useEffect(() => { setSelectedChatId(requestedChatId) }, [requestedChatId])

  useEffect(() => {
    const ac = new AbortController()
    async function loadChats() {
      setLibraryState('loading')
      try {
        const res = await fetch('/api/brainrot/chats', { cache: 'no-store', signal: ac.signal })
        const data = (await res.json()) as ChatListResponse & { detail?: string }
        if (!res.ok) throw new Error(data.detail ?? 'Failed to load chats.')
        if (!ac.signal.aborted) { setChats(data.items); setLibraryState('ready') }
      } catch (err) {
        if (ac.signal.aborted) return
        setLibraryState('error')
        setError(err instanceof Error ? err.message : 'Failed to load chat library.')
      }
    }
    void loadChats()
    return () => ac.abort()
  }, [auth.scopeKey])

  useEffect(() => {
    setSelectedChatId(requestedChatId)
    setSelectedChat(null)
    setShorts([])
    setRecommendation(null)
  }, [auth.scopeKey, requestedChatId])

  useEffect(() => {
    if (libraryState === 'loading') return
    const fallback = chats[0]?.id ?? null
    const next = requestedChatId || fallback
    if (!next) { setSelectedChatId(null); setSelectedChat(null); setShorts([]); setRecommendation(null); return }
    if (next !== selectedChatId) setSelectedChatId(next)
    if (!requestedChatId && fallback) router.replace(buildScopedShortsPath(fallback), { scroll: false })
  }, [authError, chats, libraryState, requestedChatId, router, selectedChatId])

  useEffect(() => {
    if (!selectedChatId) {
      setRecommendationSession(null)
      setSelectedChat(null)
      setShorts([])
      setRecommendation(null)
      setShortsState('idle')
      return
    }
    setRecommendationSession({ chatId: selectedChatId, id: crypto.randomUUID() })
    setRecommendationVersion(0)
  }, [selectedChatId])

  useEffect(() => {
    if (!selectedChatId) { setSelectedChat(null); setShorts([]); setShortsState('idle'); return }
    const id = selectedChatId
    const ac = new AbortController()
    async function load() {
      setShortsState('loading')
      try {
        const [cr, sr] = await Promise.all([
          fetch(`/api/brainrot/chats/${encodeURIComponent(id)}`, { cache: 'no-store', signal: ac.signal }),
          fetch(`/api/brainrot/chats/${encodeURIComponent(id)}/shorts`, { cache: 'no-store', signal: ac.signal }),
        ])
        const cd = (await cr.json()) as ChatEnvelope & { detail?: string }
        const sd = (await sr.json()) as ChatGeneratedAssetsResponse & { detail?: string }
        if (!cr.ok) throw new Error(cd.detail ?? 'Failed to load chat.')
        if (!sr.ok) throw new Error(sd.detail ?? 'Failed to load shorts.')
        let items = sd.items.map(mapAssetToShort)
        if (items.length === 0) items = loadChatShorts(id).map(mapStoredToShort)
        if (!ac.signal.aborted) {
          setSelectedChat(cd.chat); setShorts(items); setShortsState('ready')
          setError(null); setChats(prev => upsertChat(prev, cd.chat))
        }
      } catch (err) {
        if (ac.signal.aborted) return
        setShorts(loadChatShorts(id).map(mapStoredToShort))
        setRecommendation(null)
        setShortsState('error')
        setError(err instanceof Error ? err.message : 'Failed to load shorts.')
      }
    }
    void load()
    return () => ac.abort()
  }, [selectedChatId])

  useEffect(() => {
    if (!selectedChatId || !recommendationSession || recommendationSession.chatId !== selectedChatId) {
      setRecommendation(null)
      return
    }

    const chatId = selectedChatId
    const sessionScopeId = recommendationSession.id
    const ac = new AbortController()
    async function loadRecommendation() {
      try {
        const url = `/api/brainrot/chats/${encodeURIComponent(chatId)}/recommendations?session_id=${encodeURIComponent(sessionScopeId)}`
        const response = await fetch(url, { cache: 'no-store', signal: ac.signal })
        const payload = (await response.json()) as ChatRecommendationResponse & { detail?: string }
        if (!response.ok) throw new Error(payload.detail ?? 'Failed to load recommendations.')
        if (!ac.signal.aborted) {
          setRecommendation(payload)
        }
      } catch (err) {
        if (ac.signal.aborted) return
        setRecommendation(null)
        setError(err instanceof Error ? err.message : 'Failed to load recommendations.')
      }
    }

    void loadRecommendation()
    return () => ac.abort()
  }, [selectedChatId, recommendationSession, recommendationVersion])

  return (
    <ShortsShell
      libraryLabel={auth.libraryLabel}
      isAuthenticated={auth.isAuthenticated}
      authError={authError}
      chats={chats} selectedChat={selectedChat} selectedChatId={selectedChatId}
      recommendation={recommendation}
      shorts={shorts} libraryState={libraryState} shortsState={shortsState}
      error={error} onSelectChat={(id) => { setSelectedChatId(id); router.replace(buildScopedShortsPath(id), { scroll: false }) }}
      sessionScopeId={recommendationSession?.chatId === selectedChatId ? recommendationSession.id : null}
      onRetentionUpdate={() => setRecommendationVersion(value => value + 1)}
    />
  )
}

// ─── Shell layout ─────────────────────────────────────────────────────────────

function ShortsShell({
  libraryLabel,
  isAuthenticated,
  authError,
  chats, selectedChat, selectedChatId, recommendation, shorts,
  libraryState, shortsState, error, onSelectChat, sessionScopeId, onRetentionUpdate,
}: {
  libraryLabel: string
  isAuthenticated: boolean
  authError: boolean
  chats: ChatSummary[]
  selectedChat: ChatSummary | null
  selectedChatId: string | null
  recommendation: ChatRecommendationResponse | null
  shorts: GeneratedShort[]
  libraryState: 'loading' | 'ready' | 'error'
  shortsState: 'idle' | 'loading' | 'ready' | 'error'
  error: string | null
  onSelectChat: (id: string) => void
  sessionScopeId: string | null
  onRetentionUpdate: () => void
}) {
  const exportSummary = selectedChat ? formatExportSummary(selectedChat) : null
  const updatedTime   = selectedChat ? formatRelTime(selectedChat.updated_at) : null
  const hasFeed = Boolean(selectedChat && shorts.length > 0)
  const isSwitchingChat = Boolean(selectedChat && shorts.length > 0 && shortsState === 'loading')
  const [insightsOpen, setInsightsOpen] = useState(true)
  const [insightsWidth, setInsightsWidth] = useState(380)
  const [isResizing, setIsResizing] = useState(false)
  const resizeStateRef = useRef<{ startX: number; startWidth: number } | null>(null)
  const showRecommendationRail = Boolean(selectedChat && recommendation && insightsOpen)
  const canRenderRecommendation = Boolean(selectedChat && recommendation)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const storedOpen = window.localStorage.getItem(INSIGHTS_OPEN_STORAGE_KEY)
    const storedWidth = window.localStorage.getItem(INSIGHTS_WIDTH_STORAGE_KEY)
    const nextInsightsOpen = storedOpen != null ? storedOpen !== '0' : null
    const nextInsightsWidth = (() => {
      if (storedWidth == null) return null
      const parsed = Number(storedWidth)
      return Number.isFinite(parsed) ? clampInsightsWidth(parsed) : null
    })()

    const frame = window.requestAnimationFrame(() => {
      if (nextInsightsOpen != null) {
        setInsightsOpen(nextInsightsOpen)
      }
      if (nextInsightsWidth != null) {
        setInsightsWidth(nextInsightsWidth)
      }
    })

    return () => {
      window.cancelAnimationFrame(frame)
    }
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(INSIGHTS_OPEN_STORAGE_KEY, insightsOpen ? '1' : '0')
  }, [insightsOpen])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(INSIGHTS_WIDTH_STORAGE_KEY, String(insightsWidth))
  }, [insightsWidth])

  useEffect(() => {
    if (!isResizing) return

    function handlePointerMove(event: PointerEvent) {
      const state = resizeStateRef.current
      if (!state) return
      const delta = state.startX - event.clientX
      setInsightsWidth(clampInsightsWidth(state.startWidth + delta))
    }

    function handlePointerUp() {
      resizeStateRef.current = null
      setIsResizing(false)
    }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
    }
  }, [isResizing])

  const stageGridStyle = useMemo(
    () => ({
      ['--insights-width' as string]: `${insightsWidth}px`,
    }),
    [insightsWidth],
  )

  function startResize(event: React.PointerEvent<HTMLButtonElement>) {
    resizeStateRef.current = { startX: event.clientX, startWidth: insightsWidth }
    setIsResizing(true)
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  return (
    <div className={`${styles.root} ${isResizing ? styles.rootResizing : ''}`}>
      <Navbar />

      <div className={styles.libraryLayout}>
        {/* ── Sidebar ── */}
        <aside className={styles.sidebar}>
          <div className={styles.sidebarHeader}>
            <p className={styles.sidebarEyebrow}>{libraryLabel}</p>
            <h1 className={styles.sidebarTitle}>{isAuthenticated ? 'Your shorts' : 'General shorts'}</h1>
            {authError ? (
              <p className={styles.sidebarStateCopy}>
                Google sign-in is not enabled on this Supabase project yet. Add the Google provider credentials in Supabase Auth and try again.
              </p>
            ) : null}
          </div>

          <div className={styles.chatList}>
            {libraryState === 'loading' && <div className={styles.sidebarStateCard}>Loading…</div>}

            {libraryState === 'error' && chats.length === 0 && (
              <div className={styles.sidebarStateCard}>
                <p className={styles.sidebarStateTitle}>Library unavailable</p>
                <p className={styles.sidebarStateCopy}>{error ?? 'Try again in a moment.'}</p>
              </div>
            )}

            {libraryState === 'ready' && chats.length === 0 && (
              <div className={styles.sidebarStateCard}>
                <p className={styles.sidebarStateTitle}>No shorts yet.</p>
                <p className={styles.sidebarStateCopy}>
                  {isAuthenticated
                    ? 'Generate your first account-owned video in chat.'
                    : 'Generate a video in guest mode to add it to the general library.'}
                </p>
                <Link href="/chat" className={styles.sidebarStateLink}>Open chat →</Link>
              </div>
            )}

            {chats.map(chat => (
              <button
                key={chat.id}
                type="button"
                className={`${styles.chatListItem} ${chat.id === selectedChatId ? styles.chatListItemActive : ''}`}
                onClick={() => onSelectChat(chat.id)}
              >
                <ChatListCover chat={chat} />
                <div className={styles.chatListBody}>
                  <p className={styles.chatListTitle}>{chat.title}</p>
                  <p className={styles.chatListSource}>{chat.last_source_label ?? chat.last_source_url ?? 'Untitled source'}</p>
                  <div className={styles.chatListStats}>
                    <span>{formatExportSummary(chat)}</span>
                    <span>{chat.total_runs} run{chat.total_runs === 1 ? '' : 's'}</span>
                    <span className={styles.chatListTime}>{formatRelTime(chat.updated_at)}</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </aside>

        {/* ── Main ── */}
        <main className={styles.main}>
          {/* Push content below the fixed navbar */}
          <div className={styles.mainNavSpacer} />
          {/* Slim context bar */}
          <div className={styles.chatBar}>
            <div className={styles.chatBarSpacer} />
            <div className={styles.chatBarCenter}>
              <h2 className={styles.chatBarTitle}>{selectedChat?.title ?? 'Select a chat'}</h2>
            </div>
            {selectedChat && exportSummary ? (
              <div className={styles.chatBarRight}>
                <span className={styles.chatBarBadge}>{exportSummary}</span>
                {updatedTime && <span className={styles.chatBarTime}>{updatedTime}</span>}
              </div>
            ) : <div className={styles.chatBarSpacer} />}
          </div>

          {/* Feed canvas */}
          <div className={styles.mainCanvas}>
            {hasFeed ? (
              <div
                className={`${styles.stageGrid} ${showRecommendationRail ? styles.stageGridWithRail : ''}`}
                style={showRecommendationRail ? stageGridStyle : undefined}
              >
                <div className={styles.feedColumn}>
                  <div
                    key={selectedChat?.id ?? selectedChatId ?? 'shorts-feed'}
                    className={`${styles.feedViewport} ${isSwitchingChat ? styles.feedViewportSwitching : styles.feedViewportReady}`}
                  >
                    <ShortsFeed
                      key={`${selectedChat?.id ?? selectedChatId ?? 'shorts-feed'}:${shorts.length}`}
                      chatId={selectedChat?.id ?? selectedChatId ?? ''}
                      shorts={shorts}
                      sessionScopeId={sessionScopeId}
                      onRetentionUpdate={onRetentionUpdate}
                    />
                  </div>
                </div>

                {showRecommendationRail && selectedChat && recommendation ? (
                  <>
                    <button
                      type="button"
                      className={styles.recommendationRailHandle}
                      aria-label="Resize recommendation sidebar"
                      aria-orientation="vertical"
                      onPointerDown={startResize}
                    >
                      <span />
                    </button>

                    <aside className={styles.recommendationRail}>
                      <div className={styles.recommendationRailHeader}>
                        <div>
                          <p className={styles.recommendationRailEyebrow}>Insights</p>
                          <h3 className={styles.recommendationRailTitle}>Recommendation system</h3>
                        </div>
                        <button
                          type="button"
                          className={styles.recommendationRailToggle}
                          onClick={() => setInsightsOpen(false)}
                        >
                          Hide
                        </button>
                      </div>

                      <RecommendationCard chatId={selectedChat.id} recommendation={recommendation} />
                    </aside>
                  </>
                ) : null}
              </div>
            ) : null}

            {!showRecommendationRail && canRenderRecommendation ? (
              <button
                type="button"
                className={styles.recommendationDockButton}
                onClick={() => setInsightsOpen(true)}
              >
                <span className={styles.recommendationDockEyebrow}>Insights</span>
                <span className={styles.recommendationDockTitle}>Open recommendation sidebar</span>
              </button>
            ) : null}

            {isSwitchingChat ? (
              <div className={styles.canvasLoadingOverlay} aria-hidden>
                <div className={styles.canvasLoadingSpinner} />
                <p className={styles.canvasLoadingLabel}>Loading this chat’s shorts…</p>
              </div>
            ) : null}

            {selectedChat && shorts.length === 0 && shortsState === 'ready' ? (
              <div className={styles.emptyState}>
                <div className={styles.emptyIcon}>🎬</div>
                <p className={styles.emptyTitle}>No videos yet</p>
                <p className={styles.emptyCopy}>This chat has not exported any shorts yet. Start a run to generate videos.</p>
                <Link href="/chat" className={styles.emptyLink}>Go to chat →</Link>
              </div>
            ) : null}

            {!selectedChat && libraryState === 'ready' && !error ? (
              <div className={styles.emptyState}>
                <div className={styles.emptyIcon}>👈</div>
                <p className={styles.emptyTitle}>Pick a chat</p>
                <p className={styles.emptyCopy}>Select a chat from the sidebar to watch its exported shorts.</p>
              </div>
            ) : null}

            {(libraryState === 'loading' || (shortsState === 'loading' && !hasFeed)) ? (
              <div className={styles.emptyState}>
                <div className={styles.loadingSpinner} />
                <p className={styles.emptyTitle}>Loading…</p>
              </div>
            ) : null}

            {error && shortsState === 'error' ? (
              <div className={styles.emptyState}>
                <div className={styles.emptyIcon}>⚠️</div>
                <p className={styles.emptyTitle}>Something went wrong</p>
                <p className={styles.emptyCopy}>{error}</p>
              </div>
            ) : null}
          </div>
        </main>
      </div>
    </div>
  )
}

function RecommendationCard({
  chatId,
  recommendation,
}: {
  chatId: string
  recommendation: ChatRecommendationResponse
}) {
  const topGameplay = recommendation.top_gameplay[0]?.label ?? 'mixed gameplay'
  const topCaptions = recommendation.top_caption_styles[0]?.label ?? 'the current caption mix'
  const topTextStyle = recommendation.top_text_styles[0]?.label ?? 'the current hooks'
  const reelsRemaining = Math.max(0, recommendation.min_reels_required - recommendation.reels_tracked)
  const prompt = recommendation.generation_prompt
  const chatHref = prompt
    ? `/chat?chat=${encodeURIComponent(chatId)}&prefill=${encodeURIComponent(prompt)}`
    : `/chat?chat=${encodeURIComponent(chatId)}`
  const compactCopy = recommendation.has_enough_data
    ? `This session is leaning toward ${topGameplay} gameplay, ${topCaptions} captions, and ${topTextStyle} hooks.`
    : `This session has ${recommendation.reels_tracked} tracked reel${recommendation.reels_tracked === 1 ? '' : 's'}. Watch ${reelsRemaining} more to unlock a stronger recommendation.`

  return (
    <section className={styles.recommendationCard}>
      <div className={styles.recommendationHeader}>
        <p className={styles.recommendationKicker}>
          {recommendation.has_enough_data ? 'Best signal right now' : 'Retention is warming up'}
        </p>
        <h3 className={styles.recommendationTitle}>
          {recommendation.recommendation_title ?? 'Retention insights are warming up'}
        </h3>
        <p className={styles.recommendationCopy}>{compactCopy}</p>
      </div>

      <div className={styles.recommendationStats}>
        <div className={styles.recommendationStat}>
          <span className={styles.recommendationStatValue}>{recommendation.reels_tracked}</span>
          <span className={styles.recommendationStatLabel}>reels tracked</span>
        </div>
        <div className={styles.recommendationStat}>
          <span className={styles.recommendationStatValue}>{formatSeconds(recommendation.total_watch_time_seconds)}</span>
          <span className={styles.recommendationStatLabel}>watched</span>
        </div>
        <div className={styles.recommendationStat}>
          <span className={styles.recommendationStatValue}>{recommendation.high_retention_sessions}</span>
          <span className={styles.recommendationStatLabel}>high-retention</span>
        </div>
      </div>

      <div className={styles.recommendationSignals}>
        <SignalRow label="Gameplay" value={topGameplay} />
        <SignalRow label="Captions" value={topCaptions} />
        <SignalRow label="Text style" value={topTextStyle} />
      </div>

      <div className={styles.retentionSummaryBlock}>
        <div className={styles.retentionSummaryHeader}>
          <p className={styles.retentionSummaryTitle}>Current session retention summary</p>
          <p className={styles.retentionSummaryCopy}>
            {recommendation.has_enough_data
              ? 'Session-level retention by reel.'
              : `Watch at least ${recommendation.min_reels_required} reels in one session to unlock a recommendation.`}
          </p>
        </div>

        {recommendation.retention_summary.length > 0 ? (
          <div className={styles.retentionSummaryList}>
            {recommendation.retention_summary.map(summary => (
              <div key={summary.item_id} className={styles.retentionSummaryRow}>
                <div className={styles.retentionSummaryRowTop}>
                  <span className={styles.retentionSummaryIndex}>Reel {summary.reel_number}</span>
                  <span className={styles.retentionSummaryMetric}>{Math.round(summary.completion_ratio * 100)}%</span>
                </div>
                <div className={styles.retentionSummaryMeta}>
                  <p className={styles.retentionSummaryRowTitle}>{summary.title}</p>
                  <p className={styles.retentionSummaryRowCopy}>
                    Watched {formatSeconds(summary.watch_time_seconds)}
                    {summary.estimated_seconds ? ` of ${formatSeconds(summary.estimated_seconds)}` : ''}
                    {' '}• peak {formatSeconds(summary.max_progress_seconds)}
                  </p>
                </div>
                <div className={styles.retentionSummaryTags}>
                  {summary.gameplay_label ? <span>{summary.gameplay_label}</span> : null}
                  {summary.subtitle_style ? <span>{summary.subtitle_style}</span> : null}
                  {summary.subtitle_font ? <span>{summary.subtitle_font}</span> : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.retentionSummaryEmpty}>
            Start watching reels in this chat and Draftr will show exactly how many seconds each one held attention.
          </div>
        )}
      </div>

      <div className={styles.recommendationFooter}>
        <p className={styles.recommendationFootnote}>
          Based only on this current viewing session, using watch time, completion, replays, likes, info opens, and open actions.
        </p>
        {prompt ? (
          <Link href={chatHref} className={styles.recommendationLink}>
            Generate more like this
          </Link>
        ) : null}
      </div>
    </section>
  )
}

function SignalRow({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.recommendationSignal}>
      <span className={styles.recommendationSignalLabel}>{label}</span>
      <strong className={styles.recommendationSignalValue}>{value}</strong>
    </div>
  )
}

// ─── Shorts feed — owns all scroll/play logic ────────────────────────────────

function ShortsFeed({
  chatId,
  shorts,
  sessionScopeId,
  onRetentionUpdate,
}: {
  chatId: string
  shorts: GeneratedShort[]
  sessionScopeId: string | null
  onRetentionUpdate: () => void
}) {
  const [activeIndex, setActiveIndex] = useState(0)
  // Shared mute state across all slides — once user unmutes, all subsequent slides stay unmuted
  const [globalMuted, setGlobalMuted] = useState(false)
  const [viewerId] = useState(() => getOrCreateViewerId())
  const lockedRef = useRef(false)
  const touchStartRef = useRef(0)

  useEffect(() => {
    lockedRef.current = false
  }, [chatId, shorts.length])

  function go(direction: 1 | -1) {
    if (lockedRef.current) return
    setActiveIndex(previous => {
      const next = Math.max(0, Math.min(shorts.length - 1, previous + direction))
      if (next === previous) return previous
      lockedRef.current = true
      window.setTimeout(() => {
        lockedRef.current = false
      }, 720)
      return next
    })
  }

  function handleWheel(event: React.WheelEvent<HTMLDivElement>) {
    event.preventDefault()
    go(event.deltaY > 0 ? 1 : -1)
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowRight') {
      event.preventDefault()
      go(1)
    }
    if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') {
      event.preventDefault()
      go(-1)
    }
  }

  function handleTouchStart(event: React.TouchEvent<HTMLDivElement>) {
    touchStartRef.current = event.touches[0]?.clientY ?? 0
  }

  function handleTouchEnd(event: React.TouchEvent<HTMLDivElement>) {
    const delta = touchStartRef.current - (event.changedTouches[0]?.clientY ?? 0)
    if (Math.abs(delta) > 40) {
      go(delta > 0 ? 1 : -1)
    }
  }

  return (
    <div
      className={styles.feed}
      onWheel={handleWheel}
      onKeyDown={handleKeyDown}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      tabIndex={0}
    >
      {shorts.map((short, index) => (
        <div
          key={short.id}
          className={`${styles.slide} ${index === activeIndex ? styles.slideActive : styles.slideInactive}`}
          style={{ transform: `translateY(${(index - activeIndex) * 100}%)` }}
          data-idx={index}
        >
          <ShortSlide
            chatId={chatId}
            short={short}
            index={index}
            total={shorts.length}
            isActive={index === activeIndex}
            shouldPrime={Math.abs(index - activeIndex) <= 1}
            viewerId={viewerId}
            globalMuted={globalMuted}
            onMuteChange={setGlobalMuted}
            sessionScopeId={sessionScopeId}
            onRetentionUpdate={onRetentionUpdate}
          />
        </div>
      ))}
    </div>
  )
}

// ─── Individual short card ────────────────────────────────────────────────────

function ShortSlide({
  chatId, short, index, total, isActive, shouldPrime, viewerId, globalMuted, onMuteChange,
  sessionScopeId, onRetentionUpdate,
}: {
  chatId: string
  short: GeneratedShort
  index: number
  total: number
  isActive: boolean
  shouldPrime: boolean
  viewerId: string
  globalMuted: boolean
  onMuteChange: (muted: boolean) => void
  sessionScopeId: string | null
  onRetentionUpdate: () => void
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [isPaused, setIsPaused] = useState(false)
  const [isBuffering, setIsBuffering] = useState(true)
  const [hasLoadedFrame, setHasLoadedFrame] = useState(false)
  const [animateIn, setAnimateIn] = useState(false)
  const [showInfo, setShowInfo] = useState(false)
  const [isLiked, setIsLiked] = useState(false)

  const sessionIdRef = useRef<string | null>(null)
  const playStartedAtRef = useRef<number | null>(null)
  const watchTimeRef = useRef(0)
  const maxProgressRef = useRef(0)
  const replayCountRef = useRef(0)
  const heardAudioRef = useRef(false)
  const infoOpenedRef = useRef(false)
  const openClickedRef = useRef(false)
  const likedRef = useRef(false)
  const submittedRef = useRef(false)

  useEffect(() => {
    setIsBuffering(shouldPrime)
    setHasLoadedFrame(false)
    setIsLiked(false)
  }, [short.videoUrl, shouldPrime])

  // Replay entrance animations each time this slide becomes active
  useEffect(() => {
    if (isActive) {
      setAnimateIn(false)
      const raf = requestAnimationFrame(() => requestAnimationFrame(() => setAnimateIn(true)))
      return () => cancelAnimationFrame(raf)
    } else {
      setAnimateIn(false)
    }
  }, [isActive])

  // Remove the muted HTML attribute so browsers don't treat it as a muted-autoplay request
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    v.removeAttribute('muted')
    v.muted = globalMuted
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const v = videoRef.current
    if (!v || !shouldPrime) return
    v.preload = isActive ? 'auto' : 'metadata'
    if (v.readyState === 0) {
      v.load()
    }
  }, [isActive, shouldPrime, short.videoUrl])

  // Sync video mute state whenever globalMuted changes
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    v.muted = globalMuted
  }, [globalMuted])

  function startSession() {
    sessionIdRef.current = crypto.randomUUID()
    playStartedAtRef.current = null
    watchTimeRef.current = 0
    maxProgressRef.current = 0
    replayCountRef.current = 0
    heardAudioRef.current = false
    infoOpenedRef.current = false
    openClickedRef.current = false
    likedRef.current = false
    submittedRef.current = false
  }

  function accumulateWatchTime() {
    if (playStartedAtRef.current == null) {
      return
    }
    watchTimeRef.current += Math.max(0, (performance.now() - playStartedAtRef.current) / 1000)
    playStartedAtRef.current = null
  }

  function buildEngagementPayload(): ShortEngagementPayload | null {
    const sessionId = sessionIdRef.current
    if (!sessionId) {
      return null
    }

    const duration = Number.isFinite(videoRef.current?.duration) && (videoRef.current?.duration ?? 0) > 0
      ? Number(videoRef.current?.duration)
      : short.estimatedSeconds ?? Math.max(maxProgressRef.current, 1)
    const watchTimeSeconds = Number(watchTimeRef.current.toFixed(3))
    const maxProgressSeconds = Number(maxProgressRef.current.toFixed(3))
    const completionRatio = Number((Math.max(maxProgressSeconds, watchTimeSeconds) / Math.max(duration, 1)).toFixed(4))
    const skippedEarly =
      watchTimeSeconds < Math.min(3.0, duration * 0.18) &&
      completionRatio < 0.2 &&
      !infoOpenedRef.current &&
      !openClickedRef.current &&
      !likedRef.current

    if (watchTimeSeconds < 0.35 && !infoOpenedRef.current && !openClickedRef.current && !likedRef.current) {
      return null
    }

    return {
      batch_id: short.batchId,
      item_id: short.itemId,
      viewer_id: viewerId,
      session_id: sessionId,
      watch_time_seconds: watchTimeSeconds,
      completion_ratio: completionRatio,
      max_progress_seconds: maxProgressSeconds,
      replay_count: replayCountRef.current,
      unmuted: heardAudioRef.current,
      info_opened: infoOpenedRef.current,
      open_clicked: openClickedRef.current,
      liked: likedRef.current,
      skipped_early: skippedEarly,
      metadata: {
        page_session_id: sessionScopeId,
        subtitle_style: short.subtitleStyle,
        subtitle_font: short.subtitleFont,
        gameplay_asset: short.gameplayAsset,
      },
    }
  }

  function flushSession(useBeacon = false) {
    if (submittedRef.current) {
      return
    }
    accumulateWatchTime()
    const payload = buildEngagementPayload()
    if (!payload) {
      submittedRef.current = true
      return
    }
    submittedRef.current = true
    void submitShortEngagement(chatId, payload, useBeacon).then(recorded => {
      if (recorded && !useBeacon) {
        onRetentionUpdate()
      }
    })
  }

  useEffect(() => {
    if (!isActive) {
      return
    }
    startSession()
    return () => {
      flushSession(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive, short.id])

  useEffect(() => {
    const handlePageHide = () => {
      flushSession(true)
    }
    window.addEventListener('pagehide', handlePageHide)
    return () => window.removeEventListener('pagehide', handlePageHide)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatId, short.id, viewerId])

  // Play/pause + restart when this card becomes active
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    if (isActive) {
      v.currentTime = 0
      v.muted = globalMuted
      // Try play; if browser blocks unmuted, fall back to muted but keep globalMuted in sync
      v.play().catch(() => {
        v.muted = true
        onMuteChange(true)
        v.play().catch(() => {})
      })
      setIsPaused(false)
    } else {
      v.pause()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive])

  function handleCardClick() {
    const v = videoRef.current
    if (!v) return
    if (v.paused) { v.play().catch(() => {}); setIsPaused(false) }
    else          { v.pause(); setIsPaused(true); accumulateWatchTime() }
  }

  function toggleMute(e: React.MouseEvent) {
    e.stopPropagation()
    const v = videoRef.current
    if (!v) return
    const next = !v.muted
    v.muted = next
    onMuteChange(next)
    if (!next) {
      heardAudioRef.current = true
    }
  }

  function toggleLike(e: React.MouseEvent) {
    e.stopPropagation()
    setIsLiked(previous => {
      const next = !previous
      likedRef.current = next
      return next
    })
  }

  function toggleInfo(e: React.MouseEvent) {
    e.stopPropagation()
    setShowInfo(previous => {
      const next = !previous
      if (next) {
        infoOpenedRef.current = true
      }
      return next
    })
  }

  function handleOpenClick() {
    openClickedRef.current = true
    flushSession(false)
  }

  return (
    <div className={styles.shortRow}>
      {/* ── 9:16 video card ── */}
      <article className={`${styles.shortCard} ${isActive ? styles.shortCardActive : ''}`} onClick={handleCardClick}>
        <video
          ref={videoRef}
          className={`${styles.shortVideo} ${hasLoadedFrame ? styles.shortVideoReady : ''}`}
          src={shouldPrime ? short.videoUrl : undefined}
          poster={short.thumbnailUrl ?? undefined}
          playsInline
          loop
          preload={shouldPrime ? (isActive ? 'auto' : 'metadata') : 'none'}
          onLoadStart={() => setIsBuffering(true)}
          onLoadedData={() => {
            setHasLoadedFrame(true)
            setIsBuffering(false)
          }}
          onCanPlay={() => {
            setHasLoadedFrame(true)
            setIsBuffering(false)
          }}
          onPlaying={() => {
            setHasLoadedFrame(true)
            setIsBuffering(false)
            if (playStartedAtRef.current == null) {
              playStartedAtRef.current = performance.now()
            }
          }}
          onWaiting={() => {
            accumulateWatchTime()
            if (isActive) setIsBuffering(true)
          }}
          onPause={() => accumulateWatchTime()}
          onTimeUpdate={() => {
            const currentTime = videoRef.current?.currentTime ?? 0
            maxProgressRef.current = Math.max(maxProgressRef.current, currentTime)
          }}
          onEnded={() => {
            replayCountRef.current += 1
            accumulateWatchTime()
          }}
        />

        {(!hasLoadedFrame || isBuffering) && (
          <div className={styles.shortLoadingOverlay} aria-hidden>
            <div className={styles.shortLoadingPulse} />
            <div className={styles.shortLoadingSpinner} />
            <p className={styles.shortLoadingLabel}>
              {hasLoadedFrame ? 'Buffering short…' : 'Loading short…'}
            </p>
          </div>
        )}

        {/* dark-to-transparent gradient at bottom */}
        <div className={styles.shortGradient} />

        {/* Play icon flash when paused */}
        {isPaused && (
          <div className={styles.shortPauseOverlay} aria-hidden>
            <svg width="52" height="52" viewBox="0 0 24 24" fill="white">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
          </div>
        )}

        {/* Top-right: counter + mute button */}
        <div className={`${styles.shortTopControls} ${animateIn ? styles.shortTopControlsAnimate : ''}`}>
          <span className={styles.shortCounter}>{index + 1} / {total}</span>
          <button
            type="button"
            className={styles.shortMuteBtn}
            onClick={toggleMute}
            aria-label={globalMuted ? 'Unmute' : 'Mute'}
          >
            {globalMuted ? (
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                <line x1="23" y1="9" x2="17" y2="15" /><line x1="17" y1="9" x2="23" y2="15" />
              </svg>
            ) : (
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
              </svg>
            )}
          </button>
        </div>

        {/* Info panel */}
        {showInfo && (
          <div className={styles.shortInfoPanel} onClick={e => e.stopPropagation()}>
            <div className={styles.shortInfoPanelHeader}>
              <span className={styles.shortInfoPanelTitle}>About this short</span>
              <button type="button" className={styles.shortInfoPanelClose} onClick={() => setShowInfo(false)}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div className={styles.shortInfoPanelRows}>
              <InfoRow label="Title" value={short.title} />
              {short.source && <InfoRow label="Source label" value={short.source} />}
              {short.sourceUrl && short.sourceUrl !== '#' && (
                <InfoRow label="Source URL" value={short.sourceUrl} href={short.sourceUrl} />
              )}
              {short.estimatedSeconds != null && (
                <InfoRow label="Duration" value={`~${Math.round(short.estimatedSeconds)}s`} />
              )}
              {short.subtitleStyle && (
                <InfoRow label="Subtitle style" value={short.subtitleStyle} />
              )}
              {short.subtitleFont && (
                <InfoRow label="Font" value={short.subtitleFont} />
              )}
              {short.gameplayAsset && (
                <InfoRow label="Gameplay" value={short.gameplayAsset.split('/').pop()?.replace(/[-_]/g, ' ') ?? short.gameplayAsset} />
              )}
              <InfoRow label="Generated" value={formatRelTime(short.updatedAt)} />
              <InfoRow label="Batch ID" value={short.batchId} mono />
              <InfoRow label="Item ID" value={short.itemId} mono />
            </div>
          </div>
        )}

        {/* Bottom info overlay */}
        <div className={`${styles.shortInfo} ${animateIn ? styles.shortInfoAnimate : ''}`}>
          <div className={styles.shortAuthorRow}>
            <div className={styles.shortAvatar}>D</div>
            <div className={styles.shortAuthorText}>
              <p className={styles.shortAuthorName}>Draftr AI</p>
              <p className={styles.shortAuthorSub}>{formatRelTime(short.updatedAt)}</p>
            </div>
          </div>
          <h3 className={styles.shortTitle}>{short.title}</h3>
        </div>
      </article>

      {/* ── Right action column ── */}
      <div className={`${styles.shortActions} ${animateIn ? styles.shortActionsAnimate : ''}`}>
        <button type="button" className={styles.shortActionBtn} aria-label="Like" onClick={toggleLike}>
          <div className={`${styles.shortActionIcon} ${isLiked ? styles.shortActionIconActive : ''}`}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
            </svg>
          </div>
          <span className={styles.shortActionLabel}>Like</span>
        </button>

        <a
          href={short.videoUrl}
          target="_blank"
          rel="noreferrer"
          className={styles.shortActionBtn}
          aria-label="Open"
          onClick={handleOpenClick}
        >
          <div className={styles.shortActionIcon}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </div>
          <span className={styles.shortActionLabel}>Open</span>
        </a>

        <button type="button" className={styles.shortActionBtn} aria-label="Info" onClick={toggleInfo}>
          <div className={`${styles.shortActionIcon} ${showInfo ? styles.shortActionIconActive : ''}`}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="8.5" strokeWidth="3" strokeLinecap="round" />
              <line x1="12" y1="12" x2="12" y2="17" />
            </svg>
          </div>
          <span className={styles.shortActionLabel}>Info</span>
        </button>
      </div>
    </div>
  )
}

function InfoRow({ label, value, href, mono }: { label: string; value: string; href?: string; mono?: boolean }) {
  return (
    <div className={styles.infoRow}>
      <span className={styles.infoRowLabel}>{label}</span>
      {href ? (
        <a href={href} target="_blank" rel="noreferrer" className={`${styles.infoRowValue} ${styles.infoRowLink}`}>{value}</a>
      ) : (
        <span className={`${styles.infoRowValue} ${mono ? styles.infoRowMono : ''}`}>{value}</span>
      )}
    </div>
  )
}

function ChatListCover({ chat }: { chat: ChatSummary }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const coverThumbnailUrl = chat.metadata?.cover_thumbnail_url ?? null
  const coverUrl = chat.cover_output_url && !chat.cover_output_url.startsWith('file://') ? chat.cover_output_url : null
  const [isReady, setIsReady] = useState(false)
  const [hasFailed, setHasFailed] = useState(false)

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      setIsReady(false)
      setHasFailed(false)
    })

    if (coverThumbnailUrl || !coverUrl) {
      return () => {
        window.cancelAnimationFrame(frame)
      }
    }

    const timeoutId = window.setTimeout(() => {
      setHasFailed(true)
    }, 4500)

    return () => {
      window.cancelAnimationFrame(frame)
      window.clearTimeout(timeoutId)
    }
  }, [coverThumbnailUrl, coverUrl])

  function primeCoverFrame() {
    const video = videoRef.current
    if (!video) {
      return
    }

    const targetTime = Number.isFinite(video.duration) && video.duration > 0
      ? Math.min(0.12, Math.max(video.duration * 0.02, 0.04))
      : 0.08

    try {
      video.currentTime = targetTime
    } catch {
      setIsReady(true)
    }
  }

  const shouldShowVideo = Boolean(!coverThumbnailUrl && coverUrl && !hasFailed)

  return (
    <div className={styles.chatListCover}>
      {coverThumbnailUrl ? (
        <img
          className={`${styles.chatListVideo} ${styles.chatListVideoReady}`}
          src={coverThumbnailUrl}
          alt=""
          loading="lazy"
        />
      ) : shouldShowVideo ? (
        <>
          <video
            key={coverUrl}
            ref={videoRef}
            className={`${styles.chatListVideo} ${isReady ? styles.chatListVideoReady : ''}`}
            src={coverUrl ?? undefined}
            muted
            loop
            autoPlay
            playsInline
            preload="metadata"
            onLoadedMetadata={primeCoverFrame}
            onSeeked={() => setIsReady(true)}
            onLoadedData={() => setIsReady(true)}
            onCanPlay={() => setIsReady(true)}
            onPlaying={() => setIsReady(true)}
            onError={() => {
              setHasFailed(true)
              setIsReady(false)
            }}
          />
          {!isReady ? <div className={styles.chatListCoverLoading} aria-hidden /> : null}
        </>
      ) : (
        <div className={styles.chatListFallback}>{chat.title.slice(0, 1).toUpperCase()}</div>
      )}
    </div>
  )
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function mapStoredToShort(s: StoredChatShort): GeneratedShort {
  return { id: `${s.batchId}-${s.itemId}`, title: s.title, source: s.sourceLabel, sourceUrl: s.sourceUrl ?? '#', batchId: s.batchId, itemId: s.itemId, videoUrl: s.previewUrl, thumbnailUrl: s.thumbnailUrl ?? null, updatedAt: s.createdAt, estimatedSeconds: null, subtitleStyle: null, subtitleFont: null, gameplayAsset: null }
}

function mapAssetToShort(a: ChatGeneratedAsset): GeneratedShort {
  const directVideoUrl =
    a.output_url && a.output_url.startsWith('http')
      ? a.output_url
      : `/api/brainrot/batches/${a.batch_id}/items/${a.item_id}/video`

  return {
    id: `${a.batch_id}-${a.item_id}`,
    title: a.script?.title ?? a.title_hint ?? `Video ${a.item_index + 1}`,
    source: a.title_hint ?? a.source_url ?? `Chat ${a.chat_id.slice(0, 8)}`,
    sourceUrl: a.source_url ?? '#',
    batchId: a.batch_id, itemId: a.item_id,
    videoUrl: directVideoUrl,
    thumbnailUrl: a.render_metadata?.thumbnail_url ?? null,
    updatedAt: a.updated_at,
    estimatedSeconds: a.script?.estimated_seconds ?? null,
    subtitleStyle: a.render_metadata?.subtitle_style_label ?? null,
    subtitleFont: a.render_metadata?.subtitle_font_name ?? null,
    gameplayAsset: a.render_metadata?.gameplay_asset_path ?? null,
  }
}

function upsertChat(chats: ChatSummary[], chat: ChatSummary): ChatSummary[] {
  return [chat, ...chats.filter(c => c.id !== chat.id)]
    .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
}

function formatExportSummary(chat: ChatSummary): string {
  const attempted = chat.total_exported + chat.total_failed
  if (attempted > 0) return `${chat.total_exported} / ${attempted} exported`
  if (chat.total_runs > 0) return `${chat.total_runs} queued`
  return 'No exports yet'
}

function formatRelTime(value: string): string {
  const diff = Date.now() - Date.parse(value)
  const m = Math.floor(diff / 60000)
  if (m < 1)  return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function formatSeconds(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return '0.0s'
  }
  return `${value.toFixed(1)}s`
}

function clampInsightsWidth(value: number): number {
  return Math.max(320, Math.min(520, Math.round(value)))
}

function getOrCreateViewerId(): string {
  if (typeof window === 'undefined') {
    return 'server-viewer'
  }

  const existing = window.localStorage.getItem(SHORTS_VIEWER_ID_STORAGE_KEY)
  if (existing) {
    return existing
  }

  const created = crypto.randomUUID()
  window.localStorage.setItem(SHORTS_VIEWER_ID_STORAGE_KEY, created)
  return created
}

async function submitShortEngagement(
  chatId: string,
  payload: ShortEngagementPayload,
  useBeacon: boolean,
): Promise<boolean> {
  const url = `/api/brainrot/chats/${encodeURIComponent(chatId)}/engagement`
  const body = JSON.stringify(payload)

  if (useBeacon && typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
    try {
      const beaconPayload = new Blob([body], { type: 'application/json' })
      if (navigator.sendBeacon(url, beaconPayload)) {
        return true
      }
    } catch {
      // Fall back to fetch below.
    }
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body,
      keepalive: useBeacon,
      cache: 'no-store',
    })
    return response.ok
  } catch {
    // Engagement capture is best-effort.
    return false
  }
}
