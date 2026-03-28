import type { ReactNode } from 'react';
import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { modalOverlay, modalContent } from '../../lib/utils/motion';
import { cn } from '../../lib/utils/cn';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
  hideCloseButton?: boolean;
}

export function Modal({ 
  isOpen, 
  onClose, 
  title, 
  description, 
  children, 
  className,
  hideCloseButton = false 
}: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  // Focus trap and escape key handler
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();

      if (e.key === 'Tab' && contentRef.current) {
        const focusableElements = contentRef.current.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0] as HTMLElement;
        const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement?.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement?.focus();
            e.preventDefault();
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    
    // Auto-focus first element
    setTimeout(() => {
      if (contentRef.current) {
        const firstAria = contentRef.current.querySelector('[autofocus], button, input, textarea, select') as HTMLElement;
        firstAria?.focus();
      }
    }, 100);

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={overlayRef}
          variants={modalOverlay}
          initial="hidden"
          animate="visible"
          exit="exit"
          onClick={handleOverlayClick}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 md:p-12 bg-black/60 backdrop-blur-md"
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? "modal-title" : undefined}
          aria-describedby={description ? "modal-description" : undefined}
        >
          <motion.div
            ref={contentRef}
            variants={modalContent}
            className={cn(
              "relative w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-surface border border-outline-variant shadow-2xl rounded-[var(--radius-lg)] flex flex-col",
              className
            )}
          >
            {(title || !hideCloseButton) && (
              <div className="flex items-start justify-between p-6 md:p-8 border-b border-outline-variant/30 shrink-0 sticky top-0 bg-surface/95 backdrop-blur z-10">
                <div>
                  {title && (
                    <h2 id="modal-title" className="text-xl md:text-2xl font-black uppercase tracking-widest text-on-surface">
                      {title}
                    </h2>
                  )}
                  {description && (
                    <p id="modal-description" className="text-tertiary text-sm mt-2">
                      {description}
                    </p>
                  )}
                </div>
                {!hideCloseButton && (
                  <button
                    onClick={onClose}
                    className="p-2 text-tertiary hover:text-on-surface hover:bg-surface-container rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary -mr-2 -mt-2"
                    aria-label="Close dialog"
                  >
                    <span className="material-symbols-outlined">close</span>
                  </button>
                )}
              </div>
            )}
            
            <div className="p-6 md:p-8">
              {children}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
