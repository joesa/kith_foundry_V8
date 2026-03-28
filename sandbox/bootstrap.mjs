/**
 * Sandbox bootstrap — runs inside the Fly machine on startup.
 *
 * Env vars injected by the control plane:
 *   PROJECT_ID         - Forge project ID (e.g. "prj_abc123")
 *   CONTROL_PLANE_URL  - Base URL of the API  (e.g. "https://api.forgeoperator.com")
 *   BRIDGE_SECRET      - Optional auth token for the workspace bundle endpoint
 *   PORT               - Port Vite should listen on (default 3000)
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { execSync, spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const PROJECT_ID = process.env.PROJECT_ID;
const CONTROL_PLANE_URL = (process.env.CONTROL_PLANE_URL || 'https://api.forgeoperator.com').replace(/\/$/, '');
const BRIDGE_SECRET = process.env.BRIDGE_SECRET || '';
const PORT = process.env.PORT || '3000';
const WORKSPACE = '/workspace';

if (!PROJECT_ID) {
  console.error('[bootstrap] ERROR: PROJECT_ID env var is required');
  process.exit(1);
}

console.log(`[bootstrap] Starting sandbox for project ${PROJECT_ID}`);
console.log(`[bootstrap] Control plane: ${CONTROL_PLANE_URL}`);

// ── 1. Fetch the workspace bundle from the control plane ──────────────────────

const bundleUrl = `${CONTROL_PLANE_URL}/api/projects/${PROJECT_ID}/code/workspace`;
console.log(`[bootstrap] Fetching workspace from ${bundleUrl}`);

const headers = { 'Content-Type': 'application/json' };
if (BRIDGE_SECRET) headers['X-Bridge-Secret'] = BRIDGE_SECRET;

let files = {};
try {
  const resp = await fetch(bundleUrl, { headers });
  if (!resp.ok) {
    const body = await resp.text();
    console.error(`[bootstrap] Failed to fetch workspace (${resp.status}): ${body}`);
    process.exit(1);
  }
  const data = await resp.json();
  files = data.files || {};
  console.log(`[bootstrap] Received ${Object.keys(files).length} files`);
} catch (err) {
  console.error(`[bootstrap] Network error fetching workspace: ${err.message}`);
  process.exit(1);
}

// ── 2. Write files to /workspace ──────────────────────────────────────────────

mkdirSync(WORKSPACE, { recursive: true });

for (const [relPath, content] of Object.entries(files)) {
  const fullPath = join(WORKSPACE, relPath);
  mkdirSync(dirname(fullPath), { recursive: true });
  writeFileSync(fullPath, content, 'utf8');
}
console.log('[bootstrap] Files written to', WORKSPACE);

// ── 3. Ensure package.json has required deps ──────────────────────────────────

const pkgPath = join(WORKSPACE, 'package.json');
const pkg = JSON.parse(readFileSync(pkgPath, 'utf8'));

pkg.dependencies = {
  react: '^18.3.1',
  'react-dom': '^18.3.1',
  ...(pkg.dependencies || {}),
};
// Remove build tools from dependencies — they must live in devDependencies
// so the bootstrap-controlled versions always win.
delete pkg.dependencies['vite'];
delete pkg.dependencies['@vitejs/plugin-react'];
delete pkg.dependencies['typescript'];

pkg.devDependencies = {
  ...(pkg.devDependencies || {}),
  '@types/react': '^18.3.0',
  '@types/react-dom': '^18.3.0',
  '@vitejs/plugin-react': '^4.3.0',
  typescript: '^5.5.0',
  vite: '~5.4.19',
};

writeFileSync(pkgPath, JSON.stringify(pkg, null, 2), 'utf8');

// ── 3b. Ensure tsconfig.json exists for TypeScript diagnostics ────────────────
// This gives us VS Code "Problems tab" level error detection via tsc --noEmit.

const tsconfigPath = join(WORKSPACE, 'tsconfig.json');
const tsconfigContent = {
  compilerOptions: {
    target: 'ES2020',
    useDefineForClassFields: true,
    lib: ['ES2020', 'DOM', 'DOM.Iterable'],
    module: 'ESNext',
    skipLibCheck: true,
    moduleResolution: 'bundler',
    allowImportingTsExtensions: true,
    isolatedModules: true,
    moduleDetection: 'force',
    noEmit: true,
    jsx: 'react-jsx',
    strict: true,
    noUnusedLocals: false,
    noUnusedParameters: false,
    noFallthroughCasesInSwitch: true,
    allowJs: true,
    esModuleInterop: true,
    resolveJsonModule: true,
    forceConsistentCasingInFileNames: true,
    baseUrl: '.',
    paths: { '@/*': ['src/*'] },
  },
  include: ['src'],
};
// Always write tsconfig to ensure @/ alias is present even if workspace ships one
writeFileSync(tsconfigPath, JSON.stringify(tsconfigContent, null, 2), 'utf8');
console.log('[bootstrap] Wrote tsconfig.json with @/ path alias');

// ── 4. Write vite.config.js with sandbox-specific settings ───────────────────
//
// HMR is disabled: the Fly.io proxy doesn't route WebSocket upgrades to the
// container, so Vite's HMR websocket always fails.  The sandbox is a live
// preview — hot reload isn't needed; the user reprovisions to see changes.
//
// IMPORTANT: We write vite.config.js (not .ts) because Vite resolves .js first.
// Generated workspace bundles may include their own vite.config.ts — writing
// .js ensures our sandbox settings (allowedHosts, host, hmr) always win.

// Remove any competing vite config files from the generated workspace
for (const variant of ['vite.config.ts', 'vite.config.mts', 'vite.config.mjs', 'vite.config.cjs', 'vite.config.cts']) {
  const p = join(WORKSPACE, variant);
  if (existsSync(p)) {
    writeFileSync(p, '', 'utf8');   // truncate instead of unlink to avoid import issues
    console.log(`[bootstrap] Cleared competing config: ${variant}`);
  }
}

const viteConfigPath = join(WORKSPACE, 'vite.config.js');
writeFileSync(
  viteConfigPath,
  [
    `import { defineConfig } from 'vite'`,
    `import react from '@vitejs/plugin-react'`,
    `import path from 'path'`,
    `import { fileURLToPath } from 'url'`,
    ``,
    `const __dirname = path.dirname(fileURLToPath(import.meta.url))`,
    ``,
    `export default defineConfig({`,
    `  plugins: [react()],`,
    `  resolve: {`,
    `    alias: {`,
    `      '@': path.resolve(__dirname, 'src'),`,
    `    },`,
    `  },`,
    `  server: {`,
    `    host: '0.0.0.0',`,
    `    port: ${PORT},`,
    `    allowedHosts: true,`,
    `    hmr: false,`,
    `  },`,
    `  preview: {`,
    `    allowedHosts: true,`,
    `  },`,
    `})`,
    ``,
  ].join('\n'),
  'utf8'
);
console.log('[bootstrap] Wrote vite.config.js (HMR disabled, @/ alias enabled)');


// ── 5. Write public/favicon.svg so browsers don't 404 on /favicon.ico ───────

const publicDir = join(WORKSPACE, 'public');
mkdirSync(publicDir, { recursive: true });
writeFileSync(
  join(publicDir, 'favicon.svg'),
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32"><defs><filter id="g" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur in="SourceGraphic" stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><rect width="32" height="32" rx="7" fill="#0c111d"/><path d="M20 2 L10 16 L15 16 L12 30 L22 16 L17 16 Z" fill="#e65c3b" filter="url(#g)"/></svg>`,
  'utf8'
);
console.log('[bootstrap] Wrote public/favicon.svg');

// ── 6. Ensure index.html exists ───────────────────────────────────────────────

const indexPath = join(WORKSPACE, 'index.html');
if (!existsSync(indexPath)) {
  writeFileSync(
    indexPath,
    `<!doctype html>\n<html lang="en">\n  <head>\n    <meta charset="UTF-8" />\n    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />\n    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n    <title>${pkg.name || 'App'}</title>\n  </head>\n  <body>\n    <div id="root"></div>\n    <script type="module" src="/src/main.tsx"></script>\n  </body>\n</html>\n`,
    'utf8'
  );
  console.log('[bootstrap] Wrote default index.html');
}

// Always inject the live-sync reload script into index.html so the browser
// detects workspace version changes and refreshes automatically.
{
  let html = readFileSync(indexPath, 'utf8');
  const reloadScript = `<script>
(function(){
  var _v=null;
  setInterval(async function(){
    try{
      var r=await fetch('/__version.json?_='+Date.now());
      if(!r.ok)return;
      var d=await r.json();
      if(_v===null){_v=d.v;return;}
      if(d.v!==_v){location.reload();}
    }catch(e){}
  },4000);
})();
</script>`;
  if (!html.includes('/__version.json')) {
    html = html.replace('</body>', reloadScript + '\n</body>');
  }

  // Inject browser console error capture script — reports runtime errors
  // back to the control plane so the build pipeline can detect and repair them.
  const consoleErrorScript = `<script>
(function(){
  var _cp='${CONTROL_PLANE_URL}';
  var _pid='${PROJECT_ID}';
  var _bs='${BRIDGE_SECRET}';
  var _q=[];
  var _flush=null;
  function _send(){
    if(!_q.length)return;
    var batch=_q.splice(0,20);
    var h={'Content-Type':'application/json'};
    if(_bs)h['X-Bridge-Secret']=_bs;
    try{
      fetch(_cp+'/api/projects/'+_pid+'/sandbox/console-errors',{
        method:'POST',headers:h,
        body:JSON.stringify({errors:batch})
      }).catch(function(){});
    }catch(e){}
  }
  window.addEventListener('error',function(ev){
    _q.push({
      message:ev.message||'Unknown error',
      file:ev.filename||'unknown',
      line:ev.lineno||0,
      col:ev.colno||0,
      code:'RUNTIME-ERROR',
      stack:(ev.error&&ev.error.stack)?ev.error.stack.slice(0,500):'',
      timestamp:new Date().toISOString()
    });
    clearTimeout(_flush);
    _flush=setTimeout(_send,2000);
  });
  window.addEventListener('unhandledrejection',function(ev){
    var msg=ev.reason?(ev.reason.message||String(ev.reason)):'Unhandled promise rejection';
    var stack=ev.reason&&ev.reason.stack?ev.reason.stack.slice(0,500):'';
    _q.push({
      message:msg,
      file:'unknown',line:0,col:0,
      code:'UNHANDLED-REJECTION',
      stack:stack,
      timestamp:new Date().toISOString()
    });
    clearTimeout(_flush);
    _flush=setTimeout(_send,2000);
  });
  var _origError=console.error;
  console.error=function(){
    var args=Array.prototype.slice.call(arguments);
    var msg=args.map(function(a){try{return typeof a==='object'?JSON.stringify(a):String(a)}catch(e){return String(a)}}).join(' ');
    if(msg.length>10){
      _q.push({
        message:msg.slice(0,500),
        file:'console',line:0,col:0,
        code:'CONSOLE-ERROR',
        stack:'',
        timestamp:new Date().toISOString()
      });
      clearTimeout(_flush);
      _flush=setTimeout(_send,2000);
    }
    return _origError.apply(console,arguments);
  };
})();
</script>`;
  if (!html.includes('console-errors')) {
    html = html.replace('</head>', consoleErrorScript + '\n</head>');
  }

  writeFileSync(indexPath, html, 'utf8');
  console.log('[bootstrap] Injected live-sync reload + console error capture scripts into index.html');
}

// Write initial version file — browser polls this to detect workspace changes.
writeFileSync(join(publicDir, '__version.json'), JSON.stringify({ v: 1 }), 'utf8');

// Signal the control plane that the full workspace bundle has been written.
await reportBuildStatus('workspace_synced');

// ── 7. npm install + vite dev + live workspace sync loop ──────────────────────

const buildStatusUrl = `${CONTROL_PLANE_URL}/api/projects/${PROJECT_ID}/sandbox/build-status`;
const statusHeaders = { 'Content-Type': 'application/json' };
if (BRIDGE_SECRET) statusHeaders['X-Bridge-Secret'] = BRIDGE_SECRET;

async function reportBuildStatus(status, error = null, structuredErrors = []) {
  try {
    await fetch(buildStatusUrl, {
      method: 'POST',
      headers: statusHeaders,
      body: JSON.stringify({
        status,
        error: error ? String(error).slice(0, 2000) : null,
        errors: structuredErrors.slice(0, 30),
      }),
    });
  } catch (e) {
    console.warn('[bootstrap] Could not report build status:', e.message);
  }
}

/**
 * Parse Vite/esbuild/TypeScript error output into structured error objects.
 */
