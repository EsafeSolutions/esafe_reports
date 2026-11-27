<template>
	<div class="m-period" role="group" :aria-label="t('Sales period')">
		<button v-for="item in periods" :key="item.key" type="button" :aria-pressed="modelValue === item.key" :class="{ selected: modelValue === item.key }" @click="pick(item.key)">{{ t(item.label) }}</button>
	</div>
	<button v-if="modelValue === 'custom'" class="m-custom-range" type="button" :aria-label="t('Edit custom date range')" @click="open"><MobileIcon name="calendar" :size="18"/><span>{{ formatMobileRange(customRange, lang) }}</span><MobileIcon name="down" :size="17" /></button>
	<dialog ref="dialog" class="m-dialog" aria-labelledby="mobile-date-title" @click="backdrop" @close="error = ''">
		<form novalidate @submit.prevent="apply">
			<div class="m-dialog-title"><h2 id="mobile-date-title">{{ t('Custom date range') }}</h2><button class="m-icon-button" type="button" :aria-label="t('Close')" @click="dialog.close()"><MobileIcon name="close" /></button></div>
			<div class="m-date-fields">
				<label><span>{{ t('Start date') }}</span><input v-model="draft[0]" type="date" :aria-label="t('Start date')" autofocus @input="error = ''" /></label>
				<label><span>{{ t('End date') }}</span><input v-model="draft[1]" type="date" :aria-label="t('End date')" @input="error = ''" /></label>
			</div>
			<p v-if="error" class="m-error" role="alert">{{ t(error) }}</p>
			<div class="m-date-actions"><button class="m-outline" type="button" @click="dialog.close()">{{ t('Cancel') }}</button><button class="m-primary" type="submit">{{ t('Apply dates') }}</button></div>
		</form>
	</dialog>
</template>
<script setup>
import { ref } from 'vue'
import MobileIcon from './MobileIcon.vue'
import { presetRange } from '@/lib/dateRanges'
import { validDateRange, formatMobileRange } from '@/lib/mobileDateRange'
import { t, lang } from '@/lib/i18n'

const props = defineProps({ modelValue: { type: String, default: 'today' }, customRange: { type: Array, default: () => [] } })
const emit = defineEmits(['update:modelValue', 'update:customRange'])
const periods = [{ key: 'today', label: 'Today' }, { key: 'last_7_days', label: '7 days' }, { key: 'this_month', label: 'Month' }, { key: 'custom', label: 'Custom' }]
const dialog = ref(null), draft = ref(['', '']), error = ref('')
function pick(key) {
	if (key === 'custom') open()
	else emit('update:modelValue', key)
}
function open() {
	draft.value = [...(validDateRange(props.customRange) ? props.customRange : presetRange(props.modelValue) || presetRange('today'))]
	error.value = ''
	dialog.value.showModal()
}
function apply() {
	if (!validDateRange(draft.value)) {
		error.value = !draft.value[0] || !draft.value[1] ? 'Choose a start and end date.' : 'The end date must be on or after the start date.'
		return
	}
	emit('update:customRange', [...draft.value])
	emit('update:modelValue', 'custom')
	dialog.value.close()
}
function backdrop(event) {
	if (event.target !== dialog.value) return
	const box = dialog.value.getBoundingClientRect()
	if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.value.close()
}
</script>
