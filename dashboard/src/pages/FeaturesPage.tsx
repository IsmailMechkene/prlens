import { Navbar } from '../components/landing/Navbar'
import { CtaBand } from '../components/landing/CtaBand'
import { Footer } from '../components/landing/Footer'
import { Card } from '../components/ui/Card'
import { Icon } from '../components/ui/Icon'
import styles from './FeaturesPage.module.css'

interface DetectionCategory {
  icon: string
  color: string
  tint: string
  title: string
  desc: string
  examples: string[]
}

const DETECTION: DetectionCategory[] = [
  {
    icon: 'shield-alert',
    color: 'var(--danger)',
    tint: 'rgba(248,81,73,0.12)',
    title: 'Security',
    desc: 'OWASP Top 10 coverage on every diff. Issues that would sail through a rushed human review get flagged on the exact line.',
    examples: ['SQL injection', 'Hardcoded secrets', 'Path traversal', 'Command injection', 'XSS', 'Unsafe deserialization', 'Auth flaws'],
  },
  {
    icon: 'gauge',
    color: 'var(--success)',
    tint: 'rgba(63,185,80,0.12)',
    title: 'Quality',
    desc: 'Structural problems that make code hard to change later — caught while the change is still cheap to make.',
    examples: ['Excessive nesting', 'Code duplication', 'God functions', 'Bare except blocks', 'Poor error handling'],
  },
  {
    icon: 'zap',
    color: 'var(--attention)',
    tint: 'rgba(210,153,34,0.12)',
    title: 'Performance',
    desc: 'Patterns that are invisible in review but expensive in production, spotted before they ship.',
    examples: ['N+1 queries', 'Expensive work in loops', 'Blocking calls', 'Inefficient algorithms'],
  },
  {
    icon: 'file-code',
    color: 'var(--done)',
    tint: 'rgba(210,168,255,0.12)',
    title: 'Style & documentation',
    desc: 'Not nitpicks — only the naming, validation, and documentation gaps that cause real maintainability problems.',
    examples: ['Confusing naming', 'Missing validation', 'Documentation gaps'],
  },
]

const SEVERITIES = [
  { emoji: '🔴', name: 'critical', penalty: '−25', color: 'var(--danger)', desc: 'Security breach, data loss, or outage risk' },
  { emoji: '🟠', name: 'error', penalty: '−10', color: '#f0883e', desc: 'A real bug that will misbehave in some paths' },
  { emoji: '🟡', name: 'warning', penalty: '−4', color: 'var(--attention)', desc: 'Quality or performance concern worth fixing' },
  { emoji: '🔵', name: 'info', penalty: '−1', color: 'var(--pa)', desc: 'Minor style or documentation note' },
]

const AUTOMATION = [
  {
    icon: 'message-square',
    color: 'var(--pa)',
    tint: 'var(--pa-t12)',
    title: 'Inline comments',
    desc: 'Findings land on the exact diff line, with a severity indicator and a concrete fix suggestion — not a wall of text at the bottom of the PR.',
  },
  {
    icon: 'scan-eye',
    color: 'var(--success)',
    tint: 'rgba(63,185,80,0.12)',
    title: 'Summary & score',
    desc: 'One structured summary per review: the verdict, the 0–100 score, issues by severity, positive observations, and top recommendations.',
  },
  {
    icon: 'tags',
    color: 'var(--done)',
    tint: 'rgba(210,168,255,0.12)',
    title: 'Automatic labels',
    desc: 'Labels like ai-approved, needs-changes, security-concern, and large-pr are applied from the findings, so PR lists stay scannable.',
  },
  {
    icon: 'git-pull-request',
    color: 'var(--attention)',
    tint: 'rgba(210,153,34,0.12)',
    title: 'Formal review verdict',
    desc: 'PRLens submits a real GitHub review — Approve, Request changes, or Comment — so branch protection rules and merge queues can act on it.',
  },
  {
    icon: 'users',
    color: 'var(--danger)',
    tint: 'rgba(248,81,73,0.12)',
    title: 'Reviewer routing',
    desc: 'Map issue types to people or teams. A critical security finding can automatically request your security lead as a reviewer.',
  },
  {
    icon: 'circle-alert',
    color: 'var(--fg-muted)',
    tint: 'rgba(125,133,144,0.12)',
    title: 'Honest failure states',
    desc: 'If some files can’t be analyzed the review is marked Incomplete — never a silently over-optimistic score you can’t trust.',
  },
]

