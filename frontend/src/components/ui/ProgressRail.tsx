import { Link } from 'react-router-dom';

export interface ProgressStage {
  id: string;
  label: string;
  route: string;
  icon: string;
  status: 'pending' | 'active' | 'complete';
}

interface ProgressRailProps {
  projectId: string;
  currentStageId: string;
  stages: ProgressStage[];
}

export function ProgressRail({ projectId, currentStageId, stages }: ProgressRailProps) {
  return (
    <div className="hidden lg:flex flex-col w-[72px] min-h-screen border-r border-outline-variant/8 bg-surface-container-lowest/50 backdrop-blur-sm items-center py-8 z-20 sticky top-0">
      <div className="flex-1 flex flex-col gap-4 w-full items-center">
        {stages.map((stage, i) => {
          const isActive = stage.id === currentStageId;
          const isComplete = stage.status === 'complete';

          return (
            <div key={stage.id} className="relative flex flex-col items-center group w-full">
              <Link
                to={`/app/projects/${projectId}/${stage.route}`}
                className="relative flex flex-col items-center justify-center gap-2"
                title={stage.label}
              >
                <div
                  className={`flex items-center justify-center w-9 h-9 rounded-xl transition-all duration-300
                    ${isActive
                      ? 'bg-primary/12 text-primary ring-1 ring-primary/25 shadow-[0_0_16px_rgba(244,165,138,0.12)]'
                      : isComplete
                        ? 'bg-emerald-500/12 text-emerald-400 ring-1 ring-emerald-400/25 shadow-[0_0_16px_rgba(74,222,128,0.14)]'
                        : 'bg-surface-container/60 text-tertiary/35 hover:bg-surface-container-high hover:text-tertiary/60 ring-1 ring-outline-variant/8'
                    }`}
                >
                  <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: isComplete ? "'FILL' 1" : undefined }}>
                    {stage.icon}
                  </span>
                </div>

                <div className="absolute left-[calc(100%+14px)] px-3 py-1.5 bg-surface-container-highest/95 backdrop-blur-sm text-on-surface text-[10px] font-medium tracking-wide rounded-lg shadow-xl border border-outline-variant/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50">
                  {stage.label}
                </div>
              </Link>

              {i < stages.length - 1 && (
                <div className="h-4 w-px my-1 relative">
                  <div className={`absolute inset-0 transition-colors duration-500 ${
                    isComplete ? 'bg-emerald-400/30' : 'bg-outline-variant/8'
                  }`} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
