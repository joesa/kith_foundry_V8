import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export interface ArtifactCardProps {
  title: string;
  subtitle: string;
  icon: string;
  iconBgColor?: string; // e.g. 'bg-orange-500' or hex '#E17055'
  iconTextColor?: string;
  markdownContent: string;
  onDownload?: () => void;
  defaultExpanded?: boolean;
}

export function ArtifactCard({
  title,
  subtitle,
  icon,
  iconBgColor = 'bg-[#E17055]', // Default matching the orange in the screenshot
  iconTextColor = 'text-[#2D1B15]',
  markdownContent,
  onDownload,
  defaultExpanded = true,
}: ArtifactCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className="rounded-[1.5rem] bg-[#1E1E1E] border border-outline-variant/10 overflow-hidden shadow-lg">
      {/* Header section */}
      <div 
        className="p-6 md:p-8 flex items-start gap-5 cursor-pointer hover:bg-white/[0.02] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className={`mt-1 h-[60px] w-[60px] shrink-0 rounded-full ${iconBgColor} flex items-center justify-center shadow-md`}>
          <span className={`material-symbols-outlined text-[32px] ${iconTextColor}`}>{icon}</span>
        </div>
        
        <div className="flex-1 min-w-0 pr-4 mt-1">
          <h2 className="text-xl font-black tracking-tight text-white mb-1">{title}</h2>
          <p className="text-sm md:text-base text-tertiary leading-relaxed truncate">{subtitle}</p>
        </div>

        <div className="flex items-center gap-3 mt-1" onClick={(e) => e.stopPropagation()}>
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="h-10 w-10 rounded-full flex items-center justify-center hover:bg-white/10 text-tertiary hover:text-white transition-colors"
          >
            <span className="material-symbols-outlined text-2xl transition-transform duration-300" style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0)' }}>
              expand_more
            </span>
          </button>
          {onDownload && (
            <button
              type="button"
              onClick={onDownload}
              className="h-10 w-10 rounded-full flex items-center justify-center hover:bg-white/10 text-tertiary hover:text-white transition-colors bg-[#2A2A2A]"
            >
              <span className="material-symbols-outlined text-xl">download</span>
            </button>
          )}
        </div>
      </div>

      {/* Expandable content area */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-6 pb-6 md:px-8 md:pb-8 pt-0 pl-[108px]">
              <div className="text-sm md:text-base text-tertiary font-mono whitespace-pre-wrap leading-relaxed">
                {markdownContent}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
