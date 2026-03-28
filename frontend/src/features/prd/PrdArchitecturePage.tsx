import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../lib/utils/cn'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type PrdState = 'loading' | 'loaded' | 'error'

const tabs = [
  { id: 'prd',          label: 'PRD',                    icon: 'description',  short: 'PRD' },
  { id: 'architecture', label: 'Architecture',            icon: 'schema',       short: 'ARCH' },
  { id: 'db_plan',      label: 'DB Plan',                icon: 'database',     short: 'DB' },
  { id: 'auth_plan',    label: 'Auth Plan',              icon: 'lock_person',  short: 'AUTH' },
  { id: 'phases',       label: 'Implementation Phases',  icon: 'route',        short: 'PHASES' },
]

const artifactTypeMap: Record<string, string> = {
  prd:          'prd',
  architecture: 'tech_spec',
  db_plan:      'db_plan',
  auth_plan:    'auth_plan',
  phases:       'implementation_phases',
}

const tabAccents: Record<string, string> = {
  prd:          '#ed6746',
  architecture: '#86d0f5',
  db_plan:      '#34d399',
  auth_plan:    '#fbbf24',
  phases:       '#c084fc',
}

function PrdArchitecturePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { getAccessToken } = useAuth()
  const [state, setState] = useState<PrdState>('loading')
  const [activeTab, setActiveTab] = useState('prd')
  const [artifacts, setArtifacts] = useState<Record<string, any>>({})
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!projectId || projectId === 'new') return
    ;(async () => {
      try {
        const token = await getAccessToken()
        const res = await fetch(`/api/v1/projects/${projectId}/artifacts`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (res.ok) {
          const data = await res.json()
          const map: Record<string, any> = {}
          for (const a of (data.artifacts || data || [])) {
            map[a.type] = a
          }
          setArtifacts(map)
          setState('loaded')
        } else {
          setState('error')
        }
      } catch {
        setState('error')
      }
    })()
  }, [projectId, getAccessToken])

  const handleTabChange = (id: string) => {
    setActiveTab(id)
    contentRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const accent = tabAccents[activeTab]
  const artifact = artifacts[artifactTypeMap[activeTab]]
  const content = artifact
    ? (typeof artifact.content === 'string' ? artifact.content : JSON.stringify(artifact.content, null, 2))
    : null

  return (
    <div className="flex flex-col h-full min-h-0" style={{ '--tab-accent': accent } as React.CSSProperties}>

      {/* ── Page header ─────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        className="shrink-0 px-8 pt-8 pb-0"
      >
        <div className="flex items-end justify-between mb-6">
          <div>
            <p
              className="uppercase font-black tracking-widest text-tertiary mb-1"
              style={{ fontSize: '0.55rem', letterSpacing: '0.18em' }}
            >
              Planning Artifacts
            </p>
            <h1
              className="font-black uppercase text-on-surface leading-none"
              style={{ fontSize: 'clamp(1.8rem, 4vw, 2.6rem)', letterSpacing: '-0.04em' }}
            >
              PRD &amp; Architecture
            </h1>
          </div>

          {/* Artifact status badge */}
          {artifact && artifact.status === 'complete' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full border"
              style={{
                color: '#34d399',
                background: 'color-mix(in srgb, #34d399 8%, transparent)',
                borderColor: 'color-mix(in srgb, #34d399 20%, transparent)',
              }}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-[#34d399]" />
              <span className="font-black uppercase" style={{ fontSize: '0.55rem', letterSpacing: '0.15em' }}>
                Complete · {new Date(artifact.updated_at || artifact.created_at).toLocaleDateString()}
              </span>
            </motion.div>
          )}
        </div>

        {/* ── Tab rail ─────────────────────────────────────── */}
        <div className="flex items-end gap-0 relative">
          {tabs.map(({ id, label, icon }) => {
            const isActive = activeTab === id
            const tabColor = tabAccents[id]
            return (
              <button
                key={id}
                onClick={() => handleTabChange(id)}
                className={cn(
                  'group relative flex items-center gap-2 px-5 py-3 transition-all duration-200',
                  'rounded-t-xl border-t border-l border-r',
                  isActive
                    ? 'bg-surface-container-lowest border-outline-variant/30 translate-y-px'
                    : 'bg-surface-container-low/50 border-transparent text-on-surface/30 hover:text-on-surface/60 hover:bg-surface-container-low',
                )}
                style={{
                  ...(isActive ? {
                    color: tabColor,
                    borderBottom: `2px solid ${tabColor}`,
                  } : {}),
                }}
              >
                <span
                  className="material-symbols-outlined shrink-0 transition-all"
                  style={{ fontSize: '15px' }}
                >
                  {icon}
                </span>
                <span
                  className="font-black uppercase whitespace-nowrap hidden sm:inline"
                  style={{ fontSize: '0.6rem', letterSpacing: '0.1em' }}
                >
                  {label}
                </span>
                <span
                  className="font-black uppercase sm:hidden"
                  style={{ fontSize: '0.6rem', letterSpacing: '0.1em' }}
                >
                  {tabs.find(t => t.id === id)?.short}
                </span>
                {isActive && (
                  <motion.div
                    layoutId="tab-glow"
                    className="absolute inset-0 rounded-t-xl pointer-events-none"
                    style={{ background: `radial-gradient(ellipse at 50% 100%, color-mix(in srgb, ${tabColor} 12%, transparent), transparent 70%)` }}
                    transition={{ duration: 0.25 }}
                  />
                )}
              </button>
            )
          })}
          {/* Bottom border underline for non-active area */}
          <div className="flex-1 border-b border-outline-variant/30 self-end" />
        </div>
      </motion.div>

      {/* ── Document panel ──────────────────────────────────── */}
      <div
        ref={contentRef}
        className="flex-1 min-h-0 overflow-y-auto bg-surface-container-lowest border-l border-r border-b border-outline-variant/30 mx-8 mb-8 rounded-b-2xl"
        style={{ scrollbarWidth: 'thin', scrollbarColor: 'var(--sys-outline-variant) transparent' }}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="h-full"
          >
            {state === 'loading' ? (
              <DocumentSkeleton />
            ) : state === 'error' ? (
              <DocumentEmpty icon="error" message="Failed to load artifacts." sub="Check your connection and try again." />
            ) : !artifact || artifact.status === 'pending' ? (
              <DocumentEmpty
                icon="hourglass_empty"
                message={`No ${activeTab.replace(/_/g, ' ')} generated yet.`}
                sub="Complete the C-Suite analysis to auto-generate planning artifacts."
              />
            ) : artifact.status === 'generating' ? (
              <DocumentGenerating label={tabs.find(t => t.id === activeTab)?.label || activeTab} accent={accent} />
            ) : (
              <DocumentContent content={content || ''} accent={accent} />
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}

// ── Sub-components ──────────────────────────────────────────────────────────

function DocumentSkeleton() {
  return (
    <div className="p-10 space-y-6 animate-pulse">
      <div className="space-y-3">
        <div className="h-7 bg-surface-container rounded-lg w-2/3" />
        <div className="h-4 bg-surface-container rounded w-1/3" />
      </div>
      <div className="h-px bg-outline-variant/20 w-full" />
      {[0.9, 0.7, 0.8, 0.6, 0.75].map((w, i) => (
        <div key={i} className="h-4 bg-surface-container rounded" style={{ width: `${w * 100}%` }} />
      ))}
      <div className="space-y-2 pt-4">
        <div className="h-5 bg-surface-container rounded w-1/4" />
        {[0.85, 0.65, 0.9, 0.7].map((w, i) => (
          <div key={i} className="h-4 bg-surface-container rounded ml-4" style={{ width: `${w * 100}%` }} />
        ))}
      </div>
    </div>
  )
}

function DocumentEmpty({ icon, message, sub }: { icon: string; message: string; sub: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-64 gap-4 py-24">
      <span
        className="material-symbols-outlined text-outline-variant/40"
        style={{ fontSize: '48px', fontVariationSettings: "'wght' 200" }}
      >
        {icon}
      </span>
      <p className="font-black uppercase tracking-widest text-on-surface/25" style={{ fontSize: '0.65rem' }}>
        {message}
      </p>
      <p className="font-black uppercase tracking-widest text-on-surface/15" style={{ fontSize: '0.55rem' }}>
        {sub}
      </p>
    </div>
  )
}

function DocumentGenerating({ label, accent }: { label: string; accent: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-64 gap-5 py-24">
      <div
        className="w-10 h-10 rounded-full border-2 border-t-transparent animate-spin"
        style={{ borderColor: `color-mix(in srgb, ${accent} 30%, transparent)`, borderTopColor: accent }}
      />
      <p className="font-black uppercase tracking-widest" style={{ fontSize: '0.6rem', color: accent }}>
        Generating {label}…
      </p>
    </div>
  )
}

function DocumentContent({ content, accent }: { content: string; accent: string }) {
  return (
    <div className="px-10 py-10 max-w-4xl">
      <div
        className="prd-prose"
        style={{ '--prose-accent': accent } as React.CSSProperties}
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => (
              <h1 className="prd-h1">{children}</h1>
            ),
            h2: ({ children }) => (
              <h2 className="prd-h2">
                <span className="prd-h2-bar" style={{ background: accent }} />
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="prd-h3">{children}</h3>
            ),
            h4: ({ children }) => (
              <h4 className="prd-h4">{children}</h4>
            ),
            p: ({ children }) => (
              <div className="prd-p">{children}</div>
            ),
            ul: ({ children }) => (
              <ul className="prd-ul">{children}</ul>
            ),
            ol: ({ children }) => (
              <ol className="prd-ol">{children}</ol>
            ),
            li: ({ children }) => (
              <li className="prd-li">
                <span className="prd-li-dot" style={{ background: accent }} />
                <span>{children}</span>
              </li>
            ),
            pre: ({ children }) => (
              <pre className="prd-code-block">{children}</pre>
            ),
            code: ({ node, children, ...props }: any) => {
              const isBlock = node?.position?.start?.line !== node?.position?.end?.line
                || String(children).includes('\n')
              if (isBlock) {
                return <code {...props}>{children}</code>
              }
              return (
                <code className="prd-code-inline" style={{ color: accent, borderColor: `color-mix(in srgb, ${accent} 25%, transparent)` }}>
                  {children}
                </code>
              )
            },
            blockquote: ({ children }) => (
              <blockquote className="prd-blockquote" style={{ borderLeftColor: accent }}>
                {children}
              </blockquote>
            ),
            hr: () => (
              <hr className="prd-hr" style={{ borderColor: `color-mix(in srgb, ${accent} 20%, transparent)` }} />
            ),
            table: ({ children }) => (
              <div className="prd-table-wrap">
                <table className="prd-table">{children}</table>
              </div>
            ),
            thead: ({ children }) => <thead className="prd-thead" style={{ borderBottomColor: `color-mix(in srgb, ${accent} 30%, transparent)` }}>{children}</thead>,
            th: ({ children }) => <th className="prd-th" style={{ color: accent }}>{children}</th>,
            td: ({ children }) => <td className="prd-td">{children}</td>,
            strong: ({ children }) => <strong className="prd-strong">{children}</strong>,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  )
}

export default PrdArchitecturePage
