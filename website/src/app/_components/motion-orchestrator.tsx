'use client'

import { usePathname } from 'next/navigation'
import { useEffect } from 'react'

function normalizeValue(value: string | undefined) {
  if (!value) {
    return undefined
  }

  return /^\d+$/.test(value) ? `${value}ms` : value
}

export function MotionOrchestrator() {
  const pathname = usePathname()

  useEffect(() => {
    const root = document.documentElement
    const elements = Array.from(document.querySelectorAll<HTMLElement>('[data-reveal]'))

    if (!elements.length) {
      return
    }

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    root.dataset.motion = prefersReducedMotion ? 'reduced' : 'ready'

    elements.forEach((element) => {
      element.classList.remove('is-visible')

      const delay = normalizeValue(element.dataset.revealDelay)
      const revealX = element.dataset.revealX
      const revealY = element.dataset.revealY
      const revealScale = element.dataset.revealScale

      if (delay) {
        element.style.setProperty('--reveal-delay', delay)
      }

      if (revealX) {
        element.style.setProperty('--reveal-x', revealX)
      }

      if (revealY) {
        element.style.setProperty('--reveal-y', revealY)
      }

      if (revealScale) {
        element.style.setProperty('--reveal-scale', revealScale)
      }
    })

    if (prefersReducedMotion) {
      elements.forEach((element) => {
        element.classList.add('is-visible')
      })

      return
    }

    const reveal = (element: HTMLElement) => {
      element.classList.add('is-visible')
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return
          }

          reveal(entry.target as HTMLElement)
          observer.unobserve(entry.target)
        })
      },
      {
        rootMargin: '0px 0px -12% 0px',
        threshold: 0.18,
      },
    )

    const frame = window.requestAnimationFrame(() => {
      elements.forEach((element) => {
        const rect = element.getBoundingClientRect()

        if (rect.top <= window.innerHeight * 0.88) {
          reveal(element)
          return
        }

        observer.observe(element)
      })
    })

    return () => {
      window.cancelAnimationFrame(frame)
      observer.disconnect()
    }
  }, [pathname])

  return null
}
