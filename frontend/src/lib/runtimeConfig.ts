const LOCAL_DEV_HOSTS = new Set(["localhost", "127.0.0.1"]);

function getEnv(name: string): string | undefined {
    const value = import.meta.env[name] as string | undefined;
    return value?.trim() || undefined;
}

export function getApiBaseUrl(): string {
    const explicit = getEnv("VITE_API_BASE_URL");
    if (explicit) {
        return explicit.replace(/\/+$/, "");
    }

    if (typeof window !== "undefined" && LOCAL_DEV_HOSTS.has(window.location.hostname)) {
        return "http://localhost:8000";
    }

    if (typeof window !== "undefined") {
        return window.location.origin;
    }

    return "http://localhost:8000";
}

export function getWsUrl(path: string): string {
    const explicit = getEnv("VITE_WS_URL");
    if (explicit) {
        return `${explicit.replace(/\/+$/, "")}${path}`;
    }

    if (typeof window !== "undefined" && LOCAL_DEV_HOSTS.has(window.location.hostname)) {
        return `ws://localhost:8000${path}`;
    }

    if (typeof window !== "undefined") {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        return `${protocol}//${window.location.host}${path}`;
    }

    return `ws://localhost:8000${path}`;
}
