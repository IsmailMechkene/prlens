import type { ReactNode } from 'react'
import { Navbar } from '../landing/Navbar'
import { Footer } from '../landing/Footer'
import styles from './StaticPageShell.module.css'

interface StaticPageShellProps {
  title: string
  subtitle?: string
  updated?: string
  children: ReactNode
}

export function StaticPageShell({ title, subtitle, updated, children }: StaticPageShellProps) {
  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <Navbar />
        <div className={styles.container}>
          <header className={styles.header}>
            <h1 className={styles.title}>{title}</h1>
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
            {updated && <p className={styles.updated}>Last updated: {updated}</p>}
          </header>
          <div className={styles.prose}>{children}</div>
        </div>
        <Footer />
      </div>
    </div>
  )
}
