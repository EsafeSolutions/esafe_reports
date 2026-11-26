import { reactive } from 'vue'

export const installState = reactive({ prompt: null, installed: false, help: false })
let initialized = false
let workerPromise

export function deviceEnvironment(nav = navigator, win = window) {
	return {
		ios:
			/iPad|iPhone|iPod/.test(nav.userAgent) ||
			(nav.platform === 'MacIntel' && nav.maxTouchPoints > 1),
		standalone: Boolean(
			win.matchMedia('(display-mode: standalone)').matches || nav.standalone,
		),
		secure: win.isSecureContext,
		push: 'serviceWorker' in nav && 'PushManager' in win && 'Notification' in win,
	}
}

export function initializeInstall() {
	if (initialized) return
	initialized = true
	installState.installed = deviceEnvironment().standalone
	window.addEventListener('beforeinstallprompt', (event) => {
		event.preventDefault()
		installState.prompt = event
	})
	window.addEventListener('appinstalled', () => {
		installState.installed = true
		installState.prompt = null
	})
}

export async function installApp() {
	if (!installState.prompt) {
		installState.help = true
		return 'manual'
	}
	const prompt = installState.prompt
	installState.prompt = null
	await prompt.prompt()
	const choice = await prompt.userChoice
	return choice.outcome
}

export function pushWorker() {
	if (workerPromise) return workerPromise
	workerPromise = (async () => {
		if (!deviceEnvironment().secure || !('serviceWorker' in navigator))
			throw new Error('Open this app over HTTPS to install it and enable notifications.')
		const registration = await navigator.serviceWorker.register(
			'/api/method/lumen_reports.pwa.service_worker',
			{
				scope: '/esafe-report/',
				updateViaCache: 'none',
			},
		)
		if (registration.active) return registration
		const worker = registration.installing || registration.waiting
		await new Promise((resolve, reject) => {
			const timer = setTimeout(
				() => reject(new Error('App setup took too long. Please try again.')),
				12000,
			)
			const changed = () => {
				if (worker?.state === 'activated') {
					clearTimeout(timer)
					worker.removeEventListener('statechange', changed)
					resolve()
				} else if (worker?.state === 'redundant') {
					clearTimeout(timer)
					worker.removeEventListener('statechange', changed)
					reject(new Error('App setup failed. Please try again.'))
				}
			}
			worker?.addEventListener('statechange', changed)
			changed()
		})
		return registration
	})().catch((error) => {
		workerPromise = null
		throw error
	})
	return workerPromise
}

export function applicationServerKey(value) {
	const padded = value + '='.repeat((4 - (value.length % 4)) % 4)
	return Uint8Array.from(atob(padded.replace(/-/g, '+').replace(/_/g, '/')), (c) =>
		c.charCodeAt(0),
	)
}

export function numericValue(result) {
	return result?.result_type === 'number' &&
		typeof result.value === 'number' &&
		Number.isFinite(result.value)
		? result.value
		: null
}
