/** True when Vite env lists a Nhost Cloud subdomain + region (client-safe). */
export function isNhostConfigured(): boolean {
  const sub = import.meta.env.VITE_NHOST_SUBDOMAIN;
  const region = import.meta.env.VITE_NHOST_REGION;
  return Boolean(
    sub &&
      region &&
      String(sub).trim().length > 0 &&
      String(region).trim().length > 0
  );
}
