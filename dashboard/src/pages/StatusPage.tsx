import { StaticPageShell } from '../components/legal/StaticPageShell'
import { api, type HealthCheck } from '../lib/api'
import { useAsync } from '../lib/useAsync'
import styles from './StatusPage.module.css'

interface Probe extends HealthCheck {
  at: Date
}

export function StatusPage() {
  const { data: probe, loading, reload } = useAsync<Probe>(
    async () => ({ ...(await api.getHealth()), at: new Date() }),
    [],
  )

  const apiOk = !loading && probe !== undefined && probe.ok
  const apiDown = !loading && probe !== undefined && !probe.ok

  return (
    <StaticPageShell
      title="Status"
      subtitle="Live availability of the PRLens services, checked from your browser."
    >
      <div
        className={`${styles.banner} ${apiOk ? styles.bannerOk : apiDown ? styles.bannerDown : ''}`}
      >
        <span
          className={`${styles.dot} ${apiOk ? styles.dotOk : apiDown ? styles.dotDown : styles.dotChecking}`}
        />
        <span className={styles.bannerText}>
          {loading
            ? 'Checking systems…'
            : apiOk
              ? 'All systems operational'
              : 'Service disruption — the API is unreachable'}
        </span>
        <span className={styles.checked}>
          {probe && !loading && `Checked at ${probe.at.toLocaleTimeString()} · `}
          <button type="button" className={styles.refresh} onClick={reload} disabled={loading}>
            Refresh
          </button>
        </span>
      </div>

      <div className={styles.list}>
        <ComponentRow
          name="Dashboard"
          desc="This web app — the UI you are looking at right now."
          checking={false}
          ok
        />
        <ComponentRow
          name="API & webhook service"
          desc="Serves the dashboard's data and receives pull request events from GitHub."
          checking={loading}
          ok={apiOk}
          latencyMs={probe?.latencyMs}
        />
        <ComponentRow
          name="Automated reviews"
          desc="The GitHub App that analyzes pull requests. Runs on the webhook service above."
          checking={loading}
          ok={apiOk}
        />
      </div>

      <h2 id="about">About this page</h2>
      <p>
        The check above is performed live from your browser against the API's health endpoint, so
        it reflects reachability from your network. Webhook events delivered during an outage are
        not replayed automatically — if a pull request opened while the API was down never got a
        review, push a new commit to it to trigger one.
      </p>
      <p>
        Having trouble that this page doesn't explain? Check the{' '}
        <a href="https://github.com/IsmailMechkene/prlens/issues" target="_blank" rel="noreferrer">
          issue tracker
        </a>{' '}
        or open a new issue.
      </p>
    </StaticPageShell>
  )
}

function ComponentRow({
  name,
  desc,
  checking,
  ok,
  latencyMs,
}: {
  name: string
  desc: string
  checking: boolean
  ok: boolean
  latencyMs?: number
}) {
  const down = !checking && !ok

  return (
    <div className={styles.row}>
      <span
        className={`${styles.dot} ${checking ? styles.dotChecking : ok ? styles.dotOk : styles.dotDown}`}
      />
      <div>
        <div className={styles.rowName}>{name}</div>
        <div className={styles.rowDesc}>{desc}</div>
      </div>
      <span
        className={`${styles.rowState} ${checking ? styles.stateChecking : ok ? styles.stateOk : styles.stateDown}`}
      >
        {checking ? 'Checking…' : down ? 'Down' : 'Operational'}
        {ok && !checking && latencyMs !== undefined && (
          <span className={styles.latency}>{latencyMs} ms</span>
        )}
      </span>
    </div>
  )
}
