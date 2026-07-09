import { Navbar } from '../components/landing/Navbar'
import { Hero } from '../components/landing/Hero'
import { PullRequestPreview } from '../components/landing/PullRequestPreview'
import { StatsBand } from '../components/landing/StatsBand'
import { HowItWorks } from '../components/landing/HowItWorks'
import { Features } from '../components/landing/Features'
import { CtaBand } from '../components/landing/CtaBand'
import { Footer } from '../components/landing/Footer'
import styles from './LandingPage.module.css'

export function LandingPage() {
  return (
    <div className={styles.page}>
      <div className={styles.aurora} aria-hidden="true" />
      <div className={styles.grid} aria-hidden="true" />
      <div className={styles.content}>
        <Navbar />
        <Hero />
        <PullRequestPreview />
        <StatsBand />
        <HowItWorks />
        <Features />
        <CtaBand />
        <Footer />
        <div className={styles.spacer} />
      </div>
    </div>
  )
}
