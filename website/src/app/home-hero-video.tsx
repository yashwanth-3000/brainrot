'use client'

import { useState } from 'react'

const heroVideoUrl =
  'https://bblxxjxelituczzebbip.supabase.co/storage/v1/object/public/final-renders/marketing/home-hero-20260416.mp4'

export default function HomeHeroVideo() {
  const [muted, setMuted] = useState(true)

  return (
    <div className="hp-hero-video">
      <video
        className="hp-hero-video__media"
        autoPlay
        loop
        muted={muted}
        playsInline
        preload="metadata"
        src={heroVideoUrl}
      />

      <div className="hp-hero-video__gradient" />

      {/* mute button */}
      <button
        type="button"
        className="hp-hero-video__mute"
        onClick={() => setMuted(m => !m)}
        aria-label={muted ? 'Unmute' : 'Mute'}
      >
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

      {/* bottom info overlay */}
      <div className="hp-hero-video__info">
        <div className="hp-hero-video__author">
          <div className="hp-hero-video__avatar">D</div>
          <div>
            <p className="hp-hero-video__name">Draftr AI</p>
            <p className="hp-hero-video__time">2h ago</p>
          </div>
        </div>
        <p className="hp-hero-video__title">Turn any article into a short, instantly.</p>
      </div>
    </div>
  )
}
