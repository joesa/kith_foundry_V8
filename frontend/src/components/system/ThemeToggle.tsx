import React from 'react';
import { motion } from 'framer-motion';
import { useUiStore } from '../../store/uiStore';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useUiStore();
  const isDark = theme === 'dark';

  return (
    <button
      onClick={toggleTheme}
      className="relative p-2 rounded-full text-tertiary hover:text-on-surface hover:bg-surface-container transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} theme`}
      title={`Switch to ${isDark ? 'light' : 'dark'} theme`}
    >
      <div className="relative w-5 h-5 flex items-center justify-center overflow-hidden">
        <motion.span
          className="material-symbols-outlined absolute text-[20px]"
          initial={false}
          animate={{
            y: isDark ? 0 : 24,
            opacity: isDark ? 1 : 0,
            scale: isDark ? 1 : 0.5,
          }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
        >
          dark_mode
        </motion.span>
        
        <motion.span
          className="material-symbols-outlined absolute text-[20px]"
          initial={false}
          animate={{
            y: isDark ? -24 : 0,
            opacity: isDark ? 0 : 1,
            scale: isDark ? 0.5 : 1,
          }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
        >
          light_mode
        </motion.span>
      </div>
    </button>
  );
};
