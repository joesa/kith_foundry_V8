import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useUiStore, type Toast as ToastType } from '../../store/uiStore';
import { cn } from '../../lib/utils/cn';

function ToastItem({ toast }: { toast: ToastType }) {
  const { removeToast } = useUiStore();

  useEffect(() => {
    const timer = setTimeout(() => {
      removeToast(toast.id);
    }, toast.duration || 5000);
    return () => clearTimeout(timer);
  }, [toast, removeToast]);

  const styles = {
    success: 'bg-emerald-500/10 border-emerald-500 text-emerald-500',
    error: 'bg-error/10 border-error text-error',
    info: 'bg-secondary/10 border-secondary text-secondary',
    warning: 'bg-amber-500/10 border-amber-500 text-amber-500',
  };

  const icons = {
    success: 'check_circle',
    error: 'error',
    info: 'info',
    warning: 'warning',
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 50, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
      className={cn(
        'flex items-start gap-3 w-80 p-4 rounded-xl border-l-4 border bg-surface/95 backdrop-blur shadow-2xl relative overflow-hidden',
        styles[toast.variant]
      )}
    >
      <span className="material-symbols-outlined flex-shrink-0 mt-0.5">{icons[toast.variant]}</span>
      <div className="flex-1 pr-6">
        <h4 className="text-sm font-bold m-0 leading-tight">{toast.title}</h4>
        {toast.description && (
          <p className="text-xs opacity-80 mt-1 leading-snug">{toast.description}</p>
        )}
      </div>
      <button 
        onClick={() => removeToast(toast.id)}
        className="absolute top-4 right-4 opacity-50 hover:opacity-100 transition-opacity focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-current rounded"
      >
        <span className="material-symbols-outlined text-sm">close</span>
      </button>
      
      {/* Progress bar */}
      <motion.div 
        className="absolute bottom-0 left-0 h-1 bg-current opacity-20"
        initial={{ width: '100%' }}
        animate={{ width: '0%' }}
        transition={{ duration: (toast.duration || 5000) / 1000, ease: 'linear' }}
      />
    </motion.div>
  );
}

export function ToastContainer() {
  const { toasts } = useUiStore();

  return (
    <div className="fixed bottom-0 right-0 z-[200] p-6 flex flex-col gap-4 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem toast={toast} />
          </div>
        ))}
      </AnimatePresence>
    </div>
  );
}
