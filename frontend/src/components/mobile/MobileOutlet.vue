<template>
	<button class="m-outlet" type="button" @click="open">
		<span>{{ modelValue || t('All outlets') }}</span
		><MobileIcon name="down" :size="19" />
	</button>
	<dialog ref="dialog" class="m-dialog" @click="backdrop" @close="finish">
		<div class="m-dialog-title">
			<h2>{{ t('Choose outlet') }}</h2>
			<button class="m-icon-button" :aria-label="t('Close')" @click="dialog.close()">
				<MobileIcon name="close" />
			</button>
		</div>
		<label class="sr-only" for="outlet-search">{{ t('Search outlets') }}</label>
		<input
			id="outlet-search"
			v-model="search"
			class="m-search"
			type="search"
			:placeholder="t('Search outlets')"
			autofocus
		/>
		<div class="m-outlet-options">
			<button @click="choose('')">
				{{ t('All outlets') }}<MobileIcon v-if="!modelValue" name="check" :size="20" />
			</button>
			<p v-if="loading" class="m-muted">{{ t('Searching…') }}</p>
			<button v-for="option in options" :key="option.value" @click="choose(option.value)">
				{{ option.label
				}}<MobileIcon v-if="modelValue === option.value" name="check" :size="20" />
			</button>
			<p v-if="!loading && !options.length" class="m-muted">
				{{ error || t('No matches') }}
			</p>
		</div>
	</dialog>
</template>
<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import MobileIcon from './MobileIcon.vue'
import { mobileApi } from '@/lib/mobileApi'
import { t } from '@/lib/i18n'
defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])
const dialog = ref(null),
	search = ref(''),
	options = ref([]),
	loading = ref(false),
	error = ref('')
let timer,
	sequence = 0
async function load() {
	const id = ++sequence
	loading.value = true
	error.value = ''
	try {
		const result = await mobileApi('lumen_reports.api.get_link_options', {
			link_doctype: 'POS Profile',
			txt: search.value,
		})
		if (id === sequence) options.value = result || []
	} catch (e) {
		if (id === sequence) error.value = e.message
	} finally {
		if (id === sequence) loading.value = false
	}
}
function open() {
	dialog.value.showModal()
	load()
}
function choose(value) {
	emit('update:modelValue', value)
	dialog.value.close()
}
function finish() {
	search.value = ''
	options.value = []
}
function backdrop(event) {
	if (event.target === dialog.value) {
		const box = dialog.value.getBoundingClientRect()
		if (
			event.clientX < box.left ||
			event.clientX > box.right ||
			event.clientY < box.top ||
			event.clientY > box.bottom
		)
			dialog.value.close()
	}
}
watch(search, () => {
	clearTimeout(timer)
	timer = setTimeout(load, 250)
})
onBeforeUnmount(() => {
	clearTimeout(timer)
	sequence++
})
</script>
