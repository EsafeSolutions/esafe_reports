/* Esafe BLABS: cache public assets only. Never persist API replies or signed-in HTML. */
const CACHE = 'lumen-mobile-__LUMEN_BUILD__'
const OFFLINE = '/assets/lumen_reports/pwa/offline.html'
const HOME = '/esafe-report/mobile'
const ICON = '/assets/lumen_reports/pwa/icon-192.png'

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll([OFFLINE, ICON])))
  self.skipWaiting()
})

self.addEventListener('activate', event => {
  event.waitUntil(Promise.all([
    caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('lumen-mobile-') && key !== CACHE).map(key => caches.delete(key)))),
    self.clients.claim(),
  ]))
})

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url)
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => caches.match(OFFLINE)))
    return
  }
  if (!url.pathname.startsWith('/assets/lumen_reports/frontend/assets/') && !url.pathname.startsWith('/assets/lumen_reports/pwa/')) return
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
    if (response.ok && !response.redirected) {
      const copy = response.clone()
      event.waitUntil(caches.open(CACHE).then(cache => cache.put(event.request, copy)))
    }
    return response
  })))
})

self.addEventListener('push', event => {
  let message = {}
  try { message = event.data?.json() || {} } catch { /* show a useful generic alert */ }
  event.waitUntil(Promise.all([
    self.registration.showNotification(message.title || 'Esafe BLABS', {
      body: message.body || 'Your POS dashboard has an update.',
      icon: ICON,
      badge: '/assets/lumen_reports/pwa/badge.png',
      tag: message.tag || 'lumen-update',
      data: { url: HOME + '?tab=alerts' },
    }),
    self.navigator.setAppBadge ? self.navigator.setAppBadge(1).catch(() => {}) : Promise.resolve(),
  ]))
})

self.addEventListener('notificationclick', event => {
  event.notification.close()
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(async clients => {
    const app = clients.find(client => new URL(client.url).pathname === HOME)
    if (self.navigator.clearAppBadge) await self.navigator.clearAppBadge().catch(() => {})
    if (app) {
      await app.navigate(HOME + '?tab=alerts')
      return app.focus()
    }
    return self.clients.openWindow(HOME + '?tab=alerts')
  }))
})
