import { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { fetchBuildContextDebug, fetchProjectPipeline } from '../../lib/api/orchestrator';
import type { OrchestrationStep } from '../../lib/api/types';

export function ProjectPipeline({ projectId }: { projectId: string }) {
  const [steps, setSteps] = useState<OrchestrationStep[]>([]);
  const [buildFailureReason, setBuildFailureReason] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const [res, debug] = await Promise.all([
          fetchProjectPipeline(projectId),
          fetchBuildContextDebug(projectId).catch(() => null),
        ]);
        if (!active) return;
        setSteps(res.steps);

        const buildJob = debug?.build_job;
        const rawResult = buildJob?.result as Record<string, unknown> | undefined;
        const label = typeof rawResult?.label === 'string' ? rawResult.label : null;
        if (buildJob?.status === 'failed' && label) {
          setBuildFailureReason(label);
        } else {
          setBuildFailureReason(null);
        }
      } catch (e) {
        // ignore bg errors
      }
    };
    load();
    const interval = setInterval(load, 3000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [projectId]);

  const prevActiveIdRef = useRef<string | null>(null);
  useEffect(() => {
    const activeStep = steps.find(s => s.status === 'active' || (s.status as string) === 'executing');
    const activeId = activeStep?.id ?? null;
    if (activeId && activeId !== prevActiveIdRef.current && scrollRef.current) {
      const activeEl = scrollRef.current.querySelector('[data-active="true"]');
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
    prevActiveIdRef.current = activeId;
  }, [steps]);

  if (!steps.length) return null;

  const completedCount = steps.filter(s => s.status === 'complete').length;
  const progress = Math.round((completedCount / steps.length) * 100);
  const buildFailedByIdleTimeout = Boolean(
    buildFailureReason && buildFailureReason.includes('Build stream idle timeout')
  );

  return (
    <div className="rounded-2xl border border-outline-variant/15 overflow-hidden h-full max-h-[650px] flex flex-col">
      <div className="p-6 md:p-8 border-b border-outline-variant/10 bg-surface-container/30">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="relative w-8 h-8 rounded-lg bg-secondary/10 flex items-center justify-center">
              <div className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
            </div>
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.25em] text-tertiary">
              Live Pipeline
            </h3>
          </div>
          <span className="text-[10px] font-mono text-tertiary/50">
            {completedCount}/{steps.length}
          </span>
        </div>

        <div className="relative h-1 rounded-full bg-surface-container overflow-hidden">
          <motion.div
            className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-secondary/80 to-secondary"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
          />
        </div>

        {buildFailureReason ? (
          <div className="mt-4 rounded-lg border border-primary/30 bg-primary/10 px-3 py-2.5">
            <div className="text-[10px] font-black uppercase tracking-widest text-primary">
              {buildFailedByIdleTimeout ? 'Build timed out (idle stream)' : 'Build failed'}
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-primary/90 break-words">
              {buildFailureReason}
            </p>
          </div>
        ) : null}
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-elegant p-5 md:p-6 space-y-1">
        {steps.map((step, i) => {
          const isComplete = step.status === 'complete';
          const isActive = step.status === 'active';

          return (
            <motion.div
              key={step.id}
              data-active={isActive ? "true" : "false"}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: Math.min(i * 0.04, 0.4) }}
              className={`group relative flex items-start gap-4 px-3 py-3 rounded-xl transition-all duration-300 ${
                isActive ? 'bg-primary/[0.04]' : 'hover:bg-surface-container/40'
              }`}
            >
              <div className="relative flex flex-col items-center pt-0.5">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center transition-all duration-300 ${
                    isComplete
                      ? 'bg-secondary/15 ring-1 ring-secondary/30'
                      : isActive
                        ? 'bg-primary/15 ring-1 ring-primary/40 shadow-[0_0_12px_rgba(244,165,138,0.2)]'
                        : 'bg-surface-container ring-1 ring-outline-variant/20'
                  }`}
                >
                  {isComplete ? (
                    <span className="material-symbols-outlined text-[13px] text-secondary" style={{ fontVariationSettings: "'FILL' 1" }}>check</span>
                  ) : isActive ? (
                    <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                  ) : (
                    <div className="w-1.5 h-1.5 rounded-full bg-tertiary/30" />
                  )}
                </div>

                {i < steps.length - 1 && (
                  <div className={`w-px h-4 mt-1 transition-colors duration-300 ${
                    isComplete ? 'bg-secondary/20' : 'bg-outline-variant/10'
                  }`} />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className={`text-[13px] font-medium leading-tight transition-colors duration-300 ${
                  isActive ? 'text-primary' : isComplete ? 'text-on-surface' : 'text-tertiary/60'
                }`}>
                  {step.label}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] font-mono text-tertiary/40">
                    {(i + 1).toString().padStart(2, '0')}
                  </span>
                  {isActive && (
                    <span className="text-[9px] font-medium text-primary/70 uppercase tracking-widest">
                      Executing
                    </span>
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
