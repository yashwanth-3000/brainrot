'use client'

import { useEffect, useRef, useState } from 'react'
import styles from './about.module.css'

interface VideoHeroProps {
  src: string
  caption?: string
  /** When true, fills its parent container instead of rendering its own card frame */
  fill?: boolean
}

export default function VideoHero({ src, caption, fill }: VideoHeroProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [muted, setMuted] = useState(true)
  const [hasLoaded, setHasLoaded] = useState(false)

  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    v.play().catch(() => {})
  }, [])

  function toggleMute(e: React.MouseEvent) {
    e.stopPropagation()
    const v = videoRef.current
    if (!v) return
    v.muted = !v.muted
    setMuted(v.muted)
  }

  const inner = (
    <>
      <video
        ref={videoRef}
        className={`${styles.videoEl} ${hasLoaded ? styles.videoElReady : ''}`}
        src={src || undefined}
        muted
        loop
        playsInline
        preload="auto"
        onLoadedData={() => setHasLoaded(true)}
        onCanPlay={() => setHasLoaded(true)}
      />

      {/* bottom gradient */}
      <div className={styles.videoGradient} />

      {/* mute button — top right */}
      <button
        type="button"
        className={styles.videoMuteBtn}
        onClick={toggleMute}
        aria-label={muted ? 'Unmute' : 'Mute'}
      >
        {muted ? (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
            <line x1="23" y1="9" x2="17" y2="15" /><line x1="17" y1="9" x2="23" y2="15" />
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
          </svg>
        )}
      </button>

      {/* caption overlay */}
      {caption && (
        <div className={styles.videoCaption}>
          <p className={styles.videoCaptionText}>{caption}</p>
        </div>
      )}
    </>
  )

  if (fill) {
    return <div className={styles.videoFill}>{inner}</div>
  }

  return (
    <div className={styles.videoHeroWrap}>
      <div className={styles.videoCard}>
        {inner}
      </div>
    </div>
  )
}
