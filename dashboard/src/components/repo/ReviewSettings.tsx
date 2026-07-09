import { useState } from 'react'
import type { KeyboardEvent } from 'react'
import { api } from '../../lib/api'
import { accentMix } from '../../theme/theme'
import type { RepoSettings, Severity } from '../../lib/types'
import { Icon } from '../ui/Icon'
import { Button } from '../ui/Button'
import styles from './ReviewSettings.module.css'

const SEVERITIES: Severity[] = ['info', 'warning', 'error', 'critical']

interface ReviewSettingsProps {
  repo: string
  initial: RepoSettings
}

export function ReviewSettings({ repo, initial }: ReviewSettingsProps) {
  const [settings, setSettings] = useState<RepoSettings>(initial)
  const [excludedInput, setExcludedInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const patch = (next: Partial<RepoSettings>) => {
    setSettings((prev) => ({ ...prev, ...next }))
    setSaved(false)
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

  const save = async () => {
    setSaving(true)
    try {
      await api.updateRepoSettings(repo, settings)
      setSaved(true)
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
            placeholder="Add pattern…"
            className={styles.tagInput}
          />
        </div>
      </div>

      {/* Reviewer mapping */}
      <div className={styles.field}>
        <label className={styles.label}>Reviewer mapping</label>
        <div className={styles.mapList}>
          {settings.reviewerMap.map((m) => (
            <div key={m.key} className={styles.mapRow}>
              <span className={styles.mapKey} style={{ color: 'var(--danger)' }}>
                {m.key}
              </span>
              <Icon name="arrow-right" size={14} className={styles.mapArrow} />
              <span className={styles.mapVal}>{m.value}</span>
            </div>
          ))}
          <button type="button" className={styles.addMapping}>
            <Icon name="plus" size={14} /> Add mapping
          </button>
        </div>
      </div>

      {/* Save */}
      <div className={styles.saveRow}>
        <Button variant="primary" onClick={save} disabled={saving}>
          <Icon name={saved ? 'check' : 'save'} size={15} />
          {saving ? 'Saving…' : saved ? 'Saved' : 'Save changes'}
        </Button>
        <span className={styles.saveHint}>Applies to all new pull requests.</span>
      </div>
    </div>
  )
}
