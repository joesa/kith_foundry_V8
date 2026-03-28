import type { HTMLAttributes } from 'react'
import { motion } from 'framer-motion'
import { cn } from '../../lib/utils/cn'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean
  accent?: 'ember' | 'cyan' | 'success' | 'warning' | 'error'
  noPadding?: boolean
}

const accentClasses: Record<string, string> = {
  ember: 'status-ribbon-ember',
  cyan: 'status-ribbon-cyan',
  success: 'border-l-4 border-l-[#34d399]',
  warning: 'border-l-4 border-l-[#fbbf24]',
  error: 'border-l-4 border-l-[#f87171]',
}

function Card({ hover, accent, noPadding, className, children, ...props }: CardProps) {
  const classes = cn(
    'steel-gradient rounded-[var(--radius-module)] ghost-border',
    accent && accentClasses[accent],
    !noPadding && 'p-6',
    hover && 'cursor-pointer hover:shadow-md transition-shadow',
    className,
  )

  if (hover) {
    return (
      <motion.div
        className={classes}
        whileHover={{ scale: 1.01, y: -2 }}
        transition={{ duration: 0.2 }}
        {...(props as any)}
      >
        {children}
      </motion.div>
    )
  }

  return (
    <div className={classes} {...props}>
      {children}
    </div>
  )
}

export { Card, type CardProps }
