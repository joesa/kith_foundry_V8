import { type InputHTMLAttributes, type TextareaHTMLAttributes, forwardRef } from 'react'
import { cn } from '../../lib/utils/cn'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label className="block text-[10px] font-bold uppercase tracking-widest text-tertiary mb-2">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={cn(
            'w-full bg-surface-container border border-outline-variant/20',
            'focus:border-secondary rounded-lg px-4 py-2.5',
            'text-on-surface text-sm outline-none transition-colors',
            error && 'border-error/50',
            className,
          )}
          {...props}
        />
        {error && (
          <span className="text-xs text-error">{error}</span>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label className="block text-[10px] font-bold uppercase tracking-widest text-tertiary mb-2">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          className={cn(
            'w-full bg-background border border-outline-variant rounded-[var(--radius-module)] p-5',
            'text-on-surface resize-none',
            'focus:ring-2 focus:ring-primary/50 outline-none',
            'placeholder:text-tertiary/40',
            error && 'border-error/50',
            className,
          )}
          {...props}
        />
        {error && (
          <span className="text-xs text-error">{error}</span>
        )}
      </div>
    )
  }
)

Textarea.displayName = 'Textarea'

export { Input, Textarea, type InputProps, type TextareaProps }
