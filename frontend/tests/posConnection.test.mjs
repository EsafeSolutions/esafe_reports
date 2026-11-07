import test from 'node:test'
import assert from 'node:assert/strict'
import { connectionState, readConnection } from '../src/lib/posConnection.js'

const ready = {
  contract: 3, pos_installed: true, can_read_source: true,
  dashboard_exists: true, can_view: true, can_create: false, reason: null,
}

test('ready requires POS, a visible dashboard and permission to read invoice data', () => {
  assert.equal(connectionState(ready), 'ready')
  assert.equal(connectionState({ ...ready, pos_installed: false }), 'pos_missing')
  assert.equal(connectionState({ ...ready, can_read_source: false }), 'needs_data_access')
  assert.equal(connectionState({ ...ready, can_view: false }), 'not_in_audience')
  assert.equal(connectionState({ ...ready, reason: 'needs_role' }), 'needs_role')
  assert.equal(connectionState({ ...ready, reason: 'frontend_missing' }), 'frontend_missing')
})

test('setup is offered only when allowed and never for an expired subscription', () => {
  const missing = { ...ready, dashboard_exists: false, can_view: false, reason: 'not_set_up' }
  assert.equal(connectionState(missing), 'needs_setup_access')
  assert.equal(connectionState({ ...missing, can_create: true }), 'not_set_up')
  assert.equal(connectionState({ ...missing, can_create: true, license: 'expired' }), 'license_expired')
  assert.equal(connectionState({ ...ready, license: 'expired' }), 'ready')
  assert.equal(connectionState({ ...missing, reason: 'needs_erpnext' }), 'needs_erpnext')
})

test('connection checks are read-only same-origin requests', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/method/lumen_reports.integrations.lumenpos.get_status')
    assert.equal(options.method, 'GET')
    assert.equal(options.credentials, 'same-origin')
    return { ok: true, json: async () => ({ message: ready }) }
  })
  assert.deepEqual(await readConnection(), ready)
})

test('failed or outdated responses cannot appear connected', async (t) => {
  const mock = t.mock.method(globalThis, 'fetch', async () => ({ ok: false }))
  await assert.rejects(readConnection, /signed in/)
  mock.mock.mockImplementation(async () => ({ ok: true, json: async () => ({ message: { contract: 2 } }) }))
  await assert.rejects(readConnection, /Update ESAFE REPORT/)
  mock.mock.mockImplementation(async () => ({ ok: true, json: async () => ({}) }))
  await assert.rejects(readConnection, /Update ESAFE REPORT/)
})
