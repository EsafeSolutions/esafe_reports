// Built-production UI with isolated fixtures, never production records.
import assert from 'node:assert/strict'
import { mkdir, copyFile, readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { startFixtureServer, fixture } from './mobile-fixture.mjs'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const output = path.join(root, '.qa/catalog')
await mkdir(output, { recursive: true })
const server = await startFixtureServer()
const origin = `http://127.0.0.1:${server.address().port}`
let browser
try {
  browser = await chromium.launch({ channel: 'chrome', headless: true })
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, timezoneId: 'Asia/Colombo' })
  const page = await context.newPage(), errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(origin + '/esafe-report/mobile?tab=products')
  await page.getByRole('button', { name: /Tea 100g/ }).waitFor()
  await page.evaluate(() => document.fonts.ready)
  assert.equal(await page.locator('.m-product-row').count(), 20)
  await page.getByRole('searchbox').fill('123456789')
  await page.waitForFunction(() => document.querySelectorAll('.m-product-row').length === 1)
  assert.match(await page.locator('.m-product-row').innerText(), /Tea 100g/)
  await page.getByRole('button', { name: /Tea 100g/ }).click()
  await page.getByRole('dialog').getByText('Main Warehouse', { exact: true }).waitFor()
  assert.match(await page.getByRole('dialog').innerText(), /Reserved 2/)
  await page.getByRole('button', { name: 'Close', exact: true }).click()
  await page.getByRole('searchbox').fill('')
  await page.getByRole('searchbox').blur()
  await page.mouse.move(0, 0)
  await page.waitForFunction(() => document.querySelectorAll('.m-product-row').length === 20)
  await page.getByLabel('Price list', { exact: true }).selectOption('Wholesale')
  await page.getByRole('button', { name: /Tea 100g.*LKR 1,000/ }).waitFor()
  await page.getByLabel('Price list', { exact: true }).selectOption('Standard Selling')
  await page.getByRole('button', { name: /Tea 100g.*LKR 1,250/ }).waitFor()
  await page.getByRole('button', { name: 'Next', exact: true }).click()
  await page.getByText('Page 2', { exact: true }).waitFor()
  assert.equal(await page.locator('.m-product-row').count(), 5)
  await page.getByRole('button', { name: 'Previous', exact: true }).click()
  await page.getByRole('button', { name: /Tea 100g/ }).waitFor()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export this page', exact: true }).click()
  const download = await downloadPromise
  assert.equal(download.suggestedFilename(), 'esafe-products.csv')
  const csv = await readFile(await download.path(), 'utf8')
  assert.equal(csv.startsWith('\ufeff\ufeff'), false)
  assert.match(csv, /Tea 100g/)
  await page.getByLabel('Category', { exact: true }).selectOption('Groceries')
  await page.waitForFunction(() => !document.querySelector('.m-product-list')?.textContent.includes('Tea 100g'))
  await page.getByLabel('Category', { exact: true }).selectOption('')
  await page.getByRole('button', { name: /Tea 100g/ }).waitFor()
  // Capture the actual first page without focus/hover decoration.
  await page.getByRole('searchbox').fill('')
  await page.getByRole('searchbox').blur()
  await page.mouse.move(0, 0)
  await page.screenshot({ path: path.join(output, 'products.png') })

  await page.getByRole('button', { name: 'Inventory', exact: true }).click()
  await page.getByRole('heading', { name: 'Inventory', exact: true }).waitFor()
  await page.getByRole('button', { name: /Milk powder 400g/ }).waitFor()
  await page.getByRole('button', { name: 'Out of stock', exact: true }).click()
  assert.equal(await page.locator('.m-product-row').count(), 1)
  await page.getByRole('button', { name: 'In stock', exact: true }).click()
  assert.equal(await page.locator('.m-product-row').count(), 19)
  await page.getByRole('button', { name: 'All stock', exact: true }).click()
  await page.getByLabel('Warehouse', { exact: true }).selectOption('Showroom')
  await page.waitForFunction(() => [...document.querySelectorAll('.m-product-row')].every(row => row.textContent.includes('0 Nos')))
  await page.getByLabel('Warehouse', { exact: true }).selectOption('')
  await page.getByRole('button', { name: /Tea 100g.*24 Nos/ }).waitFor()
  await page.mouse.move(0, 0)
  await page.screenshot({ path: path.join(output, 'inventory.png') })

  await page.getByRole('button', { name: 'Sales', exact: true }).click()
  await page.getByRole('heading', { name: 'Category sales', exact: true }).waitFor()
  await page.locator('.m-category-summary').getByText('LKR 284,650', { exact: true }).waitFor()
  await page.mouse.move(0, 0)
  await page.screenshot({ path: path.join(output, 'sales.png') })
  await page.getByRole('button', { name: /Groceries LKR/ }).click()
  await page.locator('.m-category-row').getByText('Basmati rice 1kg', { exact: true }).waitFor()
  assert.ok(fixture.requests.some(r => r.method.endsWith('get_sales') && r.data.category === 'Groceries' && r.data.group_by === 'product'))
  await page.getByRole('button', { name: 'All categories', exact: true }).click()
  await page.getByRole('button', { name: '7 days', exact: true }).click()
  await page.getByRole('button', { name: 'All outlets', exact: true }).click()
  await page.getByRole('button', { name: 'SHOWROOM · Esafe', exact: true }).click()
  await page.locator('.m-category-summary').getByText('LKR 142,325', { exact: true }).waitFor()
  fixture.catalogPartial = true
  await page.getByRole('button', { name: 'Refresh sales', exact: true }).click()
  await page.getByRole('alert').filter({ hasText: 'Partial results.' }).waitFor()
  fixture.catalogPartial = false

  // Native CSV bridge is exercised separately from browser download.
  await page.evaluate(() => { window.EsafeNative = { shareCsv: (filename, content) => { window.capturedShare = { filename, content } } } })
  await page.getByRole('button', { name: 'Export sales', exact: true }).click()
  const share = await page.evaluate(() => window.capturedShare)
  assert.equal(share.filename, 'esafe-sales.csv')
  assert.match(share.content, /Groceries/)

  for (const viewport of [{ width: 320, height: 740 }, { width: 390, height: 844 }, { width: 1440, height: 1000 }]) {
    await page.setViewportSize(viewport)
    for (const tab of ['Products', 'Inventory', 'Sales', 'Settings']) {
      await page.getByRole('button', { name: tab, exact: true }).click()
      await page.locator('.m-loading').waitFor({ state: 'hidden' })
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${tab} overflows ${viewport.width}`)
    }
  }
  await page.setViewportSize({ width: 390, height: 844 })
  assert.equal(await page.getByRole('link', { name: 'Download Android APK', exact: true }).getAttribute('href'), '/assets/lumen_reports/downloads/Esafe-BLABS-Android-development.apk')
  const apkResponse = await page.request.get(origin + '/assets/lumen_reports/downloads/Esafe-BLABS-Android-development.apk')
  assert.equal(apkResponse.status(), 200)
  assert.equal((await apkResponse.body()).subarray(0, 2).toString(), 'PK')
  await page.getByRole('button', { name: 'Appearance Light' }).click()
  await page.getByRole('button', { name: 'Language English' }).click()
  for (const label of ['المنتجات', 'المخزون', 'المبيعات']) {
    await page.getByRole('button', { name: label, exact: true }).click()
    await page.locator('.m-loading').waitFor({ state: 'hidden' })
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
  }
  await page.getByRole('button', { name: 'الإعدادات', exact: true }).click()
  await page.getByRole('button', { name: /اللغة/ }).click()
  await page.getByRole('button', { name: 'Appearance Dark' }).click()

  // Loss of access must clear rows; an unavailable API must not invent prices/zero stock.
  fixture.denied = true
  await page.getByRole('button', { name: 'Products', exact: true }).click()
  await page.getByRole('alert').waitFor()
  assert.equal(await page.locator('.m-product-row').count(), 0)
  fixture.denied = false
  await page.getByRole('button', { name: 'Try again', exact: true }).click()
  await page.getByRole('button', { name: /Tea 100g/ }).waitFor()
  await context.setOffline(true)
  await page.getByRole('alert').waitFor()
  assert.equal(await page.locator('.m-product-row').count(), 0)
  await context.setOffline(false)
  await page.getByRole('button', { name: /Tea 100g/ }).waitFor()
  assert.deepEqual(errors, [])
  assert.ok(fixture.requests.filter(r => r.method.includes('mobile_catalog')).every(r => r.verb === 'GET'))
  for (const name of ['products', 'inventory', 'sales']) await copyFile(path.join(output, `${name}.png`), path.join(root, 'docs/design', `mobile-catalog-${name}.png`))
  console.log('Catalogue browser checks passed: search/barcode, prices, detail, pages, CSV/native share, warehouse, stock filters, category drill-down, dates/outlet, partial/error/offline states; 320/390/1440px.')
} finally {
  await browser?.close()
  await new Promise(resolve => server.close(resolve))
}
