/**
 * Nhost client and auth adapter when VITE_USE_NHOST=1.
 * Uses @nhost/nhost-js v4.
 */
import { createClient } from "@nhost/nhost-js";
import type { AuthClient, AuthSession } from "./auth";

const nhostSubdomain = import.meta.env.VITE_NHOST_SUBDOMAIN || "";
const nhostRegion = import.meta.env.VITE_NHOST_REGION || "";
export const nhost = nhostSubdomain
    ? createClient({ subdomain: nhostSubdomain, region: nhostRegion })
    : null;

// Minimal session shape we care about internally
interface V4Session {
    accessToken: string;
    refreshToken: string;
    refreshTokenId: string;
    user?: { id: string; email?: string };
}

function getV4Session(): V4Session | null {
    return (nhost?.getUserSession() ?? null) as V4Session | null;
}

function toAuthSession(session: V4Session | null | undefined): AuthSession | null {
    if (!session?.user) return null;
    return {
        access_token: session.accessToken,
        user: { id: session.user.id, email: session.user.email },
    };
}

// v4 has no built-in onAuthStateChanged — use a simple event emitter.
const _listeners = new Set<(session: AuthSession | null) => void>();

function _broadcast() {
    if (!nhost) return;
    const s = toAuthSession(getV4Session());
    _listeners.forEach((cb) => { try { cb(s); } catch { /* ignore */ } });
}

// Cross-tab / cross-window sync
if (typeof window !== "undefined") {
    window.addEventListener("storage", _broadcast);
}

// Deduplicate concurrent refresh attempts — only one in-flight at a time.
let _refreshPromise: Promise<unknown> | null = null;
let _refreshFailedAt = 0;
const REFRESH_COOLDOWN_MS = 5_000;

function _debouncedRefresh(): Promise<unknown> {
    if (_refreshFailedAt && Date.now() - _refreshFailedAt < REFRESH_COOLDOWN_MS) {
        return Promise.reject(new Error("refresh cooldown"));
    }
    if (_refreshPromise) return _refreshPromise;
    _refreshPromise = nhost!
        .refreshSession(0)
        .then((s) => { _refreshFailedAt = 0; return s; })
        .catch((err: unknown) => { _refreshFailedAt = Date.now(); throw err; })
        .finally(() => { _refreshPromise = null; });
    return _refreshPromise;
}

export const nhostAuth: AuthClient = nhost
    ? {
          async getSession() {
              return toAuthSession(getV4Session());
          },
          onAuthStateChange(cb: (session: AuthSession | null) => void) {
              _listeners.add(cb);
              // Fire immediately so AuthContext resolves initial auth state on startup.
              cb(toAuthSession(getV4Session()));
              return () => { _listeners.delete(cb); };
          },
          async signUp(email: string, password: string) {
              try {
                  await nhost.auth.signUpEmailPassword({ email, password });
                  _broadcast();
                  return { error: null };
              } catch (err: unknown) {
                  return { error: err instanceof Error ? err.message : "Sign up failed" };
              }
          },
          async signIn(email: string, password: string) {
              try {
                  await nhost.auth.signInEmailPassword({ email, password });
                  _broadcast();
                  return { error: null };
              } catch (err: unknown) {
                  return { error: err instanceof Error ? err.message : "Sign in failed" };
              }
          },
          async signOut() {
              const session = getV4Session();
              try {
                  await nhost.auth.signOut({ refreshToken: session?.refreshToken });
              } catch { /* ignore network errors on sign-out */ }
              nhost.clearSession();
              _broadcast();
          },
          async getAccessToken() {
              const session = getV4Session();
              if (!session) return null;

              // Only proactively refresh if the access token expires within 60 seconds.
              const readExpiry = (token: string | null | undefined): number => {
                  if (!token) return 0;
                  try {
                      const payload = JSON.parse(atob(token.split(".")[1]));
                      return (payload.exp ?? 0) * 1000;
                  } catch {
                      return 0;
                  }
              };

              const expiresAt = readExpiry(session.accessToken);
              const needsRefresh = !session.accessToken || expiresAt - Date.now() < 60_000;
              if (!needsRefresh) return session.accessToken;

              try {
                  await _debouncedRefresh();
              } catch {
                  /* ignore — return whatever we have */
              }

              const refreshed = getV4Session();
              if (!refreshed?.accessToken) return null;
              const refreshedExpiry = readExpiry(refreshed.accessToken);
              if (refreshedExpiry <= Date.now()) return null;
              return refreshed.accessToken;
          },
      }
    : (null as unknown as AuthClient);
