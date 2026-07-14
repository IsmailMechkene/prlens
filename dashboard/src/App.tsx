import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ThemeProvider } from './theme/ThemeProvider'
import { AppLayout } from './components/layout/AppLayout'
import { RequireAuth } from './components/layout/RequireAuth'
import { RequireAdmin } from './components/layout/RequireAdmin'
import { LandingPage } from './pages/LandingPage'
import { DashboardPage } from './pages/DashboardPage'
import { RepoDetailPage } from './pages/RepoDetailPage'
import { ConnectPage } from './pages/ConnectPage'
import { AdminPage } from './pages/AdminPage'
import { AdminUserPage } from './pages/AdminUserPage'
import { FeaturesPage } from './pages/FeaturesPage'
import { DocsPage } from './pages/DocsPage'
import { PrivacyPage } from './pages/PrivacyPage'
import { TermsPage } from './pages/TermsPage'
import { StatusPage } from './pages/StatusPage'

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/features" element={<FeaturesPage />} />
          <Route path="/docs" element={<DocsPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/status" element={<StatusPage />} />
          <Route element={<RequireAuth />}>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              {/* Splat, not ":name": a repo name is a GitHub full_name
                  ("acme/api-gateway"), and a :param matches a single path segment.
                  A URL that reached the browser with the slash decoded therefore
                  matched no route and fell through to the catch-all below, which
                  bounced the user out to the landing page on every reload. */}
              <Route path="/repos/*" element={<RepoDetailPage />} />
              <Route path="/connect" element={<ConnectPage />} />
              {/* The admin section sits inside the same shell as everything else, so
                  an admin moves between it and their own dashboard the way they move
                  between any two pages. RequireAdmin only adds the role check — the
                  session has already been established by RequireAuth above. */}
              <Route element={<RequireAdmin />}>
                <Route path="/admin" element={<AdminPage />} />
                <Route path="/admin/users/:id" element={<AdminUserPage />} />
              </Route>
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}
