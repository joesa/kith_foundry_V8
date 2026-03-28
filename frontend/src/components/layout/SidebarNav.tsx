import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../../lib/utils/cn';
import { useUiStore } from '../../store/uiStore';

const NAV_ITEMS = [
  { name: 'Overview', path: '/app/home', icon: 'dashboard' },
  { name: 'Neural Grid', path: '/app/projects', icon: 'memory' },
  { name: 'Active Agents', path: '/app/agents', icon: 'group_work' },
  { name: 'Process Logs', path: '/app/logs', icon: 'terminal' },
  { name: 'Telemetry', path: '/app/telemetry', icon: 'sensors' },
  { name: 'Vault', path: '/app/vault', icon: 'key' },
  { name: 'Security', path: '/app/capabilities', icon: 'shield' },
];

export function SidebarNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const { sidebarOpen, setSidebarOpen } = useUiStore();

  return (
    <AnimatePresence initial={false}>
      {sidebarOpen && (
        <motion.aside
          initial={{ x: -280 }}
          animate={{ x: 0 }}
          exit={{ x: -280 }}
          transition={{ type: 'spring', bounce: 0, duration: 0.45 }}
          className="h-screen w-[280px] fixed lg:relative z-40 bg-surface-container-lowest/95 backdrop-blur-xl flex flex-col pt-24 pb-8 border-r border-outline-variant/10 flex-shrink-0"
        >
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden absolute top-6 right-6 p-2 text-tertiary hover:text-on-surface transition-colors"
          >
            <span className="material-symbols-outlined">close</span>
          </button>

          <div className="px-8 mb-14">
            <h2 className="font-headline text-primary font-bold text-2xl tracking-tight">FORGE</h2>
            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-tertiary/50 mt-1">v5.0.0-LUX</p>
          </div>

          <nav className="flex-1 relative px-3">
            {NAV_ITEMS.map((item) => {
              const isActive = location.pathname.startsWith(item.path);
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => window.innerWidth < 1024 && setSidebarOpen(false)}
                  className={cn(
                    'px-5 py-3.5 flex items-center gap-4 text-[12px] font-medium tracking-wide transition-all duration-300 relative z-10 rounded-xl mb-0.5',
                    isActive
                      ? 'text-on-surface'
                      : 'text-tertiary/60 hover:text-on-surface hover:bg-surface-container/40'
                  )}
                >
                  <span
                    className={cn(
                      'material-symbols-outlined text-[20px] transition-colors duration-300',
                      isActive ? 'text-primary' : ''
                    )}
                    style={{ fontVariationSettings: isActive ? "'FILL' 1" : undefined }}
                  >
                    {item.icon}
                  </span>
                  <span>{item.name}</span>
                  {isActive && (
                    <motion.div
                      layoutId="activeSidebarIndicator"
                      className="absolute inset-0 bg-surface-container/60 rounded-xl border border-outline-variant/10 -z-10"
                      initial={false}
                      transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                    />
                  )}
                </NavLink>
              );
            })}
          </nav>

          <div className="px-5 mt-auto">
            <button
              onClick={() => {
                navigate('/app/agents');
                if (window.innerWidth < 1024) setSidebarOpen(false);
              }}
              className="w-full py-3.5 bg-gradient-to-r from-primary-container to-primary-container/90 text-on-primary-container rounded-xl font-semibold text-[11px] uppercase tracking-[0.15em] hover:shadow-[0_0_30px_rgba(212,101,74,0.15)] transition-all duration-300 focus-visible:ring-2 focus-visible:ring-secondary focus-visible:outline-none"
            >
              Deploy Agent
            </button>
            <div className="mt-8 flex flex-col gap-1 px-2">
              <NavLink
                to="/app/telemetry"
                onClick={() => window.innerWidth < 1024 && setSidebarOpen(false)}
                className="text-tertiary/50 flex items-center gap-3 text-[11px] tracking-wide hover:text-on-surface transition-colors duration-300 py-2 rounded-lg hover:bg-surface-container/30 px-3"
              >
                <span className="material-symbols-outlined text-[16px]">sensors</span>
                <span>System Health</span>
              </NavLink>
              <NavLink
                to="/app/profile"
                onClick={() => window.innerWidth < 1024 && setSidebarOpen(false)}
                className="text-tertiary/50 flex items-center gap-3 text-[11px] tracking-wide hover:text-on-surface transition-colors duration-300 py-2 rounded-lg hover:bg-surface-container/30 px-3"
              >
                <span className="material-symbols-outlined text-[16px]">settings</span>
                <span>Profile &amp; Settings</span>
              </NavLink>
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
