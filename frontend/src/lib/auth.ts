/**
 * Auth client — Nhost only (VITE_USE_NHOST=1). Supabase is no longer used.
 */
const useNhost = import.meta.env.VITE_USE_NHOST === "1";

export interface AuthUser {
    id: string;
    email?: string;
}

export interface AuthSession {
    access_token: string;
    user: AuthUser;
}

export interface AuthClient {
    getSession(): Promise<AuthSession | null>;
    onAuthStateChange(cb: (session: AuthSession | null) => void): () => void;
    signUp(email: string, password: string): Promise<{ error: string | null }>;
    signIn(email: string, password: string): Promise<{ error: string | null }>;
    signOut(): Promise<void>;
    getAccessToken(): Promise<string | null>;
}

async function getAuthClient(): Promise<AuthClient> {
    if (useNhost) {
        const { nhostAuth } = await import("./nhost");
        if (nhostAuth) return nhostAuth;
        throw new Error(
            "Nhost auth not configured. Set VITE_NHOST_SUBDOMAIN and VITE_NHOST_REGION in .env"
        );
    }
    throw new Error(
        "Auth requires Nhost. Set VITE_USE_NHOST=1 and configure VITE_NHOST_SUBDOMAIN in .env"
    );
}

let _client: AuthClient | null = null;

export async function getAuth(): Promise<AuthClient> {
    if (!_client) {
        _client = await getAuthClient();
    }
    return _client;
}
