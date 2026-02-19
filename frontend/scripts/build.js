const fs = require('fs');
const path = require('path');
const esbuild = require('esbuild');

const rootDir = path.join(__dirname, '..');
const buildDir = path.join(rootDir, 'build');

fs.rmSync(buildDir, { recursive: true, force: true });
fs.mkdirSync(buildDir, { recursive: true });

esbuild
  .build({
    entryPoints: [path.join(rootDir, 'src', 'main.jsx')],
    bundle: true,
    minify: true,
    sourcemap: false,
    target: ['es2018'],
    outfile: path.join(buildDir, 'assets', 'app.js'),
    loader: {
      '.js': 'jsx',
      '.jsx': 'jsx',
      '.css': 'css',
    },
    logLevel: 'info',
  })
  .then(() => {
    const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Support Ticket System</title>
    <link rel="stylesheet" href="/assets/app.css" />
    <script defer src="/assets/app.js"></script>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
`;
    fs.writeFileSync(path.join(buildDir, 'index.html'), html, 'utf8');
    console.log('Frontend build complete.');
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
