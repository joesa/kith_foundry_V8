import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { SidebarNav } from '../components/layout/SidebarNav';
import { ToastContainer } from '../components/system/Toast';
import { TopCommandBar } from '../components/layout/TopCommandBar';
import { useUiStore } from '../store/uiStore';
import { pageTransition } from '../lib/utils/motion';

export function AppShell() {
  const {
    theme,
    sidebarOpen,
    setSidebarOpen,
    hideSidebarDuringBuild,
    setHideSidebarDuringBuild,
    setActiveProjectIdBeingBuilt,
  } = useUiStore();
  const location = useLocation();

  const projectMatch = location.pathname.match(/^\/app\/projects\/([^/]+)(?:\/|$)/);
  const activeProjectId = projectMatch?.[1] ?? null;

  useEffect(() => {
    if (activeProjectId) {
      setHideSidebarDuringBuild(true);
      setActiveProjectIdBeingBuilt(activeProjectId);
      setSidebarOpen(false);
      return;
    }

    if (hideSidebarDuringBuild) {
      setHideSidebarDuringBuild(false);
      setActiveProjectIdBeingBuilt(null);
    }
  }, [
    activeProjectId,
    hideSidebarDuringBuild,
    setActiveProjectIdBeingBuilt,
    setHideSidebarDuringBuild,
    setSidebarOpen,
  ]);

  useEffect(() => {
    if (theme === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  }, [theme]);

  useEffect(() => {
    const handleResize = () => {
      if (hideSidebarDuringBuild) {
        setSidebarOpen(false);
        return;
      }
      if (window.innerWidth < 1024) {
        setSidebarOpen(false);
      } else {
        setSidebarOpen(true);
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [hideSidebarDuringBuild, setSidebarOpen]);

  return (
    <div className="bg-background min-h-screen text-on-surface font-body selection:bg-primary/20 selection:text-on-surface flex overflow-hidden">
      {!hideSidebarDuringBuild && <SidebarNav />}
      {sidebarOpen && !hideSidebarDuringBuild && (
        <div
          className="fixed inset-0 bg-black/30 backdrop-blur-sm z-30 lg:hidden transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="flex-1 flex flex-col min-w-0 transition-all duration-300 relative h-screen overflow-y-auto">
        <TopCommandBar />

        <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 md:px-8 lg:px-12 py-8 md:py-12 relative">
          <div className="ambient-mesh absolute inset-0 pointer-events-none" />
          <AnimatePresence mode="sync">
            <motion.div
              key={`${location.pathname}${location.search}`}
              variants={pageTransition}
              initial="initial"
              animate="animate"
              exit="exit"
              className="space-y-12 relative"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
      <ToastContainer />
    </div>
  );
}
