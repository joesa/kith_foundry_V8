/**
 * Kith Foundry Unicorn Worker — Edge Intelligence Layer
 *
 * Lightweight AI/data tasks performed at the Cloudflare edge:
 * 1. Request classifier — adds X-Kith-Route header to hint origin routing
 * 2. Token estimator    — estimates LLM token budget before hitting origin
 * 3. Cache orchestrator — serves cached AI responses from KV (optional)
 * 4. Telemetry beacon   — collects client-side perf metrics, stores in KV
 *
 * Deploy:  npx wrangler deploy -c workers/wrangler-unicorn.toml
 */

// ── Request Classifier ────────────────────────────────────────────────────────

function classifyRequest(pathname, method) {
  if (pathname.startsWith('/api/projects/') && pathname.includes('/chat'))       return 'agent-pipeline';
  if (pathname.startsWith('/api/projects/') && pathname.includes('/orchestrate'))return 'orchestration';
  if (pathname.startsWith('/api/projects/') && pathname.includes('/design'))     return 'design-agent';
  if (pathname.startsWith('/api/projects/') && pathname.includes('/csuite'))     return 'csuite-agent';
  if (pathname.startsWith('/api/projects/') && pathname.includes('/sandbox'))    return 'sandbox';
  if (pathname.startsWith('/api/platform/'))                                     return 'platform';
  if (pathname.startsWith('/api/turnstile/'))                                    return 'auth';
  if (pathname.startsWith('/api/cloudflare/'))                                   return 'infra';
  return 'general';
}

// ── Token Estimator ───────────────────────────────────────────────────────────

function estimateTokens(text) {
  if (!text) return 0;
  return Math.ceil(text.length / 4); // ~4 chars/token for English
}

// ── Telemetry Beacon ──────────────────────────────────────────────────────────

async function handleTelemetryBeacon(request, env) {
  try {
    const body = await request.json();
    const payload = {
      ts: Date.now(),
      metric: body.metric || 'unknown',
      value: body.value || 0,
      page: body.page || '/',
      ua: request.headers.get('User-Agent') || '',
      geo: request.cf?.country || 'unknown',
      colo: request.cf?.colo || 'unknown',
    };

    if (env.TELEMETRY_KV) {
      const key = `tel:${payload.metric}:${payload.ts}:${Math.random().toString(36).slice(2, 8)}`;
      await env.TELEMETRY_KV.put(key, JSON.stringify(payload), { expirationTtl: 86400 * 7 });
    }

    return new Response(JSON.stringify({ ok: true }), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch {
    return new Response(JSON.stringify({ ok: false }), { status: 400 });
  }
}

// ── AI Response Cache ─────────────────────────────────────────────────────────

async function getCachedResponse(env, cacheKey) {
  if (!env.AI_CACHE_KV) return null;
  return env.AI_CACHE_KV.get(cacheKey, { type: 'json' });
}

async function setCachedResponse(env, cacheKey, data, ttlSeconds = 3600) {
  if (!env.AI_CACHE_KV) return;
  await env.AI_CACHE_KV.put(cacheKey, JSON.stringify(data), { expirationTtl: ttlSeconds });
}

function buildCacheKey(pathname) {
  if (!pathname.includes('/daily-idea') && !pathname.includes('/platform/')) return null;
  const hash = Array.from(new TextEncoder().encode(pathname))
    .reduce((h, b) => ((h << 5) - h + b) | 0, 0)
    .toString(36);
  return `cache:${pathname}:${hash}`;
}

// ── Main Handler ──────────────────────────────────────────────────────────────

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const { pathname } = url;

    // Telemetry beacon — fully handled at edge
    if (pathname === '/api/telemetry/beacon' && request.method === 'POST') {
      return handleTelemetryBeacon(request, env);
    }

    // Worker health check
    if (pathname === '/unicorn/health') {
      return new Response(JSON.stringify({
        worker: 'kith-unicorn',
        status: 'ok',
        capabilities: ['classify', 'token-estimate', 'cache', 'telemetry'],
        ts: Date.now(),
      }), { headers: { 'Content-Type': 'application/json' } });
    }

    // Classify request + enrich headers
    const category = classifyRequest(pathname, request.method);
    const newHeaders = new Headers(request.headers);
    newHeaders.set('X-Kith-Route', category);

    // Token estimation for chat requests
    if (category === 'agent-pipeline' && request.method === 'POST') {
      try {
        const cloned = request.clone();
        const body = await cloned.json();
        const promptTokens = estimateTokens(body.message || body.prompt || '');
        newHeaders.set('X-Kith-Est-Tokens', String(promptTokens));
      } catch {
        // body parse failed — skip
      }
    }

    // Edge cache for GET-only cacheable paths
    const cacheKey = request.method === 'GET' ? buildCacheKey(pathname) : null;
    if (cacheKey) {
      const cached = await getCachedResponse(env, cacheKey);
      if (cached) {
        return new Response(JSON.stringify(cached), {
          headers: {
            'Content-Type': 'application/json',
            'X-Kith-Cache': 'HIT',
            'X-Kith-Route': category,
          },
        });
      }
    }

    // Forward to origin with enriched headers
    const modifiedRequest = new Request(request.url, {
      method: request.method,
      headers: newHeaders,
      body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : null,
    });

    const response = await fetch(modifiedRequest);

    // Cache successful GET responses
    if (cacheKey && response.ok) {
      try {
        const data = await response.clone().json();
        ctx.waitUntil(setCachedResponse(env, cacheKey, data));
      } catch {
        // non-JSON response — skip caching
      }
    }

    return response;
  },
};
