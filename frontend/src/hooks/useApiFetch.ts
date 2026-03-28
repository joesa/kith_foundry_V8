/**
 * Authenticated fetch hook — attaches Nhost Bearer token and handles 401.
 * Use for all backend API calls. On 401 or missing token: signOut + redirect to /login.
 */
import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { getApiBaseUrl } from "../lib/runtimeConfig";

export type ApiFetchOptions = RequestInit & { skipAuth?: boolean };

export function useApiFetch() {
    const { getAccessToken, signOut } = useAuth();
    const navigate = useNavigate();

    const apiFetch = useCallback(
        async (path: string, options: ApiFetchOptions = {}): Promise<Response> => {
            const { skipAuth, ...init } = options;
            const url = path.startsWith("http") ? path : `${getApiBaseUrl()}${path}`;

            const isIdeationRequest = path.includes("/api/v1/ideation/generate-unique") || path.includes("/api/v1/ideation/questionnaire");
            const timeoutMs = isIdeationRequest ? 120000 : 30000;
            const timeoutController = new AbortController();
            const timeoutHandle = window.setTimeout(() => timeoutController.abort(), timeoutMs);
            const incomingSignal = init.signal;

            if (incomingSignal) {
                if (incomingSignal.aborted) {
                    window.clearTimeout(timeoutHandle);
                    throw new Error("Request aborted");
                }
                incomingSignal.addEventListener("abort", () => timeoutController.abort(), { once: true });
            }

            if (!skipAuth) {
                const token = await getAccessToken();
                if (!token) {
                    await signOut();
                    navigate("/login", { replace: true });
                    throw new Error("Not authenticated");
                }
                init.headers = {
                    ...init.headers,
                    Authorization: `Bearer ${token}`,
                };
            }

            let resp: Response;
            try {
                resp = await fetch(url, { ...init, signal: timeoutController.signal });
            } catch (err: any) {
                if (err?.name === "AbortError") {
                    throw new Error("Request timed out. Please try again.");
                }
                throw err;
            } finally {
                window.clearTimeout(timeoutHandle);
            }

            const ct = resp.headers.get("content-type") || "";
            if ((ct.includes("text/html") || ct.includes("application/xhtml+xml")) && !path.includes(".html")) {
                const body = await resp.text().catch(() => "");
                if (body.toLowerCase().includes("just a moment") || body.toLowerCase().includes("cf-chl")) {
                    throw new Error("Network security challenge blocked the API request. Please refresh and try again.");
                }
            }

            if (resp.status === 401) {
                await signOut();
                navigate("/login", { replace: true });
                throw new Error("Session expired");
            }
            return resp;
        },
        [getAccessToken, signOut, navigate]
    );

    return apiFetch;
}
