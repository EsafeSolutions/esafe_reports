<template>
  <main class="pos-page">
    <div class="pos-intro">
      <div>
        <div class="eyebrow">ESAFE REPORT / {{ t('POS connection') }}</div>
        <h1>{{ t('Your sales. The full picture.') }}</h1>
        <p>{{ t('Connect your POS to live sales reports, all in one place.') }}</p>
      </div>
      <router-link to="/" class="lbtn">{{ t('All dashboards') }} →</router-link>
    </div>

    <section class="connection panel" :aria-busy="loading || working" aria-labelledby="connection-title">
      <div class="connection-top">
        <div class="connection-label"><span class="signal" :class="{ ready: state === 'ready' && !loading && !error }"></span>{{ t('POS connection') }}</div>
        <span class="site">{{ site }}</span>
      </div>
      <div class="connection-body">
        <div class="connection-mark" aria-hidden="true">
          <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M3 3v18h18M8 16v-5m5 5V7m5 9v-3" /></svg>
        </div>
        <div class="connection-copy" aria-live="polite">
          <h2 id="connection-title">{{ error ? t('Could not check the connection') : t(message[0]) }}</h2>
          <p>{{ error || t(message[1]) }}</p>
          <p v-if="actionError" class="error" role="alert">{{ actionError }}</p>
          <p v-if="dropped.length" class="notice">{{ t('Some charts could not be created with your current data permissions:') }} {{ dropped.map(item => item.title || item.widget_type || item).join(', ') }}</p>
          <div class="actions">
            <button v-if="!error && !loading && state === 'not_set_up'" class="lbtn primary" :disabled="working" @click="setup">
              {{ working ? t('Creating dashboard…') : t('Set up sales dashboard') }}
            </button>
            <template v-if="!error && !loading && state === 'ready'">
              <a href="/pos#insights" class="lbtn primary">{{ t('Open POS Insights') }} ↗</a>
              <router-link :to="{ name: 'DashboardView', params: { slug: status.slug } }" class="lbtn">{{ t('View sales dashboard') }}</router-link>
            </template>
            <button class="lbtn" :disabled="loading || working" @click="load">{{ loading ? t('Checking…') : t('Check again') }}</button>
          </div>
        </div>
      </div>
      <div class="connection-foot">{{ t('Uses your existing POS sign-in and permissions. No API key needed.') }}</div>
    </section>

    <section class="coverage" aria-labelledby="coverage-title">
      <div class="section-heading"><h2 id="coverage-title">{{ t('From every sale to every insight') }}</h2><span>{{ t('Powered by your POS invoices') }}</span></div>
      <div class="coverage-grid">
        <article v-for="(feature, index) in features" :key="feature[0]" class="panel feature">
          <span class="feature-index">0{{ index + 1 }}</span>
          <h3>{{ t(feature[0]) }}</h3><p>{{ t(feature[1]) }}</p>
        </article>
      </div>
    </section>
    <p class="data-note">{{ t('Reports use submitted POS invoices, including returns. Closing a register does not count the same sale twice.') }}</p>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { call } from 'frappe-ui'
import { lang, t } from '@/lib/i18n'
import { connectionState, CONNECTION_MESSAGES, readConnection, SETUP_METHOD } from '@/lib/posConnection'

const status = ref(null)
const loading = ref(true)
const working = ref(false)
const error = ref('')
const actionError = ref('')
const dropped = ref([])
const site = window.location.host
const state = computed(() => connectionState(status.value))
const message = computed(() => CONNECTION_MESSAGES[loading.value ? 'loading' : state.value] || ['Connection needs attention', 'Ask your site administrator to check the reporting integration.'])
const features = [
  ['Sales performance', 'Net sales, invoice count, average basket and returns.'],
  ['Outlets & cashiers', 'See where sales happen and how your team performs.'],
  ['Payment mix', 'Understand how customers pay across your outlets.'],
  ['Products & busy hours', 'Find your top items and the busiest times to trade.'],
]

async function load() {
  loading.value = true
  error.value = ''
  try { status.value = await readConnection() }
  catch (err) { error.value = t(err.message || 'Could not check the connection. Please try again.') }
  finally { loading.value = false }
}

async function setup() {
  if (working.value) return
  working.value = true
  actionError.value = ''
  try {
    const result = await call(SETUP_METHOD, { lang: lang.value })
    if (result?.status !== 'ready') {
      actionError.value = result?.message || t('The dashboard could not be created. Please try again.')
      return
    }
    dropped.value = result.dropped || []
    await load()
  } catch (err) {
    actionError.value = err.message || t('The dashboard could not be created. Please try again.')
  } finally { working.value = false }
}

onMounted(load)
</script>

<style scoped>
.pos-page { max-width: 1200px; margin: 0 auto; padding: 42px 24px; }
.pos-intro, .connection-top, .section-heading { display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.eyebrow { color: var(--blue); font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
h1 { font-size: clamp(26px, 3vw, 36px); font-weight: 800; letter-spacing: -.035em; margin: 12px 0 8px; }
.pos-intro p, .feature p, .data-note { color: var(--muted); line-height: 1.75; }
.connection { margin-top: 32px; overflow: hidden; }
.connection-top { padding: 18px 26px; border-bottom: 1px solid var(--border); background: var(--panel-2); font-size: 12px; }
.connection-label { display: flex; align-items: center; gap: 9px; font-weight: 700; }
.signal { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); }
.signal.ready { background: var(--success); box-shadow: 0 0 0 4px var(--success-bg); }
.site { color: var(--muted); overflow-wrap: anywhere; }
.connection-body { display: flex; align-items: flex-start; gap: 24px; padding: 38px 30px; }
.connection-mark { flex: none; padding: 18px; border-radius: 18px; background: var(--success-bg); color: var(--blue); }
h2 { font-size: 21px; font-weight: 750; letter-spacing: -.025em; }
.connection-copy p { max-width: 680px; color: var(--muted); font-size: 14px; line-height: 1.8; margin-top: 10px; }
.connection-copy .error { color: var(--danger); }
.connection-copy .notice { color: var(--warning); }
.actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }
.lbtn { text-decoration: none; }
button:disabled { opacity: .55; cursor: wait; }
.connection-foot { border-top: 1px solid var(--border); padding: 15px 26px; color: var(--muted); font-size: 12px; }
.coverage { margin-top: 38px; }
.section-heading { margin-bottom: 16px; }
.section-heading h2 { font-size: 17px; }
.section-heading span { font-size: 12px; color: var(--muted); }
.coverage-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.feature { padding: 22px; }
.feature-index { font-family: var(--mono); color: var(--blue); font-size: 12px; }
.feature h3 { font-size: 14px; font-weight: 750; margin: 18px 0 8px; }
.feature p { font-size: 12px; }
.data-note { margin-top: 24px; font-size: 12px; }
@media (max-width: 800px) { .coverage-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 540px) {
  .pos-page { padding: 28px 16px; }
  .pos-intro, .section-heading { align-items: flex-start; flex-direction: column; gap: 12px; }
  .connection-body { padding: 24px 20px; flex-direction: column; gap: 18px; }
  .connection-top { padding: 16px 20px; flex-wrap: wrap; gap: 8px; }
  .coverage-grid { grid-template-columns: 1fr; }
  .actions .lbtn { width: 100%; justify-content: center; }
}
</style>
