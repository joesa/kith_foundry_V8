import { cn } from '../../lib/utils/cn'

// Semantic signal buckets
type SignalVariant = 'idle' | 'running' | 'success' | 'warning' | 'error'

const signalColors: Record<SignalVariant, { color: string; bg: string; border: string }> = {
  idle:    { color: 'var(--color-on-surface-variant)', bg: 'color-mix(in srgb, var(--color-on-surface-variant) 10%, transparent)', border: 'color-mix(in srgb, var(--color-on-surface-variant) 20%, transparent)' },
  running: { color: 'var(--color-tertiary)',           bg: 'color-mix(in srgb, var(--color-tertiary) 12%, transparent)',           border: 'color-mix(in srgb, var(--color-tertiary) 25%, transparent)' },
  success: { color: '#34d399',                         bg: 'color-mix(in srgb, #34d399 12%, transparent)',                         border: 'color-mix(in srgb, #34d399 25%, transparent)' },
  warning: { color: '#fbbf24',                         bg: 'color-mix(in srgb, #fbbf24 12%, transparent)',                         border: 'color-mix(in srgb, #fbbf24 25%, transparent)' },
  error:   { color: '#f87171',                         bg: 'color-mix(in srgb, #f87171 12%, transparent)',                         border: 'color-mix(in srgb, #f87171 25%, transparent)' },
}

const statusToSignal: Record<string, SignalVariant> = {
  // Idle / neutral
  draft:               'idle',
  queued:              'idle',
  cancelled:           'idle',
  stopped:             'idle',
  // Running / active
  ideation:            'running',
  executive_review:    'running',
  csuite_running:      'running',
  planning:            'running',
  designing:           'running',
  generating_code:     'running',
  building:            'running',
  running:             'running',
  provisioning:        'running',
  syncing:             'running',
  installing:          'running',
  // Warning / gated
  csuite_pending:      'warning',
  capability_gate:     'warning',
  waiting_for_secrets: 'warning',
  repairing:           'warning',
  paused:              'warning',
  waiting_input:       'warning',
  retrying:            'warning',
  // Success
  csuite_complete:     'success',
  ready_for_preview:   'success',
  deploy_ready:        'success',
  deployed:            'success',
  completed:           'success',
  // Error
  failed:              'error',
  error:               'error',
}

const statusLabels: Record<string, string> = {
  draft:               'Draft',
  ideation:            'Ideation',
  executive_review:    'Executive Review',
  csuite_pending:      'C-Suite Pending',
  csuite_running:      'C-Suite Running',
  csuite_complete:     'C-Suite Complete',
  planning:            'Planning',
  designing:           'Designing',
  capability_gate:     'Capability Gate',
  waiting_for_secrets: 'Waiting for Secrets',
  generating_code:     'Generating Code',
  building:            'Building',
  repairing:           'Repairing',
  ready_for_preview:   'Ready for Preview',
  deploy_ready:        'Deploy Ready',
  deployed:            'Deployed',
  failed:              'Failed',
  queued:              'Queued',
  running:             'Running',
  paused:              'Paused',
  waiting_input:       'Waiting for Input',
  retrying:            'Retrying',
  completed:           'Completed',
  cancelled:           'Cancelled',
  error:               'Error',
  provisioning:        'Provisioning',
  syncing:             'Syncing',
  installing:          'Installing',
  stopped:             'Stopped',
  idle:                'Idle',
  success:             'Success',
  warning:             'Warning',
}

interface StatusPillProps {
  status: string
  size?: 'sm' | 'md'
  pulse?: boolean
  className?: string
}

function StatusPill({ status, size = 'sm', pulse, className }: StatusPillProps) {
  const signal = statusToSignal[status] ?? ((['running', 'success', 'warning', 'error', 'idle'] as string[]).includes(status) ? (status as SignalVariant) : 'idle')
  const colors = signalColors[signal]
  const label = statusLabels[status] ?? status.replace(/_/g, ' ')
  const isPulsing = pulse ?? signal === 'running'

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-black uppercase tracking-widest',
        size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-[11px] px-2.5 py-1',
        className,
      )}
      style={{
        color: colors.color,
        backgroundColor: colors.bg,
        border: `1px solid ${colors.border}`,
      }}
    >
      {isPulsing && (
        <span
          className="w-1.5 h-1.5 rounded-full animate-pulse shrink-0"
          style={{ backgroundColor: colors.color }}
        />
      )}
      {label}
    </span>
  )
}

export { StatusPill, type StatusPillProps }
