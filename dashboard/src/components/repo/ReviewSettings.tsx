import { useState } from 'react'
import type { KeyboardEvent } from 'react'
import { api } from '../../lib/api'
import { accentMix } from '../../theme/theme'
import type { RepoSettings, Severity } from '../../lib/types'
import { Icon } from '../ui/Icon'
import { Button } from '../ui/Button'
import { Select } from '../ui/Select'
import styles from './ReviewSettings.module.css'

const SEVERITIES: Severity[] = ['info', 'warning', 'error', 'critical']

// The backend maps these onto the ReviewType enum and drops anything it does not
// recognise, so the key has to be a fixed choice rather than free text.
const REVIEW_TYPES = ['quality', 'security', 'performance', 'style', 'documentation']

interface ReviewSettingsProps {
  repo: string
  initial: RepoSettings
}

export function ReviewSettings({ repo, initial }: ReviewSettingsProps) {
  const [settings, setSettings] = useState<RepoSettings>(initial)
  const [excludedInput, setExcludedInput] = useState('')
  const [focusRow, setFocusRow] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [failed, setFailed] = useState(false)

  const patch = (next: Partial<RepoSettings>) => {
    setSettings((prev) => ({ ...prev, ...next }))
    setSaved(false)
    setFailed(false)
  }

  const toggleLang = (lang: string) =>
    patch({ languages: { ...settings.languages, [lang]: !settings.languages[lang] } })

  const removeExcluded = (idx: number) =>
    patch({ excluded: settings.excluded.filter((_, i) => i !== idx) })

  const addExcluded = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && excludedInput.trim()) {
      e.preventDefault()
      patch({ excluded: [...settings.excluded, excludedInput.trim()] })
      setExcludedInput('')
    }
  }

  // A review type already mapped cannot be picked again: the backend keys the map
  // by type, so a duplicate row would silently overwrite the one above it.
  const unusedTypes = REVIEW_TYPES.filter(
    (t) => !settings.reviewerMap.some((m) => m.key === t),
  )

  const addMapping = () => {
    const next = unusedTypes[0]
    if (!next) return
    setFocusRow(settings.reviewerMap.length)
    patch({ reviewerMap: [...settings.reviewerMap, { key: next, value: '' }] })
  }

  const setMapping = (idx: number, next: Partial<{ key: string; value: string }>) =>
    patch({
      reviewerMap: settings.reviewerMap.map((m, i) => (i === idx ? { ...m, ...next } : m)),
    })

  const removeMapping = (idx: number) =>
    patch({ reviewerMap: settings.reviewerMap.filter((_, i) => i !== idx) })

  const save = async () => {
    setSaving(true)
    setFailed(false)
    // A row whose reviewer was never filled in is an unfinished edit, not a
    // mapping to store — sending it would map the type to an empty reviewer.
    const payload = {
      ...settings,
      reviewerMap: settings.reviewerMap
        .map((m) => ({ ...m, value: m.value.trim() }))
        .filter((m) => m.value),
    }
    try {
      await api.updateRepoSettings(repo, payload)
      setSettings(payload)
      setSaved(true)
    } catch {
      // A rejected save used to leave the button back on "Save changes" with no
      // other sign, so the user believed a change had been stored that had not.
      setFailed(true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={styles.body}>
      {/* Minimum severity */}
      <div className={styles.field}>
        <label className={styles.label}>Minimum severity</label>
        <div className={styles.sevRow}>
          {SEVERITIES.map((sv) => {
            const on = settings.minSeverity === sv
            return (
              <button
                key={sv}
                type="button"
                className={styles.sevBtn}
                data-on={on}
                style={
                  on
                    ? { borderColor: 'var(--pa)', background: accentMix(15), color: 'var(--pa)' }
                    : undefined
                }
                onClick={() => patch({ minSeverity: sv })}
              >
                {sv}
              </button>
            )
          })}
        </div>
      </div>

      {/* Languages */}
      <div className={styles.field}>
        <label className={styles.label}>Target languages</label>
        <div className={styles.langGrid}>
          {Object.entries(settings.languages).map(([lang, on]) => (
            <button
              key={lang}
              type="button"
              className={styles.lang}
              data-on={on}
              style={
                on
                  ? { borderColor: 'var(--pa-t40)', background: accentMix(9) }
                  : undefined
              }
              onClick={() => toggleLang(lang)}
              aria-pressed={on}
            >
              <span
                className={styles.checkbox}
                style={{
                  borderColor: on ? 'var(--pa)' : 'var(--border-strong)',
                  background: on ? 'var(--pa)' : 'transparent',
                }}
              >
                <Icon name="check" size={12} color="#fff" style={{ opacity: on ? 1 : 0 }} />
              </span>
              <span className={styles.langName}>{lang}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Approve threshold */}
      <div className={styles.field}>
        <div className={styles.sliderHead}>
          <label className={styles.label}>Approve threshold</label>
          <span className={styles.sliderVal} style={{ color: 'var(--success)' }}>
            {settings.approveThreshold}
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          value={settings.approveThreshold}
          onChange={(e) => patch({ approveThreshold: Number(e.target.value) })}
          className={styles.slider}
          style={{ accentColor: 'var(--success)' }}
        />
      </div>

      {/* Request-changes threshold */}
      <div className={styles.field}>
        <div className={styles.sliderHead}>
          <label className={styles.label}>Request-changes threshold</label>
          <span className={styles.sliderVal} style={{ color: 'var(--attention)' }}>
            {settings.changesThreshold}
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          value={settings.changesThreshold}
          onChange={(e) => patch({ changesThreshold: Number(e.target.value) })}
          className={styles.slider}
          style={{ accentColor: 'var(--attention)' }}
        />
      </div>

      {/* Excluded files */}
      <div className={styles.field}>
        <label className={styles.label}>Excluded files</label>
        <div className={styles.tagBox}>
          {settings.excluded.map((pattern, i) => (
            <span key={pattern} className={styles.tag}>
              {pattern}
              <button
                type="button"
                className={styles.tagRemove}
                aria-label={`Remove ${pattern}`}
                onClick={() => removeExcluded(i)}
              >
                <Icon name="x" size={13} />
              </button>
            </span>
          ))}
          <input
            value={excludedInput}
            onChange={(e) => setExcludedInput(e.target.value)}
            onKeyDown={addExcluded}
            placeholder="Add pattern, then press Enter…"
            className={styles.tagInput}
          />
        </div>
      </div>

      {/* Reviewer mapping */}
      <div className={styles.field}>
        <label className={styles.label}>Reviewer mapping</label>
        <div className={styles.mapList}>
          {settings.reviewerMap.map((m, i) => (
            <div key={m.key} className={styles.mapRow}>
              <Select
                className={styles.mapKey}
                value={m.key}
                label="Review type"
                valueStyle={{ color: 'var(--danger)' }}
                /* Its own type stays selectable; the rest are the unused ones. */
                options={[m.key, ...unusedTypes].map((t) => ({ value: t, label: t }))}
                onChange={(key) => setMapping(i, { key })}
              />
              <Icon name="arrow-right" size={14} className={styles.mapArrow} />
              <input
                className={styles.mapVal}
                value={m.value}
                autoFocus={i === focusRow}
                placeholder="username or team:slug"
                aria-label={`Reviewer for ${m.key}`}
                onChange={(e) => setMapping(i, { value: e.target.value })}
              />
              <button
                type="button"
                className={styles.mapRemove}
                aria-label={`Remove ${m.key} mapping`}
                onClick={() => removeMapping(i)}
              >
                <Icon name="x" size={14} />
              </button>
            </div>
          ))}
          <button
            type="button"
            className={styles.addMapping}
            onClick={addMapping}
            disabled={unusedTypes.length === 0}
          >
            <Icon name="plus" size={14} />
            {unusedTypes.length === 0 ? 'All review types mapped' : 'Add mapping'}
          </button>
        </div>
        <p className={styles.mapHint}>
          A GitHub username (no “@”) or <code>team:slug</code>. Reviewers are only
          requested when a PR has a <strong>critical</strong> issue, and must be
          collaborators on the repo.
        </p>
      </div>

      {/* Save */}
      <div className={styles.saveRow}>
        <Button variant="primary" onClick={save} disabled={saving}>
          <Icon name={saved ? 'check' : 'save'} size={15} />
          {saving ? 'Saving…' : saved ? 'Saved' : 'Save changes'}
        </Button>
        {failed ? (
          <span className={styles.saveHint} style={{ color: 'var(--danger)' }} role="alert">
            <Icon name="circle-alert" size={13} /> Couldn’t save — nothing was changed. Try again.
          </span>
        ) : (
          <span className={styles.saveHint}>Applies to all new pull requests.</span>
        )}
      </div>
    </div>
  )
}
