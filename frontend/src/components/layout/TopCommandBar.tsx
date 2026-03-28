import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { TopAuthMenu } from '../auth/TopAuthMenu';

import { isNhostConfigured } from '../../lib/nhost-config';
import { useUiStore } from '../../store/uiStore';
import { useProjectStore } from '../../store/projectStore';
import { ThemeToggle } from '../system/ThemeToggle';

export function TopCommandBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { projectId } = useParams();
  const [primaryProjectId, setPrimaryProjectId] = useState<string | null>(null);
  const { setSidebarOpen, sidebarOpen, hideSidebarDuringBuild, activeProjectIdBeingBuilt } = useUiStore();
  const { currentProject } = useProjectStore();

  const isProjectRoute = /^\/app\/projects\/[^/]+(?:\/|$)/.test(location.pathname);
  const compactNavMode = hideSidebarDuringBuild && isProjectRoute && Boolean(activeProjectIdBeingBuilt || projectId);

  const compactNavItems = [
    { to: '/app/home', icon: 'dashboard', label: 'Overview' },
    { to: '/app/projects', icon: 'memory', label: 'Neural Grid' },
    { to: '/app/agents', icon: 'group_work', label: 'Active Agents' },
    { to: '/app/logs', icon: 'terminal', label: 'Process Logs' },
    { to: '/app/telemetry', icon: 'sensors', label: 'Telemetry' },
    { to: '/app/vault', icon: 'key', label: 'Vault' },
    { to: '/app/capabilities', icon: 'shield', label: 'Security' },
  ];

  useEffect(() => {
    setPrimaryProjectId('new');
  }, []);

  const onInitialize = () => {
    const id = primaryProjectId ?? 'prj_1';
    navigate(`/app/projects/${id}/ideas`);
  };

  return (
    <header className="sticky top-0 w-full z-30 bg-surface/70 backdrop-blur-2xl flex justify-between items-center px-4 md:px-8 h-16 border-b border-outline-variant/10 flex-shrink-0">
      <div className="flex items-center gap-6">
        {!sidebarOpen && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 -ml-2 text-tertiary hover:text-on-surface lg:hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary rounded-lg transition-colors"
          >
            <span className="material-symbols-outlined">menu</span>
          </button>
        )}

        {compactNavMode ? (
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10 text-primary flex-shrink-0">
              <span className="material-symbols-outlined text-[16px]">folder_open</span>
            </div>
            <div className="flex flex-col">
              <h1 className="text-sm font-headline font-semibold text-on-surface">
                {currentProject?.name ?? 'Project Workspace'}
              </h1>
              <p className="text-[10px] text-tertiary/60 font-medium">
                {currentProject?.status ? `Stage: ${currentProject.status}` : 'Project pipeline in progress'}
              </p>
            </div>

            <nav className="hidden lg:flex items-center gap-1 pl-2">
              {compactNavItems.map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  title={item.label}
                  className="w-9 h-9 rounded-lg border border-outline-variant/20 text-tertiary/70 hover:text-on-surface hover:border-outline-variant/50 hover:bg-surface-container/50 transition-all flex items-center justify-center"
                >
                  <span className="material-symbols-outlined text-[18px]">{item.icon}</span>
                </Link>
              ))}
            </nav>
          </div>
        ) : (
          <>
            <h1 className="text-lg font-headline font-semibold tracking-tight text-on-surface lg:hidden">
              Forge
            </h1>

            <nav className="hidden xl:flex gap-1">
              <Link
                className="px-4 py-2 rounded-lg text-[11px] font-medium tracking-wide text-primary bg-primary/[0.06] transition-all duration-300"
                to="/app/home"
              >
                Command
              </Link>
              <Link
                className="px-4 py-2 rounded-lg text-[11px] font-medium tracking-wide text-tertiary/60 hover:text-on-surface hover:bg-surface-container/40 transition-all duration-300"
                to="/app/agents"
              >
                Agents
              </Link>
              <Link
                className="px-4 py-2 rounded-lg text-[11px] font-medium tracking-wide text-tertiary/60 hover:text-on-surface hover:bg-surface-container/40 transition-all duration-300"
                to="/app/telemetry"
              >
                Telemetry
              </Link>
              <Link
                className="px-4 py-2 rounded-lg text-[11px] font-medium tracking-wide text-tertiary/60 hover:text-on-surface hover:bg-surface-container/40 transition-all duration-300"
                to="/app/vault"
              >
                Vault
              </Link>
            </nav>
          </>
        )}
      </div>

      <div className="flex items-center gap-2 md:gap-4">
        <div className="relative hidden md:block">
          <span className="absolute inset-y-0 left-3 flex items-center text-tertiary/40">
            <span className="material-symbols-outlined text-[16px]">search</span>
          </span>
          <input
            className="bg-surface-container/50 border border-outline-variant/10 rounded-xl py-2 pl-9 pr-4 text-[11px] font-medium tracking-wide text-on-surface placeholder:text-tertiary/30 focus:ring-1 focus:ring-secondary/30 focus:border-secondary/20 w-44 lg:w-52 outline-none transition-all duration-300"
            placeholder="Search system..."
            type="text"
          />
        </div>

        <ThemeToggle />

        <button
          type="button"
          onClick={onInitialize}
          className="hidden md:flex items-center gap-2 bg-gradient-to-r from-primary-container to-primary-container/85 text-on-primary-container px-5 py-2 rounded-xl font-semibold text-[11px] tracking-wide hover:shadow-[0_0_24px_rgba(212,101,74,0.15)] transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
        >
          <span className="material-symbols-outlined text-[14px]">bolt</span>
          Initialize
        </button>

        <button
          type="button"
          onClick={onInitialize}
          className="md:hidden bg-gradient-to-r from-primary-container to-primary-container/85 text-on-primary-container p-2 rounded-xl flex items-center justify-center hover:shadow-[0_0_20px_rgba(212,101,74,0.15)] transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
        >
          <span className="material-symbols-outlined text-[16px]">bolt</span>
        </button>

        {isNhostConfigured() ? (
          <TopAuthMenu />
        ) : (
          <Link
            to="/login"
            className="rounded-xl border border-outline-variant/15 px-4 py-2 text-[11px] font-medium text-tertiary/60 hover:border-primary/25 hover:text-primary transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
          >
            Sign in
          </Link>
        )}
      </div>
    </header>
  );
}
