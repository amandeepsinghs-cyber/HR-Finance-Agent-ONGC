/**
 * Yukti AI — single-origin server.
 *
 * Wraps Next.js and proxies backend traffic through the UI origin so the browser
 * only ever talks to ONE port (forward only port 3200 from your laptop):
 *   /api/turn, /api/export, /api/export/{id}, /api/auth/*, /health  -> YUKTI_BACKEND_URL (HTTP or HTTPS, e.g. Cloud Run)
 *   /ws/live                                          -> YUKTI_BACKEND_URL (WebSocket upgrade)
 * Everything else (pages, assets, HMR websocket) is served by Next.
 *
 * Usage:  node server.js --dev     (npm run dev)
 *         node server.js           (npm run start, after npm run build)
 * Env:    PORT (default 3200), HOST (default 0.0.0.0),
 *         YUKTI_BACKEND_URL (default http://127.0.0.1:8095)
 */
const http = require('http');
const https = require('https');
const net = require('net');
const tls = require('tls');
const { parse } = require('url');
const next = require('next');

const dev = process.argv.includes('--dev') || process.env.NODE_ENV === 'development';
const port = parseInt(process.env.PORT || '3200', 10);
const host = process.env.HOST || '0.0.0.0';
const backend = new URL(process.env.YUKTI_BACKEND_URL || 'http://127.0.0.1:8095');
// H1.3a: https backends (Cloud Run) are proxied over TLS for both HTTP and the WebSocket upgrade
const secure = backend.protocol === 'https:' || backend.protocol === 'wss:';
const backendPort = parseInt(backend.port || (secure ? '443' : '80'), 10);
const httpLib = secure ? https : http;

// P0.4: /api/auth/* (persona session: personas, session, me) and /api/jobs/*, /api/actions/* (P3.2 background jobs) are proxied too so the yk_session cookie stays same-origin
const PROXY_HTTP = [
  /^\/api\/turn(\/|$|\?)/,
  /^\/api\/voice-turn(\/|$|\?)/,
  /^\/api\/export(\/|$|\?)/,
  /^\/api\/auth(\/|$|\?)/,
  /^\/api\/jobs(\/|$|\?)/,
  /^\/api\/actions(\/|$|\?)/,
  /^\/health(\/|$|\?)/,
];
const isProxiedHttp = (p) => PROXY_HTTP.some((re) => re.test(p));
const isProxiedWs = (p) => /^\/ws\/live(\/|$|\?)/.test(p);

const log = (...a) => console.log('[yukti-proxy]', ...a);

function proxyHttp(req, res) {
  const headers = { ...req.headers, host: backend.host };
  headers['x-forwarded-host'] = req.headers.host || '';
  headers['x-forwarded-for'] = req.socket.remoteAddress || '';
  const upstream = httpLib.request(
    { hostname: backend.hostname, port: backendPort, method: req.method, path: req.url, headers, servername: backend.hostname },
    (up) => {
      res.writeHead(up.statusCode || 502, up.headers);
      up.on('aborted', () => res.destroy()); // backend died mid-stream: end the client response, don't hang
      up.pipe(res);
    }
  );
  upstream.setTimeout(180000, () => upstream.destroy(new Error('upstream timeout')));
  // H1.3a: when the browser gives up (AbortController / tab closed), cancel the backend request too, so a
  // superseded question doesn't keep running BigQuery + Gemini work for nobody.
  const abortUpstream = () => {
    if (!res.writableEnded) upstream.destroy(new Error('client aborted'));
  };
  req.on('aborted', abortUpstream);
  res.on('close', abortUpstream);
  upstream.on('error', (err) => {
    if (err && err.message === 'client aborted') return; // nobody is listening any more
    if (res.headersSent) return res.destroy(); // never append JSON to a partial body
    if (!res.headersSent) {
      res.writeHead(502, { 'content-type': 'application/json' });
    }
    res.end(JSON.stringify({ type: 'error', message: `Backend unreachable (${err.code || err.message})`, retryable: true }));
  });
  req.pipe(upstream);
}

function proxyWs(req, socket, head) {
  const onConnect = () => {
    const lines = [`${req.method} ${req.url} HTTP/${req.httpVersion}`];
    for (let i = 0; i < req.rawHeaders.length; i += 2) {
      const k = req.rawHeaders[i];
      const v = k.toLowerCase() === 'host' ? backend.host : req.rawHeaders[i + 1];
      lines.push(`${k}: ${v}`);
    }
    upstream.write(lines.join('\r\n') + '\r\n\r\n');
    if (head && head.length) upstream.write(head);
    socket.pipe(upstream).pipe(socket);
  };
  const upstream = secure
    ? tls.connect({ port: backendPort, host: backend.hostname, servername: backend.hostname }, onConnect)
    : net.connect(backendPort, backend.hostname, onConnect);
  upstream.setNoDelay(true);
  socket.setNoDelay(true);
  const close = () => {
    socket.destroy();
    upstream.destroy();
  };
  upstream.on('error', (err) => {
    log('ws upstream error', err.code || err.message);
    if (socket.writable) socket.end('HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n');
    close();
  });
  socket.on('error', close);
  upstream.on('close', () => socket.destroy());
  socket.on('close', () => upstream.destroy());
}

// Prevent Next.js 14 from calling process.exit(0) when stdin is closed in daemon / Cloud Run environments
try {
  process.stdin.resume();
  const origStdinOn = process.stdin.on.bind(process.stdin);
  process.stdin.on = (ev, fn) => {
    if (ev === 'end' || ev === 'close') return process.stdin;
    return origStdinOn(ev, fn);
  };
} catch {}

const app = next({ dev, hostname: 'localhost', port });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const server = http.createServer((req, res) => {
    const { pathname } = parse(req.url || '/');
    if (isProxiedHttp(pathname || '')) return proxyHttp(req, res);
    return handle(req, res, parse(req.url || '/', true));
  });

  server.on('upgrade', (req, socket, head) => {
    const { pathname } = parse(req.url || '/');
    if (isProxiedWs(pathname || '')) return proxyWs(req, socket, head);
    // Other upgrades (Next dev HMR at /_next/webpack-hmr) are handled by the listener
    // Next attaches to this server on the first request; unmatched paths are left alone.
  });

  server.listen(port, host, () => {
    log(`${dev ? 'dev' : 'production'} UI on http://${host}:${port}  ->  backend ${backend.origin}`);
    log('Forward ONLY this port from your laptop (e.g. ssh -L 3200:localhost:3200 <cloudtop>).');
  });
});
