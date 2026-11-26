import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'

const source = await readFile(
  new URL('../../lumen_reports/public/pwa/sw.js', import.meta.url),
  'utf8',
)

function workerRuntime(overrides = {}) {
  const handlers = {}
  const self = {
    location: { origin: 'https://pos.example.test' },
    addEventListener: (name, callback) => {
      handlers[name] = callback
    },
    navigator: {},
    registration: {},
    clients: {},
    ...overrides,
  }
  vm.runInNewContext(source, { self, URL, Promise })
  return { self, handlers }
}

test('push alerts still display when optional app badging is denied', async () => {
  let shown
  const { handlers } = workerRuntime({
    registration: {
      showNotification: async (title, options) => {
        shown = { title, options }
      },
    },
    navigator: {
      setAppBadge: async () => {
        throw new Error('Badging blocked')
      },
    },
  })
  let completion
  handlers.push({
    data: {
      json: () => ({
        title: 'A new sale',
        body: 'Open dashboard',
        url: 'https://untrusted.example.test/',
      }),
    },
    waitUntil: (value) => {
      completion = value
    },
  })
  await completion
  assert.equal(shown.title, 'A new sale')
  assert.equal(shown.options.data.url, '/esafe-report/mobile?tab=alerts')
})

test('notification clicks open only the dashboard even if clearing the badge fails', async () => {
  let opened,
    closed = false
  const { handlers } = workerRuntime({
    navigator: {
      clearAppBadge: async () => {
        throw new Error('Badging blocked')
      },
    },
    clients: {
      matchAll: async () => [],
      openWindow: async (url) => {
        opened = url
      },
    },
  })
  let completion
  handlers.notificationclick({
    notification: {
      data: { url: 'https://untrusted.example.test/' },
      close: () => {
        closed = true
      },
    },
    waitUntil: (value) => {
      completion = value
    },
  })
  await completion
  assert.equal(closed, true)
  assert.equal(opened, '/esafe-report/mobile?tab=alerts')
})
