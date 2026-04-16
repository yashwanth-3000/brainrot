'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import Navbar from '@/components/ui/navbar'
import styles from './about.module.css'
import Link from 'next/link'

const TRANSITION_MS = 680

type SectionDef = {
  n: string
  label: string
  title: string
  accent: string
  bg: string
  caption: string
  videoUrl: string
  pullquote?: string
  logo?: React.ReactNode
  body: React.ReactNode[]
}

const sections: SectionDef[] = [
  {
    n: '00',
    label: 'What is Draftr',
    title: 'Short-form video, pointed at things worth knowing.',
    accent: '#5235ef',
    bg: 'linear-gradient(160deg, #0d0b1e 0%, #180e40 100%)',
    caption: 'The format you already know',
    videoUrl: 'https://bblxxjxelituczzebbip.supabase.co/storage/v1/object/public/final-renders/0c06a7db-62c8-44a7-a679-e63508338b77/d59acbcc-3309-42b5-a04d-2de36edfa85c.mp4',
    pullquote: 'The same format that made you watch six hours of gameplay clips can make you actually learn something. We just had to build the machine.',
    body: [
      <>People will sit through a five-minute breakdown of quantum computing delivered over Minecraft parkour. They won&apos;t open the paper it&apos;s based on. We didn&apos;t set out to exploit that. We set out to <strong>point it at something worth knowing.</strong></>,
      <><strong>Draftr</strong> is a pipeline that takes any written source (a URL, a PDF, a raw paste) and produces a <strong>fully rendered, narrated, subtitled short-form video</strong>. No editing. No recording. No script writing. You drop the content in chat. The machine handles everything else.</>,
    ],
  },
  {
    n: '01',
    label: 'Ingestion',
    title: 'Getting the text out of anything.',
    accent: '#f97316',
    bg: 'linear-gradient(160deg, #100c04 0%, #1f1503 100%)',
    caption: 'URL → clean markdown',
    videoUrl: 'https://bblxxjxelituczzebbip.supabase.co/storage/v1/object/public/final-renders/6e63fbf2-065f-4d01-8345-b03d3b02bfd8/595bbc73-7f79-4fd2-95ba-4cdfa988b2e1.mp4',
    logo: (
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="26" fill="none" viewBox="0 0 50 72">
        <path fill="#fa5d19" d="M41.715 23.193c-2.762.82-4.844 2.675-6.37 4.69-.327.432-1.01.107-.88-.423 2.92-12.007-.937-21.986-12.961-26.898a.803.803 0 0 0-1.085.937c5.47 21.961-17.537 20.109-14.63 45.005.05.427-.43.72-.78.47-1.09-.782-2.307-2.415-3.142-3.562a.502.502 0 0 0-.887.16c-.665 2.404-.98 4.67-.98 6.92 0 8.749 4.497 16.45 11.304 20.915.39.255.89-.11.758-.557a13.5 13.5 0 0 1-.563-3.697c0-.788.05-1.593.173-2.343.285-1.885.94-3.68 2.04-5.314 3.772-5.663 11.334-11.132 10.127-18.56-.078-.47.477-.78.827-.457 5.328 4.868 6.383 11.415 5.508 17.287-.075.51.564.782.887.382a11.6 11.6 0 0 1 2.892-2.587c.27-.168.63-.04.733.26.602 1.752 1.497 3.397 2.342 5.042a13.46 13.46 0 0 1 .905 9.982.502.502 0 0 0 .755.57C45.5 66.95 50 59.248 50 50.494c0-3.043-.532-6.025-1.54-8.82-2.112-5.862-7.472-10.264-6.117-17.904.065-.365-.273-.682-.628-.577" />
      </svg>
    ),
    body: [
      <>The internet stores knowledge in dozens of formats: behind JavaScript renders, inside PDF binaries, spread across multi-page documentation sites. We use <strong>Firecrawl</strong>. For a single article URL, the backend calls Firecrawl&apos;s <strong>scrape endpoint</strong> requesting both <code>markdown</code> and <code>summary</code> formats. Firecrawl handles the render, strips the nav, footer, and ads, and returns the actual content as <strong>clean markdown</strong>.</>,
      <>For an entire documentation website, we first call the <strong>map endpoint</strong> to enumerate candidate URLs across the domain, then rank and filter them by path heuristics. Paths containing <code>/blog</code>, <code>/docs</code>, or <code>/research</code> score up. Paths like <code>/tag</code> or <code>/legal</code> score down. The top-ranked URLs go into a <strong>batch crawl job</strong>, polled until completion.</>,
    ],
  },
  {
    n: '02',
    label: 'Script generation · CrewAI + OpenAI + backend QA',
    title: 'CrewAI maps the source before a single line gets written.',
    accent: '#6c47ff',
    bg: 'linear-gradient(160deg, #080612 0%, #120d2a 100%)',
    caption: 'Sections → slots → QA',
    videoUrl: 'https://bblxxjxelituczzebbip.supabase.co/storage/v1/object/public/final-renders/807ce865-dd3d-4a50-b071-cae1f731bb35/76ccf926-c627-468a-b9e6-c44d1afa0074.mp4',
    body: [
      <>Once the source text is ingested, it does not go straight into one giant summary prompt. The backend first hands the markdown to <strong>CrewAI</strong>, which splits it into meaningful sections, plans coverage, and assigns each short a different section plus a different angle family so the batch actually spreads across the source.</>,
      <>Each planned slot is then written with <strong>OpenAI</strong>. The model gets the local section context, the angle it needs to hit, the pacing target, and grounding constraints. The result is not one generic recap, but a structured batch of scripts tuned for <strong>25–30 second videos</strong> that each sound distinct.</>,
      <>After writing, the backend runs a <strong>QA and repair pass</strong> for overlap, stale hook phrasing, schema shape, pacing, and grounded claims. Failed slots are repaired and retried up to <strong>three passes</strong>, so one weak script does not stall the rest of the bundle.</>,
    ],
  },
  {
    n: '03',
    label: 'Narration + subtitle timing · ElevenLabs',
    title: 'The audio comes back with timing, so the captions are already in sync.',
    accent: '#8b5cf6',
    bg: 'linear-gradient(160deg, #06050f 0%, #0e0a20 100%)',
    caption: 'ElevenLabs TTS → timed subtitle track',
    videoUrl: 'https://bblxxjxelituczzebbip.supabase.co/storage/v1/object/public/final-renders/5e11c26b-9de3-40a5-b925-1a087181fc20/88870a71-9393-42d5-a40a-238e8b177dbb.mp4',
    body: [
      <>Once a script clears QA, Draftr runs the narration through <strong>ElevenLabs TTS by default</strong>. Each short gets a narrator voice selected up front, and if that voice returns bad audio, the backend can automatically retry with the <strong>default voice</strong> instead of killing the whole render.</>,
      <>The returned audio already includes <strong>word-level timing data</strong>. Draftr stores that alignment, turns the timed words into an animated <strong>Advanced SubStation Alpha (.ass)</strong> subtitle track, and picks the subtitle preset that best fits the gameplay energy. By the time the final encode starts, the voiceover and captions are already locked together.</>,
    ],
  },
  {
    n: '04',
    label: 'Rendering · FFmpeg',
    title: 'Clip in. MP4 out. Nothing in between.',
    accent: '#10b981',
    bg: 'linear-gradient(160deg, #030f09 0%, #061a10 100%)',
    caption: '9:16 · libass · sidechain',
    videoUrl: 'https://bblxxjxelituczzebbip.supabase.co/storage/v1/object/public/final-renders/7485cfb7-71cb-45a2-98ec-2a7e2a2190ee/4a2e460d-8c50-4cbc-9333-de018fdbd2a4.mp4',
    body: [
      <>The final step is assembly. The renderer takes three inputs (<strong>gameplay video</strong>, <strong>narration audio</strong>, and the generated <strong>.ass subtitle file</strong>) and runs them through a single <strong>FFmpeg encode pass</strong>. The gameplay clip is cropped and scaled to fill a <strong>9:16 vertical frame</strong>. The narration audio goes on the primary audio track.</>,
      <>The subtitle track is burned directly into the video using <strong>libass</strong> during the encode pass. The final file is a <strong>self-contained MP4</strong>. It goes straight to <strong>Supabase storage</strong> and the public URL is returned to the orchestrator. A batch of <strong>ten videos generates in about three minutes</strong> from the moment ingestion completes.</>,
    ],
  },
  {
    n: '05',
    label: 'Authentication + library · Supabase + Google',
    title: 'Guest mode stays instant. Login turns the generator into your own archive.',
    accent: '#26c281',
    bg: 'linear-gradient(160deg, #03110b 0%, #062118 100%)',
    caption: 'Guest library → personal library',
    videoUrl: 'https://bblxxjxelituczzebbip.supabase.co/storage/v1/object/public/final-renders/88ac3031-e07f-4758-b7e1-7c7184428835/db2a5332-de5c-4396-b4b1-ffd9e3775a1e.mp4',
    pullquote: 'The same generator works in both modes. Auth only changes who owns the history.',
    logo: (
      <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" viewBox="0 0 24 24">
        <path fill="#26c281" d="M12 2a5 5 0 0 1 5 5v1.1a3.9 3.9 0 0 1 2.8 3.75v6.3A3.85 3.85 0 0 1 15.95 22H8.05A3.85 3.85 0 0 1 4.2 18.15v-6.3A3.9 3.9 0 0 1 7 8.1V7a5 5 0 0 1 5-5m0 2.1A2.9 2.9 0 0 0 9.1 7v1h5.8V7A2.9 2.9 0 0 0 12 4.1M12 11a1.8 1.8 0 0 0-1.8 1.8c0 .68.37 1.27.93 1.58v1.82h1.9v-1.82A1.8 1.8 0 0 0 12 11"/>
      </svg>
    ),
    body: [
      <>Draftr now supports <strong>Supabase authentication with Google login</strong>. If you want to try the product fast, you can keep moving in guest mode and generate into the <strong>general library</strong> without creating an account.</>,
      <>The moment you sign in, the same workflow becomes personal. New chats, rendered MP4s, reruns, and saved shorts are scoped to <strong>your account</strong>, so your library becomes a private archive instead of a shared feed.</>,
      <>That split keeps the product simple. Guests get instant access, while logged-in users get ownership, persistence, and a cleaner place to revisit everything they have generated later.</>,
    ],
  },
  {
    n: '06',
    label: 'Testing + QA · TestSprite',
    title: 'We pressure-test the full workflow before users ever feel the regression.',
    accent: '#ff9f43',
    bg: 'linear-gradient(160deg, #120904 0%, #251003 100%)',
    caption: 'UI + API + auth + render verification',
    videoUrl: 'https://bblxxjxelituczzebbip.supabase.co/storage/v1/object/public/final-renders/a84b8571-1777-466a-a822-74eabf6a1723/f69a44c5-d8b5-4dad-bf54-88993ee0badf.mp4',
    pullquote: 'The goal is not one happy-path demo. The goal is to keep the whole machine honest.',
    logo: (
      <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" viewBox="0 0 24 24">
        <path fill="#ff9f43" d="M12 2.4 20.2 7v10L12 21.6 3.8 17V7L12 2.4Zm0 2.32L5.8 8.21v7.58L12 19.28l6.2-3.49V8.2L12 4.73Zm3.64 4.41-4.32 4.96-2.96-2.47-1.23 1.48 4.37 3.63 5.56-6.38-1.42-1.2Z"/>
      </svg>
    ),
    body: [
      <>We use <strong>TestSprite</strong> as an AI-native testing layer for the product. It plans and executes end-to-end UI, API, and workflow checks, then returns the kind of evidence that matters when something breaks: <strong>reports, logs, screenshots, videos, and fix guidance</strong>.</>,
      <>In practice that means the <strong>video generator</strong>, the <strong>recommendation system</strong>, the <strong>authentication flow</strong>, Supabase-backed storage, and the rest of the backend path are tested as separate systems instead of only through one polished demo path.</>,
      <>For critical flows, we repeat the runs across multiple passes, <strong>five times over when needed</strong>, so regressions get caught early and fixes can be verified before the website ships them to real users.</>,
    ],
  },
]

