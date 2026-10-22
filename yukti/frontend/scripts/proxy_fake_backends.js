const http = require('http'); const https = require('https'); const fs = require('fs');
let aborted = 0, served = 0;
const handler = (req, res) => {
  if (req.url.startsWith('/stats')) { res.end(JSON.stringify({ aborted, served })); return; }
  if (req.url.startsWith('/api/turn')) {
    const t = setTimeout(() => { served++; res.end('{"ok":true}'); }, 3000);
    req.on('close', () => { if (!res.writableEnded) { aborted++; clearTimeout(t); } });
    return;
  }
  res.setHeader('content-type', 'application/json'); res.end('{"status":"ok","tls":' + (!!req.socket.encrypted) + '}');
};
http.createServer(handler).listen(18081);
https.createServer({ key: fs.readFileSync('key.pem'), cert: fs.readFileSync('cert.pem') }, handler).listen(18443);
console.log('fake backends up');
