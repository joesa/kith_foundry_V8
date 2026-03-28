import { cn } from '../../lib/utils/cn'

type AgentRole =
  | 'ceo' | 'cpo' | 'cto' | 'cdo' | 'cfo' | 'cmo' | 'coo' | 'ciso'
  | 'synthesizer'
  | 'intent' | 'layout' | 'component' | 'code' | 'patch' | 'validation'
  | 'design' | 'sandbox' | 'deploy'

const agentConfig: Record<string, { icon: string; label: string; color: string }> = {
  ceo:         { icon: 'psychology',        label: 'CEO',             color: 'var(--color-tertiary)' },
  cpo:         { icon: 'groups',            label: 'CPO',             color: '#A78BFA' },
  cto:         { icon: 'code',              label: 'CTO',             color: 'var(--color-secondary)' },
  cdo:         { icon: 'palette',           label: 'CDO',             color: '#F472B6' },
  cfo:         { icon: 'attach_money',      label: 'CFO',             color: '#34d399' },
  cmo:         { icon: 'trending_up',       label: 'CMO',             color: '#fbbf24' },
  coo:         { icon: 'layers',            label: 'COO',             color: '#FB923C' },
  ciso:        { icon: 'lock',              label: 'CISO',            color: '#f87171' },
  synthesizer: { icon: 'psychology',        label: 'Synthesizer',     color: 'var(--color-tertiary)' },
  intent:      { icon: 'psychology',        label: 'Intent Agent',    color: 'var(--color-secondary)' },
  layout:      { icon: 'layers',            label: 'Layout Agent',    color: 'var(--color-secondary)' },
  component:   { icon: 'code',              label: 'Component Agent', color: 'var(--color-secondary)' },
  code:        { icon: 'code',              label: 'Code Agent',      color: 'var(--color-tertiary)' },
  patch:       { icon: 'shield',            label: 'Patch Safety',    color: '#fbbf24' },
  validation:  { icon: 'verified',          label: 'Validation',      color: '#34d399' },
  design:      { icon: 'palette',           label: 'Design Agent',    color: '#F472B6' },
  sandbox:     { icon: 'layers',            label: 'Sandbox',         color: 'var(--color-secondary)' },
  deploy:      { icon: 'rocket_launch',     label: 'Deploy Agent',    color: '#34d399' },
}

interface AgentBadgeProps {
  role: AgentRole | string
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  className?: string
}

function AgentBadge({ role, size = 'md', showLabel = true, className }: AgentBadgeProps) {
  const config = agentConfig[role] ?? { icon: 'smart_toy', label: role, color: 'var(--color-on-surface-variant)' }

  const iconSizePx = size === 'sm' ? 12 : size === 'md' ? 14 : 18
  const containerPx = iconSizePx + 8
  const textClass = size === 'sm' ? 'text-[0.6rem]' : size === 'md' ? 'text-[0.7rem]' : 'text-xs'

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-black uppercase tracking-wider',
        textClass,
        className,
      )}
      style={{ color: config.color }}
    >
      <span
        className="inline-flex items-center justify-center rounded-md shrink-0"
        style={{
          width: containerPx,
          height: containerPx,
          backgroundColor: `color-mix(in srgb, ${config.color} 15%, transparent)`,
        }}
      >
        <span
          className="material-symbols-outlined"
          style={{ fontSize: iconSizePx, fontVariationSettings: "'FILL' 0, 'wght' 400" }}
        >
          {config.icon}
        </span>
      </span>
      {showLabel && config.label}
    </span>
  )
}

export { AgentBadge, type AgentBadgeProps, type AgentRole }
