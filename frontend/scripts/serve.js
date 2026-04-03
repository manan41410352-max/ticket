const fs = require('fs');
const http = require('http');
const https = require('https');
const path = require('path');

const rootDir = path.join(__dirname, '..');
const buildDir = path.join(rootDir, 'build');
const indexPath = path.join(buildDir, 'index.html');
const frontendPort = Number(process.env.FRONTEND_PORT || 3000);
const backendUrl = new URL(process.env.BACKEND_URL || 'http://127.0.0.1:8000');
const backendClient = backendUrl.protocol === 'https:' ? https : http;

const MIME_TYPES = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

function buildMissing(response) {
  response.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
  response.end('Frontend build not found. Run "npm run build" first.');
}

function sendStaticFile(filePath, request, response) {
  if (!fs.existsSync(filePath)) {
    response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Not found');
    return;
  }

  const extension = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[extension] || 'application/octet-stream';
  const stats = fs.statSync(filePath);

  response.writeHead(200, {
    'Content-Length': stats.size,
    'Content-Type': contentType,
  });

  if (request.method === 'HEAD') {
    response.end();
    return;
  }

  fs.createReadStream(filePath).pipe(response);
}

function resolveFilePath(requestPath) {
  if (!requestPath || requestPath === '/') {
    return indexPath;
  }

  const pathname = decodeURIComponent(requestPath.split('?')[0]);
  const sanitized = pathname.replace(/^\/+/, '');
  const filePath = path.normalize(path.join(buildDir, sanitized));

  if (!filePath.startsWith(buildDir)) {
    return null;
  }

  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    return filePath;
  }

  return indexPath;
}

function forwardApiRequest(request, response) {
  const backendRequest = backendClient.request(
    {
      protocol: backendUrl.protocol,
      hostname: backendUrl.hostname,
      port: backendUrl.port,
      method: request.method,
      path: request.url,
      headers: {
        ...request.headers,
        host: backendUrl.host,
      },
    },
    (backendResponse) => {
      response.writeHead(backendResponse.statusCode || 502, backendResponse.headers);
      backendResponse.pipe(response);
    }
  );

  backendRequest.on('error', (error) => {
    response.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    response.end(
      JSON.stringify({
        detail: 'Unable to reach backend server.',
        error: error.message,
      })
    );
  });

  request.pipe(backendRequest);
}

const server = http.createServer((request, response) => {
  if (!fs.existsSync(indexPath)) {
    buildMissing(response);
    return;
  }

  if (!request.url) {
    response.writeHead(400, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Bad request');
    return;
  }

  if (request.url.startsWith('/api/')) {
    forwardApiRequest(request, response);
    return;
  }

  if (!['GET', 'HEAD'].includes(request.method || 'GET')) {
    response.writeHead(405, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Method not allowed');
    return;
  }

  const filePath = resolveFilePath(request.url);
  if (!filePath) {
    response.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Forbidden');
    return;
  }

  sendStaticFile(filePath, request, response);
});

server.listen(frontendPort, () => {
  console.log(
    `Frontend server running at http://127.0.0.1:${frontendPort} and forwarding /api to ${backendUrl.origin}`
  );
});
