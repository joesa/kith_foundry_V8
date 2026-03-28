import type { ReactNode } from 'react';
import { cn } from '../../lib/utils/cn';

interface StatusBadgeProps {
  status: 'idle' | 'running' | 'success' | 'warning' | 'error';
  label: string;
  className?: string;
}

const statusConfig = {
  idle: 'bg-surface-container-high text-tertiary border-outline-variant/15',
  running: 'bg-[rgba(143,217,255,0.1)] text-secondary border-secondary/20 animate-pulse',
  success: 'bg-[rgba(16,185,129,0.1)] text-[#10B981] border-[rgba(16,185,129,0.2)]',
  warning: 'bg-[rgba(245,158,11,0.1)] text-[#F59E0B] border-[rgba(245,158,11,0.2)]',
  error: 'bg-[rgba(239,68,68,0.1)] text-[#EF4444] border-[rgba(239,68,68,0.2)]',
};

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border', statusConfig[status], className)}>
      {status === 'running' && <span className="w-1.5 h-1.5 rounded-full bg-current mr-2 animate-ping" />}
      {label}
    </span>
  );
}

export function TelemetryPill({ label, value, className }: { label: string; value: ReactNode; className?: string }) {
  return (
    <div className={cn('inline-flex items-center rounded-full bg-surface-container border border-outline-variant/15 px-3 py-1', className)}>
      <span className="text-[10px] font-bold tracking-widest uppercase text-tertiary/50 mr-2">{label}</span>
      <span className="text-sm font-mono text-secondary">{value}</span>
    </div>
  );
}

export function AgentPill({ name, src, isActive=false }: { name: string; src: string; isActive?: boolean }) {
  return (
    <div className={cn('flex items-center gap-2 px-3 py-1.5 rounded-[var(--radius-pill)] border transition-all', isActive ? 'bg-surface-container-high border-secondary/50 shadow-[0_0_12px_rgba(143,217,255,0.2)]' : 'bg-surface-container border-outline-variant/15 opacity-60 grayscale filter hover:grayscale-0 hover:opacity-100')}>
      <img src={src} alt={name} className="w-5 h-5 rounded-full object-cover" />
      <span className="text-xs font-semibold text-on-surface">{name}</span>
    </div>
  );
}

interface PipelineStepperChildProps {
  stages: { id: string; label: string; status: 'done' | 'active' | 'pending' }[];
}

export function PipelineStepper({ stages }: PipelineStepperChildProps) {
  return (
    <div className="flex items-center justify-between w-full relative">
      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-0.5 bg-outline-variant/15 -z-10" />
      {stages.map((stage) => (
        <div key={stage.id} className="flex flex-col items-center gap-2 relative">
          <div className={cn('w-4 h-4 rounded-full border-2 flex items-center justify-center transition-colors', 
            stage.status === 'done' ? 'bg-secondary border-secondary' : 
            stage.status === 'active' ? 'bg-surface-container border-secondary block' : 
            'bg-surface-container border-outline-variant/15'
          )}>
            {stage.status === 'active' && <div className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse" />}
          </div>
          <span className={cn('text-xs font-medium uppercase tracking-wide', 
            stage.status === 'done' ? 'text-secondary' : 
            stage.status === 'active' ? 'text-on-surface' : 
            'text-tertiary/50'
          )}>{stage.label}</span>
        </div>
      ))}
    </div>
  );
}