function parseViteBuildErrors(stderr) {
  const errors = [];
  // Pattern: file:line:col: ERROR: message
  const vitePattern = /([a-zA-Z0-9_.\/-]+\.(?:ts|tsx|js|jsx)):([0-9]+):([0-9]+):\s*(?:ERROR|error):\s*(.+)/g;
  let m;
  while ((m = vitePattern.exec(stderr)) !== null) {
    errors.push({ file: m[1], line: parseInt(m[2]), col: parseInt(m[3]), code: 'VITE-BUILD', message: m[4].trim().slice(0, 300) });
  }
  // Pattern: [plugin:xxx] message \n file:line:col
  const pluginPattern = /\[plugin:[^\]]+\]\s*(.+?)\n\s*([a-zA-Z0-9_.\/-]+\.(?:ts|tsx|js|jsx)):([0-9]+):([0-9]+)/g;
  while ((m = pluginPattern.exec(stderr)) !== null) {
    errors.push({ file: m[2], line: parseInt(m[3]), col: parseInt(m[4]), code: 'VITE-PLUGIN', message: m[1].trim().slice(0, 300) });
  }
  // Pattern: TS error codes
  const tsPattern = /(TS\d+):\s*(.+?)(?:\n|$)/g;
  while ((m = tsPattern.exec(stderr)) !== null) {
    errors.push({ file: 'unknown', line: 0, col: 0, code: m[1], message: m[2].trim().slice(0, 300) });
  }
  // Pattern: Module not found / Cannot find module
  const modulePattern = /(?:Module not found|Cannot find module)[:\s]+['"]?([^'"\n]+)/g;
  while ((m = modulePattern.exec(stderr)) !== null) {
    errors.push({ file: 'unknown', line: 0, col: 0, code: 'MODULE-NOT-FOUND', message: `Cannot find module '${m[1].trim()}'` });
  }
  return errors;
}

