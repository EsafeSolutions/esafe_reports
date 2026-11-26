<template>
	<section class="m-section" aria-labelledby="settings-heading">
		<h1 id="settings-heading">{{ t('App settings') }}</h1>
		<div class="m-feature-panel m-install-panel">
			<img :src="appIcon" width="62" height="62" alt="" />
			<div>
				<h2>
					{{
						installState.installed
							? t('Esafe BLABS is installed')
							: t('Install Esafe BLABS')
					}}
				</h2>
				<p>{{ t('Your sales. One tap away.') }}</p>
				<button v-if="!installState.installed" class="m-primary" @click="install">
					{{ t('Install app') }}
				</button>
				<span v-else class="m-installed"
					><MobileIcon name="check" :size="18" />{{
						t('Ready on your Home Screen')
					}}</span
				>
			</div>
		</div>
		<div
			ref="instructions"
			class="m-rows m-install-instructions"
			:class="{ highlighted: installState.help }"
			tabindex="-1"
		>
			<div class="m-setting-row">
				<MobileIcon name="download" :size="28" />
				<div class="m-row-copy">
					<strong>{{ t('Android – Install') }}</strong>
					<p>
						{{
							t(
								'Tap Install app, or open your browser menu and choose Add to Home screen.',
							)
						}}
					</p>
				</div>
			</div>
			<div class="m-setting-row">
				<MobileIcon name="share" :size="28" />
				<div class="m-row-copy">
					<strong>{{ t('iPhone – Install') }}</strong>
					<ol>
						<li>{{ t('Open this page in Safari.') }}</li>
						<li>{{ t('Tap Share, then Add to Home Screen.') }}</li>
						<li>{{ t('Tap Add, then open the app from your Home Screen.') }}</li>
					</ol>
					<p>
						{{
							t('For notifications, open the Home Screen app on iOS 16.4 or later.')
						}}
					</p>
				</div>
			</div>
		</div>
		<p v-if="installNotice" class="m-notice" role="status">{{ t(installNotice) }}</p>
		<div class="m-rows m-settings-links">
			<button class="m-setting-row" @click="setLang(lang === 'ar' ? 'en' : 'ar')">
				<MobileIcon name="globe" /><strong>{{ t('Language') }}</strong
				><span class="m-row-value">{{ lang === 'ar' ? 'العربية' : 'English' }}</span
				><MobileIcon name="chevron" :size="18" />
			</button>
			<button class="m-setting-row" @click="toggleTheme">
				<MobileIcon name="appearance" /><strong>{{ t('Appearance') }}</strong
				><span class="m-row-value">{{ t(theme === 'dark' ? 'Dark' : 'Light') }}</span
				><MobileIcon name="chevron" :size="18" />
			</button>
			<router-link to="/pos" class="m-setting-row"
				><MobileIcon name="store" /><strong>{{ t('POS connection') }}</strong
				><span class="m-row-value m-connection-state" :class="{ connected: ready }">{{
					t(ready ? 'Connected' : 'Needs attention')
				}}</span
				><MobileIcon name="chevron" :size="18"
			/></router-link>
			<router-link to="/" class="m-setting-row"
				><MobileIcon name="grid" /><strong>{{ t('View all dashboards') }}</strong
				><span class="m-row-value"></span><MobileIcon name="chevron" :size="18"
			/></router-link>
		</div>
	</section>
</template>
<script setup>
import { ref, nextTick } from 'vue'
import MobileIcon from './MobileIcon.vue'
import { appIcon } from '@/lib/brand'
import { installState, installApp } from '@/lib/mobileApp'
import { t, lang, setLang } from '@/lib/i18n'
import { theme, toggleTheme } from '@/lib/theme'
defineProps({ ready: Boolean })
const instructions = ref(null),
	installNotice = ref('')
async function install() {
	try {
		const result = await installApp()
		if (result === 'manual') {
			await nextTick()
			instructions.value.scrollIntoView({ behavior: 'smooth', block: 'center' })
			instructions.value.focus({ preventScroll: true })
			installNotice.value = 'Follow the steps above to add Esafe BLABS to your Home Screen.'
		} else if (result === 'dismissed')
			installNotice.value = 'You can install the app whenever you are ready.'
	} catch {
		installNotice.value =
			'Use your browser menu to install the app, or follow the steps above.'
	}
}
</script>
