// Production bundle in local Chrome. API/native-push fixtures do not contact a POS site or push provider.
import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { startFixtureServer, fixture } from './mobile-fixture.mjs'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const output = path.join(root, '.qa/mobile')
await mkdir(output, { recursive: true })
const server = await startFixtureServer()
const origin = `http://127.0.0.1:${server.address().port}`
let browser
try {
  browser = await chromium.launch({ channel: 'chrome', headless: true })
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    timezoneId: 'Asia/Colombo',
  })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto(origin + '/esafe-report/mobile')
  await page.getByText('LKR 284,650', { exact: true }).waitFor()
  await page.evaluate(() => document.fonts.ready)
  const returnsBox = await page.locator('.m-returns').boundingBox()
  const navigationBox = await page.locator('.m-bottom-nav').boundingBox()
  assert.ok(returnsBox.y + returnsBox.height <= navigationBox.y + 1, 'Overview controls must clear the fixed navigation at 390 x 844')
  assert.equal(await page.locator('.hd').count(), 0)
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  )
  await page.screenshot({
    path: path.join(output, 'overview.png'),
    fullPage: true,
  })
  await page.screenshot({ path: path.join(output, 'overview-viewport.png') })
  await page.getByRole('button', { name: '7 days', exact: true }).click()
  await page
    .getByRole('button', { name: '7 days', exact: true })
    .getAttribute('aria-pressed')
    .then((value) => assert.equal(value, 'true'))
  await page.getByRole('button', { name: 'All outlets', exact: true }).click()
  await page.getByRole('searchbox', { name: 'Search outlets' }).fill('showroom')
  await page
    .getByRole('button', { name: 'SHOWROOM · Esafe', exact: true })
    .click()
  await page.getByText('LKR 142,325', { exact: true }).waitFor()
  assert.ok(
    fixture.requests.some(
      (r) =>
        r.method.endsWith('run_widget') &&
        JSON.parse(r.data.filter_values).pos_profile === 'SHOWROOM · Esafe',
    ),
  )
  await page.getByRole('button', { name: 'Reports', exact: true }).click()
  await page.getByRole('heading', { name: 'Reports', exact: true }).waitFor()
  await page.getByText('Payment Mix', { exact: true }).waitFor()
  await page.getByRole('button', { name: 'Alerts', exact: true }).click()
  await page.getByRole('heading', { name: 'Alerts', exact: true }).waitFor()
  await page
    .getByRole('button', { name: 'Enable notifications', exact: true })
    .waitFor()
  await page.screenshot({
    path: path.join(output, 'alerts.png'),
    fullPage: true,
  })
  await page.screenshot({ path: path.join(output, 'alerts-viewport.png') })
  await page.getByRole('button', { name: 'Settings', exact: true }).click()
  await page.getByRole('heading', { name: 'App settings' }).waitFor()
  await page.screenshot({
    path: path.join(output, 'settings.png'),
    fullPage: true,
  })
  await page.screenshot({ path: path.join(output, 'settings-viewport.png') })
  await page.getByRole('button', { name: 'Install app', exact: true }).click()
  await page
    .getByText('Follow the steps above to add Esafe BLABS to your Home Screen.')
    .waitFor()
  await page.getByRole('button', { name: 'Appearance Light' }).click()
  assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark')
  await page.screenshot({ path: path.join(output, 'dark.png'), fullPage: true })
  await page.getByRole('button', { name: 'Language English' }).click()
  assert.equal(await page.locator('html').getAttribute('dir'), 'rtl')
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  )
  await page.screenshot({
    path: path.join(output, 'arabic.png'),
    fullPage: true,
  })
  await page.getByRole('button', { name: /اللغة/ }).click()
  await page.getByRole('button', { name: 'Appearance Dark' }).click()
  // Use a fresh device context for independent size checks.
  const desktop = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  })
  await desktop.goto(origin + '/esafe-report/mobile')
  await desktop.getByText('LKR 284,650', { exact: true }).waitFor()
  await desktop.screenshot({
    path: path.join(output, 'desktop.png'),
    fullPage: true,
  })
  await desktop.setViewportSize({ width: 320, height: 740 })
  assert.equal(
    await desktop.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  )
  await desktop.getByRole('button', { name: 'Settings', exact: true }).click()
  assert.equal(
    await desktop.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  )

  // Exercise the real service worker's installation, scope and offline navigation.
  const workerState = await page.evaluate(async () => {
    const registrations = await navigator.serviceWorker.getRegistrations()
    return registrations.map((r) => ({
      scope: r.scope,
      active: r.active?.state,
      installing: r.installing?.state,
    }))
  })
  console.log('Service worker:', JSON.stringify(workerState))
  await page.waitForFunction(
    async () =>
      Boolean(
        (await navigator.serviceWorker.getRegistration('/esafe-report/'))
          ?.active,
      ),
    { timeout: 15000 },
  )
  const registration = await page.evaluate(async () => {
    const r = await navigator.serviceWorker.getRegistration('/esafe-report/')
    return r?.scope
  })
  assert.equal(registration, origin + '/esafe-report/')
  await context.setOffline(true)
  await page.goto(origin + '/esafe-report/mobile?offline-check=1')
  await page.getByRole('heading', { name: "You're offline" }).waitFor()
  await context.setOffline(false)
  await page.getByRole('link', { name: 'Try again' }).click()
  await page
    .getByRole('heading', { name: 'Sales overview', exact: true })
    .waitFor()
  const cacheUrls = await page.evaluate(async () => {
    const keys = await caches.keys()
    return (
      await Promise.all(
        keys
          .filter((k) => k.startsWith('lumen-mobile-'))
          .map(async (k) =>
            (await (await caches.open(k)).keys()).map((r) => r.url),
          ),
      )
    ).flat()
  })
  assert.ok(
    cacheUrls.every(
      (url) =>
        !url.includes('/api/') &&
        !new URL(url).pathname.startsWith('/esafe-report/'),
    ),
  )

  // Simulate only native notification permission/subscription, while using the built app and real worker.
  const pushContext = await browser.newContext({
    viewport: { width: 390, height: 844 },
  })
  await pushContext.addInitScript(() => {
    let subscription = null
    Object.defineProperty(Notification, 'permission', { get: () => 'granted' })
    Notification.requestPermission = async () => 'granted'
    const manager = {
      getSubscription: async () => subscription,
      subscribe: async () =>
        (subscription = {
          endpoint: 'https://fcm.googleapis.com/fcm/send/fixture',
          toJSON: () => ({
            endpoint: 'https://fcm.googleapis.com/fcm/send/fixture',
            keys: { p256dh: 'test-public', auth: 'test-auth' },
          }),
          unsubscribe: async () => {
            subscription = null
            return true
          },
        }),
    }
    Object.defineProperty(ServiceWorkerRegistration.prototype, 'pushManager', {
      get: () => manager,
    })
  })
  const pushPage = await pushContext.newPage()
  await pushPage.goto(origin + '/esafe-report/mobile?tab=alerts')
  await pushPage
    .getByRole('button', { name: 'Enable notifications', exact: true })
    .click()
  await pushPage
    .getByRole('heading', { name: 'Notifications are on', exact: true })
    .waitFor()
  assert.equal(fixture.preferences.daily_summary, true)
  await pushPage
    .getByRole('switch', { name: 'New sales and returns' })
    .uncheck()
  await pushPage.getByText('Notification preferences saved.').waitFor()
  assert.equal(fixture.preferences.sales_alerts, false)
  await pushPage.getByLabel('Daily summary time', { exact: true }).fill('21:15')
  await pushPage.getByLabel('Daily summary time', { exact: true }).blur()
  await pushPage.getByRole('button', { name: 'Send test notification' }).click()
  await pushPage
    .getByText('Test notification queued. Check your device notifications.')
    .waitFor()
  assert.ok(
    fixture.requests
      .filter(
        (r) =>
          r.method.startsWith('lumen_reports.notifications.') &&
          r.verb === 'POST',
      )
      .every((r) => r.csrf === 'fixture-csrf'),
  )
  await pushPage
    .getByRole('button', { name: 'Turn off notifications on this device' })
    .click()
  await pushPage.getByText('Notifications turned off on this device.').waitFor()
  assert.equal(fixture.preferences, null)

  fixture.connected = false
  await desktop.goto(origin + '/esafe-report/mobile')
  await desktop.getByRole('button', { name: 'Set up sales dashboard' }).click()
  await desktop.getByText('LKR 284,650', { exact: true }).waitFor()
  fixture.denied = true
  await desktop.getByRole('button', { name: 'Refresh sales' }).click()
  await desktop
    .getByRole('heading', { name: 'Could not load your sales' })
    .waitFor()
  assert.equal(
    await desktop
      .getByRole('link', { name: 'Sign in again' })
      .getAttribute('href'),
    '/login?redirect-to=%2Fesafe-report%2Fmobile',
  )
  assert.equal(
    await desktop.getByText('LKR 284,650', { exact: true }).count(),
    0,
  )
  assert.deepEqual(errors, [])
  console.log(
    'PASS: mobile/desktop/320px, filters, reports, alerts, install help, dark/Arabic, SW scope/offline/privacy, push preference/test/revocation flow, setup and permission revocation.',
  )
  console.log(
    'Push permission and subscription were simulated; no device delivery or production deployment was tested.',
  )
} finally {
  if (browser) await browser.close()
  await new Promise((resolve) => server.close(resolve))
}
