import { cn } from '../../lib/utils/cn'

interface TelemetryStripProps {
  stage?: string
  projectName?: string
  jobCount?: number
  className?: string
}

const stageLabels: Record<string, string> = {
  idle:                'SYSTEM IDLE',
  ideation:            'IDEATION ACTIVE',
  executive_review:    'EXECUTIVE REVIEW IN PROGRESS',
  planning:            'PLANNING PHASE',
  designing:           'DESIGN STUDIO ACTIVE',
  capability_gate:     'CAPABILITY GATE',
  waiting_for_secrets: 'AWAITING SECRETS',
  generating_code:     'CODE GENERATION IN PROGRESS',
  building:            'SANDBOX BUILD ACTIVE',
  repairing:           'AUTO-REPAIR CYCLE',
  ready_for_preview:   'PREVIEW READY',
  deploying:           'DEPLOYMENT IN PROGRESS',
  deployed:            'DEPLOYED',
}

function TelemetryStrip({ stage = 'idle', projectName, jobCount = 0, className }: TelemetryStripProps) {
  const label = stageLabels[stage] ?? stage.toUpperCase()
  const isActive = stage !== 'idle' && stage !== 'deployed'

  return (
    <div
      className={cn(
        'h-8 flex items-center justify-between px-4 border-t border-outline-variant bg-surface',
        className,
      )}
    >
      <div className="flex items-center gap-3">
        <span
          className={cn(
            'material-symbols-outlined',
            isActive ? 'text-secondary animate-pulse' : 'text-on-surface/30',
          )}
          style={{ fontSize: 12, fontVariationSettings: "'FILL' 0, 'wght' 400" }}
        >
          sensors
        </span>
        <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-on-surface/50">
          {label}
        </span>
        {projectName && (
          <>
            <span className="text-on-surface/20 text-[0.6rem]">|</span>
            <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-on-surface/30">
              {projectName}
            </span>
          </>
        )}
      </div>
      {jobCount > 0 && (
        <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-secondary">
          {jobCount} ACTIVE JOB{jobCount > 1 ? 'S' : ''}
        </span>
      )}
    </div>
  )
}

export { TelemetryStrip, type TelemetryStripProps }
