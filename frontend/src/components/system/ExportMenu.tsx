/**
 * ExportMenu
 *
 * A compact dropdown that lets the user download data in MD, DOCX, or PDF
 * for a given export target on their project.
 *
 * Usage:
 *   <ExportMenu projectId={id} target="csuite" />
 *   <ExportMenu projectId={id} target="artifacts" label="Download All" />
 *   <ExportMenu projectId={id} target="artifact/prd" label="PRD" size="sm" />
 */
import { useState, useRef, useEffect } from 'react'
import { cn } from '../../lib/utils/cn'
import { useApiFetch } from '../../hooks/useApiFetch'

type Format = 'md' | 'docx' | 'pdf'

interface FormatMeta {
  fmt: Format
  label: string
  ext: string
  icon: string
}

const FORMATS: FormatMeta[] = [
  { fmt: 'md',   label: 'Markdown (.md)',   ext: 'md',   icon: 'draft' },
  { fmt: 'docx', label: 'Word (.docx)',      ext: 'docx', icon: 'description' },
  { fmt: 'pdf',  label: 'PDF (.pdf)',        ext: 'pdf',  icon: 'picture_as_pdf' },
]

interface ExportMenuProps {
  projectId: string
  /** Export target path segment, e.g. "csuite", "artifacts", or "artifact/prd" */
  target: string
  label?: string
  size?: 'sm' | 'md'
  className?: string
}

export function ExportMenu({
  projectId,
  target,
  label,
  size = 'md',
  className = '',
}: ExportMenuProps) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState<Format | null>(null)
  const [error, setError] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const apiFetch = useApiFetch()

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const download = async (fmt: Format) => {
    setLoading(fmt)
    setError(null)
    try {
      const path = `/api/v1/projects/${projectId}/export/${target}.${fmt}`
      const resp = await apiFetch(path)
      if (!resp.ok) {
        const msg = await resp.text().catch(() => resp.statusText)
        throw new Error(msg || `HTTP ${resp.status}`)
      }
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const cd = resp.headers.get('Content-Disposition') ?? ''
      const match = cd.match(/filename="([^"]+)"/)
      a.download = match?.[1] ?? `${target.replace('/', '_')}.${fmt}`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      setOpen(false)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Download failed')
    } finally {
      setLoading(null)
    }
  }

  const isSm = size === 'sm'

  return (
    <div ref={menuRef} className={cn('relative inline-block', className)}>
      <button
        onClick={() => { setOpen((o) => !o); setError(null) }}
        className={cn(
          'inline-flex items-center rounded-full border transition-colors',
          'border-outline-variant/30 bg-surface-container text-on-surface',
          'hover:bg-surface-container-lowest font-black uppercase',
          isSm ? 'gap-1 px-2 py-1' : 'gap-1.5 px-3 py-1.5',
        )}
        style={{
          fontSize: isSm ? '0.6rem' : '0.65rem',
          fontWeight: 900,
          letterSpacing: '0.08em',
        }}
        title="Download report"
        aria-haspopup="true"
        aria-expanded={open}
      >
        <span className="material-symbols-outlined" style={{ fontSize: isSm ? '13px' : '15px' }}>
          download
        </span>
        {label ?? 'Download'}
      </button>

      {open && (
        <div className="absolute right-0 mt-1 w-48 rounded-xl shadow-2xl bg-surface-container border border-outline-variant/30 z-50 overflow-hidden">
          {error && (
            <p
              className="px-3 py-2 text-error border-b border-outline-variant/30"
              style={{ fontSize: '0.65rem' }}
            >
              {error}
            </p>
          )}
          {FORMATS.map(({ fmt, label: fmtLabel, icon }) => (
            <button
              key={fmt}
              onClick={() => download(fmt)}
              disabled={loading !== null}
              className={cn(
                'flex w-full items-center gap-2 px-3 py-2.5 transition-colors',
                'text-on-surface hover:bg-surface-container-lowest',
                'uppercase font-black disabled:opacity-50',
              )}
              style={{ fontSize: '0.65rem', fontWeight: 900, letterSpacing: '0.06em' }}
            >
              {loading === fmt ? (
                <span className="h-3.5 w-3.5 rounded-full border-2 border-outline-variant border-t-primary animate-spin" />
              ) : (
                <span className="material-symbols-outlined text-tertiary" style={{ fontSize: '15px' }}>
                  {icon}
                </span>
              )}
              {fmtLabel}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
