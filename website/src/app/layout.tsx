import type { Metadata } from 'next'
import { DM_Sans, Instrument_Serif } from 'next/font/google'
import { MotionOrchestrator } from './_components/motion-orchestrator'
import { AuthProvider } from '@/components/auth/auth-provider'
import './globals.css'

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-body',
})

const instrumentSerif = Instrument_Serif({
  subsets: ['latin'],
  weight: '400',
  style: ['normal', 'italic'],
  variable: '--font-display',
})

export const metadata: Metadata = {
  title: 'Draftr',
  description: 'Draftr turns URLs, PDFs, and notes into narrated short-form videos with guest access, Google login, and a personal library.',
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
      <body className={`${dmSans.variable} ${instrumentSerif.variable}`}>
        <AuthProvider>
          <MotionOrchestrator />
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
