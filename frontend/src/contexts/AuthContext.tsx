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
        let unsub: () => void = () => {};
        let settled = false;               // true after initial auth state is determined
        getAuth()
            .then((auth) => {
                if (!auth) {
                    setLoading(false);
                    return;
                }
                authRef.current = auth;

                // Subscribe to auth state changes FIRST — Nhost fires this once
                // on startup after it restores session from local storage.
                unsub = auth.onAuthStateChange((s) => {
                    setSession(s);
                    setUser(s?.user ?? null);
                    if (!settled) {
                        settled = true;
                        setLoading(false);
                    }
                });

                // Fallback: if onAuthStateChange doesn't fire within 3s
                // (e.g. no stored session), stop loading anyway.
                setTimeout(() => {
                    if (!settled) {
                        settled = true;
                        // One last sync check
                        auth.getSession()
                            .then((s) => {
                                setSession(s);
                                setUser(s?.user ?? null);
                            })
                            .catch(() => {})
                            .finally(() => setLoading(false));
                    }
                }, 3000);
            })
            .catch(() => setLoading(false));
        return () => unsub();
    }, []);

    const signUp = useCallback(async (email: string, password: string) => {
        const auth = authRef.current;
        if (!auth) return { error: "Auth not ready" };
        const { error } = await auth.signUp(email, password);
        return { error };
    }, []);

    const signIn = useCallback(async (email: string, password: string) => {
        const auth = authRef.current;
        if (!auth) return { error: "Auth not ready" };
        const { error } = await auth.signIn(email, password);
        return { error };
    }, []);

    const signOut = useCallback(async () => {
        const auth = authRef.current;
        if (auth) await auth.signOut();
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
