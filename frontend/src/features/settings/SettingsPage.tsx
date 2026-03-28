import { useState } from 'react'
import { GlassPanel } from '../../components/ui/GlassPanel'
import { TrustBanner } from '../../components/ui/TrustBanner'
import { ProviderSettings } from '../../components/workspace/ProviderSettings'
import { useAuth } from '../../contexts/AuthContext'
import { motion } from 'framer-motion'
import { cn } from '../../lib/utils/cn'

const tabs = [
  { id: 'profile', label: 'Profile', icon: 'person' },
  { id: 'providers', label: 'Providers & Models', icon: 'key' },
  { id: 'workspace', label: 'Workspace', icon: 'group' },
  { id: 'security', label: 'Security & Trust', icon: 'shield' },
]

function SettingsPage() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState('profile')

  return (
    <div className="max-w-4xl mx-auto p-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <span className="text-[0.6rem] font-black uppercase tracking-widest text-tertiary block mb-3">SETTINGS</span>
        <h1 className="text-3xl font-black uppercase mb-6" style={{ letterSpacing: '-0.05em' }}>Settings</h1>

        <div className="flex gap-8">
          {/* Tab nav */}
          <nav className="w-48 shrink-0 space-y-0.5">
            {tabs.map(({ id, label, icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={cn(
                  'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition-colors',
                  activeTab === id
                    ? 'text-secondary border-l-2 border-secondary bg-surface-container'
                    : 'text-on-surface/40 hover:text-on-surface/70 hover:bg-surface-container/50'
                )}
              >
                <span className="material-symbols-outlined text-base">{icon}</span>
                <span className="text-[0.6rem] font-black uppercase tracking-widest">{label}</span>
              </button>
            ))}
          </nav>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {activeTab === 'profile' && (
              <GlassPanel>
                <h3 className="text-xs font-black uppercase tracking-widest text-on-surface mb-4">Profile</h3>
                <div className="space-y-3">
                  <div>
                    <span className="text-[0.6rem] font-black uppercase tracking-widest text-tertiary block mb-1">Email</span>
                    <p className="text-sm text-on-surface/50">{user?.email || '—'}</p>
                  </div>
                </div>
              </GlassPanel>
            )}

            {activeTab === 'providers' && (
              <ProviderSettings inline />
            )}

            {activeTab === 'workspace' && (
              <GlassPanel>
                <h3 className="text-xs font-black uppercase tracking-widest text-on-surface mb-4">Workspace</h3>
                <p className="text-sm text-on-surface/40">
                  Workspace and team management features are coming soon.
                </p>
              </GlassPanel>
            )}

            {activeTab === 'security' && (
              <div className="space-y-4">
                <GlassPanel>
                  <h3 className="text-xs font-black uppercase tracking-widest text-on-surface mb-4">Security &amp; Trust</h3>
                  <p className="text-sm text-on-surface/50 mb-4">
                    Kith Foundry enforces security best practices at every level of the platform.
                  </p>
                </GlassPanel>
                <TrustBanner variant="encryption" />
                <TrustBanner variant="sandbox" />
                <TrustBanner variant="no-localstorage" />
                <TrustBanner variant="patch-validated" />
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default SettingsPage
