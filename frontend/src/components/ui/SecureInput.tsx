import { forwardRef, useState, type InputHTMLAttributes } from 'react'
import { cn } from '../../lib/utils/cn'

interface SecureInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  error?: string
}

const SecureInput = forwardRef<HTMLInputElement, SecureInputProps>(
  ({ label, error, className, ...props }, ref) => {
    const [visible, setVisible] = useState(false)

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label className="text-[10px] font-black uppercase tracking-widest text-secondary">
            {label}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            type={visible ? 'text' : 'password'}
            className={cn(
              'w-full px-3 py-2 pr-10 text-sm font-mono',
              'bg-surface-container border border-outline-variant/20',
              'text-on-surface placeholder:text-on-surface/30',
              'rounded-lg focus:outline-none focus:border-secondary',
              'transition-colors duration-200',
              error && 'border-[#f87171]/50',
              className,
            )}
            autoComplete="off"
            spellCheck={false}
            {...props}
          />
          <button
            type="button"
            onClick={() => setVisible(!visible)}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded text-on-surface/40 hover:text-on-surface/70 transition-colors"
            tabIndex={-1}
            aria-label={visible ? 'Hide value' : 'Show value'}
          >
            <span
              className="material-symbols-outlined"
              style={{ fontSize: 14, fontVariationSettings: "'FILL' 0, 'wght' 400" }}
            >
              {visible ? 'visibility_off' : 'visibility'}
            </span>
          </button>
        </div>
        {error && (
          <span className="text-xs text-[#f87171]">{error}</span>
        )}
      </div>
    )
  }
)

SecureInput.displayName = 'SecureInput'
export { SecureInput, type SecureInputProps }
