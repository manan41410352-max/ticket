const fs = require('fs');
const path = require('path');

const buildDir = path.join(__dirname, '..', 'build');
fs.mkdirSync(buildDir, { recursive: true });

const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Support Ticket Frontend</title>
    <style>
      body {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f2f5f7;
        color: #12202f;
      }
      .container {
        max-width: 760px;
        margin: 48px auto;
        background: #ffffff;
        border-radius: 12px;
        padding: 28px;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.08);
      }
      h1 {
        margin-top: 0;
      }
      code {
        background: #eef3f8;
        padding: 2px 6px;
        border-radius: 4px;
      }
      .muted {
        color: #4c6175;
      }
    </style>
  </head>
  <body>
    <main class="container">
      <h1>Support Ticket System</h1>
      <p>Frontend container is running.</p>
      <p class="muted">Backend API base: <code>http://localhost:8000/api/</code></p>
    </main>
  </body>
</html>
`;

fs.writeFileSync(path.join(buildDir, 'index.html'), html, 'utf8');
console.log('Frontend build complete: build/index.html');
