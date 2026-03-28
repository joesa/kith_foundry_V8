import type { ReactNode } from 'react'
import { cn } from '../../lib/utils/cn'

interface SectionHeaderProps {
  icon?: string
  title: string
  subtitle?: string
  badge?: ReactNode
  action?: ReactNode
  className?: string
}

export function SectionHeader({ icon, title, subtitle, badge, action, className }: SectionHeaderProps) {
  return (
    <div className={cn('flex items-start justify-between gap-4', className)}>
      <div className="flex items-start gap-3 min-w-0">
        {icon && (
          <div className="w-8 h-8 rounded-[var(--radius-module)] bg-surface-container flex items-center justify-center shrink-0 mt-0.5">
            <span
              className="material-symbols-outlined text-secondary"
              style={{ fontSize: 16, fontVariationSettings: "'FILL' 0, 'wght' 400" }}
            >
              {icon}
            </span>
          </div>
        )}
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-black uppercase tracking-tighter cinematic-tracking text-on-surface truncate">
              {title}
            </h2>
            {badge}
          </div>
          {subtitle && (
            <p className="text-xs text-secondary mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}
