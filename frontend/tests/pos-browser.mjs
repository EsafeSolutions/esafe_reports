// Browser smoke test against the production bundle with fixture API responses.
// No live POS site is contacted. Set PLAYWRIGHT_MODULE to a module path if needed.
import { createServer } from 'node:http'
import { readFile, mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import assert from 'node:assert/strict'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const publicDir = path.join(root, 'lumen_reports/public')
const outputDir = path.join(root, '.qa')
await mkdir(outputDir, { recursive: true })
const html = (await readFile(path.join(root, 'lumen_reports/www/lumen.html'), 'utf8'))
  .replace(/<script>\s*\{% for key in boot %\}[\s\S]*?<\/script>/, '<script>window.csrf_token="test-csrf";</script>')
const ready = {
  contract: 3, product: 'ESAFE REPORT', reports_api: true, pos_installed: true,
  can_read_source: true, dashboard_exists: true, can_view: true, can_create: true,
  reason: null, license: 'licensed', slug: 'lumenpos-sales',
  url: '/lumen/dashboard/lumenpos-sales', embed_url: '/lumen/embed/lumenpos-sales',
}
let status = { ...ready, dashboard_exists: false, can_view: false, reason: 'not_set_up' }
let failRead = false
let refuseSetup = false
let setupCount = 0
let readCount = 0
const mime = { '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.woff2': 'font/woff2', '.woff': 'font/woff', '.svg': 'image/svg+xml' }
const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://localhost')
    if (url.pathname.startsWith('/api/method/')) {
      res.setHeader('Content-Type', 'application/json')
      if (url.pathname.endsWith('.get_status')) {
        assert.equal(req.method, 'GET')
        readCount++
        res.writeHead(failRead ? 503 : 200)
        res.end(JSON.stringify({ message: status }))
      } else if (url.pathname.endsWith('.ensure_dashboard')) {
        assert.equal(req.method, 'POST')
        assert.equal(req.headers['x-frappe-csrf-token'], 'test-csrf')
        setupCount++
        if (!refuseSetup) status = { ...ready }
        res.end(JSON.stringify({ message: refuseSetup
          ? { status: 'not_permitted', message: 'Setup requires a reporting builder.' }
          : { status: 'ready', created: true, dropped: [] } }))
      } else res.end(JSON.stringify({ message: { notice: '' } }))
      return
    }
    if (url.pathname.startsWith('/assets/lumen_reports/')) {
      const file = path.resolve(publicDir, decodeURIComponent(url.pathname.slice('/assets/lumen_reports/'.length)))
      if (!file.startsWith(publicDir + path.sep)) { res.writeHead(403); res.end(); return }
      res.setHeader('Content-Type', mime[path.extname(file)] || 'application/octet-stream')
      res.end(await readFile(file))
      return
    }
    res.setHeader('Content-Type', 'text/html')
    res.end(html)
  } catch (err) {
    console.error(err)
    res.writeHead(500)
    res.end('Test server error')
  }
})
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
const origin = `http://127.0.0.1:${server.address().port}`
let browser
try {
  browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' })
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  const errors = []
  page.on('pageerror', err => errors.push(err.message))
  await page.goto(`${origin}/esafe-report/pos`)
  await page.getByRole('heading', { name: 'Connect your sales dashboard', exact: true }).waitFor()
  assert.equal(await page.title(), 'ESAFE REPORT')
  await page.screenshot({ path: path.join(outputDir, 'esafe-report-desktop.png'), fullPage: true })
  refuseSetup = true
  await page.getByRole('button', { name: 'Set up sales dashboard' }).click()
  await page.getByRole('alert').filter({ hasText: 'Setup requires a reporting builder.' }).waitFor()
  refuseSetup = false
  await page.getByRole('button', { name: 'Set up sales dashboard' }).click()
  await page.getByRole('heading', { name: 'Your sales dashboard is ready' }).waitFor()
  assert.equal(setupCount, 2)
  assert.ok(readCount >= 2)
  assert.equal(await page.getByRole('button', { name: 'Set up sales dashboard' }).count(), 0)
  assert.equal(await page.getByRole('link', { name: 'Open POS Insights' }).getAttribute('href'), '/pos#insights')
  assert.equal(await page.getByRole('link', { name: 'View sales dashboard' }).getAttribute('href'), '/esafe-report/dashboard/lumenpos-sales')

  for (const [overrides, heading] of [
    [{ pos_installed: false }, 'Install ESAFE POS on this site'],
    [{ reason: 'needs_role', can_view: false }, 'Reporting access is required'],
    [{ can_read_source: false }, 'POS invoice access is required'],
    [{ reason: 'frontend_missing', can_view: false }, 'The report interface needs a build'],
  ]) {
    status = { ...ready, ...overrides }
    await page.getByRole('button', { name: 'Check again' }).click()
    await page.getByRole('heading', { name: heading }).waitFor()
    assert.equal(await page.getByRole('link', { name: 'Open POS Insights' }).count(), 0)
  }
  failRead = true
  await page.getByRole('button', { name: 'Check again' }).click()
  await page.getByRole('heading', { name: 'Could not check the connection' }).waitFor()
  failRead = false
  status = { ...ready }
  await page.getByRole('button', { name: 'Check again' }).click()
  await page.getByRole('heading', { name: 'Your sales dashboard is ready' }).waitFor()

  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(outputDir, 'esafe-report-mobile.png'), fullPage: true })
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
  await page.getByRole('button', { name: 'Dark', exact: true }).click()
  await page.waitForFunction(() => getComputedStyle(document.body).color === 'rgb(242, 245, 250)')
  await page.screenshot({ path: path.join(outputDir, 'esafe-report-dark-mobile.png'), fullPage: true })
  await page.goto(`${origin}/lumen/pos`)
  await page.getByRole('heading', { name: 'Your sales dashboard is ready' }).waitFor()
  assert.equal(await page.getByRole('link', { name: 'View sales dashboard' }).getAttribute('href'), '/lumen/dashboard/lumenpos-sales')
  assert.deepEqual(errors, [])
  console.log('PASS: production routes, setup success/refusal, CSRF, permission/error/retry states, desktop/mobile, dark mode, no page errors.')
  console.log(`Screenshots: ${outputDir}`)
} finally {
  if (browser) await browser.close()
  await new Promise(resolve => server.close(resolve))
}
