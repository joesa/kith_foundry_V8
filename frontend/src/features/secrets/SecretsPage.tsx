import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { GlassPanel } from '../../components/ui/GlassPanel'
import { Button } from '../../components/ui/Button'
import { SecureInput } from '../../components/ui/SecureInput'
import { TrustBanner } from '../../components/ui/TrustBanner'
import { StatusPill } from '../../components/ui/StatusPill'
import { useAuth } from '../../contexts/AuthContext'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../lib/utils/cn'

type SecretsState = 'idle' | 'collecting' | 'submitting' | 'stored' | 'revoking' | 'error'

interface StoredSecret {
  id: string
  secret_label: string
  secret_scope: string
  status: string
  created_at: string
}

const providers = [
  { id: 'openai', label: 'OpenAI', scope: 'ai_provider' },
  { id: 'anthropic', label: 'Anthropic', scope: 'ai_provider' },
  { id: 'supabase', label: 'Supabase', scope: 'database' },
  { id: 'google_ai', label: 'Google AI', scope: 'ai_provider' },
  { id: 'custom', label: 'Custom API Key', scope: 'custom' },
]

function SecretsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { getAccessToken } = useAuth()
  const [state, setState] = useState<SecretsState>('idle')
  const [secrets, setSecrets] = useState<StoredSecret[]>([])
  const [selectedProvider, setSelectedProvider] = useState('')
  const [secretLabel, setSecretLabel] = useState('')
  const [error, setError] = useState('')
  const keyRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!projectId || projectId === 'new') return
    loadSecrets()
  }, [projectId])

  const loadSecrets = async () => {
    try {
      const token = await getAccessToken()
      const res = await fetch(`/api/v1/projects/${projectId}/secrets`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (res.ok) {
        const data = await res.json()
        setSecrets(data.secrets || [])
      }
    } catch { /* endpoint may not exist yet */ }
  }

  const handleStore = async () => {
    const value = keyRef.current?.value
    if (!value || !selectedProvider) return
    setState('submitting')
    setError('')
    try {
      const token = await getAccessToken()
      const res = await fetch(`/api/v1/projects/${projectId}/secrets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({
          secret_label: secretLabel || selectedProvider,
          secret_scope: providers.find(p => p.id === selectedProvider)?.scope || 'custom',
          raw_value: value,
        }),
      })
      if (res.ok) {
        if (keyRef.current) keyRef.current.value = ''
        setSecretLabel('')
        setSelectedProvider('')
        setState('stored')
        await loadSecrets()
      } else {
        setError('Failed to store secret')
        setState('error')
      }
    } catch {
      setError('Network error')
      setState('error')
    }
  }

  const handleRevoke = async (secretId: string) => {
    setState('revoking')
    try {
      const token = await getAccessToken()
      await fetch(`/api/v1/secrets/${secretId}/revoke`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      await loadSecrets()
      setState('idle')
    } catch {
      setState('error')
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <span className="text-[0.6rem] font-black uppercase tracking-widest text-tertiary block mb-3">SECRET VAULT</span>
        <h1 className="text-3xl font-black uppercase mb-2" style={{ letterSpacing: '-0.05em' }}>Secure Secret Collection</h1>
        <p className="text-xs font-black uppercase tracking-widest text-on-surface/40 mb-6">
          Provide API keys and credentials securely. All secrets are encrypted server-side before storage.
        </p>

        <TrustBanner variant="encryption" className="mb-6" />
        <TrustBanner variant="no-localstorage" className="mb-8" />

        {/* Add Secret Form */}
        <GlassPanel className="mb-8">
          <h3 className="text-xs font-black uppercase tracking-widest text-on-surface mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-base">add</span>
            Add a Secret
          </h3>

          <div className="space-y-4">
            <div>
              <label className="text-[0.6rem] font-black uppercase tracking-widest text-tertiary block mb-1.5">Provider</label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {providers.map(p => (
                  <button
                    key={p.id}
                    onClick={() => { setSelectedProvider(p.id); setState('collecting') }}
                    aria-pressed={selectedProvider === p.id}
                    className={cn(
                      'p-2 text-[0.6rem] font-black uppercase tracking-widest rounded-lg border transition-all',
                      selectedProvider === p.id
                        ? 'border-secondary bg-secondary/10 text-secondary'
                        : 'border-outline-variant/20 text-on-surface/50 hover:border-outline-variant/50'
                    )}
                  >
                    <span className="material-symbols-outlined text-sm block mx-auto mb-0.5">
                      {p.scope === 'database' ? 'database' : p.id === 'custom' ? 'lock' : 'shield'}
                    </span>
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <AnimatePresence>
              {selectedProvider && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="space-y-3">
                  <SecureInput
                    ref={keyRef}
                    label="API Key / Secret Value"
                    placeholder="sk-..."
                  />
                  <div className="flex items-center gap-3">
                    <Button variant="primary" size="sm" loading={state === 'submitting'} onClick={handleStore} icon="key">
                      Encrypt &amp; Store
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => { setSelectedProvider(''); setState('idle') }}>
                      Cancel
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </GlassPanel>

        {error && (
          <p className="text-xs font-black uppercase tracking-widest text-error mb-4" role="alert">{error}</p>
        )}

        {/* Stored Secrets */}
        <div>
          <h3 className="text-xs font-black uppercase tracking-widest text-on-surface mb-3 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-base">key</span>
            Stored Secrets ({secrets.length})
          </h3>
          {secrets.length === 0 ? (
            <p className="text-xs font-black uppercase tracking-widest text-on-surface/30">No secrets stored for this project yet.</p>
          ) : (
            <div className="space-y-2">
              {secrets.map(s => (
                <div key={s.id} className="flex items-center justify-between p-3 bg-surface-container border border-outline-variant/20 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-on-surface/30 text-base">key</span>
                    <div>
                      <span className="text-xs font-black uppercase tracking-widest text-on-surface">{s.secret_label}</span>
                      <div className="flex items-center gap-2 mt-0.5">
                        <StatusPill status={s.status} size="sm" />
                        <span className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/30 flex items-center gap-1">
                          <span className="material-symbols-outlined text-[0.6rem]">schedule</span>
                          {new Date(s.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  {s.status === 'active' && (
                    <Button variant="danger" size="sm" onClick={() => handleRevoke(s.id)} icon="delete">
                      Revoke
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  )
}

export default SecretsPage
