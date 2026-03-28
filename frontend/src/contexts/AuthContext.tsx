import { createContext, useContext, useEffect, useState, useCallback, useRef, type ReactNode } from "react";
import { getAuth } from "../lib/auth";
import type { AuthUser, AuthSession, AuthClient } from "../lib/auth";

export type { AuthUser, AuthSession };

interface AuthContextType {
    user: AuthUser | null;
    session: AuthSession | null;
    loading: boolean;
    signUp: (email: string, password: string) => Promise<{ error: string | null }>;
    signIn: (email: string, password: string) => Promise<{ error: string | null }>;
    signOut: () => Promise<void>;
    getAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<AuthUser | null>(null);
    const [session, setSession] = useState<AuthSession | null>(null);
    const [loading, setLoading] = useState(true);
    const authRef = useRef<AuthClient | null>(null);

    useEffect(() => {
        let cancelled = false;
        let unsub: () => void = () => {};
        let settled = false;
        let settleTimer: number | null = null;

        const finishInitialLoad = () => {
            if (cancelled || settled) return;
            settled = true;
            setLoading(false);
        };

        getAuth()
            .then((auth) => {
                if (cancelled) return;
                if (!auth) {
                    finishInitialLoad();
                    return;
                }
                authRef.current = auth;

                // Subscribe for future auth changes, but do not use the first callback
                // as the signal that bootstrap is done. The Nhost adapter emits the
                // current stored session immediately, which can be null before the real
                // async session refresh completes on a hard load.
                unsub = auth.onAuthStateChange((s) => {
                    if (cancelled) return;
                    setSession(s);
                    setUser(s?.user ?? null);
                });

                auth.getSession()
                    .then((s) => {
                        if (cancelled) return;
                        setSession(s);
                        setUser(s?.user ?? null);
                    })
                    .catch(() => {
                        if (cancelled) return;
                        setSession(null);
                        setUser(null);
                    })
                    .finally(() => finishInitialLoad());

                // Guard against an auth SDK hang during bootstrap.
                settleTimer = window.setTimeout(() => {
                    auth.getSession()
                        .then((s) => {
                            if (cancelled) return;
                            setSession(s);
                            setUser(s?.user ?? null);
                        })
                        .catch(() => {})
                        .finally(() => finishInitialLoad());
                }, 8000);
            })
            .catch(() => finishInitialLoad());
        return () => {
            cancelled = true;
            unsub();
            if (settleTimer !== null) window.clearTimeout(settleTimer);
        };
    }, []);

    const signUp = useCallback(async (email: string, password: string) => {
        const auth = authRef.current;
        if (!auth) return { error: "Auth not ready" };
        const { error } = await auth.signUp(email, password);
        if (!error) {
            const nextSession = await auth.getSession().catch(() => null);
            setSession(nextSession);
            setUser(nextSession?.user ?? null);
        }
        return { error };
    }, []);

    const signIn = useCallback(async (email: string, password: string) => {
        const auth = authRef.current;
        if (!auth) return { error: "Auth not ready" };
        const { error } = await auth.signIn(email, password);
        if (!error) {
            const nextSession = await auth.getSession().catch(() => null);
            setSession(nextSession);
            setUser(nextSession?.user ?? null);
        }
        return { error };
    }, []);

    const signOut = useCallback(async () => {
        const auth = authRef.current;
        if (auth) await auth.signOut();
        setSession(null);
        setUser(null);
    }, []);

    const getAccessToken = useCallback(async () => {
        const auth = authRef.current;
        if (!auth) return null;
        return await auth.getAccessToken();
    }, []);

    return (
        <AuthContext.Provider value={{ user, session, loading, signUp, signIn, signOut, getAccessToken }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
    return ctx;
}
