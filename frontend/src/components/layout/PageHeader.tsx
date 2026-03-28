import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils/cn';
import { Breadcrumbs } from './Breadcrumbs';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
  withBreadcrumbs?: boolean;
}

export function PageHeader({ title, description, actions, className, withBreadcrumbs = true }: PageHeaderProps) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className={cn("flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12", className)}
    >
      <div>
        {withBreadcrumbs && <Breadcrumbs />}
        <h1 className="text-4xl sm:text-5xl md:text-7xl font-black uppercase tracking-tighter cinematic-tracking text-on-surface leading-none">
          {title}
        </h1>
        {description && (
          <p className="font-inter text-tertiary mt-4 text-sm sm:text-base md:text-lg max-w-2xl leading-relaxed">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-3 shrink-0">
          {actions}
        </div>
      )}
    </motion.div>
  );
}
