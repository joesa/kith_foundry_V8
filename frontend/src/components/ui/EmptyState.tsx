import type { ReactNode } from 'react'
import { cn } from '../../lib/utils/cn'

interface EmptyStateProps {
  icon?: string
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-16 px-6 text-center', className)}>
      {icon && (
        <div className="w-12 h-12 rounded-[var(--radius-module)] bg-surface-container flex items-center justify-center mb-4">
          <span
            className="material-symbols-outlined text-tertiary"
            style={{ fontSize: 24, fontVariationSettings: "'FILL' 0, 'wght' 300" }}
          >
            {icon}
          </span>
        </div>
      )}
      <h3 className="text-sm font-black uppercase tracking-widest text-on-surface mb-1">{title}</h3>
      {description && (
        <p className="text-xs text-tertiary max-w-xs">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