const CONFIG_CHIPS = [
  'Minimum severity',
  'Target languages',
  'Approve threshold',
  'Request-changes threshold',
  'Excluded file patterns',
  'Reviewer mapping',
]

export function FeaturesPage() {
  return (
    <div className={styles.page}>
      <div className={styles.aurora} aria-hidden="true" />
      <div className={styles.content}>
        <Navbar />

        {/* Hero */}
        <header className={styles.hero}>
          <div className={styles.eyebrow}>Features</div>
          <h1 className={styles.title}>
            A senior reviewer on
            <br />
            <span className={styles.gradient}>every pull request</span>
          </h1>
          <p className={styles.sub}>
            PRLens reads the diff of every PR, finds real security, quality, and performance
            issues, and posts everything a great human reviewer would — in seconds, not hours.
          </p>
        </header>

        {/* Detection */}
        <section className={styles.section}>
          <div className={styles.sectionHead}>
            <div className={styles.sectionEyebrow}>Detection</div>
            <h2 className={styles.sectionHeading}>Four kinds of problems, one pass</h2>
            <p className={styles.sectionSub}>
              Every changed file is analyzed against the categories that actually cause incidents
              and rewrites. Only lines in the diff are reviewed — feedback stays about your change.
            </p>
          </div>
          <div className={styles.detectGrid}>
            {DETECTION.map((cat) => (
              <Card key={cat.title} className={styles.detectCard}>
                <div className={styles.iconBox} style={{ background: cat.tint, color: cat.color }}>
                  <Icon name={cat.icon} size={21} />
                </div>
                <h3 className={styles.cardTitle}>{cat.title}</h3>
                <p className={styles.cardDesc}>{cat.desc}</p>
                <div className={styles.chips}>
                  {cat.examples.map((ex) => (
                    <span key={ex} className={styles.chip}>
                      {ex}
                    </span>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </section>

        {/* Scoring */}
        <section className={styles.section}>
          <div className={styles.sectionHead}>
            <div className={styles.sectionEyebrow}>Scoring</div>
            <h2 className={styles.sectionHeading}>A score you can gate merges on</h2>
            <p className={styles.sectionSub}>
              Every review starts at 100 and subtracts a fixed penalty per issue, weighted by
              severity. The score is deterministic from the findings — no vibes.
            </p>
          </div>

          <div className={styles.scoreLayout}>
            <Card className={styles.sevCard}>
              {SEVERITIES.map((sv) => (
                <div key={sv.name} className={styles.sevRow}>
                  <span className={styles.sevEmoji}>{sv.emoji}</span>
                  <span className={styles.sevName} style={{ color: sv.color }}>
                    {sv.name}
                  </span>
                  <span className={styles.sevDesc}>{sv.desc}</span>
                  <span className={styles.sevPenalty} style={{ color: sv.color }}>
                    {sv.penalty}
                  </span>
                </div>
              ))}
            </Card>

            <Card className={styles.verdictCard}>
              <div className={styles.verdictBar} aria-hidden="true">
                <div className={styles.barSegment} style={{ flex: 50, background: 'rgba(248,81,73,0.55)' }} />
                <div className={styles.barSegment} style={{ flex: 30, background: 'rgba(210,153,34,0.55)' }} />
                <div className={styles.barSegment} style={{ flex: 20, background: 'rgba(63,185,80,0.55)' }} />
              </div>
              <div className={styles.barLabels} aria-hidden="true">
                <span>0</span>
                <span>50</span>
                <span>80</span>
                <span>100</span>
              </div>
              <div className={styles.verdicts}>
                <div className={styles.verdictRow}>
                  <span className={styles.verdictDot} style={{ background: 'var(--danger)' }} />
                  <span className={styles.verdictName}>Request changes</span>
                  <span className={styles.verdictRule}>below 50, or any critical issue</span>
                </div>
                <div className={styles.verdictRow}>
                  <span className={styles.verdictDot} style={{ background: 'var(--attention)' }} />
                  <span className={styles.verdictName}>Comment</span>
                  <span className={styles.verdictRule}>between the two thresholds</span>
                </div>
                <div className={styles.verdictRow}>
                  <span className={styles.verdictDot} style={{ background: 'var(--success)' }} />
                  <span className={styles.verdictName}>Approve</span>
                  <span className={styles.verdictRule}>above 80 with no critical issues</span>
                </div>
              </div>
              <p className={styles.verdictNote}>
                Both thresholds are sliders in your repo settings — tighten or relax the gate per
                repository.
              </p>
            </Card>
          </div>
        </section>

        {/* Automation */}
        <section className={styles.section}>
          <div className={styles.sectionHead}>
            <div className={styles.sectionEyebrow}>Automation</div>
            <h2 className={styles.sectionHeading}>Everything lands back on the PR</h2>
            <p className={styles.sectionSub}>
              No new tab, no separate report to open. The whole review arrives as native GitHub
              objects your team already knows how to read.
            </p>
          </div>
          <div className={styles.autoGrid}>
            {AUTOMATION.map((f) => (
              <Card key={f.title} className={styles.autoCard}>
                <div className={styles.iconBox} style={{ background: f.tint, color: f.color }}>
                  <Icon name={f.icon} size={21} />
                </div>
                <h3 className={styles.cardTitle}>{f.title}</h3>
                <p className={styles.cardDesc}>{f.desc}</p>
              </Card>
            ))}
          </div>
        </section>

        {/* Configuration */}
        <section className={styles.section}>
          <Card className={styles.configCard}>
            <div className={styles.configLeft}>
              <div className={styles.iconBox} style={{ background: 'var(--pa-t12)', color: 'var(--pa)' }}>
                <Icon name="sliders-horizontal" size={21} />
              </div>
              <h2 className={styles.configHeading}>Tuned per repository</h2>
              <p className={styles.cardDesc}>
                A monorepo and a prototype shouldn’t be held to the same bar. Every connected
                repository gets its own review configuration, editable from the dashboard — changes
                apply to the very next pull request.
              </p>
            </div>
            <div className={styles.configChips}>
              {CONFIG_CHIPS.map((c) => (
                <span key={c} className={styles.configChip}>
                  <Icon name="check" size={13} /> {c}
                </span>
              ))}
            </div>
          </Card>
        </section>

        {/* Deployment */}
        <section className={styles.section}>
          <div className={styles.sectionHead}>
            <div className={styles.sectionEyebrow}>Deployment</div>
            <h2 className={styles.sectionHeading}>Two ways to run it</h2>
            <p className={styles.sectionSub}>
              Same review pipeline underneath — pick the delivery mechanism that fits your team.
            </p>
          </div>
          <div className={styles.deployGrid}>
            <Card className={styles.deployCard}>
              <div className={styles.deployHead}>
                <div className={styles.iconBox} style={{ background: 'var(--pa-t12)', color: 'var(--pa)' }}>
                  <Icon name="server" size={21} />
                </div>
                <span className={styles.deployBadge}>Recommended</span>
              </div>
              <h3 className={styles.cardTitle}>GitHub App</h3>
              <p className={styles.cardDesc}>
                Install once, and every repository you grant access gets reviews automatically.
                Zero per-repo setup — no workflow files, no secrets to copy around. Powers this
                dashboard, with per-repo settings, score trends, and review history.
              </p>
              <ul className={styles.deployList}>
                <li><Icon name="check" size={14} /> Zero per-repo configuration</li>
                <li><Icon name="check" size={14} /> Dashboard with history &amp; trends</li>
                <li><Icon name="check" size={14} /> Signed, verified webhook events</li>
              </ul>
            </Card>
            <Card className={styles.deployCard}>
              <div className={styles.deployHead}>
                <div className={styles.iconBox} style={{ background: 'rgba(210,168,255,0.12)', color: 'var(--done)' }}>
                  <Icon name="workflow" size={21} />
                </div>
                <span className={styles.deployBadgeMuted}>Self-hosted</span>
              </div>
              <h3 className={styles.cardTitle}>GitHub Actions</h3>
              <p className={styles.cardDesc}>
                Prefer everything in your own CI? Add a single workflow file and PRLens runs inside
                GitHub Actions on every pull request — no server, no app installation, credentials
                stay in your repository secrets.
              </p>
              <ul className={styles.deployList}>
                <li><Icon name="check" size={14} /> No server to operate</li>
                <li><Icon name="check" size={14} /> Lives entirely in your CI config</li>
                <li><Icon name="check" size={14} /> Same pipeline, same review quality</li>
              </ul>
            </Card>
          </div>
        </section>

        <CtaBand />
        <Footer />
        <div className={styles.spacer} />
      </div>
    </div>
  )
}
