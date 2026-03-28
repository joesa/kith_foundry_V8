/**
 * Nhost client and auth adapter when VITE_USE_NHOST=1.
 * Uses @nhost/nhost-js v4 createClient (with session middleware).
 */
import { createClient } from "@nhost/nhost-js";
import type { AuthClient, AuthSession } from "./auth";

const nhostSubdomain = import.meta.env.VITE_NHOST_SUBDOMAIN || "";
const nhostRegion = import.meta.env.VITE_NHOST_REGION || "";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const nhost: any = nhostSubdomain
    ? createClient({ subdomain: nhostSubdomain, region: nhostRegion })
    : null;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toAuthSession(session: any): AuthSession | null {
    if (!session?.accessToken || !session?.user?.id) return null;
    return {
        access_token: session.accessToken,
        user: { id: session.user.id, email: session.user.email },
    };
}

export const nhostAuth: AuthClient = nhost
    ? {
          async getSession() {
              // Try refresh first (returns fresh session or null)
              try {
                  const refreshed = await nhost.refreshSession(60);
                  if (refreshed) return toAuthSession(refreshed);
              } catch { /* ignore refresh errors */ }
              // Fall back to stored session
              return toAuthSession(nhost.getUserSession());
          },
          onAuthStateChange(cb: (session: AuthSession | null) => void) {
              // Fire with current stored session immediately
              cb(toAuthSession(nhost.getUserSession()));

              // Use SDK's built-in subscriber for session changes
              const unsub = nhost.sessionStorage.onChange(
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  (session: any) => cb(toAuthSession(session))
              );

              // Also listen for cross-tab localStorage changes
              const onStorage = (e: StorageEvent) => {
                  if (e.key === "nhostSession") {
                      cb(toAuthSession(nhost.getUserSession()));
                  }
              };
              window.addEventListener("storage", onStorage);

              return () => {
                  unsub();
                  window.removeEventListener("storage", onStorage);
              };
          },
          async signUp(email: string, password: string) {
              try {
                  await nhost.auth.signUpEmailPassword({ email, password });
                  console.log("[Nhost] Sign up successful");
                  return { error: null };
              } catch (err: unknown) {
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  const body = (err as any)?.body;
                  const msg = body?.message || (err instanceof Error ? err.message : String(err));
                  console.error("[Nhost] Sign up error:", msg);
                  if (msg.includes("already exists") || msg.includes("already registered")) {
                      return { error: "This email is already registered. Try signing in instead." };
                  }
                  return { error: msg };
              }
          },
          async signIn(email: string, password: string) {
              try {
                  await nhost.auth.signInEmailPassword({ email, password });
                  console.log("[Nhost] Sign in successful");
                  return { error: null };
              } catch (err: unknown) {
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  const body = (err as any)?.body;
                  const msg = body?.message || (err instanceof Error ? err.message : String(err));
                  console.error("[Nhost] Sign in error:", msg);
                  if (msg.includes("Incorrect") || msg.includes("invalid") || msg.includes("401")) {
                      return { error: "Invalid email or password. Don't have an account? Sign up instead." };
                  }
                  return { error: msg };
              }
          },
          async signOut() {
              try {
                  const session = nhost.getUserSession();
                  if (session?.refreshTokenId) {
                      await nhost.auth.signOut({ refreshToken: session.refreshTokenId });
                  }
                  nhost.clearSession();
              } catch { /* ignore network errors on sign-out */ }
          },
          async getAccessToken() {
              // Attempt refresh if needed, then return token
              try {
                  const refreshed = await nhost.refreshSession(60);
                  if (refreshed?.accessToken) return refreshed.accessToken;
              } catch { /* ignore */ }
              return nhost.getUserSession()?.accessToken ?? null;
          },
      }
    : (null as unknown as AuthClient);