/* ── Dummy phone ── */
function DummyPhone({ section, offset, isActive, muted, onToggleMute }: {
  section: SectionDef
  offset: number
  isActive: boolean
  muted: boolean
  onToggleMute: () => void
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [playing, setPlaying] = useState(false)

  // sync play/pause on active change
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    if (isActive) {
      v.play().catch(() => {})
    } else {
      v.pause()
    }
  }, [isActive])

  // sync muted on global mute change
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    v.muted = muted
  }, [muted])

  function toggleMute(e: React.MouseEvent) {
    e.stopPropagation()
    onToggleMute()
  }

  function togglePlay(e: React.MouseEvent) {
    e.stopPropagation()
    const v = videoRef.current
    if (!v) return
    if (v.paused) {
      v.play().catch(() => {})
      setPlaying(true)
    } else {
      v.pause()
      setPlaying(false)
    }
  }

  return (
    <div
      className={styles.phoneSlide}
      style={{ transform: `translateY(${offset * 100}%)` }}
    >
      <div className={styles.phone}>
        <div className={styles.phoneIsland} />
        <div className={styles.phoneScreen}>
          <div className={styles.dummyScreen}>
            <video
              ref={videoRef}
              className={styles.dummyVideo}
              src={section.videoUrl}
              muted
              loop
              playsInline
              preload="auto"
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
            />

            {/* gradient */}
            <div className={styles.dummyGradient} />

            {/* play/pause btn */}
            <button className={styles.dummyPlay} onClick={togglePlay} aria-label={playing ? 'Pause' : 'Play'}>
              {playing ? (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="6" y="4" width="4" height="16" /><rect x="14" y="4" width="4" height="16" />
                </svg>
              ) : (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
              )}
            </button>

            {/* mute btn */}
            <button className={styles.dummyMute} onClick={toggleMute} aria-label={muted ? 'Unmute' : 'Mute'}>
              {muted ? (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                  <line x1="23" y1="9" x2="17" y2="15" /><line x1="17" y1="9" x2="23" y2="15" />
                </svg>
              ) : (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
                </svg>
              )}
            </button>

            {/* info overlay */}
            <div className={styles.dummyInfo}>
              <div className={styles.dummyAuthor}>
                <div className={styles.dummyAvatar} style={{ background: `linear-gradient(135deg, ${section.accent}, #8a73ff)` }}>D</div>
                <div>
                  <p className={styles.dummyName}>Draftr AI</p>
                  <p className={styles.dummyTime}>2h ago</p>
                </div>
              </div>
              <p className={styles.dummyCaption}>{section.caption}</p>
            </div>
          </div>
        </div>
        <div className={`${styles.phoneBtn} ${styles.phoneBtnVolUp}`} />
        <div className={`${styles.phoneBtn} ${styles.phoneBtnVolDown}`} />
        <div className={`${styles.phoneBtn} ${styles.phoneBtnPower}`} />
        <button
          className={`${styles.phoneBtn} ${styles.phoneBtnPause}`}
          onClick={togglePlay}
          aria-label={playing ? 'Pause' : 'Play'}
        />
      </div>
    </div>
  )
}

