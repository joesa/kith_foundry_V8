import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { GlassPanel } from '../system/Surfaces';
import { cn } from '../../lib/utils/cn';

export function ArtifactCard({ title, type, date, className }: { title: string; type: string; date: string; className?: string }) {
  return (
    <GlassPanel className={cn('p-4 hover:border-secondary/30 transition-all cursor-pointer group shadow-sm hover:shadow-md hover:-translate-y-0.5', className)}>
      <div className="flex items-start justify-between mb-4">
        <div className="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center text-secondary">
          <span className="material-symbols-outlined w-5 h-5">description</span>
        </div>
        <span className="text-[10px] uppercase tracking-widest text-tertiary bg-surface-container px-2 py-0.5 rounded flex items-center">{type}</span>
      </div>
      <h4 className="text-sm font-semibold text-on-surface group-hover:text-secondary transition-colors mb-1">{title}</h4>
      <p className="text-xs text-tertiary">{date}</p>
    </GlassPanel>
  );
}

export function MetricCard({ label, value, trend, className, icon = 'activity' }: { label: string; value: string | number; trend?: 'up' | 'down' | 'neutral'; className?: string; icon?: string }) {
  return (
    <div className={cn('p-5 rounded-[var(--radius-module)] bg-surface-container border border-outline-variant/30 shadow-sm hover:border-outline-variant transition-colors', className)}>
      <div className="flex items-center gap-2 mb-2 text-tertiary">
        <span className="material-symbols-outlined w-4 h-4">{icon}</span>
        <span className="text-xs uppercase tracking-widest font-semibold">{label}</span>
      </div>
      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-black font-mono text-on-surface">{value}</span>
        {trend && (
          <span className={cn('text-xs font-bold font-mono', trend === 'up' ? 'text-emerald-500' : trend === 'down' ? 'text-error' : 'text-tertiary')}>
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '-'}
          </span>
        )}
      </div>
    </div>
  );
}

export function ActivityFeed({ items }: { items: { id: string; user: string; action: string; time: string }[] }) {
  return (
    <div className="space-y-4">
      {items.map((item, idx) => (
        <div key={item.id} className="flex gap-3 relative">
          {idx !== items.length - 1 && <div className="absolute top-6 bottom-0 left-2.5 w-px bg-outline-variant/30 -z-10" />}
          <div className="w-5 h-5 rounded-full bg-secondary/20 flex items-center justify-center shrink-0 mt-0.5">
            <div className="w-1.5 h-1.5 rounded-full bg-secondary" />
          </div>
          <div>
            <p className="text-sm">
              <span className="font-semibold text-on-surface">{item.user}</span>{' '}
              <span className="text-tertiary">{item.action}</span>
            </p>
            <p className="text-xs text-tertiary/70 mt-0.5">{item.time}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export function AlertBanner({ title, description, variant = 'info', className, onDismiss }: { title: string; description: string; variant?: 'info' | 'warning' | 'error' | 'success'; className?: string; onDismiss?: () => void }) {
  const styles = {
    info: 'bg-secondary/10 border-secondary text-secondary',
    warning: 'bg-amber-500/10 border-amber-500 text-amber-500',
    error: 'bg-error/10 border-error text-error',
    success: 'bg-emerald-500/10 border-emerald-500 text-emerald-500',
  };
  
  const icons = {
    info: 'info',
    warning: 'warning',
    error: 'error',
    success: 'check_circle',
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={cn('p-4 rounded-xl border-l-4 border flex gap-3 relative shadow-sm', styles[variant], className)}
    >
      <span className="material-symbols-outlined w-5 h-5 shrink-0">{icons[variant]}</span>
      <div className="flex-1 pr-6">
        <h4 className="text-sm font-bold mb-1">{title}</h4>
        <p className="text-xs opacity-80">{description}</p>
      </div>
      {onDismiss && (
        <button 
          onClick={onDismiss}
          className="absolute top-4 right-4 opacity-50 hover:opacity-100 transition-opacity"
          aria-label="Dismiss alert"
        >
          <span className="material-symbols-outlined text-sm">close</span>
        </button>
      )}
    </motion.div>
  );
}

export function EmptyState({ title, description, action, icon = 'folder_open' }: { title: string; description: string; action?: ReactNode; icon?: string }) {
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center p-12 text-center rounded-[var(--radius-module)] border border-dashed border-outline-variant/50 bg-surface-container/30"
    >
      <div className="w-16 h-16 rounded-full bg-surface-container flex items-center justify-center text-tertiary mb-4 shadow-sm">
        <span className="material-symbols-outlined w-8 h-8 opacity-50">{icon}</span>
      </div>
      <h3 className="text-lg font-bold text-on-surface mb-2">{title}</h3>
      <p className="text-tertiary text-sm max-w-sm mb-6">{description}</p>
      {action}
    </motion.div>
  );
}

export function LoadingState({ message = 'Loading system parameters...', variant = 'spinner' }: { message?: string; variant?: 'spinner' | 'skeleton' }) {
  if (variant === 'skeleton') {
    return (
      <div className="w-full space-y-4 animate-pulse">
        <div className="h-8 bg-surface-container rounded-md w-1/3 mb-8" />
        <div className="h-32 bg-surface-container rounded-xl w-full" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="h-24 bg-surface-container rounded-xl" />
          <div className="h-24 bg-surface-container rounded-xl" />
          <div className="h-24 bg-surface-container rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center p-12 min-h-[300px]">
      <span className="material-symbols-outlined w-8 h-8 text-secondary animate-spin mb-4">progress_activity</span>
      <span className="text-sm font-medium tracking-widest uppercase text-tertiary animate-pulse">{message}</span>
    </div>
  );
}
