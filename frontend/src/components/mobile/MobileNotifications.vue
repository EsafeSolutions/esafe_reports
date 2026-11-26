<template>
	<section class="m-section" aria-labelledby="alerts-heading">
		<h1 id="alerts-heading">{{ t('Alerts') }}</h1>
		<p class="m-intro">{{ t('Sales and daily summaries.') }}</p>
		<div class="m-feature-panel notification-banner">
			<MobileIcon name="bell" :size="45" />
			<div>
				<h2>{{ enabled ? t('Notifications are on') : t('Set up sale alerts') }}</h2>
				<p>
					{{
						enabled
							? t(
									'New sales, returns and your daily summary can reach this device, even when the app is closed.',
								)
							: t(
									'Get notified about new sales, returns and daily summaries on this device.',
								)
					}}
				</p>
				<button
					v-if="!enabled"
					class="m-primary"
					:disabled="busy || loading || !ready"
					@click="enable"
				>
					{{ busy ? t('Enabling…') : t('Enable notifications') }}
				</button>
				<button v-else class="m-outline" :disabled="busy" @click="test">
					{{ t('Send test notification') }}
				</button>
			</div>
		</div>
		<p v-if="!ready" class="m-notice">
			{{ t('Connect your sales dashboard before enabling notifications.') }}
			<router-link to="/pos">{{ t('Check POS connection') }}</router-link>
		</p>
		<p v-else-if="environment.ios && !environment.standalone" class="m-notice">
			{{
				t(
					'On iPhone, add this app to your Home Screen and open it there before enabling notifications.',
				)
			}}
		</p>
		<p v-else-if="!environment.push || !environment.secure" class="m-notice">
			{{ t('Use a browser with Web Push support over HTTPS to receive notifications.') }}
		</p>
		<p v-else-if="permission === 'denied'" class="m-notice">
			{{
				t(
					'Notifications are blocked. Allow them in your device or browser settings, then try again.',
				)
			}}
		</p>
		<p v-if="error" class="m-error" role="alert">{{ error }}</p>
		<p v-if="notice" class="m-notice" role="status">{{ notice }}</p>

		<h2 class="m-subheading">{{ t('Notifications on this device') }}</h2>
		<div class="m-rows">
			<label class="m-setting-row">
				<MobileIcon name="store" /><span class="m-row-copy"
					><strong>{{ t('New sales and returns') }}</strong
					><small>{{
						t('Get an alert when a sale or return is recorded.')
					}}</small></span
				>
				<input
					v-model="preferences.sales_alerts"
					class="m-toggle"
					role="switch"
					type="checkbox"
					:aria-label="t('New sales and returns')"
					:disabled="!enabled || busy"
					@change="save"
				/>
			</label>
			<label class="m-setting-row">
				<MobileIcon name="calendar" /><span class="m-row-copy"
					><strong>{{ t('Daily sales summary') }}</strong
					><small>{{ t('A daily summary of your invoices and returns.') }}</small></span
				>
				<input
					v-model="preferences.daily_summary"
					class="m-toggle"
					role="switch"
					type="checkbox"
					:aria-label="t('Daily sales summary')"
					:disabled="!enabled || busy"
					@change="save"
				/>
			</label>
			<label class="m-setting-row">
				<MobileIcon name="clock" /><span class="m-row-copy"
					><strong>{{ t('Daily summary time') }}</strong
					><small>{{ preferences.timezone }}</small></span
				>
				<input
					v-model="preferences.summary_time"
					class="m-time"
					type="time"
					:aria-label="t('Daily summary time')"
					:disabled="!enabled || !preferences.daily_summary || busy"
					@change="save"
				/>
			</label>
			<button
				v-if="registered"
				class="m-setting-row m-danger-link"
				:disabled="busy"
				@click="disable"
			>
				<MobileIcon name="bell" /><span>{{
					t('Turn off notifications on this device')
				}}</span>
			</button>
		</div>
		<div v-if="feed.length" class="m-feed" aria-label="Notifications">
			<article v-for="item in feed" :key="item.name" class="m-feed-item">
				<MobileIcon
					:name="
						item.kind === 'Summary'
							? 'calendar'
							: item.kind === 'Return'
								? 'return'
								: 'bell'
					"
				/>
				<div>
					<h3>{{ item.title }}</h3>
					<p>{{ item.body }}</p>
					<time>{{ displayDate(item.creation) }}</time>
				</div>
			</article>
		</div>
		<div v-else class="m-empty-feed">
			<MobileIcon name="bell" :size="54" />
			<h2>{{ t("You're all caught up") }}</h2>
			<p>{{ t('Your sale alerts and daily summaries appear here.') }}</p>
			<button v-if="enabled" class="m-text-button" @click="loadFeed">
				{{ t('Refresh alerts') }}
			</button>
		</div>
	</section>
