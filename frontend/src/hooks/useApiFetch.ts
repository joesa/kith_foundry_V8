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

            const resp = await fetch(url, init);
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
