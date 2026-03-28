/** Base URL for control-plane API. Empty string uses same origin (Vite dev proxy → FastAPI). */
export function getApiBaseUrl(): string {
  const v = import.meta.env.VITE_API_BASE_URL;
  if (typeof v === 'string' && v.length > 0) {
    const cleaned = v.replace(/\/$/, '');
    try {
      const u = new URL(cleaned);
      if (u.hostname === 'sandbox-api.forgeoperator.com' || u.hostname === 'api.forgeoperator.com') {
        return 'https://kith-backend.fly.dev';
      }
    } catch {
      // ignore parse errors and keep cleaned value
    }
    return cleaned;
  }
  return '';
}

export function apiPath(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`;
  const base = getApiBaseUrl();
  return `${base}${p}`;
}
