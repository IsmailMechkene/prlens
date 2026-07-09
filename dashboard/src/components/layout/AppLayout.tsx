import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import styles from './AppLayout.module.css'

/** Two-pane app shell: sticky sidebar + scrollable main content. */
export function AppLayout() {
  return (
    <div className={styles.shell}>
      <Sidebar />
      <main className={`${styles.main} prl-scroll`}>
        <Outlet />
      </main>
    </div>
  )
}
