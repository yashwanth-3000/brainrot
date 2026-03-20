import type { Metadata } from 'next'
import { Inter, Inter_Tight } from 'next/font/google'
import { MotionOrchestrator } from './_components/motion-orchestrator'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-body',
})

const interTight = Inter_Tight({
  subsets: ['latin'],
  variable: '--font-display',
})

export const metadata: Metadata = {
  title: 'Draftr',
  description: 'SaaS landing page for a collaborative design workflow platform.',
  icons: {
    icon: '/favicon.svg',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" data-motion="ready">
      <body className={`${inter.variable} ${interTight.variable}`}>
        <MotionOrchestrator />
        {children}
      </body>
    </html>
  )
}
