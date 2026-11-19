// Copyright (c) 2026 Lumen Solutions. All rights reserved.
// SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
// Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import path from 'node:path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'

function sourceRevision() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], {
      cwd: __dirname,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim()
  } catch {
    // Packaged installs can build from source with no Git metadata.
    return ''
  }
}

export default defineConfig({
  plugins: [
    frappeui({
      // frappe-ui's bench discovery stops at '/', which loops at a Windows
      // drive root. Use an explicit local proxy on Windows instead.
      frappeProxy: process.platform !== 'win32',
      lucideIcons: true,
      jinjaBootData: true,
      buildConfig: {
        indexHtmlPath: '../lumen_reports/www/lumen.html',
        sourcemap: false,
      },
    }),
    vue(),
    {
      name: 'normalize-page-html',
      transformIndexHtml: {
        order: 'post',
        handler: (html) => html.replace(/\r\n?/g, '\n').replace(/[\t ]+$/gm, ''),
      },
    },
    {
      name: 'app-build-version',
      apply: 'build',
      generateBundle: {
        order: 'post',
        handler(_options, bundle) {
          const page = bundle['index.html']
          // Track the deployed commit and the actual frontend output.
          const version = createHash('sha256')
            .update(sourceRevision())
            .update(String(page.source))
            .update(JSON.stringify(Object.keys(bundle).sort()))
            .digest('hex')
          page.source = String(page.source).replace(
            '</head>',
            `  <meta name="lumen-build" content="${version}" />\n  </head>`,
          )
          this.emitFile({
            type: 'asset',
            fileName: 'version.json',
            source: JSON.stringify({ version }),
          })
        },
      },
    },
  ],
  // the built frontend is committed to the app repo (see .gitignore) so a bench
  // that cannot run the build (Frappe v14 on Node below 18) still ships the page.
  // No source maps: they double the committed size and would expose the source.
  build: {
    sourcemap: false,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 8080,
    allowedHosts: true,
    ...(process.platform === 'win32' ? {
      proxy: {
        '^/(desk|app|login|api|assets|files|private)': {
          target: `http://127.0.0.1:${process.env.FRAPPE_WEB_SERVER_PORT || 8000}`,
          ws: true,
        },
      },
    } : {}),
  },
})
