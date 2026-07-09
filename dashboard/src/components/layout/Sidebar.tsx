import { useCallback, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { api } from '../../lib/api'
import { useAsync } from '../../lib/useAsync'
import { Icon } from '../ui/Icon'
import { Logo } from '../ui/Logo'
import { ThemeControls } from './ThemeControls'
import styles from './Sidebar.module.css'

export function Sidebar() {
  const navigate = useNavigate()
  const [themeOpen, setThemeOpen] = useState(false)

  const repos = useAsync(() => api.getRepos(), [])
  const user = useAsync(() => api.getUser(), [])

  const navClass = useCallback(
    ({ isActive }: { isActive: boolean }) =>
      `${styles.navItem} ${isActive ? styles.navItemActive : ''}`,
    [],
  )

  const connected = (repos.data ?? []).filter((r) => r.connected)

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <button type="button" className={styles.brandBtn} onClick={() => navigate('/')}>
          <Logo size={30} />
        </button>
      </div>

      <nav className={styles.nav}>
        <NavLink to="/dashboard" className={navClass}>
          <Icon name="layout-dashboard" size={16} /> Dashboard
        </NavLink>
        <NavLink to="/connect" className={navClass}>
          <Icon name="circle-plus" size={16} /> Connect repo
        </NavLink>
      </nav>

      <div className={`${styles.repos} prl-scroll`}>
        <div className={styles.reposLabel}>Repositories</div>
        {connected.map((r) => (
          <NavLink
            key={r.name}
            to={`/repos/${r.name}`}
            className={({ isActive }) =>
              `${styles.repo} ${isActive ? styles.repoActive : ''}`
            }
          >
            <Icon name={r.visibility === 'Public' ? 'book' : 'lock'} size={14} className={styles.repoIcon} />
            <span className={styles.repoName}>{r.name}</span>
            <span
              className={styles.repoDot}
              style={{ background: r.active ? 'var(--success)' : 'var(--fg-subtle)' }}
              title={r.active ? 'Active' : 'Inactive'}
            />
          </NavLink>
        ))}
        {repos.loading && <div className={styles.reposHint}>Loading…</div>}
        {repos.error && <div className={styles.reposHint}>Couldn’t load repos</div>}
      </div>

      <div className={styles.footer}>
        {themeOpen && <ThemeControls />}
        <div className={styles.user}>
          <div className={styles.avatar}>{user.data?.initials ?? '··'}</div>
          <div className={styles.userMeta}>
            <div className={styles.userName}>{user.data?.name ?? 'Loading…'}</div>
            <div className={styles.userHandle}>{user.data?.handle ?? ''}</div>
          </div>
          <button
            type="button"
            className={styles.gear}
            aria-label="Theme settings"
            aria-pressed={themeOpen}
            onClick={() => setThemeOpen((v) => !v)}
          >
            <Icon name="settings" size={16} />
          </button>
        </div>
      </div>
    </aside>
  )
}