/**
 * Parse tsc --noEmit output into structured diagnostics.
 * TSC format: src/App.tsx(14,5): error TS2304: Cannot find name 'foo'.
 *             src/App.tsx:14:5 - error TS2304: Cannot find name 'foo'.
 */
function parseTscDiagnostics(output) {
  const errors = [];
  // Pattern 1: file(line,col): error TSxxxx: message
  const p1 = /([a-zA-Z0-9_.\/-]+\.(?:ts|tsx|js|jsx))\(([0-9]+),([0-9]+)\):\s*(error|warning)\s+(TS\d+):\s*(.+)/g;
  let m;
  while ((m = p1.exec(output)) !== null) {
    errors.push({
      file: m[1], line: parseInt(m[2]), col: parseInt(m[3]),
      code: m[5], severity: m[4] === 'error' ? 'error' : 'warning',
      message: m[6].trim().slice(0, 400),
    });
  }
  // Pattern 2: file:line:col - error TSxxxx: message
  const p2 = /([a-zA-Z0-9_.\/-]+\.(?:ts|tsx|js|jsx)):([0-9]+):([0-9]+)\s*-\s*(error|warning)\s+(TS\d+):\s*(.+)/g;
  while ((m = p2.exec(output)) !== null) {
    errors.push({
      file: m[1], line: parseInt(m[2]), col: parseInt(m[3]),
      code: m[5], severity: m[4] === 'error' ? 'error' : 'warning',
      message: m[6].trim().slice(0, 400),
    });
  }
  return errors;
}

