import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthenticationStatus } from '@nhost/react';

import { isNhostConfigured } from '../../lib/nhost-config';

export function RequireAuth({ children }: { children: ReactNode }) {
  if (!isNhostConfigured()) {
    return <>{children}</>;
  }
  return <RequireAuthGate>{children}</RequireAuthGate>;
}

function RequireAuthGate({ children }: { children: ReactNode }) {
  const location = useLocation();
  const { isAuthenticated, isLoading } = useAuthenticationStatus();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-container-lowest text-on-surface">
        <p className="text-sm font-bold uppercase tracking-widest text-tertiary animate-pulse">
          Loading session…
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }

  return <>{children}</>;
}
