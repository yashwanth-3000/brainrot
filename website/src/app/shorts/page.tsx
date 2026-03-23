'use client'

import { Suspense, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import styles from './shorts-page.module.css'
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

type GeneratedShort = {
  id: string
  title: string
  source: string
  sourceUrl: string
  batchId: string
  itemId: string
  videoUrl: string
  updatedAt: string
}

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
      shorts={[]} libraryState="loading" shortsState="idle"
      error={null} onSelectChat={() => {}}
    />
  )
}

// ─── Data-fetching layer ──────────────────────────────────────────────────────

function ShortsPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const requestedChatId = searchParams.get('chat')

  const [chats, setChats] = useState<ChatSummary[]>([])
  const [selectedChatId, setSelectedChatId] = useState<string | null>(requestedChatId)
  const [selectedChat, setSelectedChat] = useState<ChatSummary | null>(null)
  const [shorts, setShorts] = useState<GeneratedShort[]>([])
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
  }, [])

  useEffect(() => {
    if (libraryState === 'loading') return
    const fallback = chats[0]?.id ?? null
    const next = requestedChatId || fallback
    if (!next) { setSelectedChatId(null); setSelectedChat(null); setShorts([]); return }
    if (next !== selectedChatId) setSelectedChatId(next)
    if (!requestedChatId && fallback) router.replace(buildChatShortsPath(fallback), { scroll: false })
  }, [chats, libraryState, requestedChatId, router, selectedChatId])

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
        setShortsState('error')
        setError(err instanceof Error ? err.message : 'Failed to load shorts.')
      }
    }
    void load()
    return () => ac.abort()
  }, [selectedChatId])

  return (
    <ShortsShell
      chats={chats} selectedChat={selectedChat} selectedChatId={selectedChatId}
      shorts={shorts} libraryState={libraryState} shortsState={shortsState}
      error={error} onSelectChat={(id) => { setSelectedChatId(id); router.replace(buildChatShortsPath(id), { scroll: false }) }}
    />
  )
}

// ─── Shell layout ─────────────────────────────────────────────────────────────

