import type { HTMLAttributes } from 'react'
import { cn } from '../../lib/utils/cn'

interface GlassPanelProps extends HTMLAttributes<HTMLDivElement> {
  noBorder?: boolean
  noPadding?: boolean
}

function GlassPanel({ noBorder, noPadding, className, children, ...props }: GlassPanelProps) {
  return (
    <div
      className={cn(
        'glass-panel',
        !noBorder && 'ghost-border',
        !noPadding && 'p-6',
        'rounded-[var(--radius-module)]',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export { GlassPanel, type GlassPanelProps }
