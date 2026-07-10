import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/global.css'
import App from './App.tsx'
import { captureAuthToken } from './lib/api'

// Persist the post-OAuth `?token=` before React mounts, so the auth guard's very
// first /api/user request already carries the bearer token.
captureAuthToken()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