/**
 * Run tsc --noEmit and report diagnostics (like VS Code's Problems tab).
 * Non-blocking: does not prevent Vite from starting.
 */
async function runTypeCheck() {
  const tscBin = join(WORKSPACE, 'node_modules', '.bin', 'tsc');
  if (!existsSync(tscBin)) {
    console.log('[bootstrap] tsc not found, skipping type check');
    return;
  }
  console.log('[bootstrap] Running tsc --noEmit (Problems tab diagnostics)...');
  try {
    const result = execSync(`${tscBin} --noEmit --pretty false 2>&1`, {
      cwd: WORKSPACE,
      encoding: 'utf8',
      timeout: 60000,
    });
    // If it succeeds with no output, no errors
    console.log('[bootstrap] tsc --noEmit: clean (0 errors)');
    await reportBuildStatus('typecheck_ok');
  } catch (err) {
    // tsc exits non-zero when there are errors — the output is in stdout
    const output = err.stdout || err.message || '';
    const diagnostics = parseTscDiagnostics(output);
    const errorCount = diagnostics.filter(d => d.severity === 'error').length;
    const warnCount = diagnostics.filter(d => d.severity === 'warning').length;
    console.log(`[bootstrap] tsc --noEmit: ${errorCount} error(s), ${warnCount} warning(s)`);
    if (diagnostics.length > 0) {
      // Report as build errors so the pipeline can detect and auto-repair
      await reportBuildStatus(
        'typecheck_errors',
        `TypeScript: ${errorCount} error(s), ${warnCount} warning(s)\n${output.slice(0, 1500)}`,
        diagnostics.slice(0, 30)
      );
    }
  }
}

