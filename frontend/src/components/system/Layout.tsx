import { Outlet } from 'react-router-dom'

/**
 * Layout
 *
 * Simplified top-level layout wrapper. AppShell handles the main app chrome
 * (sidebar, top command bar, page transitions). This component provides a
 * minimal shell for routes that live outside of AppShell (e.g. auth pages).
 */
export default function Layout() {
  return (
    <div className="min-h-screen bg-background text-on-surface">
      <Outlet />
    </div>
  )
}
