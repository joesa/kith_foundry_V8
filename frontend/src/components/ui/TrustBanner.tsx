import { cn } from '../../lib/utils/cn'

type TrustVariant = 'encryption' | 'sandbox' | 'no-localstorage' | 'patch-validated' | 'info'

const trustConfig: Record<TrustVariant, { icon: string; label: string; detail: string }> = {
  encryption: {
    icon: 'lock',
    label: 'AES-256-GCM Encrypted',
    detail: 'All secrets are encrypted at rest using AES-256-GCM. Decryption happens server-side only.',
  },
  sandbox: {
    icon: 'shield',
    label: 'Sandbox Isolated',
    detail: 'Builds run in isolated Fly.io MicroVMs. Heavy backend services are blocked by policy.',
  },
  'no-localstorage': {
    icon: 'lock',
    label: 'No Raw Keys in Browser',
    detail: 'Raw API keys are never stored in browser localStorage or sessionStorage.',
  },
  'patch-validated': {
    icon: 'shield',
    label: 'Patch Validated',
    detail: 'All code patches are validated by tree-sitter AST analysis before application.',
  },
  info: {
    icon: 'shield',
    label: 'Secure by Default',
    detail: 'The platform enforces security policies at every stage of the build pipeline.',
  },
}

interface TrustBannerProps {
  variant: TrustVariant
  compact?: boolean
  className?: string
}

function TrustBanner({ variant, compact, className }: TrustBannerProps) {
  const config = trustConfig[variant]

  if (compact) {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-secondary',
          className,
        )}
      >
        <span
          className="material-symbols-outlined"
          style={{ fontSize: 10, fontVariationSettings: "'FILL' 0, 'wght' 400" }}
        >
          {config.icon}
        </span>
        {config.label}
      </span>
    )
  }

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-[var(--radius-module)]',
        'border border-secondary/15 bg-secondary/5',
        className,
      )}
    >
      <div className="p-1.5 rounded-md bg-secondary/10 text-secondary shrink-0 mt-0.5">
        <span
          className="material-symbols-outlined"
          style={{ fontSize: 14, fontVariationSettings: "'FILL' 0, 'wght' 400" }}
        >
          {config.icon}
        </span>
      </div>
      <div>
        <p className="text-[10px] font-black uppercase tracking-widest text-secondary">
          {config.label}
        </p>
        <p className="text-xs text-on-surface/60 mt-0.5 leading-relaxed">{config.detail}</p>
      </div>
    </div>
  )
}

export { TrustBanner, type TrustBannerProps, type TrustVariant }