process.chdir(WORKSPACE);
console.log('[bootstrap] Running npm install...');
try {
  execSync('npm install --prefer-offline --no-audit --no-fund', { stdio: 'inherit' });
  await reportBuildStatus('npm_ok');

  // Run TypeScript diagnostic check (like VS Code Problems tab)
  await runTypeCheck();
} catch (err) {
  console.error('[bootstrap] npm install failed:', err.message);
  // Parse npm stderr for structured errors
  const npmStderr = err.stderr ? err.stderr.toString() : err.message;
  const npmErrors = [];
  const npmErrLines = npmStderr.match(/npm ERR!\s*(.+)/g) || [];
  for (const line of npmErrLines.slice(0, 10)) {
    const msg = line.replace(/^npm ERR!\s*/, '').trim();
    if (msg && !msg.startsWith('A complete log')) {
      npmErrors.push({ file: 'package.json', line: 0, col: 0, code: 'NPM-ERROR', message: msg.slice(0, 300) });
    }
  }
  await reportBuildStatus('npm_failed', err.message, npmErrors);
  // Continue anyway — Vite may still start with partial deps
}

console.log(`[bootstrap] Starting Vite on port ${PORT}...`);
const vite = spawn('./node_modules/.bin/vite', ['--host', '0.0.0.0', '--port', PORT], {
  stdio: ['inherit', 'pipe', 'pipe'],
  cwd: WORKSPACE,
  env: { ...process.env, VITE_ALLOW_ANY_HOST: '1' },
});

// Capture both stdout and stderr to detect build/compile errors
let stderrBuf = '';
let stdoutBuf = '';
let stderrDone = false;

vite.stderr.on('data', (chunk) => {
  const text = chunk.toString();
  process.stderr.write(text);
  if (!stderrDone) stderrBuf += text;
});

