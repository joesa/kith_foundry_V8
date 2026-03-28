import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { GlassPanel } from '../../components/ui/GlassPanel'
import { Button } from '../../components/ui/Button'
import { TrustBanner } from '../../components/ui/TrustBanner'
import { StatusPill } from '../../components/ui/StatusPill'
import { useAuth } from '../../contexts/AuthContext'
import { motion } from 'framer-motion'
import { cn } from '../../lib/utils/cn'

type GateState = 'idle' | 'editing' | 'submitting' | 'needs_secrets' | 'complete' | 'error'

interface Capabilities {
  wantsDatabase: boolean
  wantsAuth: boolean
  wantsAI: boolean
  externalIntegrations: string[]
}

function CapabilityGatePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { getAccessToken } = useAuth()
  const navigate = useNavigate()
  const [state, setState] = useState<GateState>('idle')
  const [error, setError] = useState('')
  const [caps, setCaps] = useState<Capabilities>({
    wantsDatabase: false,
    wantsAuth: false,
    wantsAI: false,
    externalIntegrations: [],
  })

  useEffect(() => {
    if (!projectId || projectId === 'new') return
    ;(async () => {
      try {
        const token = await getAccessToken()
        const res = await fetch(`/api/v1/projects/${projectId}/capabilities`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (res.ok) {
          const data = await res.json()
          if (data.wants_database !== undefined) {
            setCaps({
              wantsDatabase: data.wants_database,
              wantsAuth: data.wants_auth,
              wantsAI: data.wants_ai,
              externalIntegrations: data.external_integrations || [],
            })
            setState('complete')
          }
        }
      } catch { /* endpoint may not exist yet */ }
    })()
  }, [projectId, getAccessToken])

  const needsSecrets = caps.wantsAI || caps.externalIntegrations.length > 0

  const handleSubmit = async () => {
    setState('submitting')
    try {
      const token = await getAccessToken()
      const res = await fetch(`/api/v1/projects/${projectId}/capabilities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({
          wants_database: caps.wantsDatabase,
          wants_auth: caps.wantsAuth,
          wants_ai: caps.wantsAI,
          external_integrations: caps.externalIntegrations,
        }),
      })
      if (res.ok) {
        if (needsSecrets) {
          setState('needs_secrets')
        } else {
          setState('complete')
          navigate(`/app/projects/${projectId}/build`)
        }
      } else {
        setError('Failed to save capability choices')
        setState('error')
      }
    } catch (e) {
      setError('Network error')
      setState('error')
    }
  }

  const toggles: Array<{
    key: keyof Pick<Capabilities, 'wantsDatabase' | 'wantsAuth' | 'wantsAI'>
    icon: string
    label: string
    desc: string
  }> = [
    { key: 'wantsDatabase', icon: 'database', label: 'Database', desc: 'Your generated app will have a database (Supabase DB recommended for managed apps)' },
    { key: 'wantsAuth', icon: 'how_to_reg', label: 'Authentication', desc: 'Your generated app will have user authentication (Supabase Auth recommended)' },
    { key: 'wantsAI', icon: 'auto_awesome', label: 'AI Capabilities', desc: 'Your generated app will integrate AI providers (requires API keys)' },
  ]

  return (
    <div className="max-w-3xl mx-auto p-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <span className="text-[0.6rem] font-black uppercase tracking-widest text-tertiary block mb-3">CAPABILITY GATE</span>
        <h1 className="text-3xl font-black uppercase mb-2" style={{ letterSpacing: '-0.05em' }}>Configure Your App's Backend</h1>
        <p className="text-xs font-black uppercase tracking-widest text-on-surface/40 mb-8">
          Select what infrastructure your generated app needs. You can skip all of these and build a frontend-only app.
        </p>

        <div className="space-y-4 mb-8">
          {toggles.map(({ key, icon, label, desc }) => (
            <div
              key={key}
              role="switch"
              aria-checked={caps[key]}
              aria-label={label}
              tabIndex={0}
              onClick={() => {
                setCaps(prev => ({ ...prev, [key]: !prev[key] }))
                if (state === 'idle' || state === 'complete') setState('editing')
              }}
              onKeyDown={(e: React.KeyboardEvent) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  setCaps(prev => ({ ...prev, [key]: !prev[key] }))
                  if (state === 'idle' || state === 'complete') setState('editing')
                }
              }}
              className={cn(
                'steel-gradient ghost-border rounded-[var(--radius-module)] p-4 cursor-pointer transition-all',
                caps[key] && 'border-l-2 border-secondary'
              )}
            >
              <div className="flex items-center gap-4">
                <div className={cn(
                  'p-2.5 rounded-full',
                  caps[key] ? 'bg-secondary/10' : 'bg-surface-container'
                )}>
                  <span className={cn(
                    'material-symbols-outlined text-xl',
                    caps[key] ? 'text-secondary' : 'text-on-surface/40'
                  )}>{icon}</span>
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-xs font-black uppercase tracking-widest text-on-surface">{label}</h3>
                    {caps[key] && <StatusPill status="completed" size="sm" />}
                  </div>
                  <p className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/40 mt-0.5">{desc}</p>
                </div>
                {/* Toggle switch */}
                <div className={cn(
                  'w-10 h-6 rounded-full transition-colors flex items-center shrink-0',
                  caps[key] ? 'bg-secondary' : 'bg-surface-container border border-outline-variant/20'
                )}>
                  <div className={cn(
                    'w-4 h-4 rounded-full bg-white shadow transition-transform',
                    caps[key] ? 'translate-x-5' : 'translate-x-1'
                  )} />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* External integrations */}
        <GlassPanel className="mb-8">
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-on-surface/40 text-base">shield</span>
            <h3 className="text-xs font-black uppercase tracking-widest text-on-surface">External Cloud Integrations</h3>
          </div>
          <p className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/40 mb-3">
            External services are supported as credentials-only integrations — they are never installed locally inside the sandbox.
          </p>
          <TrustBanner variant="sandbox" compact />
        </GlassPanel>

        {/* Decision summary */}
        {(caps.wantsDatabase || caps.wantsAuth || caps.wantsAI) && (
          <GlassPanel className="mb-8">
            <span className="text-[0.6rem] font-black uppercase tracking-widest text-tertiary block mb-2">DECISION SUMMARY</span>
            <ul className="space-y-1 text-xs font-black uppercase tracking-widest text-on-surface/50">
              {caps.wantsDatabase && <li>• Generated app backend: Supabase DB (optional)</li>}
              {caps.wantsAuth && <li>• Authentication: Supabase Auth (optional)</li>}
              {caps.wantsAI && <li>• AI integration: Requires API key configuration</li>}
              <li>• Secrets needed: {needsSecrets ? 'Yes — configure next' : 'No'}</li>
            </ul>
          </GlassPanel>
        )}

        {error && <p className="text-xs font-black uppercase tracking-widest text-error mb-4">{error}</p>}

        {/* Actions */}
        <div className="flex items-center gap-3">
          {needsSecrets && state === 'needs_secrets' ? (
            <Button variant="primary" onClick={() => navigate(`/app/projects/${projectId}/secrets`)} icon="arrow_forward">
              Configure Secrets
            </Button>
          ) : (
            <Button variant="primary" loading={state === 'submitting'} onClick={handleSubmit} icon="arrow_forward">
              {needsSecrets ? 'Save & Configure Secrets' : 'Continue to Build'}
            </Button>
          )}
          <Button variant="ghost" onClick={() => navigate(`/app/projects/${projectId}/build`)} icon="skip_next">
            Skip All &amp; Continue
          </Button>
        </div>
      </motion.div>
    </div>
  )
}

export default CapabilityGatePage
