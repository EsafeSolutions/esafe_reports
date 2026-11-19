// Copyright (c) 2026 Lumen Solutions. All rights reserved.
// SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
// Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
import { onMounted, onUnmounted, ref, watch } from 'vue'

const CHECK_INTERVAL = 60_000
const VERSION_URL = '/assets/lumen_reports/frontend/version.json'
const IS_VERSION = /^[a-f0-9]{64}$/

export function useAppUpdate(route) {
  const currentVersion = document.querySelector('meta[name="lumen-build"]')?.content
  const availableVersion = ref('')
  let timer
  let request

  function reload(automatic = false) {
    try {
      const key = `lumen-reloaded:${availableVersion.value}`
      // A rolling deployment can still serve the previous page after a reload.
      if (automatic && sessionStorage.getItem(key)) return
      sessionStorage.setItem(key, '1')
    } catch {
      if (automatic) return
    }
    window.location.reload()
  }

  watch([availableVersion, () => route.meta.autoReload], ([version, autoReload]) => {
    if (version && autoReload) reload(true)
  })

  async function check() {
    if (request) return
    request = new AbortController()
    try {
      const response = await fetch(VERSION_URL, { cache: 'no-store', signal: request.signal })
      if (!response.ok) return
      const { version } = await response.json()
      if (typeof version === 'string' && IS_VERSION.test(version)) {
        availableVersion.value = version === currentVersion ? '' : version
      }
    } catch {
      // Offline tabs and deployments in progress can try again on the next check.
    } finally {
      request = null
    }
  }

  onMounted(() => {
    if (!currentVersion || !IS_VERSION.test(currentVersion)) return
    check()
    timer = window.setInterval(check, CHECK_INTERVAL)
    window.addEventListener('focus', check)
    window.addEventListener('vite:preloadError', check)
  })

  onUnmounted(() => {
    window.clearInterval(timer)
    window.removeEventListener('focus', check)
    window.removeEventListener('vite:preloadError', check)
    request?.abort()
  })

  return { availableVersion, reload }
}
