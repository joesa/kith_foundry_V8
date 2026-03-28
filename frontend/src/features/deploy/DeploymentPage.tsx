import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { GlassPanel } from '../../components/ui/GlassPanel'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { StatusPill } from '../../components/ui/StatusPill'
import { ProgressRail } from '../../components/ui/ProgressRail'
import { motion } from 'framer-motion'

import type { ProgressStage } from '../../components/ui/ProgressRail'

type DeployState = 'idle' | 'connecting_git' | 'committing' | 'deploying' | 'deployed' | 'failed'

const baseDeployStages = [
  { id: 'connecting_git', label: 'Git', icon: 'cloud_sync', route: '' },
  { id: 'committing', label: 'Commit', icon: 'upload', route: '' },
  { id: 'deploying', label: 'Deploy', icon: 'rocket_launch', route: '' },
  { id: 'deployed', label: 'Done', icon: 'check_circle', route: '' }
];

function DeploymentPage() {
  const { projectId: _projectId } = useParams<{ projectId: string }>()
  const [state, _setState] = useState<DeployState>('idle')
  const [repoUrl, setRepoUrl] = useState('')
  const [branch, setBranch] = useState('main')
  const [commitMessage, setCommitMessage] = useState('')
  const [deployUrl, _setDeployUrl] = useState('')

  const stages: ProgressStage[] = baseDeployStages.map((s, i) => {
    const currentIndex = baseDeployStages.findIndex(bs => bs.id === state);
    let status: 'pending' | 'active' | 'complete' = 'pending';
    if (state === 'deployed') status = 'complete';
    else if (i < currentIndex) status = 'complete';
    else if (i === currentIndex) status = 'active';
    return { ...s, status };
  });

  return (
    <div className="max-w-3xl mx-auto p-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <span className="text-[0.6rem] font-black uppercase tracking-widest text-tertiary block mb-3">DEPLOYMENT</span>
        <h1 className="text-3xl font-black uppercase mb-2" style={{ letterSpacing: '-0.05em' }}>Deploy Your App</h1>
        <p className="text-xs font-black uppercase tracking-widest text-on-surface/40 mb-8">
          Connect your repository, commit your code, and deploy to production.
        </p>

        {state !== 'idle' && (
          <div className="mb-8">
            <ProgressRail projectId={_projectId || '1'} currentStageId={state} stages={stages} />
          </div>
        )}

        {/* Git Connection */}
        <GlassPanel className="mb-6">
          <h3 className="text-xs font-black uppercase tracking-widest text-on-surface mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-base">cloud_sync</span>
            Git Connection
          </h3>
          <div className="space-y-3">
            <Input label="Repository URL" placeholder="https://github.com/you/repo" value={repoUrl} onChange={e => setRepoUrl(e.target.value)} />
            <Input label="Branch" value={branch} onChange={e => setBranch(e.target.value)} />
            <Button variant="secondary" size="sm" loading={state === 'connecting_git'} icon="cloud_sync">
              Connect Repository
            </Button>
          </div>
        </GlassPanel>

        {/* Commit */}
        <GlassPanel className="mb-6">
          <h3 className="text-xs font-black uppercase tracking-widest text-on-surface mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-base">upload</span>
            Commit &amp; Push
          </h3>
          <div className="space-y-3">
            <Input label="Commit Message" placeholder="feat: initial build from Kith Foundry" value={commitMessage} onChange={e => setCommitMessage(e.target.value)} />
            <Button variant="secondary" size="sm" loading={state === 'committing'} icon="upload">
              Commit &amp; Push
            </Button>
          </div>
        </GlassPanel>

        {/* Deploy */}
        <GlassPanel className="mb-6">
          <h3 className="text-xs font-black uppercase tracking-widest text-on-surface mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-base">rocket_launch</span>
            Deploy to Vercel
          </h3>
          <Button variant="primary" loading={state === 'deploying'} icon="rocket_launch">
            Deploy to Vercel
          </Button>
          {state === 'deployed' && deployUrl && (
            <div className="mt-4 flex items-center gap-2">
              <StatusPill status="deployed" />
              <a href={deployUrl} target="_blank" rel="noopener noreferrer" className="text-xs font-black uppercase tracking-widest text-secondary hover:underline flex items-center gap-1">
                {deployUrl} <span className="material-symbols-outlined text-xs">open_in_new</span>
              </a>
            </div>
          )}
        </GlassPanel>

        {/* History */}
        <div>
          <h3 className="text-xs font-black uppercase tracking-widest text-on-surface mb-3 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-base">cloud_done</span>
            Deployment History
          </h3>
          <p className="text-xs font-black uppercase tracking-widest text-on-surface/30">No deployments yet.</p>
        </div>
      </motion.div>
    </div>
  )
}

export default DeploymentPage
