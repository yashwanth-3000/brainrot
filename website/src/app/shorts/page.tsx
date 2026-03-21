'use client'

import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import styles from './shorts-page.module.css'

type Short = {
  id: number
  source: string
  sourceUrl: string
  tag: string
  facts: string[]
  likes: string
  comments: string
  shares: string
  bg: 'subway' | 'minecraft' | 'satisfying' | 'racing'
  accent: string
}

const SHORTS: Short[] = [
  {
    id: 1,
    source: 'nature.com/articles/ai-transformers-2025',
    sourceUrl: '#',
    tag: 'AI Research',
    facts: [
      'Transformer models process context by computing attention across every token simultaneously — not sequentially like humans read.',
      'This is why GPT-4 can "see" the beginning and end of your prompt at the same time.',
      'Attention mechanisms were first introduced in 2017 — the entire LLM revolution runs on that one paper.',
    ],
    likes: '24.1K',
    comments: '843',
    shares: '2.1K',
    bg: 'subway',
    accent: '#5235ef',
  },
  {
    id: 2,
    source: 'pubmed.ncbi.nlm.nih.gov/neuroplasticity',
    sourceUrl: '#',
    tag: 'Neuroscience',
    facts: [
      'Your brain physically rewires itself every time you learn something new — neurons that fire together, wire together.',
      'Sleep is when your brain consolidates short-term memories into long-term storage. Pulling all-nighters destroys retention.',
      'The hippocampus can generate new neurons well into adulthood — neuroplasticity never stops.',
    ],
    likes: '18.7K',
    comments: '612',
    shares: '3.4K',
    bg: 'minecraft',
    accent: '#7c3aed',
  },
  {
    id: 3,
    source: 'arxiv.org/abs/quantum-computing-2025',
    sourceUrl: '#',
    tag: 'Quantum',
    facts: [
      "Quantum computers don't run faster — they solve certain problems in fundamentally fewer steps.",
      'A qubit can be 0 and 1 simultaneously until you measure it. That superposition is the whole magic.',
      'Google\'s 70-qubit processor solved in 200 seconds what would take classical computers 10,000 years.',
    ],
    likes: '31.2K',
    comments: '1.1K',
    shares: '4.7K',
    bg: 'racing',
    accent: '#6d28d9',
  },
  {
    id: 4,
    source: 'hbr.org/decision-making-psychology',
    sourceUrl: '#',
    tag: 'Psychology',
    facts: [
      'The average person makes 35,000 decisions per day. Most are automatic, handled by your subconscious.',
      'Decision fatigue is real — judges approve more paroles in the morning than after lunch.',
      'Limiting choices increases satisfaction. Too many options leads to paralysis and regret.',
    ],
    likes: '44.8K',
    comments: '2.3K',
    shares: '8.9K',
    bg: 'satisfying',
    accent: '#4f46e5',
  },
  {
    id: 5,
    source: 'economist.com/behavioral-economics-2025',
    sourceUrl: '#',
    tag: 'Economics',
    facts: [
      'Loss aversion: losing $100 feels twice as bad as gaining $100 feels good. Evolution wired us this way.',
      'The sunk cost fallacy keeps people in bad investments, bad jobs, and bad movies they already paid for.',
      'Anchoring bias: the first number you hear disproportionately influences every estimate you make after.',
    ],
    likes: '22.3K',
    comments: '905',
    shares: '1.8K',
    bg: 'minecraft',
    accent: '#5235ef',
  },
]

const BG_LABELS: Record<Short['bg'], string> = {
  subway: '🏃 Subway Surfers',
  minecraft: '⛏️ Minecraft Parkour',
  satisfying: '✨ Satisfying Clips',
  racing: '🏎️ Racing Highlights',
}

function GameplayBg({ type }: { type: Short['bg'] }) {
  const colors: Record<string, string[]> = {
    subway: ['#1a0a2e', '#2d1b69', '#1a0a2e', '#3b1f7a', '#1a0a2e', '#2d1b69'],
    minecraft: ['#1a2e1a', '#2d4a1e', '#1a3a1a', '#3b5e22', '#1a2e1a', '#2d4a1e'],
    satisfying: ['#0a1a2e', '#1b3a5e', '#0a2a3e', '#1f4a7a', '#0a1a2e', '#1b3a5e'],
    racing: ['#2e1a0a', '#5e3a1b', '#3e2a0a', '#7a4e1f', '#2e1a0a', '#5e3a1b'],
  }
  const cols = colors[type]
  return (
    <div className={styles.gameplayBg}>
      <div className={styles.gameplayGrid}>
        {Array.from({ length: 48 }).map((_, i) => (
          <div
            key={i}
            className={styles.gameplayCell}
            style={{ background: cols[i % cols.length], animationDelay: `${(i * 0.07) % 2}s` }}
          />
        ))}
      </div>
      <div className={styles.gameplayLabel}>{BG_LABELS[type]}</div>
      <div className={styles.gameplayScanline} />
    </div>
  )
}

