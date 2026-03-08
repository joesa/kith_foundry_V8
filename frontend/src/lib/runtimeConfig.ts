function getEnv(name: string): string | undefined {
    const value = import.meta.env[name] as string | undefined;
    return value?.trim() || undefined;
}

/**
 * Returns the API base URL.
 * - Explicit VITE_API_BASE_URL env var: use it (for staging/prod pointing at separate backend)
 * - Otherwise: empty string (same-origin) — Vite proxy handles /api in dev,
 *   nginx/caddy handles it in production. Works regardless of hostname/IP.
 */
export function getApiBaseUrl(): string {
    const explicit = getEnv("VITE_API_BASE_URL");
    if (explicit) {
        return explicit.replace(/\/+$/, "");
    }
    return ""; // same-origin: let proxy/server handle routing
}

/**
 * Returns the WebSocket URL for a given path.
 * - Explicit VITE_WS_URL env var: use it (for prod/staging)
 * - VITE_API_BASE_URL set: derive from it (http->ws, https->wss) — fixes WSL/dev setups
 *   where frontend hostname (e.g. 172.29.x.x) differs from reachable backend (localhost)
 * - Otherwise: connect directly to the backend port on the same hostname.
 */
export function getWsUrl(path: string): string {
    const explicit = getEnv("VITE_WS_URL");
    if (explicit) {
        return `${explicit.replace(/\/+$/, "")}${path}`;
    }

    // Derive from API base URL so one env var controls both (WSL, Docker, etc.)
    const apiBase = getEnv("VITE_API_BASE_URL");
    if (apiBase) {
        try {
            const url = new URL(apiBase);
            const wsProtocol = url.protocol === "https:" ? "wss:" : "ws:";
            const origin = `${wsProtocol}//${url.hostname}${url.port ? `:${url.port}` : ""}`;
            return `${origin.replace(/\/+$/, "")}${path}`;
        } catch {
            /* ignore */
        }
    }

    if (typeof window !== "undefined") {
        // Same-origin: Vite proxies /ws in dev, nginx in prod — avoids connecting to
        // hostname:8000 directly (fails on WSL/Docker when 172.29.x.x isn't reachable).
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        return `${protocol}//${window.location.host}${path}`;
    }

    return `ws://localhost:8000${path}`;
}