/* ── Text slide ── */
function TextSlide({ section, offset, isLast }: { section: SectionDef; offset: number; isLast: boolean }) {
  return (
    <div
      className={styles.textSlide}
      style={{ transform: `translateY(${offset * 100}%)` }}
    >
      <div className={styles.textSlideInner}>
        <div className={styles.sectionLabel}>
          <span className={styles.sectionN} style={{ color: section.accent }}>{section.n}</span>
          <span>{section.label}</span>
          {section.logo && <span className={styles.sectionLogo}>{section.logo}</span>}
        </div>
        <h2 className={styles.sectionTitle}>{section.title}</h2>
        <div className={styles.bodyText}>
          {section.body.map((p, i) => <p key={i}>{p}</p>)}
        </div>
        {section.pullquote && (
          <blockquote className={styles.pullquote} style={{ borderColor: section.accent }}>
            {section.pullquote}
          </blockquote>
        )}
        {isLast && (
          <div className={styles.ctaRow}>
            <Link href="/chat" className={styles.ctaBtn}>Try Draftr →</Link>
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Page ── */
export default function AboutPage() {
  const [current, setCurrent] = useState(0)
  const [globalMuted, setGlobalMuted] = useState(false)
  const lockedRef = useRef(false)

  const go = useCallback((dir: 1 | -1) => {
    if (lockedRef.current) return
    setCurrent(prev => {
      const next = Math.max(0, Math.min(sections.length - 1, prev + dir))
      if (next === prev) return prev
      lockedRef.current = true
      setTimeout(() => { lockedRef.current = false }, TRANSITION_MS + 50)
      return next
    })
  }, [])

  useEffect(() => {
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      go(e.deltaY > 0 ? 1 : -1)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowRight') go(1)
      if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') go(-1)
    }
    window.addEventListener('wheel', onWheel, { passive: false })
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('wheel', onWheel)
      window.removeEventListener('keydown', onKey)
    }
  }, [go])

  const touchY = useRef(0)
  const onTouchStart = (e: React.TouchEvent) => { touchY.current = e.touches[0].clientY }
  const onTouchEnd = (e: React.TouchEvent) => {
    const delta = touchY.current - e.changedTouches[0].clientY
    if (Math.abs(delta) > 40) go(delta > 0 ? 1 : -1)
  }

  return (
    <div className={styles.root} onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
      <Navbar />

      <div className={styles.layout}>
        {/* Left: phone viewer + dots */}
        <div className={styles.leftCol}>
          <div className={styles.phonesWrap}>
            {sections.map((s, i) => (
              <DummyPhone key={i} section={s} offset={i - current} isActive={i === current} muted={globalMuted} onToggleMute={() => setGlobalMuted(m => !m)} />
            ))}
          </div>
          {/* dots sit above phonesWrap via z-index */}
          <div className={styles.dots}>
            {sections.map((_, i) => (
              <button
                key={i}
                className={`${styles.dot} ${i === current ? styles.dotActive : ''}`}
                style={i === current ? { background: sections[current].accent } : {}}
                onClick={() => {
                  if (!lockedRef.current) {
                    lockedRef.current = true
                    setCurrent(i)
                    setTimeout(() => { lockedRef.current = false }, TRANSITION_MS + 50)
                  }
                }}
                aria-label={`Go to section ${i + 1}`}
              />
            ))}
          </div>
        </div>

        {/* Right: text */}
        <div className={styles.rightCol}>
          {sections.map((s, i) => (
            <TextSlide key={i} section={s} offset={i - current} isLast={i === sections.length - 1} />
          ))}
        </div>
      </div>
    </div>
  )
}