function ShortCard({ short, isActive }: { short: Short; isActive: boolean }) {
  const [liked, setLiked] = useState(false)
  const [factIdx, setFactIdx] = useState(0)

  useEffect(() => {
    if (!isActive) return
    setFactIdx(0)
    const t = setInterval(() => {
      setFactIdx(i => (i + 1) % short.facts.length)
    }, 3200)
    return () => clearInterval(t)
  }, [isActive, short.facts.length])

  return (
    <div className={styles.short}>
      {/* Gameplay background */}
      <GameplayBg type={short.bg} />

      {/* Dark overlay gradient */}
      <div className={styles.overlay} />

      {/* Top bar */}
      <div className={styles.topBar}>
        <div className={styles.sourceChip}>
          <span className={styles.sourceIcon}>🔗</span>
          <span className={styles.sourceUrl}>{short.source}</span>
        </div>
        <span className={styles.tagChip} style={{ background: short.accent + '33', borderColor: short.accent + '66', color: short.accent === '#5235ef' ? '#a89cff' : '#c4b5fd' }}>
          {short.tag}
        </span>
      </div>

      {/* Content card center */}
      <div className={styles.contentArea}>
        <div className={styles.factWrap}>
          {short.facts.map((fact, i) => (
            <div
              key={i}
              className={`${styles.factCard} ${i === factIdx ? styles.factCardActive : ''} ${i < factIdx ? styles.factCardPast : ''}`}
            >
              <p className={styles.factText}>{fact}</p>
              <div className={styles.factDots}>
                {short.facts.map((_, di) => (
                  <span key={di} className={`${styles.factDot} ${di === factIdx ? styles.factDotActive : ''}`} style={di === factIdx ? { background: short.accent } : {}} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Progress bar */}
      <div className={styles.progressBar}>
        <div
          className={styles.progressFill}
          style={{
            width: `${((factIdx + 1) / short.facts.length) * 100}%`,
            background: short.accent,
          }}
        />
      </div>

      {/* Right action buttons */}
      <div className={styles.actions}>
        <button
          className={`${styles.actionBtn} ${liked ? styles.actionBtnLiked : ''}`}
          onClick={() => setLiked(l => !l)}
          aria-label="Like"
        >
          <span className={styles.actionIcon}>{liked ? '❤️' : '🤍'}</span>
          <span className={styles.actionLabel}>{short.likes}</span>
        </button>
        <button className={styles.actionBtn} aria-label="Comment">
          <span className={styles.actionIcon}>💬</span>
          <span className={styles.actionLabel}>{short.comments}</span>
        </button>
        <button className={styles.actionBtn} aria-label="Share">
          <span className={styles.actionIcon}>↗️</span>
          <span className={styles.actionLabel}>{short.shares}</span>
        </button>
        <button className={styles.actionBtn} aria-label="Save">
          <span className={styles.actionIcon}>🔖</span>
          <span className={styles.actionLabel}>Save</span>
        </button>
      </div>

      {/* Bottom bar */}
      <div className={styles.bottomBar}>
        <div className={styles.bottomLeft}>
          <div className={styles.avatar} style={{ background: `linear-gradient(135deg, ${short.accent}, #9b87ff)` }}>
            <span>D</span>
          </div>
          <div>
            <p className={styles.authorName}>Draftr AI</p>
            <p className={styles.authorSub}>Generated from your content</p>
          </div>
        </div>
        <Link href="/chat" className={styles.generateBtn} style={{ background: short.accent }}>
          Make yours →
        </Link>
      </div>
    </div>
  )
}

export default function ShortsPage() {
  const [activeIdx, setActiveIdx] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const idx = Number((entry.target as HTMLElement).dataset.idx)
            setActiveIdx(idx)
          }
        })
      },
      { root: container, threshold: 0.6 }
    )

    const cards = container.querySelectorAll('[data-idx]')
    cards.forEach(c => observer.observe(c))
    return () => observer.disconnect()
  }, [])

  return (
    <div className={styles.root}>
      {/* Fixed navbar strip */}
      <header className={styles.navbar}>
        <Link href="/" className={styles.navLogo}>Draftr</Link>
        <nav className={styles.navLinks}>
          <Link href="/chat" className={styles.navLink}>Chat</Link>
          <Link href="/shorts" className={`${styles.navLink} ${styles.navLinkActive}`}>Shorts</Link>
          <Link href="/about" className={styles.navLink}>About</Link>
        </nav>
      </header>

      {/* Scroll container */}
      <div className={styles.feed} ref={containerRef}>
        {SHORTS.map((short, i) => (
          <div key={short.id} className={styles.slide} data-idx={i}>
            <ShortCard short={short} isActive={i === activeIdx} />
          </div>
        ))}
      </div>

      {/* Side scroll indicators */}
      <div className={styles.scrollDots}>
        {SHORTS.map((_, i) => (
          <button
            key={i}
            className={`${styles.scrollDot} ${i === activeIdx ? styles.scrollDotActive : ''}`}
            onClick={() => {
              const container = containerRef.current
              if (!container) return
              const slides = container.querySelectorAll('[data-idx]')
              slides[i]?.scrollIntoView({ behavior: 'smooth' })
            }}
            aria-label={`Go to short ${i + 1}`}
          />
        ))}
      </div>
    </div>
  )
}
