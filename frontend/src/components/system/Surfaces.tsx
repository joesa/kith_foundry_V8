import { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '../../lib/utils/cn';

export const GlassPanel = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'glass-panel ghost-border',
        className
      )}
      {...props}
    />
  )
);
GlassPanel.displayName = 'GlassPanel';

export const SteelPanel = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'steel-gradient rounded-[var(--radius-module)] ghost-border',
        className
      )}
      {...props}
    />
  )
);
SteelPanel.displayName = 'SteelPanel';

export const PriorityPanel = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'steel-gradient rounded-[var(--radius-module)] status-ribbon-ember relative overflow-hidden',
        className
      )}
      {...props}
    >
      {props.children}
    </div>
  )
);
PriorityPanel.displayName = 'PriorityPanel';
