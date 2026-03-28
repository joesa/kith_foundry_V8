import { getApiBaseUrl } from "../runtimeConfig";

export class ApiError extends Error {
    status: number;
    detail: unknown;

    constructor(
        status: number,
        detail: unknown,
        message?: string,
    ) {
        super(message ?? `API error ${status}`);
        this.status = status;
        this.detail = detail;
        this.name = "ApiError";
    }
}

export async function apiRequest<T>(
    path: string,
    token: string,
    init?: RequestInit,
): Promise<T> {
    const url = `${getApiBaseUrl()}${path}`;
    const res = await fetch(url, {
        ...init,
        headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            ...init?.headers,
        },
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(res.status, body?.detail ?? body, body?.detail ?? `Request failed (${res.status})`);
    }
    if (res.status === 204) return undefined as T;
    return res.json();
}
