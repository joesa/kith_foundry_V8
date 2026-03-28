import { type ButtonHTMLAttributes, forwardRef } from 'react'
import { motion } from 'framer-motion'
import { cn } from '../../lib/utils/cn'
import { buttonHover } from '../../lib/utils/motion'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'contrast'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  icon?: string
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-primary-container text-on-primary-container ember-glow shadow-[0_0_20px_rgba(237,103,70,0.15)] hover:opacity-90',
  secondary:
    'bg-secondary text-surface font-black hover:opacity-90',
  ghost:
    'border border-outline-variant/30 ghost-border text-tertiary hover:text-on-surface hover:border-primary/60 hover:text-primary',
  danger:
    'bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20',
  contrast:
    'bg-on-surface text-surface shadow-lg shadow-on-surface/10 hover:shadow-on-surface/20 hover:-translate-y-0.5 active:translate-y-0',
}

const sizeStyles: Record<string, string> = {
  sm: 'px-4 py-2 text-[10px] gap-1.5',
  md: 'px-6 py-2.5 text-micro gap-2',
  lg: 'px-8 py-3 text-label gap-2.5',
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, icon, children, className, disabled, ...props }, ref) => {
    return (
      <motion.button
        ref={ref}
        variants={buttonHover}
        whileHover={disabled ? undefined : 'hover'}
        whileTap={disabled ? undefined : 'tap'}
        className={cn(
          'inline-flex items-center justify-center rounded-full font-black uppercase tracking-widest transition-all cursor-pointer',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary',
          variantStyles[variant],
          sizeStyles[size],
          className,
        )}
        disabled={disabled || loading}
        {...(props as any)}
      >
        {loading ? (
          <span className="material-symbols-outlined animate-spin w-4">progress_activity</span>
        ) : icon ? (
          <span className="material-symbols-outlined w-4">{icon}</span>
        ) : null}
        {children}
      </motion.button>
    )
  }
)

Button.displayName = 'Button'
export { Button, type ButtonProps, type ButtonVariant }