vite.stdout.on('data', (chunk) => {
  const text = chunk.toString();
  process.stdout.write(text);
  if (!stderrDone) stdoutBuf += text;

  // Detect Vite compilation errors in stdout (Vite often prints them here)
  if (text.includes('[ERROR]') || text.includes('error during build') || text.includes('Failed to resolve import')) {
    if (!stderrDone) stderrBuf += text;
  }
});

setTimeout(async () => {
  stderrDone = true;
  const combinedOutput = stderrBuf + stdoutBuf;
  const hasErrors = combinedOutput.includes('error') || combinedOutput.includes('Error') ||
                    combinedOutput.includes('ENOENT') || combinedOutput.includes('[ERROR]') ||
                    combinedOutput.includes('Failed to resolve');

  if (stderrBuf.length > 0 && hasErrors) {
    const structuredErrors = parseViteBuildErrors(combinedOutput);
    await reportBuildStatus('vite_error', stderrBuf.slice(0, 2000), structuredErrors);
  } else {
    await reportBuildStatus('running');
  }
}, 15000);

vite.on('exit', async (code) => {
  console.log(`[bootstrap] Vite exited with code ${code}`);
  if (code !== 0) {
    const structuredErrors = parseViteBuildErrors(stderrBuf);
    await reportBuildStatus('crashed', `Vite exited with code ${code}\n${stderrBuf.slice(0, 1000)}`, structuredErrors);
  }
  process.exit(code ?? 1);
});

// ── 8. Workspace sync loop ────────────────────────────────────────────────────
// Poll the control plane every 5 seconds for workspace changes.
// When changed: write updated files to disk (Vite serves them on next request)
// and bump __version.json so the injected browser script triggers a reload.

const versionUrl = `${CONTROL_PLANE_URL}/api/projects/${PROJECT_ID}/code/workspace/version`;
const bundleUrl2 = `${CONTROL_PLANE_URL}/api/projects/${PROJECT_ID}/code/workspace`;
const syncHeaders = { 'Content-Type': 'application/json' };
if (BRIDGE_SECRET) syncHeaders['X-Bridge-Secret'] = BRIDGE_SECRET;

let knownVersion = null;
let syncCounter = 1;

setInterval(async () => {
  try {
    // Cheap version check first
    const vr = await fetch(versionUrl, { headers: syncHeaders });
    if (!vr.ok) return;
    const { version } = await vr.json();
    if (version === knownVersion) return; // no change

    // Workspace changed — fetch full bundle
    console.log(`[bootstrap] Workspace changed (${knownVersion} → ${version}), syncing files...`);
    const wr = await fetch(bundleUrl2, { headers: syncHeaders });
    if (!wr.ok) { console.warn('[bootstrap] Failed to fetch workspace bundle:', wr.status); return; }
    const data = await wr.json();
    const remoteFiles = data.files || {};

    let written = 0;
    for (const [relPath, content] of Object.entries(remoteFiles)) {
      // Never overwrite vite.config.ts or the version file
      if (relPath === 'vite.config.ts' || relPath === 'public/__version.json') continue;
      const fullPath = join(WORKSPACE, relPath);
      mkdirSync(dirname(fullPath), { recursive: true });
      let current = null;
      try { current = readFileSync(fullPath, 'utf8'); } catch {}
      if (current !== content) {
        writeFileSync(fullPath, content, 'utf8');
        written++;
      }
    }

    knownVersion = version;
    syncCounter++;
    // Bump version file → browser reloads
    writeFileSync(join(WORKSPACE, 'public/__version.json'), JSON.stringify({ v: syncCounter }), 'utf8');
    console.log(`[bootstrap] Synced ${written} file(s), version ${syncCounter}`);

    // Re-run type check after workspace sync (like VS Code Problems tab updating)
    if (written > 0) {
      runTypeCheck().catch(e => console.warn('[bootstrap] Post-sync type check failed:', e.message));
    }
  } catch (err) {
    console.warn('[bootstrap] Sync error:', err.message);
  }
}, 5000);
