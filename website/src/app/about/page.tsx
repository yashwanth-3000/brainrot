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
    label: 'Script generation · OpenAI + backend QA',
    title: 'A script pipeline that writes for the ear.',
    accent: '#6c47ff',
    bg: 'linear-gradient(160deg, #080612 0%, #120d2a 100%)',
    caption: 'Prompt → scripts → QA',
    videoUrl: 'https://bblxxjxelituczzebbip.supabase.co/storage/v1/object/public/final-renders/807ce865-dd3d-4a50-b071-cae1f731bb35/76ccf926-c627-468a-b9e6-c44d1afa0074.mp4',
    body: [
      <>Once the source text is ingested, it goes to the <strong>Producer stage</strong>. The backend sends the cleaned brief to <strong>OpenAI</strong>, which returns a structured bundle of candidate scripts. Each script includes a title, hook line, narration text, caption text, estimated duration, visual beat notes, gameplay tags, music tags, and the source facts it used.</>,
      <>The goal is not one generic summary. The Producer generates up to <strong>fifteen scripts per batch</strong>, each covering a different angle of the source material. Every narration text must land inside a configured word range targeting <strong>25–30 second videos</strong>.</>,
      <>After generation, the backend runs a <strong>local QA and repair pass</strong>. It checks hook grounding, duplicate ideas, schema shape, pacing, and word counts. If a script bundle fails validation, the backend sends the errors back for repair and retries up to <strong>three times</strong> before isolating the remaining failed slots and continuing independently.</>,
    ],
  },
  {
    n: '03',
    label: 'Narration + alignment · ElevenLabs Agent',
    title: 'Every word, timestamped to the millisecond.',
    accent: '#8b5cf6',
    bg: 'linear-gradient(160deg, #06050f 0%, #0e0a20 100%)',
    caption: 'Word-level forced alignment',
    videoUrl: 'https://bblxxjxelituczzebbip.supabase.co/storage/v1/object/public/final-renders/f68c8bf6-d28f-4a39-b0bc-04eadb511206/2a682f90-f495-4900-b4c7-65c6f4442f70.mp4',
    body: [
      <>With scripts in hand, the orchestrator calls the <strong>Narrator</strong>. This is a <strong>second ElevenLabs agent</strong>, separate from the Producer, whose job is to convert the narration text into audio and return <strong>word-level timestamps</strong>. Every word in the output has a precise start time and end time in milliseconds, produced by <strong>ElevenLabs&apos; forced alignment system</strong> running over the generated audio.</>,
      <>The word timings are then passed directly into the <strong>subtitle generator</strong>, which builds an <strong>Advanced SubStation Alpha (.ass) track</strong>, the same subtitle format used in professional anime fansubs and broadcast production. Unlike SRT captions that just display text at timestamps, ASS supports <strong>per-word animation effects</strong>. Draftr ships with five subtitle presets: a karaoke-style sweep, and four single-word-pop variants using the Komika, Bebas Neue, Anton, and Lilita One typefaces.</>,
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
      setPlaying(true)
    } else {
      v.pause()
      setPlaying(false)
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
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <video
              ref={videoRef}
              className={styles.dummyVideo}
              src={section.videoUrl}
              muted
              loop
              playsInline
              preload="auto"
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
