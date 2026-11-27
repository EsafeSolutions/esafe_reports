<template>
	<section class="m-returns-detail" aria-labelledby="return-invoices-title" :aria-busy="loading">
		<div class="m-return-heading"><h2 id="return-invoices-title">{{ t('Return invoices') }}</h2><span v-if="result">{{ t('{0} returns', number(result.total)) }}</span></div>
		<p class="m-notice">{{ t('Submitted returns for your selected dates and outlet.') }}</p>
		<p v-if="error" class="m-error" role="alert">{{ error }}</p>
		<div v-if="loading" class="m-loading" role="status">{{ t('Loading returns…') }}</div>
		<template v-else-if="result">
			<div v-if="!result.rows.length" class="m-empty-returns"><MobileIcon name="return" :size="32" /><h2>{{ t('No returns in this period') }}</h2><p>{{ t('Choose different dates or another outlet to view returns.') }}</p></div>
			<div v-else class="m-return-invoices">
				<article v-for="invoice in result.rows" :key="invoice.name" class="m-return-invoice">
					<div class="m-return-invoice-top"><strong dir="auto">{{ invoice.name }}</strong><strong class="m-return-amount" dir="auto">{{ invoice.currency }} {{ number(invoice.grand_total) }}</strong></div>
					<p v-if="invoice.customer" dir="auto">{{ invoice.customer }}</p>
					<div class="m-return-meta"><time>{{ formatMobileRange([invoice.posting_date, invoice.posting_date], lang) }}</time><span v-if="invoice.pos_profile" dir="auto">{{ invoice.pos_profile }}</span></div>
					<small v-if="invoice.return_against" dir="auto">{{ t('Against invoice {0}', invoice.return_against) }}</small>
				</article>
			</div>
			<div v-if="result.total > result.limit || start > 0" class="m-return-pagination"><button class="m-outline" :disabled="start === 0 || loading" @click="page(-1)">{{ t('Previous') }}</button><span>{{ t('{0}–{1} of {2}', number(result.rows.length ? start + 1 : 0), number(start + result.rows.length), number(result.total)) }}</span><button class="m-outline" :disabled="start + result.rows.length >= result.total || loading" @click="page(1)">{{ t('Next') }}</button></div>
		</template>
		<button v-if="error" class="m-outline m-full" @click="load">{{ t('Try again') }}</button>
	</section>
</template>
<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import MobileIcon from './MobileIcon.vue'
import { mobileApi } from '@/lib/mobileApi'
import { formatMobileRange, validDateRange } from '@/lib/mobileDateRange'
import { t, lang } from '@/lib/i18n'

const props = defineProps({ range: { type: Array, required: true }, outlet: { type: String, default: '' }, refreshKey: { type: Number, default: 0 }, online: { type: Boolean, default: true } })
const result = ref(null), loading = ref(false), error = ref(''), start = ref(0)
let sequence = 0
const number = value => Intl.NumberFormat('en', { maximumFractionDigits: 2 }).format(value)
async function load() {
	const id = ++sequence
	loading.value = true
	error.value = ''
	result.value = null
	try {
		if (!props.online) throw new Error(t("You're offline. Connect to refresh your sales."))
		if (!validDateRange(props.range)) throw new Error(t('Choose a valid start and end date.'))
		const data = await mobileApi('lumen_reports.mobile.get_returns', { from_date: props.range[0], to_date: props.range[1], ...(props.outlet ? { pos_profile: props.outlet } : {}), start: start.value })
		if (id === sequence) result.value = data
	} catch (e) { if (id === sequence) error.value = e.message }
	finally { if (id === sequence) loading.value = false }
}
function page(direction) { start.value = Math.max(0, start.value + direction * (result.value?.limit || 20)); load() }
watch(() => [props.range, props.outlet, props.refreshKey, props.online], () => { start.value = 0; load() }, { deep: true, immediate: true })
onBeforeUnmount(() => { sequence++ })
</script>
