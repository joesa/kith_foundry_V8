import { Link } from 'react-router-dom'
import { cn } from '../../lib/utils/cn'

export default function NotFoundPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-16">
      <div className={cn('rounded-2xl border p-8 sm:p-10', 'bg-surface border-outline-variant')}>
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-outline-variant/30 bg-surface-container mb-5">
          <span className="material-symbols-outlined text-tertiary" style={{ fontSize: '14px' }}>
            explore
          </span>
          <span
            className="uppercase font-black text-tertiary"
            style={{ fontSize: '0.6rem', fontWeight: 900, letterSpacing: '0.1em' }}
          >
            Page Not Found
          </span>
        </div>

        <h1
          className="text-on-surface font-black uppercase mb-3"
          style={{ fontSize: '1.75rem', fontWeight: 900, letterSpacing: '-0.05em' }}
        >
          This screen does not exist yet.
        </h1>

        <p
          className="text-tertiary max-w-2xl mb-8"
          style={{ fontSize: '0.875rem', lineHeight: '1.6' }}
        >
          The link may be outdated, or the page was moved. Use one of these destinations to continue
          your build workflow.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Link
            to="/app/projects"
            className={cn(
              'flex items-center gap-2 rounded-xl border px-4 py-3 transition-colors',
              'border-outline-variant bg-surface-container text-on-surface',
              'hover:border-secondary/40 hover:text-secondary',
            )}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
              dashboard
            </span>
            <span
              className="uppercase font-black"
              style={{ fontSize: '0.65rem', fontWeight: 900, letterSpacing: '0.08em' }}
            >
              Projects Dashboard
            </span>
          </Link>

          <Link
            to="/app/ideation"
            className={cn(
              'flex items-center gap-2 rounded-xl border px-4 py-3 transition-colors',
              'border-outline-variant bg-surface-container text-on-surface',
              'hover:border-secondary/40 hover:text-secondary',
            )}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
              lightbulb
            </span>
            <span
              className="uppercase font-black"
              style={{ fontSize: '0.65rem', fontWeight: 900, letterSpacing: '0.08em' }}
            >
              Ideation Flow
            </span>
          </Link>

          <Link
            to="/app/profile"
            className={cn(
              'flex items-center gap-2 rounded-xl border px-4 py-3 transition-colors',
              'border-outline-variant bg-surface-container text-on-surface',
              'hover:border-secondary/40 hover:text-secondary',
            )}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
              manage_accounts
            </span>
            <span
              className="uppercase font-black"
              style={{ fontSize: '0.65rem', fontWeight: 900, letterSpacing: '0.08em' }}
            >
              Profile Settings
            </span>
          </Link>
        </div>
      </div>
    </div>
  )
}