</template>
<script setup>
import { reactive, ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import MobileIcon from './MobileIcon.vue'
import { mobileApi } from '@/lib/mobileApi'
import { applicationServerKey, deviceEnvironment, pushWorker } from '@/lib/mobileApp'
import { lang, t } from '@/lib/i18n'

const props = defineProps({ ready: Boolean, active: Boolean })
const environment = reactive(deviceEnvironment())
const permission = ref('Notification' in window ? Notification.permission : 'unsupported')
const subscription = ref(null),
	device = ref(null),
	settings = ref(null),
	feed = ref([])
const busy = ref(false),
	loading = ref(true),
	error = ref(''),
	notice = ref('')
const preferences = reactive({
	sales_alerts: true,
	daily_summary: true,
	summary_time: '20:00',
	timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Colombo',
})
const registered = computed(() =>
	Boolean(subscription.value && device.value?.enabled && permission.value === 'granted'),
)
const enabled = computed(() => registered.value && props.ready)
let alive = true

function adopt(next) {
	device.value = next
	if (next) Object.assign(preferences, next, { summary_time: next.summary_time.slice(0, 5) })
}
async function loadFeed() {
	if (!props.ready) return
	try {
		const rows = await mobileApi('lumen_reports.notifications.get_feed')
		if (alive) feed.value = rows || []
	} catch (e) {
		if (alive) error.value = e.message
	}
}
async function load() {
	if (!props.ready) {
		loading.value = false
		return
	}
	loading.value = true
	try {
		Object.assign(environment, deviceEnvironment())
		permission.value = 'Notification' in window ? Notification.permission : 'unsupported'
		// Registration requires no permission prompt; asking to receive push is explicit.
		if (environment.secure && 'serviceWorker' in navigator) {
			const worker = await pushWorker()
			if (environment.push) subscription.value = await worker.pushManager.getSubscription()
		}
		settings.value = await mobileApi('lumen_reports.notifications.get_settings', {
			endpoint: subscription.value?.endpoint,
		})
		if (!alive) return
		adopt(settings.value?.device)
		if (props.active) await loadFeed()
	} catch (e) {
		if (alive) error.value = e.message
	} finally {
		if (alive) loading.value = false
	}
}
async function enable() {
	error.value = ''
	notice.value = ''
	if (environment.ios && !environment.standalone) {
		error.value = t(
			'Add this app to your Home Screen, open it there, then enable notifications.',
		)
		return
	}
	if (!environment.push || !environment.secure) {
		error.value = t('Use a browser with Web Push support over HTTPS to receive notifications.')
		return
	}
	if (!settings.value?.configured) {
		error.value = t(
			'Notifications are not configured on this site yet. Ask your administrator to migrate the reports app.',
		)
		return
	}
	busy.value = true
	let created = null
	try {
		// Keep the permission request directly inside the tap, before any network work.
		permission.value = await Notification.requestPermission()
		if (permission.value !== 'granted')
			throw new Error(t('Allow notifications on this device to receive sales alerts.'))
		const worker = await pushWorker()
		subscription.value = await worker.pushManager.getSubscription()
		if (subscription.value && device.value?.enabled === false) {
			await subscription.value.unsubscribe()
			subscription.value = null
		}
		if (!subscription.value) {
			created = await worker.pushManager.subscribe({
				userVisibleOnly: true,
				applicationServerKey: applicationServerKey(settings.value.public_key),
			})
			subscription.value = created
		}
		adopt(
			await mobileApi(
				'lumen_reports.notifications.subscribe',
				{
					subscription: subscription.value.toJSON(),
					preferences: { ...preferences, language: lang.value },
				},
				'POST',
			),
		)
		notice.value = t('Notifications enabled. You can send a test to check this device.')
		await loadFeed()
	} catch (e) {
		error.value = e.message
		if (created) {
			await created.unsubscribe().catch(() => {})
			subscription.value = null
		}
	} finally {
		busy.value = false
	}
}
async function save() {
	if (!enabled.value) return
	busy.value = true
	error.value = ''
	notice.value = ''
	try {
		adopt(
			await mobileApi(
				'lumen_reports.notifications.subscribe',
				{
					subscription: subscription.value.toJSON(),
					preferences: { ...preferences, language: lang.value },
				},
				'POST',
			),
		)
		notice.value = t('Notification preferences saved.')
	} catch (e) {
		error.value = e.message
		adopt(device.value)
	} finally {
		busy.value = false
	}
}
async function disable() {
	if (!subscription.value) return
	busy.value = true
	error.value = ''
	notice.value = ''
	try {
		await mobileApi(
			'lumen_reports.notifications.unsubscribe',
			{ endpoint: subscription.value.endpoint },
			'POST',
		)
		await subscription.value.unsubscribe()
		subscription.value = null
		device.value = null
		notice.value = t('Notifications turned off on this device.')
	} catch (e) {
		error.value = e.message
	} finally {
		busy.value = false
	}
}
async function test() {
	busy.value = true
	error.value = ''
	notice.value = ''
	try {
		await mobileApi(
			'lumen_reports.notifications.send_test',
			{ endpoint: subscription.value.endpoint },
			'POST',
		)
		notice.value = t('Test notification queued. Check your device notifications.')
	} catch (e) {
		error.value = e.message
	} finally {
		busy.value = false
	}
}
function displayDate(value) {
	return new Date(value.replace(' ', 'T')).toLocaleString(lang.value === 'ar' ? 'ar' : 'en', {
		dateStyle: 'medium',
		timeStyle: 'short',
	})
}
watch(() => props.ready, load)
watch(
	() => props.active,
	(active) => {
		if (active) {
			loadFeed()
			navigator.clearAppBadge?.().catch(() => {})
		}
	},
)
onMounted(() => {
	load()
	window.addEventListener('focus', load)
})
onBeforeUnmount(() => {
	alive = false
	window.removeEventListener('focus', load)
})
</script>
