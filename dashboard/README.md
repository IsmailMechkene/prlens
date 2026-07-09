# PRLens Dashboard

The web UI for **PRLens** — AI code review for GitHub. Built with React 19, Vite,
TypeScript, and React Router. Implemented from the `PRLens.dc.html` design,
split into small, focused components.

## Getting started

```bash
npm install
npm run dev      # start the dev server
npm run build    # type-check + production build
npm run lint     # eslint
```

By default the app runs against **local mock data** so you can browse the whole
UI with no backend. To point it at a real API, set `VITE_API_BASE_URL`:

```bash
# dashboard/.env.local
VITE_API_BASE_URL=https://your-backend.example.com
```

The endpoints and JSON shapes the backend must provide are documented in
`BACKEND_CONTRACT.md` (gitignored — local integration notes).

## Routes

| Path             | Screen                                              |
| ---------------- | --------------------------------------------------- |
| `/`              | Marketing landing page                              |
| `/dashboard`     | Activity overview: stat tiles + recent reviews      |
| `/repos/:name`   | Repo detail: score trend, issues donut, settings    |
| `/connect`       | Connect / enable repositories                       |

## Structure

```
src/
├─ main.tsx                 # entry — mounts <App/> + global styles
├─ App.tsx                  # ThemeProvider + Router
├─ styles/global.css        # design tokens (GitHub-dark palette) + fonts
├─ theme/                   # accent / corners / density theming (CSS vars)
├─ lib/                     # types, API client, mock data, helpers, useAsync
├─ components/
│  ├─ ui/                   # Button, Card, Icon, ScoreBadge, Toggle, …
│  ├─ landing/              # Navbar, Hero, PullRequestPreview, Features, Footer
│  ├─ layout/               # AppLayout, Sidebar, PageHeader, ThemeControls
│  ├─ dashboard/            # StatCard, ReviewsTable
│  ├─ repo/                 # QualityTrendChart, IssuesDonut, RecentReviews, ReviewSettings
│  └─ connect/              # ConnectRepoRow
└─ pages/                   # LandingPage, DashboardPage, RepoDetailPage, ConnectPage
```

## Design system

- **Palette** — centralised as CSS custom properties in `styles/global.css`
  (GitHub "dark" colours), so components reference `var(--bg-surface)`,
  `var(--fg-muted)`, `var(--danger)`, … instead of hard-coded hex.
- **Theming** — the sidebar settings gear opens live controls for accent
  colour, corner radius, and density. These map to `--pa*`, `--rad*`, and
  `--dsc` tokens and persist in `localStorage`.
- **Icons** — [lucide](https://lucide.dev) via a small registry in
  `components/ui/Icon.tsx`; data references icons by kebab-case name.
