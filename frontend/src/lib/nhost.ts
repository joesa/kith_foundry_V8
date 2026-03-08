/**
 * Nhost client and auth adapter when VITE_USE_NHOST=1.
 * Install: npm install @nhost/nhost-js
 */
import { NhostClient } from "@nhost/nhost-js";
import type { AuthClient, AuthSession, AuthUser } from "./auth";

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
              if (result && typeof (result as Promise<unknown>).then === "function") {
                  (result as Promise<() => void>).then((unsub) => {
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
          async refreshSession() {
              const res = await nhost.auth.refreshSession();
              const session = (res as { session?: unknown; data?: { session?: unknown } })?.session
                  ?? (res as { data?: { session?: unknown } })?.data?.session
                  ?? null;
              return toAuthSession(session as Parameters<typeof toAuthSession>[0]);
          },
          async getAccessToken() {
              const session = nhost.auth.getSession();
              if (!session) return null;

              // Only proactively refresh if the access token expires within 60 seconds.
              // Avoids hammering /v1/token on every API call.
              try {
                  const token = nhost.auth.getAccessToken();
                  if (token) {
                      // Decode exp claim from JWT payload (no verification needed here)
                      const payload = JSON.parse(atob(token.split(".")[1]));
                      const expiresAt = (payload.exp ?? 0) * 1000;
                      const needsRefresh = expiresAt - Date.now() < 60_000;
                      if (!needsRefresh) return token;
                  }
                  // Token missing or near expiry — attempt refresh
                  await nhost.auth.refreshSession();
              } catch {
                  /* ignore — use current token, 401 will trigger signOut via useApiFetch */
              }
              return nhost.auth.getAccessToken() ?? null;
          },
      }
    : (null as unknown as AuthClient);
