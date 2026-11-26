<template>
	<div class="mobile-app">
		<header class="m-header">
			<router-link :to="{ name: 'MobilePOS' }" class="m-brand"
				><img :src="appIcon" width="40" height="40" alt="" /><span
					><strong>Esafe BLABS</strong
					><small>{{ brand.organization || siteName }}</small></span
				></router-link
			><button
				class="m-icon-button m-bell-button"
				:aria-label="t('Open alerts')"
				@click="pick('alerts')"
			>
				<MobileIcon name="bell" :size="25" />
			</button>
		</header>
		<div v-if="!online" class="m-offline" role="status">
			<MobileIcon name="offline" :size="18" />{{
				t("You're offline. Connect to refresh your sales.")
			}}
		</div>
		<main class="m-main">
			<section
				v-if="tab === 'overview' || tab === 'reports'"
				class="m-section"
				:aria-busy="loading"
			>
				<div class="m-heading-line">
					<h1>{{ t(tab === 'overview' ? 'Sales overview' : 'Reports') }}</h1>
					<button
						class="m-icon-button m-refresh"
						:disabled="loading || refreshing || !online"
						:aria-label="t('Refresh sales')"
						@click="load"
					>
						<MobileIcon name="refresh" :size="20" />
					</button>
				</div>
				<p class="m-date"><MobileIcon name="calendar" :size="19" />{{ dateLabel }}</p>
				<template v-if="loading"
					><div class="m-loading" role="status">
						{{ t('Loading your sales…') }}
					</div></template
				>
				<template v-else-if="!ready">
					<div class="m-connection-panel">
						<MobileIcon name="chart" :size="40" />
						<h2>{{ t(connectionMessage[0]) }}</h2>
						<p>{{ error || t(connectionMessage[1]) }}</p>
						<button
							v-if="state === 'not_set_up'"
							class="m-primary"
							:disabled="creating"
							@click="setup"
						>
							{{
								t(creating ? 'Creating dashboard…' : 'Set up sales dashboard')
							}}</button
						><a
							v-else-if="needsSignIn"
							href="/login?redirect-to=%2Fesafe-report%2Fmobile"
							class="m-primary"
							>{{ t('Sign in again') }}</a
						><router-link v-else to="/pos" class="m-primary">{{
							t('Check POS connection')
						}}</router-link
						><button class="m-text-button" @click="load">{{ t('Try again') }}</button>
					</div>
				</template>
				<template v-else>
					<div class="m-period" role="group" :aria-label="t('Sales period')">
						<button
							v-for="item in periods"
							:key="item.key"
							:aria-pressed="period === item.key"
							:class="{ selected: period === item.key }"
							@click="period = item.key"
						>
							{{ t(item.label) }}
						</button>
					</div>
					<MobileOutlet v-if="hasOutletFilter" v-model="outlet" />
					<p v-if="error" class="m-error" role="alert">{{ error }}</p>
					<template v-if="tab === 'overview'">
						<div class="m-sales-panel" :aria-busy="refreshing">
							<div class="m-sales-primary">
								<MobileIcon name="receipt" :size="45" />
								<div>
									<h2>{{ t('Net sales') }}</h2>
									<div class="m-sales-value" dir="auto">
										{{ metric('net_sales') }}
									</div>
								</div>
							</div>
							<div class="m-sales-secondary">
								<div>
									<span>{{ t('Invoices') }}</span
									><strong>{{ metric('invoices', false) }}</strong>
								</div>
								<div>
									<span>{{ t('Average basket') }}</span
									><strong dir="auto">{{ metric('avg_basket') }}</strong>
								</div>
							</div>
						</div>
						<div class="m-trend-panel">
							<div class="m-trend-heading">
								<h2>{{ t('Sales trend') }}</h2>
								<span
									:title="
										t(
											live
												? 'Live updates connected'
												: 'Figures refresh while this app is open.',
										)
									"
									>{{ refreshing ? t('Refreshing…') : updatedLabel }}</span
								>
							</div>
							<MobileTrend :result="results.sales_by_day" />
							<p v-if="widgetErrors.sales_by_day" class="m-error">
								{{ widgetErrors.sales_by_day }}
							</p>
						</div>
						<button class="m-returns" @click="pick('reports')">
							<MobileIcon name="return" /><strong>{{ t('Returns') }}</strong
							><span dir="auto">{{ metric('returns') }}</span
							><MobileIcon name="chevron" :size="19" />
						</button>
						<p
							v-if="Object.keys(widgetErrors).some((key) => key !== 'sales_by_day')"
							class="m-notice"
						>
							{{
								t(
									'Some figures could not be loaded with your current permissions. Open Reports for details.',
								)
							}}
						</p>
					</template>
					<template v-else>
						<div class="m-reports-grid">
							<div
								v-for="(widget, i) in reportWidgets"
								:key="widget.widget_id"
								class="m-report-widget"
							>
								<TableWidget
									v-if="widget.widget_type === 'Table'"
									:slug="dashboard.slug"
									:widget="widget"
									:filter-values="filters"
									:refresh-key="refreshKey"
									:index="i"
								/><NumberCard
									v-else-if="widget.widget_type === 'Number Card'"
									:slug="dashboard.slug"
									:widget="widget"
									:filter-values="filters"
									:refresh-key="refreshKey"
									:index="i"
								/><ChartWidget
									v-else
									:slug="dashboard.slug"
									:widget="widget"
									:filter-values="filters"
									:refresh-key="refreshKey"
									:index="i"
								/>
							</div>
						</div>
						<router-link
							:to="{ name: 'DashboardView', params: { slug: dashboard.slug } }"
							class="m-outline m-full"
							>{{ t('Open full dashboard') }}</router-link
						>
					</template>
				</template>
			</section>
			<MobileNotifications
				v-show="tab === 'alerts'"
				:ready="ready"
				:active="tab === 'alerts'"
			/>
			<MobileSettings v-show="tab === 'settings'" :ready="ready" />
		</main>
		<nav class="m-bottom-nav" :aria-label="t('Mobile navigation')">
			<button
				v-for="item in tabs"
				:key="item.key"
				:class="{ selected: tab === item.key }"
				:aria-current="tab === item.key ? 'page' : undefined"
				@click="pick(item.key)"
			>
				<MobileIcon :name="item.icon" :size="24" /><span>{{ t(item.label) }}</span>
			</button>
		</nav>
	</div>
