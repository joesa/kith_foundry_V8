/**
 * Nhost client and auth adapter when VITE_USE_NHOST=1.
 * Install: npm install @nhost/nhost-js
 */
import { NhostClient } from "@nhost/nhost-js";
import type { AuthClient, AuthSession } from "./auth";

const nhostSubdomain = import.meta.env.VITE_NHOST_SUBDOMAIN || "";
const nhostRegion = import.meta.env.VITE_NHOST_REGION || "";
export const nhost = nhostSubdomain ? new NhostClient({ subdomain: nhostSubdomain, region: nhostRegion }) : null;

function toAuthSession(session: { user: { id: string; email?: string }; accessToken: string } | null): AuthSession | null {
    if (!session?.user) return null;
    return {
        access_token: session.accessToken,
        user: { id: session.user.id, email: session.user.email },
    };
}

// Deduplicate concurrent refresh attempts — only one in-flight at a time.
let _refreshPromise: Promise<void> | null = null;
let _refreshFailedAt = 0;
const REFRESH_COOLDOWN_MS = 5_000;

function _debouncedRefresh(): Promise<void> {
    // If a refresh just failed, don't retry until cooldown expires.
    if (_refreshFailedAt && Date.now() - _refreshFailedAt < REFRESH_COOLDOWN_MS) {
        return Promise.reject(new Error("refresh cooldown"));
    }
    if (_refreshPromise) return _refreshPromise;
    _refreshPromise = nhost!.auth
        .refreshSession()
        .then(() => { _refreshFailedAt = 0; })
        .catch((err: unknown) => { _refreshFailedAt = Date.now(); throw err; })
        .finally(() => { _refreshPromise = null; });
    return _refreshPromise;
}

export const nhostAuth: AuthClient = nhost
    ? {
          async getSession() {
              try {
                  // getSession() is synchronous and returns NhostSession | null (not { data: { session } })
                  const session = nhost.auth.getSession();
                  return toAuthSession(session);
              } catch {
                  return null;
              }
          },
          onAuthStateChange(cb: (session: AuthSession | null) => void) {
              let unsubscribe: (() => void) | null = null;
              let destroyed = false;
              const fn = nhost.auth.onAuthStateChanged;
              if (typeof fn !== "function") {
                  console.warn("nhost.auth.onAuthStateChanged is not a function");
                  return () => {};
              }
              const result = fn.call(nhost.auth, (_event: string, session: unknown) => {
                  cb(toAuthSession(session as Parameters<typeof toAuthSession>[0]));
              });
              // nhost-js v2 returns Promise<() => void>, v1 returns () => void
              if (result && typeof (result as { then?: unknown }).then === "function") {
                  (result as unknown as Promise<() => void>).then((unsub) => {
                      if (destroyed) unsub();
                      else unsubscribe = unsub;
                  });
              } else {
                  unsubscribe = result as (() => void);
              }
              return () => {
                  destroyed = true;
                  unsubscribe?.();
              };
          },
          async signUp(email: string, password: string) {
              const { error } = await nhost.auth.signUp({ email, password });
              return { error: error?.message ?? null };
          },
          async signIn(email: string, password: string) {
              const { error } = await nhost.auth.signIn({ email, password });
              return { error: error?.message ?? null };
          },
          async signOut() {
              await nhost.auth.signOut();
          },
          async getAccessToken() {
              const session = nhost.auth.getSession();
              if (!session) return null;

              // Only proactively refresh if the access token expires within 60 seconds.
              // Avoids hammering /v1/token on every API call.
              const readExpiry = (token: string | null | undefined): number => {
                  if (!token) return 0;
                  try {
                      const payload = JSON.parse(atob(token.split(".")[1]));
                      return (payload.exp ?? 0) * 1000;
                  } catch {
                      return 0;
                  }
              };

              try {
                  const token = nhost.auth.getAccessToken();
                  const expiresAt = readExpiry(token);
                  const needsRefresh = !token || expiresAt - Date.now() < 60_000;
                  if (!needsRefresh) return token;
                  // Token missing or near expiry — single deduplicated refresh
                  await _debouncedRefresh();
              } catch {
                  /* ignore — we'll validate the final token below */
              }
              const refreshed = nhost.auth.getAccessToken() ?? null;
              const refreshedExpiry = readExpiry(refreshed);
              if (!refreshed || refreshedExpiry <= Date.now()) return null;
              return refreshed;
          },
      }
    : (null as unknown as AuthClient);
