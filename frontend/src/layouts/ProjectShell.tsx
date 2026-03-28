import { useEffect, useMemo, useState } from 'react';
import { Outlet, useParams, useLocation } from 'react-router-dom';
import { ProgressRail, type ProgressStage } from '../components/ui/ProgressRail';
import { fetchProjectPipeline } from '../lib/api/orchestrator';

// A static representation for testing UI logic.
// In actual use, fetchProjectPipeline from the API sets the completion statuses.
const PIPELINE_STAGES: Omit<ProgressStage, 'status'>[] = [
  { id: 'ideation', label: 'Ideation', route: '', icon: 'lightbulb' },
  { id: 'csuite', label: 'Executive Analysis', route: 'executive/agents', icon: 'groups' },
  { id: 'prd', label: 'PRD Generation', route: 'prd', icon: 'description' },
  { id: 'design', label: 'Design Identity', route: 'design', icon: 'palette' },
  { id: 'capabilities', label: 'Capabilities Gate', route: 'capabilities', icon: 'tune' },
  { id: 'build', label: 'Build & Compilation', route: 'build', icon: 'code' },
  { id: 'deploy', label: 'Deployment', route: 'deploy', icon: 'rocket_launch' },
];

export function ProjectShell() {
  const { projectId } = useParams();
  const location = useLocation();
  const [projectStatus, setProjectStatus] = useState<string | null>(null);

  if (!projectId) {
    return <Outlet />;
  }

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const pipeline = await fetchProjectPipeline(projectId);
        if (active) setProjectStatus(pipeline.project_status ?? null);
      } catch {
        // Keep route-derived fallback if polling fails.
      }
    };

    load();
    const interval = setInterval(load, 3000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [projectId]);

  const statusToStage: Record<string, string> = {
    ideation: 'ideation',
    idea_selected: 'csuite',
    executive_review: 'csuite',
    planning: 'prd',
    architecture: 'prd',
    designing: 'design',
    generating_code: 'capabilities',
    building: 'build',
    in_progress: 'deploy',
    deploy_ready: 'deploy',
    deployed: 'deploy',
    failed: 'deploy',
  };

  // Fallback to pathname-based stage when pipeline status isn't available yet.
  let routeStageId = 'ideation';
  if (location.pathname.includes('/executive')) routeStageId = 'csuite';
  else if (location.pathname.includes('/prd')) routeStageId = 'prd';
  else if (location.pathname.includes('/design')) routeStageId = 'design';
  else if (location.pathname.includes('/capabilities')) routeStageId = 'capabilities';
  else if (location.pathname.includes('/build')) routeStageId = 'build';
  else if (location.pathname.includes('/deploy') || location.pathname.includes('/sandbox')) routeStageId = 'deploy';

  const currentStageId = (projectStatus && statusToStage[projectStatus]) || routeStageId;

  const stages: ProgressStage[] = useMemo(() => {
    const currentIndex = PIPELINE_STAGES.findIndex((s) => s.id === currentStageId);
    return PIPELINE_STAGES.map((s, i) => ({
      ...s,
      status: i < currentIndex ? 'complete' : i === currentIndex ? 'active' : 'pending',
    }));
  }, [currentStageId]);

  return (
    <div className="flex h-full w-full relative">
      <ProgressRail projectId={projectId} currentStageId={currentStageId} stages={stages} />
      <div className="flex-1 w-full min-w-0 pr-4 pl-4 md:pl-8 py-8 h-full overflow-y-auto">
        <Outlet />
      </div>
    </div>
  );
}
