import { Icon } from '../ui/Icon'
import styles from './PullRequestPreview.module.css'

/** Static "hero screenshot" mocking a PRLens review inline on a GitHub PR. */
export function PullRequestPreview() {
  return (
    <div className={styles.wrap}>
      <div className={styles.stage}>
        <div className={styles.halo} aria-hidden="true" />

        {/* floating stat chips */}
        <div className={`${styles.chip} ${styles.chipScore}`} aria-hidden="true">
          <span className={styles.chipIcon} style={{ color: 'var(--attention)' }}>
            <Icon name="gauge" size={15} />
          </span>
          <span>
            <span className={styles.chipLabel}>Quality score</span>
            <span className={styles.chipValue}>64 / 100</span>
          </span>
        </div>
        <div className={`${styles.chip} ${styles.chipSpeed}`} aria-hidden="true">
          <span className={styles.chipIcon} style={{ color: 'var(--pa)' }}>
            <Icon name="zap" size={15} />
          </span>
          <span>
            <span className={styles.chipLabel}>Reviewed in</span>
            <span className={styles.chipValue}>4.2s</span>
          </span>
        </div>

        <div className={styles.window}>
          {/* window chrome */}
          <div className={styles.chrome}>
            <span className={styles.dot} style={{ background: '#f85149' }} />
            <span className={styles.dot} style={{ background: '#d29922' }} />
            <span className={styles.dot} style={{ background: '#3fb950' }} />
            <span className={styles.url}>github.com/acme/api-gateway/pull/482</span>
          </div>

          {/* PR header */}
          <div className={styles.prHeader}>
            <div className={styles.prTitleRow}>
              <span className={styles.openPill}>
                <Icon name="git-pull-request" size={13} /> Open
              </span>
              <span className={styles.prTitle}>Add JWT auth middleware to gateway</span>
              <span className={styles.prNum}>#482</span>
            </div>
            <div className={styles.labels}>
              <span className={`${styles.label} ${styles.labelDanger}`}>security-concern</span>
              <span className={`${styles.label} ${styles.labelWarn}`}>needs-changes</span>
              <span className={`${styles.label} ${styles.labelAccent}`}>backend</span>
            </div>
          </div>

          {/* diff + bot comment */}
          <div className={styles.body}>
            <div className={styles.diff}>
              <div className={styles.diffLine}>
                <span className={styles.gutter}>14</span>
                <span className={styles.code} style={{ color: 'var(--fg-muted)' }}>
                  const token = req.headers.authorization;
                </span>
              </div>
              <div className={`${styles.diffLine} ${styles.diffRemoved}`}>
                <span className={`${styles.gutter} ${styles.gutterRemoved}`}>15</span>
                <span className={styles.code} style={{ color: 'var(--danger-fg)' }}>
                  - jwt.verify(token, secret, {'{'} algorithms: ['none'] {'}'})
                </span>
              </div>
              <div className={`${styles.diffLine} ${styles.diffAdded}`}>
                <span className={`${styles.gutter} ${styles.gutterAdded}`}>15</span>
                <span className={styles.code} style={{ color: 'var(--accent-code)' }}>
                  + jwt.verify(token, secret, {'{'} algorithms: ['RS256'] {'}'})
                </span>
              </div>
            </div>

            <div className={styles.commentRow}>
              <img src="/prlens_logo.png" alt="" className={styles.avatar} />
              <div className={styles.comment}>
                <div className={styles.commentHeader}>
                  <span className={styles.botName}>prlens-reviewer</span>
                  <span className={styles.botTag}>bot</span>
                  <span className={styles.commentedAt}>commented just now</span>
                  <span className={styles.critical}>
                    <Icon name="shield-alert" size={13} /> Critical
                  </span>
                </div>
                <div className={styles.commentBody}>
                  <strong style={{ color: 'var(--danger)' }}>Insecure JWT verification.</strong>{' '}
                  Passing <code className={styles.codeDanger}>algorithms: ['none']</code> disables
                  signature checks entirely, allowing forged tokens. Pin to{' '}
                  <code className={styles.codeOk}>['RS256']</code>.
                  <div className={styles.commentMeta}>
                    <span className={styles.metaItem}>
                      <Icon name="file-code" size={13} /> auth/middleware.js:15
                    </span>
                    <span className={styles.metaSep}>·</span>
                    <span>
                      Quality score impact: <strong style={{ color: 'var(--danger)' }}>−18</strong>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