function ShortsShell({
  chats, selectedChat, selectedChatId, shorts,
  libraryState, shortsState, error, onSelectChat,
}: {
  chats: ChatSummary[]
  selectedChat: ChatSummary | null
  selectedChatId: string | null
  shorts: GeneratedShort[]
  libraryState: 'loading' | 'ready' | 'error'
  shortsState: 'idle' | 'loading' | 'ready' | 'error'
  error: string | null
  onSelectChat: (id: string) => void
}) {
  const exportSummary = selectedChat ? formatExportSummary(selectedChat) : null
  const updatedTime   = selectedChat ? formatRelTime(selectedChat.updated_at) : null
  const hasFeed = Boolean(selectedChat && shorts.length > 0)
  const isSwitchingChat = Boolean(selectedChat && shorts.length > 0 && shortsState === 'loading')

  return (
    <div className={styles.root}>
      <Navbar />

      <div className={styles.libraryLayout}>
        {/* ── Sidebar ── */}
        <aside className={styles.sidebar}>
          <div className={styles.sidebarHeader}>
            <p className={styles.sidebarEyebrow}>Library</p>
            <h1 className={styles.sidebarTitle}>Your shorts</h1>
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
                <p className={styles.sidebarStateCopy}>Generate your first video in chat.</p>
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
                  <div className={styles.chatListMeta}>
                    <p className={styles.chatListTitle}>{chat.title}</p>
                    <span className={styles.chatListTime}>{formatRelTime(chat.updated_at)}</span>
                  </div>
                  <p className={styles.chatListSource}>{chat.last_source_label ?? chat.last_source_url ?? 'Untitled source'}</p>
                  <div className={styles.chatListStats}>
                    <span>{formatExportSummary(chat)}</span>
                    <span>{chat.total_runs} run{chat.total_runs === 1 ? '' : 's'}</span>
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
            <div className={styles.chatBarLeft}>
              <h2 className={styles.chatBarTitle}>{selectedChat?.title ?? 'Select a chat'}</h2>
              {selectedChat?.last_source_label && (
                <span className={styles.chatBarSource}>{selectedChat.last_source_label}</span>
              )}
            </div>
            {selectedChat && exportSummary && (
              <div className={styles.chatBarRight}>
                <span className={styles.chatBarBadge}>{exportSummary}</span>
                {updatedTime && <span className={styles.chatBarTime}>{updatedTime}</span>}
              </div>
            )}
          </div>

          {/* Feed canvas */}
          <div className={styles.mainCanvas}>
            {hasFeed ? (
              <div
                key={selectedChat?.id ?? selectedChatId ?? 'shorts-feed'}
                className={`${styles.feedViewport} ${isSwitchingChat ? styles.feedViewportSwitching : styles.feedViewportReady}`}
              >
                <ShortsFeed shorts={shorts} />
              </div>
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
                <p className={styles.emptyCopy}>This chat hasn't exported any shorts. Start a run to generate videos.</p>
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

// ─── Shorts feed — owns all scroll/play logic ────────────────────────────────

function ShortsFeed({ shorts }: { shorts: GeneratedShort[] }) {
  const feedRef = useRef<HTMLDivElement>(null)
  const [activeIndex, setActiveIndex] = useState(0)
  const isScrolling = useRef(false)
  const cooldown = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ── Wheel hijack: one video per scroll event, absorb momentum ──────────────
  useEffect(() => {
    const el = feedRef.current
    if (!el) return

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault()
      if (isScrolling.current) return   // absorb momentum / repeated events

      const dir = e.deltaY > 0 ? 1 : -1

      isScrolling.current = true

      setActiveIndex(prev => {
        const next = Math.max(0, Math.min(shorts.length - 1, prev + dir))
        el.scrollTo({ top: next * el.clientHeight, behavior: 'smooth' })
        return next
      })

      if (cooldown.current) clearTimeout(cooldown.current)
      cooldown.current = setTimeout(() => { isScrolling.current = false }, 800)
    }

    // passive: false is required to call e.preventDefault()
    el.addEventListener('wheel', handleWheel, { passive: false })
    return () => {
      el.removeEventListener('wheel', handleWheel)
      if (cooldown.current) clearTimeout(cooldown.current)
    }
  }, [shorts.length])

  // ── IntersectionObserver: sync activeIndex for touch/swipe ────────────────
  useEffect(() => {
    const el = feedRef.current
    if (!el || shorts.length === 0) return

    const observer = new IntersectionObserver(
      entries => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const idx = Number((entry.target as HTMLElement).dataset.idx)
            setActiveIndex(idx)
          }
        }
      },
      { root: el, threshold: 0.75 }
    )

    const slides = el.querySelectorAll('[data-idx]')
    slides.forEach(s => observer.observe(s))
    return () => observer.disconnect()
  }, [shorts.length])

  return (
    <div className={styles.feed} ref={feedRef}>
      {shorts.map((short, index) => (
        <div key={short.id} className={styles.slide} data-idx={index}>
          <ShortSlide
            short={short}
            index={index}
            total={shorts.length}
            isActive={index === activeIndex}
            shouldPrime={Math.abs(index - activeIndex) <= 1}
          />
        </div>
      ))}
    </div>
  )
}

// ─── Individual short card ────────────────────────────────────────────────────