</template>
<script setup>
import { computed, defineAsyncComponent, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MobileIcon from '@/components/mobile/MobileIcon.vue'
import MobileTrend from '@/components/mobile/MobileTrend.vue'
import MobileOutlet from '@/components/mobile/MobileOutlet.vue'
import MobileNotifications from '@/components/mobile/MobileNotifications.vue'
import MobileSettings from '@/components/mobile/MobileSettings.vue'
import { mobileApi } from '@/lib/mobileApi'
import { numericValue, pushWorker } from '@/lib/mobileApp'
import { appIcon, brand } from '@/lib/brand'
import { presetRange, ymd } from '@/lib/dateRanges'
import { connectionState, CONNECTION_MESSAGES, SETUP_METHOD } from '@/lib/posConnection'
import { getSocket } from '@/lib/socket'
import { isStatic } from '@/lib/widgetTypes'
import { t, lang } from '@/lib/i18n'
import '@/components/mobile/mobile.css'

// The home screen stays light; ECharts and detailed reports load on demand.
const ChartWidget = defineAsyncComponent(() => import('@/components/widgets/ChartWidget.vue'))
const NumberCard = defineAsyncComponent(() => import('@/components/widgets/NumberCard.vue'))
const TableWidget = defineAsyncComponent(() => import('@/components/widgets/TableWidget.vue'))

const route = useRoute(),
	router = useRouter()
const tabs = [
	{ key: 'overview', label: 'Overview', icon: 'chart' },
	{ key: 'reports', label: 'Reports', icon: 'reports' },
	{ key: 'alerts', label: 'Alerts', icon: 'bell' },
	{ key: 'settings', label: 'Settings', icon: 'settings' },
]
const periods = [
	{ key: 'today', label: 'Today' },
	{ key: 'last_7_days', label: '7 days' },
	{ key: 'this_month', label: 'Month' },
]
const tab = computed(() =>
	tabs.some((item) => item.key === route.query.tab) ? route.query.tab : 'overview',
)
const period = ref('today'),
	outlet = ref(''),
	context = ref(null),
	dashboard = ref(null),
	results = ref({}),
	widgetErrors = ref({})
const loading = ref(true),
	refreshing = ref(false),
	creating = ref(false),
	needsSignIn = ref(false),
	error = ref(''),
	refreshKey = ref(0),
	updated = ref(null)
const online = ref(navigator.onLine),
	live = ref(false),
	today = ref(ymd(new Date()))
const siteName = window.site_name || window.location.hostname
const state = computed(() => connectionState(context.value?.connection))
const ready = computed(() => state.value === 'ready' && Boolean(dashboard.value))
const connectionMessage = computed(() =>
	error.value && !context.value
		? ['Could not load your sales', 'Check your connection and try again.']
		: CONNECTION_MESSAGES[state.value] || CONNECTION_MESSAGES.loading,
)
const filters = computed(() => ({
	posting_date: presetRange(period.value),
	...(outlet.value ? { pos_profile: outlet.value } : {}),
}))
const hasOutletFilter = computed(() =>
	dashboard.value?.filters?.some((filter) => filter.name === 'pos_profile'),
)
const reportWidgets = computed(() =>
	(dashboard.value?.widgets || []).filter((widget) => !isStatic(widget.widget_type)),
)
const dateLabel = computed(() => {
	void today.value
	return new Date().toLocaleDateString(lang.value === 'ar' ? 'ar' : 'en', {
		weekday: 'short',
		day: 'numeric',
		month: 'short',
		year: 'numeric',
	})
})
const updatedLabel = computed(() =>
	updated.value
		? t(
				'Updated {0}',
				updated.value.toLocaleTimeString(lang.value === 'ar' ? 'ar' : 'en', {
					hour: '2-digit',
					minute: '2-digit',
				}),
			)
		: t('Waiting for sales'),
)
let socket,
	interval,
	debounce,
	sequence = 0,
	loadSequence = 0,
	alive = true
const subscribed = new Set()
function pick(next) {
	router.replace({ name: 'MobilePOS', query: next === 'overview' ? {} : { tab: next } })
	window.scrollTo({ top: 0, behavior: 'instant' })
}
function metric(id, money = true) {
	const value = numericValue(results.value[id])
	if (value === null) return '—'
	const number = Intl.NumberFormat(lang.value === 'ar' ? 'ar-u-nu-latn' : 'en', {
		maximumFractionDigits: money ? 2 : 0,
	}).format(value)
	return money && context.value?.currency ? `${context.value.currency} ${number}` : number
}
async function load() {
	const id = ++loadSequence
	loading.value = !dashboard.value
	needsSignIn.value = false
	error.value = ''
	try {
		const meta = await mobileApi('lumen_reports.mobile.get_context')
		if (!alive || id !== loadSequence) return
		context.value = meta
		if (connectionState(meta?.connection) !== 'ready') {
			sequence++
			dashboard.value = null
			results.value = {}
			return
		}
		const definition = await mobileApi('lumen_reports.api.get_dashboard', {
			slug: meta.connection.slug,
		})
		if (!alive || id !== loadSequence) return
		dashboard.value = definition
		subscribeRooms()
		await loadMetrics()
	} catch (e) {
		if (alive && id === loadSequence) {
			sequence++
			error.value = e.message
			needsSignIn.value = e.status === 401 || e.status === 403
			context.value = null
			dashboard.value = null
			results.value = {}
			refreshing.value = false
		}
	} finally {
		if (alive && id === loadSequence) loading.value = false
	}
}
async function loadMetrics() {
	if (!ready.value || !online.value) return
	const id = ++sequence
	refreshing.value = true
	const widgets = (dashboard.value.widgets || []).filter((widget) =>
		['net_sales', 'invoices', 'avg_basket', 'returns', 'sales_by_day'].includes(
			widget.widget_id,
		),
	)
	const next = {},
		errors = {}
	await Promise.all(
		widgets.map(async (widget) => {
			try {
				const relevant = Object.fromEntries(
					Object.entries(filters.value).filter(
						([key]) => key in (widget.linked_filters || {}),
					),
				)
				next[widget.widget_id] = await mobileApi('lumen_reports.api.run_widget', {
					slug: dashboard.value.slug,
					widget_id: widget.widget_id,
					filter_values: relevant,
				})
			} catch (e) {
				errors[widget.widget_id] = e.message
			}
		}),
	)
	if (!alive || id !== sequence) return
	results.value = next
	widgetErrors.value = errors
	refreshing.value = false
	refreshKey.value++
	if (widgets.length && Object.keys(next).length) updated.value = new Date()
}
async function setup() {
	creating.value = true
	error.value = ''
	try {
		const result = await mobileApi(SETUP_METHOD, { lang: lang.value }, 'POST')
		if (result?.status !== 'ready')
			throw new Error(
				result?.message || t('The dashboard could not be created. Please try again.'),
			)
		await load()
	} catch (e) {
		error.value = e.message
	} finally {
		creating.value = false
	}
}
function subscribeRooms() {
	if (!socket || !dashboard.value) return
	for (const widget of dashboard.value.widgets || [])
		for (const doctype of [widget.query?.doctype, widget.query?.parent_doctype].filter(
			Boolean,
		)) {
			if (!subscribed.has(doctype)) {
				socket.emit('doctype_subscribe', doctype)
				subscribed.add(doctype)
			}
		}
}
function onConnect() {
	live.value = true
	subscribed.clear()
	subscribeRooms()
	loadMetrics()
}
function onDisconnect() {
	live.value = false
}
function onInvalidate(message) {
	if (!message?.dashboards?.includes(dashboard.value?.slug)) return
	clearTimeout(debounce)
	debounce = setTimeout(loadMetrics, 800)
}
function onVisibility() {
	if (document.visibilityState === 'visible') {
		today.value = ymd(new Date())
		if (ready.value) loadMetrics()
		else load()
	}
}
function onNetwork() {
	online.value = navigator.onLine
	if (online.value) load()
}
watch([period, outlet], loadMetrics)
onMounted(() => {
	load()
	pushWorker().catch(() => {})
	socket = getSocket()
	live.value = socket.connected
	socket.on('connect', onConnect)
	socket.on('disconnect', onDisconnect)
	socket.on('lumen_reports:invalidate', onInvalidate)
	document.addEventListener('visibilitychange', onVisibility)
	window.addEventListener('online', onNetwork)
	window.addEventListener('offline', onNetwork)
	interval = setInterval(() => {
		if (document.visibilityState === 'visible' && navigator.onLine) {
			today.value = ymd(new Date())
			loadMetrics()
		}
	}, 45000)
})
onBeforeUnmount(() => {
	alive = false
	sequence++
	loadSequence++
	clearInterval(interval)
	clearTimeout(debounce)
	socket?.off('connect', onConnect)
	socket?.off('disconnect', onDisconnect)
	socket?.off('lumen_reports:invalidate', onInvalidate)
	for (const doctype of subscribed) socket?.emit('doctype_unsubscribe', doctype)
	document.removeEventListener('visibilitychange', onVisibility)
	window.removeEventListener('online', onNetwork)
	window.removeEventListener('offline', onNetwork)
})
</script>
