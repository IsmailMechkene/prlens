import { Navbar } from '../components/landing/Navbar'
import { Hero } from '../components/landing/Hero'
import { PullRequestPreview } from '../components/landing/PullRequestPreview'
import { Features } from '../components/landing/Features'
import { Footer } from '../components/landing/Footer'
import styles from './LandingPage.module.css'

export function LandingPage() {
  return (
    <div className={styles.page}>
      <Navbar />
      <Hero />
      <PullRequestPreview />
      <Features />
      <Footer />
      <div className={styles.spacer} />
    </div>
  )
}
