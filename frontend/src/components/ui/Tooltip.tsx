import { useState, useRef, type ReactNode } from 'react'
import { cn } from '../../lib/utils/cn'

interface TooltipProps {
  content: ReactNode
  children: ReactNode
  side?: 'top' | 'bottom' | 'left' | 'right'
  delay?: number
  className?: string
}

export function Tooltip({ content, children, side = 'top', delay = 300, className }: TooltipProps) {
  const [open, setOpen] = useState(false)
  const timer = useRef<number>(0)

  const show = () => {
    timer.current = window.setTimeout(() => setOpen(true), delay)
  }
  const hide = () => {
    clearTimeout(timer.current)
    setOpen(false)
  }

  const positionClasses: Record<string, string> = {
    top:    'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left:   'right-full top-1/2 -translate-y-1/2 mr-2',
    right:  'left-full top-1/2 -translate-y-1/2 ml-2',
  }

  return (
    <div
      className={cn('relative inline-flex', className)}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {open && (
        <div
          role="tooltip"
          className={cn(
            'absolute z-50 px-2 py-1 whitespace-nowrap pointer-events-none',
            'bg-surface-container-highest border border-outline-variant shadow-2xl rounded-lg',
            'text-[10px] font-bold uppercase tracking-widest text-on-surface',
            positionClasses[side],
          )}
        >
          {content}
        </div>
      )}
    </div>
  )
}
