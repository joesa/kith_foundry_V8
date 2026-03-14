/**
 * Nhost client and auth adapter when VITE_USE_NHOST=1.
 * Uses @nhost/nhost-js v4.
 */
import { NhostClient } from "@nhost/nhost-js";
import type { AuthClient, AuthSession } from "./auth";

const nhostSubdomain = import.meta.env.VITE_NHOST_SUBDOMAIN || "";
const nhostRegion = import.meta.env.VITE_NHOST_REGION || "";
export const nhost = nhostSubdomain
    ? new NhostClient({ subdomain: nhostSubdomain, region: nhostRegion })
    : null;

// Nhost v4 session shape (HasuraAuthClient)
interface V4Session {
    accessToken: string;
    accessTokenExpiresIn?: number;
    refreshToken: string | null;
    user?: { id: string; email?: string };
}

function toAuthSession(session: V4Session | null | undefined): AuthSession | null {
    if (!session?.user?.id || !session?.accessToken) return null;
    return {
        access_token: session.accessToken,
        user: { id: session.user.id, email: session.user.email },
    };
}

export const nhostAuth: AuthClient = nhost
    ? {
          async getSession() {
              return toAuthSession(nhost.auth.getSession() as V4Session);
          },
          onAuthStateChange(cb: (session: AuthSession | null) => void) {
              // Subscribe to future SIGNED_IN / SIGNED_OUT transitions via v4
              const unsub = nhost.auth.onAuthStateChanged((_event: string, session: unknown) => {
                  cb(toAuthSession(session as V4Session));
              });
              // isAuthenticatedAsync resolves once the machine finishes its startup
              // session-restore (reads localStorage, possibly refreshes token).
              // This fires the initial-state callback reliably even if the machine
              // already completed before this listener was registered.
              nhost.auth
                  .isAuthenticatedAsync()
                  .then((authed) => {
                      cb(authed ? toAuthSession(nhost.auth.getSession() as V4Session) : null);
                  })
                  .catch(() => cb(null));
              return typeof unsub === "function" ? (unsub as () => void) : () => {};
          },
          async signUp(email: string, password: string) {
              try {
                  const result = await nhost.auth.signUp({ email, password });
                  if (result.error) return { error: result.error.message };
                  return { error: null };
              } catch (err: unknown) {
                  return { error: err instanceof Error ? err.message : "Sign up failed" };
              }
          },
          async signIn(email: string, password: string) {
              try {
                  const result = await nhost.auth.signIn({ email, password });
                  if (result.error) return { error: result.error.message };
                  return { error: null };
              } catch (err: unknown) {
                  return { error: err instanceof Error ? err.message : "Sign in failed" };
              }
          },
          async signOut() {
              try {
                  await nhost.auth.signOut();
              } catch { /* ignore network errors on sign-out */ }
          },
          async getAccessToken() {
              // nhost.auth.getAccessToken() returns the current access token
              // and auto-refreshes if needed.
              return nhost.auth.getAccessToken() ?? null;
          },
      }
    : (null as unknown as AuthClient);
