import test from 'node:test'
import assert from 'node:assert/strict'
import {
  deviceEnvironment,
  applicationServerKey,
  numericValue,
} from '../src/lib/mobileApp.js'
import { mobileApi } from '../src/lib/mobileApi.js'

test('iPhone and iPad installation requirements are detected without affecting Android', () => {
  const win = {
    matchMedia: () => ({ matches: false }),
    isSecureContext: true,
    PushManager: {},
    Notification: {},
  }
  assert.equal(
    deviceEnvironment(
      { userAgent: 'iPhone', standalone: false, serviceWorker: {} },
      win,
    ).ios,
    true,
  )
  assert.equal(
    deviceEnvironment(
      {
        userAgent: 'Mac',
        platform: 'MacIntel',
        maxTouchPoints: 5,
        serviceWorker: {},
      },
      win,
    ).ios,
    true,
  )
  assert.equal(
    deviceEnvironment({ userAgent: 'Android', serviceWorker: {} }, win).ios,
    false,
  )
  assert.equal(
    deviceEnvironment({ userAgent: 'iPhone', standalone: true }, win)
      .standalone,
    true,
  )
  assert.equal(deviceEnvironment({ userAgent: 'iPhone' }, win).push, false)
})

test('missing or failed metrics never appear as zero sales', () => {
  for (const result of [
    null,
    {},
    { value: 0 },
    { result_type: 'number', value: null },
    { result_type: 'number', value: NaN },
  ])
    assert.equal(numericValue(result), null)
  assert.equal(numericValue({ result_type: 'number', value: 0 }), 0)
  assert.equal(numericValue({ result_type: 'number', value: -50 }), -50)
})

test('VAPID public keys use URL-safe base64 decoding', () => {
  assert.deepEqual([...applicationServerKey('BAECA_8')], [4, 1, 2, 3, 255])
})

test('mobile reads are same-origin GET and writes include CSRF protection', async (t) => {
  const previousWindow = globalThis.window
  globalThis.window = {
    location: { origin: 'https://pos.example.test' },
    csrf_token: 'csrf-test',
  }
  t.after(() => {
    if (previousWindow === undefined) delete globalThis.window
    else globalThis.window = previousWindow
  })
  const requests = []
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    requests.push({ url, options })
    return { ok: true, json: async () => ({ message: { ok: true } }) }
  })
  await mobileApi('lumen_reports.mobile.get_context')
  assert.equal(requests[0].options.method, 'GET')
  assert.equal(requests[0].options.credentials, 'same-origin')
  assert.equal(requests[0].options.cache, 'no-store')
  await mobileApi(
    'lumen_reports.notifications.subscribe',
    { preferences: { daily_summary: true } },
    'POST',
  )
  assert.equal(requests[1].options.headers['X-Frappe-CSRF-Token'], 'csrf-test')
  assert.deepEqual(JSON.parse(requests[1].options.body), {
    preferences: { daily_summary: true },
  })
})
