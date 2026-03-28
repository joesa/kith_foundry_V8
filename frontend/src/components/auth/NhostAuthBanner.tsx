import { useAuthenticationStatus } from '@nhost/react';

/**
 * Surfaces Nhost bootstrap/refresh failures (e.g. POST /v1/token 500) and offers a one-click storage reset.
 */
export function NhostAuthBanner() {
  const { isLoading, isError, error, connectionAttempts } = useAuthenticationStatus();

  if (isLoading || !isError || !error) {
    return null;
  }

  const detail =
    typeof error.message === 'string'
      ? error.message
      : error.message != null
        ? JSON.stringify(error.message)
        : error.error;

  return (
    <div
      role="alert"
      className="fixed top-0 left-0 right-0 z-[100] flex flex-wrap items-center justify-center gap-4 px-4 py-3 bg-amber-950/95 border-b border-amber-700/80 text-amber-100 text-sm"
    >
      <span className="font-medium">
        Auth sync failed
        {error.status ? ` (HTTP ${error.status})` : ''}
        {connectionAttempts ? ` · attempts ${connectionAttempts}` : ''}: {detail}
      </span>
      <button
        type="button"
        className="rounded-full bg-amber-200 text-amber-950 px-4 py-1.5 text-xs font-black uppercase tracking-widest hover:bg-white transition-colors"
        onClick={() => {
          Object.keys(localStorage).forEach(k => {
            if (k.startsWith('nhost:')) localStorage.removeItem(k);
          });
          window.location.reload();
        }}
      >
        Clear saved session &amp; reload
      </button>
    </div>
  );
}
