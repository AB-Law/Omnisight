import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Sidebar } from '@/components/layout/sidebar'
import { Providers } from '@/components/auth/Providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Omnisight OSINT',
  description: 'AI-Powered OSINT & Market Intelligence',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark h-full bg-background-dark text-slate-100">
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet"/>
      </head>
      <body className={`${inter.className} h-screen overflow-hidden flex bg-background-dark font-display`}>
        <Providers>
          <Sidebar />
          <main className="flex-1 flex flex-col relative overflow-hidden">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  )
}
