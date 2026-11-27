<template>
  <div class="m-category-sales" :aria-busy="loading">
    <div v-if="category || mode === 'product'" class="m-sales-breadcrumb"><button class="m-text-button" @click="reset"><MobileIcon name="back" :size="18" />{{ t('All categories') }}</button><strong>{{ category || t('Product sales') }}</strong></div>
    <p class="m-notice">{{ t('Submitted POS sales, net of returns, for products you can access. Amounts exclude taxes.') }}</p>
    <p v-if="error" class="m-error" role="alert">{{ error }}</p>
    <p v-if="result?.partial" class="m-error" role="alert">{{ t('Partial results. Narrow the date range or category to see complete totals.') }}</p>
    <div v-if="loading" class="m-loading" role="status">{{ t('Loading sales…') }}</div>
    <template v-else-if="result">
      <div class="m-category-summary"><div><span>{{ t(result.partial ? 'Net sales · partial' : 'Net sales') }}</span><strong dir="auto">{{ result.currency }} {{ number(result.net_sales) }}</strong></div><div><span>{{ t(mode === 'category' ? 'Categories' : 'Products') }}</span><strong>{{ result.rows.length }}</strong></div></div>
      <div v-if="!result.rows.length" class="m-catalog-empty"><MobileIcon name="chart" :size="40" /><h2>{{ t('No sales in this period') }}</h2><p>{{ t('Choose different dates or another outlet.') }}</p></div>
      <div v-else class="m-category-list">
        <button v-for="row in visibleRows" :key="row.key" class="m-category-row" :disabled="mode === 'product' || !row.key" @click="drill(row)">
          <span class="m-category-top"><strong>{{ row.label }}</strong><strong dir="auto">{{ result.currency }} {{ number(row.amount) }}</strong><MobileIcon v-if="mode === 'category'" name="chevron" :size="18" /></span>
          <span v-if="mode === 'product'" class="m-notice">{{ row.key }} · {{ number(row.quantity) }} {{ row.uom }}</span>
          <span class="m-category-bar" aria-hidden="true"><i :style="{ width: barWidth(row.amount) + '%' }" :class="{ negative: row.amount < 0 }"></i></span>
        </button>
      </div>
      <button v-if="visibleRows.length < result.rows.length" class="m-outline m-full" @click="shown += 30">{{ t('Show more') }}</button>
      <button v-if="mode === 'category'" class="m-product-sales-link" @click="mode = 'product'"><span><strong>{{ t('Product sales') }}</strong><small>{{ t('Tap a category to view its products.') }}</small></span><MobileIcon name="chevron" /></button>
      <button class="m-text-button m-export" :disabled="!result.rows.length" @click="exportRows"><MobileIcon name="download" :size="18" />{{ t('Export sales') }}</button>
    </template>
    <button v-if="error" class="m-outline m-full" @click="load">{{ t('Try again') }}</button>
  </div>
</template>
<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import MobileIcon from './MobileIcon.vue'
import { mobileApi } from '@/lib/mobileApi'
import { exportMobileCsv, number } from '@/lib/mobileCatalog'
import { validDateRange } from '@/lib/mobileDateRange'
import { t } from '@/lib/i18n'

const props = defineProps({ range: { type: Array, required: true }, outlet: String, refreshKey: Number, online: { type: Boolean, default: true } })
const mode = ref('category'), category = ref(''), result = ref(null), loading = ref(false), error = ref(''), shown = ref(30)
const visibleRows = computed(() => (result.value?.rows || []).slice(0, shown.value))
const maxAmount = computed(() => Math.max(1, ...(result.value?.rows || []).map(row => Math.abs(row.amount))))
let sequence = 0
function barWidth(amount) { return Math.max(0, Math.min(100, Math.abs(amount) / maxAmount.value * 100)) }
function drill(row) { if (row.key) { category.value = row.key; mode.value = 'product' } }
function reset() { category.value = ''; mode.value = 'category' }
async function load() {
  const id = ++sequence
  loading.value = true; error.value = ''; result.value = null; shown.value = 30
  try {
    if (!props.online) throw new Error(t('Connect to the internet to load current sales.'))
    if (!validDateRange(props.range)) throw new Error(t('Choose a valid start and end date.'))
    const data = await mobileApi('lumen_reports.mobile_catalog.get_sales', { from_date: props.range[0], to_date: props.range[1], pos_profile: props.outlet || '', category: category.value, group_by: mode.value })
    if (id === sequence) result.value = data
  } catch (e) { if (id === sequence) error.value = e.message }
  finally { if (id === sequence) loading.value = false }
}
async function exportRows() {
  try { await exportMobileCsv('esafe-sales.csv', [['From', 'To', 'Outlet', 'Category', 'Key', 'Name', 'Net sales', 'Currency', 'Stock quantity', 'UOM', 'Partial'], ...result.value.rows.map(row => [props.range[0], props.range[1], props.outlet || 'All permitted outlets', category.value, row.key, row.label, row.amount, result.value.currency, mode.value === 'product' ? row.quantity : '', row.uom, result.value.partial])]) }
  catch { error.value = t('Could not export. Please try again.') }
}
watch(() => [props.range, props.outlet, props.refreshKey, props.online, category.value, mode.value], load, { deep: true, immediate: true })
onBeforeUnmount(() => { sequence++ })
</script>
