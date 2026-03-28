/**
 * Kith Foundry API Gateway Worker
 *
 * Sits in front of the origin (cloudflared tunnel / Fly backend) and:
 * - Handles CORS preflight at the edge — never hits origin for OPTIONS
 * - Injects security headers on every response
 * - Provides a /healthz edge check
 *
 * Deploy:  npx wrangler deploy -c workers/wrangler-gateway.toml
 * Bind to: sandbox-api.forgeoperator.com  (Cloudflare zone DNS → Workers route)
 */

const ALLOWED_ORIGINS = [
  'https://forgeoperator.com',
  'https://www.forgeoperator.com',
  'http://localhost:5173',
  'http://localhost:4173',
];

const SECURITY_HEADERS = {
  'X-Content-Type-Options': 'nosniff',                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          
  'X-Frame-Options': 'DENY',
  'X-XSS-Protection': '1; mode=block',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
};

function corsHeaders(origin) {
  if (!origin || !ALLOWED_ORIGINS.includes(origin)) return {};
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Max-Age': '86400',
  };
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = request.headers.get('Origin');

    // CORS preflight — handle at edge, never hits origin
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          ...corsHeaders(origin),
          ...SECURITY_HEADERS,
        },
      });
    }

    // Edge health check
    if (url.pathname === '/healthz') {
      return new Response(
        JSON.stringify({ status: 'ok', worker: 'kith-api-gateway', ts: Date.now() }),
        { headers: { 'Content-Type': 'application/json', ...SECURITY_HEADERS } },
      );
    }

    // Forward to origin
    const response = await fetch(request);
    const newResponse = new Response(response.body, response);

    // Inject security + CORS headers on response
    for (const [k, v] of Object.entries(SECURITY_HEADERS)) {
      newResponse.headers.set(k, v);
    }
    for (const [k, v] of Object.entries(corsHeaders(origin))) {
      newResponse.headers.set(k, v);
    }

    return newResponse;
  },
};
