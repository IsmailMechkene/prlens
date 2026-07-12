import type { DisconnectResult } from './types'

/**
 * Disconnecting is destructive and not undoable — it deletes the repo's settings
 * and its whole review history — so both entry points (the Connect list and the
 * repo page) ask first, in the same words.
 */
export function confirmDisconnect(name: string): boolean {
  return window.confirm(
    `Remove PRLens from ${name}?\n\n` +
      'Its review history, issue stats and settings are deleted, and the repository ' +
      'is detached from the PRLens GitHub App so it stops being reviewed.\n\n' +
      'This cannot be undone. You can reconnect the repo later, but the history is gone.',
  )
}

/**
 * Say so when the rows went but GitHub did not: the repo is off the dashboard yet
 * still attached to the App, so it would keep being reviewed. Silence here would
 * be a lie about what "disconnect" did.
 */
export function reportDisconnect(name: string, result: DisconnectResult): void {
  if (result.githubRemoved) return

  window.alert(
    `${name} was removed from PRLens, but it could not be detached from the PRLens ` +
      'GitHub App — so GitHub may keep sending pull requests for review.\n\n' +
      'Remove it yourself under GitHub → Settings → Applications → PRLens → ' +
      'Configure.',
  )
}
