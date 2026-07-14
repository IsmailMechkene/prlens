import { useCallback, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { api } from '../../lib/api'
import { useAsync } from '../../lib/useAsync'
import { Icon } from '../ui/Icon'
import { Logo } from '../ui/Logo'
import { Skeleton } from '../ui/Skeleton'
import { LogoutDialog } from './LogoutDialog'
import { ThemeControls } from './ThemeControls'
import styles from './Sidebar.module.css'

export function Sidebar() {
  const [themeOpen, setThemeOpen] = useState(false)
  const [logoutOpen, setLogoutOpen] = useState(false)

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
        <Logo size={30} />
      </div>

      <nav className={styles.nav}>
        <NavLink to="/dashboard" className={navClass}>
          <Icon name="layout-dashboard" size={16} /> Dashboard
        </NavLink>
        <NavLink to="/connect" className={navClass}>
          <Icon name="circle-plus" size={16} /> Connect repo
        </NavLink>
        {/* Offered to admins only, and *in addition to* Dashboard above — an admin
            still has their own repos, so both links stay live and they switch
            between the two views at will. Hiding this is not the access control:
            /api/admin re-checks the role on every request. */}
        {user.data?.role === 'admin' && (
          <NavLink to="/admin" className={navClass}>
            <Icon name="users" size={16} /> Admin
          </NavLink>
        )}
      </nav>

      <div className={`${styles.repos} prl-scroll`}>
        <div className={styles.reposLabel}>Repositories</div>
        {connected.map((r) => (
          <NavLink
            key={r.name}
            to={`/repos/${encodeURIComponent(r.name)}`}
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
        {repos.loading &&
          repos.data === undefined &&
          [0, 1, 2, 3].map((i) => (
            <div key={i} className={styles.repoSkeleton}>
              <Skeleton width={14} height={14} radius={3} />
              <Skeleton width={`${58 + i * 9}%`} height={12} />
            </div>
          ))}
        {repos.error && <div className={styles.reposHint}>Couldn’t load repos</div>}
      </div>

      <div className={styles.footer}>
        {themeOpen && <ThemeControls onClose={() => setThemeOpen(false)} />}
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
          <button
            type="button"
            className={styles.gear}
            aria-label="Disconnect from account"
            title="Disconnect from account"
            onClick={() => setLogoutOpen(true)}
          >
            <Icon name="log-out" size={16} />
          </button>
        </div>
      </div>

      <LogoutDialog open={logoutOpen} onCancel={() => setLogoutOpen(false)} />
    </aside>
  )
}