function ShortSlide({
  short, index, total, isActive, shouldPrime,
}: {
  short: GeneratedShort
  index: number
  total: number
  isActive: boolean
  shouldPrime: boolean
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [isMuted, setIsMuted] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [isBuffering, setIsBuffering] = useState(true)
  const [hasLoadedFrame, setHasLoadedFrame] = useState(false)

  useEffect(() => {
    setIsBuffering(shouldPrime)
    setHasLoadedFrame(false)
  }, [short.videoUrl, shouldPrime])

  // Ensure video starts unmuted. Remove the muted HTML attribute so browsers
  // don't treat it as a muted-autoplay request. We explicitly set muted=false.
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    v.removeAttribute('muted')
    v.muted = false
  }, [])

  useEffect(() => {
    const v = videoRef.current
    if (!v || !shouldPrime) return
    v.preload = isActive ? 'auto' : 'metadata'
    if (v.readyState === 0) {
      v.load()
    }
  }, [isActive, shouldPrime, short.videoUrl])

  // Play/pause + restart when this card becomes active
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    if (isActive) {
      v.currentTime = 0    // always restart from the beginning
      v.muted = false      // always unmute on entry
      setIsMuted(false)
      // Try unmuted play; if browser blocks it, fall back to muted play
      v.play().catch(() => {
        v.muted = true
        setIsMuted(true)
        v.play().catch(() => {})
      })
      setIsPaused(false)
    } else {
      v.pause()
    }
  }, [isActive])

  function handleCardClick() {
    const v = videoRef.current
    if (!v) return
    if (v.paused) { v.play().catch(() => {}); setIsPaused(false) }
    else          { v.pause(); setIsPaused(true) }
  }

  function toggleMute(e: React.MouseEvent) {
    e.stopPropagation()
    const v = videoRef.current
    if (!v) return
    v.muted = !v.muted
    setIsMuted(v.muted)
  }

  return (
    <div className={styles.shortRow}>
      {/* ── 9:16 video card ── */}
      <article className={styles.shortCard} onClick={handleCardClick}>
        <video
          ref={videoRef}
          className={`${styles.shortVideo} ${hasLoadedFrame ? styles.shortVideoReady : ''}`}
          src={shouldPrime ? short.videoUrl : undefined}
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
          }}
          onWaiting={() => {
            if (isActive) setIsBuffering(true)
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
        <div className={styles.shortTopControls}>
          <span className={styles.shortCounter}>{index + 1} / {total}</span>
          <button
            type="button"
            className={styles.shortMuteBtn}
            onClick={toggleMute}
            aria-label={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? (
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

        {/* Bottom info overlay */}
        <div className={styles.shortInfo}>
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
      <div className={styles.shortActions}>
        <button type="button" className={styles.shortActionBtn} aria-label="Like">
          <div className={styles.shortActionIcon}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
            </svg>
          </div>
          <span className={styles.shortActionLabel}>Like</span>
        </button>

        <a href={short.videoUrl} target="_blank" rel="noreferrer" className={styles.shortActionBtn} aria-label="Open">
          <div className={styles.shortActionIcon}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </div>
          <span className={styles.shortActionLabel}>Open</span>
        </a>

        <button type="button" className={styles.shortActionBtn} aria-label="Share">
          <div className={styles.shortActionIcon}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
            </svg>
          </div>
          <span className={styles.shortActionLabel}>Share</span>
        </button>
      </div>
    </div>
  )
}

function ChatListCover({ chat }: { chat: ChatSummary }) {
  const [isReady, setIsReady] = useState(false)
  const hasVideo = Boolean(chat.cover_output_url && !chat.cover_output_url.startsWith('file://'))

  useEffect(() => {
    setIsReady(false)
  }, [chat.cover_output_url])

  return (
    <div className={styles.chatListCover}>
      {hasVideo ? (
        <>
          <video
            className={`${styles.chatListVideo} ${isReady ? styles.chatListVideoReady : ''}`}
            src={chat.cover_output_url ?? undefined}
            muted
            loop
            playsInline
            preload="metadata"
            onLoadedData={() => setIsReady(true)}
            onCanPlay={() => setIsReady(true)}
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
  return { id: `${s.batchId}-${s.itemId}`, title: s.title, source: s.sourceLabel, sourceUrl: s.sourceUrl ?? '#', batchId: s.batchId, itemId: s.itemId, videoUrl: s.previewUrl, updatedAt: s.createdAt }
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
    updatedAt: a.updated_at,
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
