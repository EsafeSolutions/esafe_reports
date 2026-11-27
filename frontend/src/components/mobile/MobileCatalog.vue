<template>
  <section class="m-section m-catalog" :aria-labelledby="inventory ? 'inventory-title' : 'products-title'" :aria-busy="loading">
    <div class="m-heading-line">
      <h1 :id="inventory ? 'inventory-title' : 'products-title'">{{ t(inventory ? 'Inventory' : 'Products') }}</h1>
      <button class="m-icon-button m-refresh" :disabled="loading || !online" :aria-label="t('Refresh products')" @click="load"><MobileIcon name="refresh" /></button>
    </div>
    <label class="m-catalog-search"><MobileIcon name="search" :size="21" /><input v-model="search" type="search" :placeholder="t(inventory ? 'Search products' : 'Search name, code or barcode')" :aria-label="t('Search name, code or barcode')" /></label>
    <div class="m-catalog-filters">
      <select v-if="inventory" v-model="warehouse" :aria-label="t('Warehouse')"><option value="">{{ t('All warehouses') }}</option><option v-for="choice in options.warehouses" :key="choice.name" :value="choice.name">{{ choice.name }}</option></select>
      <select v-model="category" :aria-label="t('Category')"><option value="">{{ t('All categories') }}</option><option v-for="choice in options.categories" :key="choice.name" :value="choice.name">{{ choice.name }}</option></select>
      <select v-if="!inventory" v-model="priceList" :aria-label="t('Price list')"><option value="">{{ t('Choose price list') }}</option><option v-for="choice in options.price_lists" :key="choice.name" :value="choice.name">{{ choice.name }}</option></select>
    </div>
    <p v-if="!inventory" class="m-notice">{{ t('Price list rates per selling unit. Taxes and transaction discounts may differ.') }}</p>
    <template v-else>
      <div class="m-inventory-summary"><span>{{ t('This page') }}</span><strong>{{ result?.items.length || 0 }} {{ t('products') }}</strong><span>{{ t('Stock in permitted warehouses') }}</span></div>
      <div class="m-period" role="group" :aria-label="t('Filter stock on this page')"><button v-for="choice in stockChoices" :key="choice.key" :class="{ selected: stockFilter === choice.key }" :aria-pressed="stockFilter === choice.key" @click="stockFilter = choice.key">{{ t(choice.label) }}</button></div>
      <p v-if="stockFilter !== 'all'" class="m-notice">{{ t('Stock filter applies to this page. Use Next to check more products.') }}</p>
    </template>
    <p v-for="(message, key) in options.errors" :key="key" class="m-notice">{{ message }}</p>
    <p v-if="error" class="m-error" role="alert">{{ error }}</p>
    <p v-for="(message, key) in result?.errors" :key="key" class="m-error" role="alert">{{ message }}</p>
    <p v-if="result?.partial" class="m-error" role="alert">{{ t('Some rates or stock rows exceed the limit. Select one warehouse or search a product for details.') }}</p>
    <div v-if="loading" class="m-loading" role="status">{{ t('Loading products…') }}</div>
    <template v-else-if="result">
      <div v-if="!visibleItems.length" class="m-catalog-empty"><MobileIcon name="box" :size="40" /><h2>{{ t('No products found') }}</h2><p>{{ t('Try a different search, category or stock filter.') }}</p></div>
      <div v-else class="m-product-list">
        <button v-for="item in visibleItems" :key="item.name" class="m-product-row" @click="openDetail(item)">
          <span class="m-product-copy"><small v-if="!inventory">{{ item.item_group }} · {{ item.name }}</small><strong>{{ item.item_name }}</strong><small v-if="inventory">{{ item.name }} · {{ warehouse || t('All permitted warehouses') }}</small></span>
          <span class="m-product-values">
            <strong v-if="!inventory" dir="auto">{{ displayPrice(item) }}</strong>
            <small v-if="!inventory && priceFor(item)">{{ t('per {0}', priceFor(item).uom || item.stock_uom) }}</small>
            <span :class="{ 'm-stock-out': stockStatus(item) === 'out' }" dir="auto"><strong v-if="inventory">{{ number(item.actual_qty) }}</strong><span v-else>{{ number(item.actual_qty) }}</span> {{ item.is_stock_item ? item.stock_uom : t('Non-stock item') }}</span>
            <small v-if="!inventory && stockStatus(item) !== 'unknown'" class="m-stock-label" :class="{ 'm-stock-out': stockStatus(item) === 'out' }">{{ t(stockStatus(item) === 'in' ? 'In stock' : 'Out of stock') }}</small>
          </span>
          <MobileIcon name="chevron" :size="18" />
        </button>
      </div>
      <div class="m-catalog-pages"><button v-if="start" class="m-outline" @click="page(-1)">{{ t('Previous') }}</button><span>{{ t('Page {0}', start / 20 + 1) }}</span><button v-if="result.has_more" class="m-primary" @click="page(1)">{{ t('Next') }}<MobileIcon name="chevron" :size="18" /></button></div>
      <button class="m-text-button m-export" :disabled="!visibleItems.length" @click="exportRows"><MobileIcon name="download" :size="18" />{{ t('Export this page') }}</button>
    </template>
    <button v-if="error" class="m-outline m-full" @click="load">{{ t('Try again') }}</button>
    <dialog ref="detailDialog" class="m-dialog m-product-dialog" @close="selected = null">
      <template v-if="selected">
        <div class="m-dialog-title"><h2>{{ selected.item_name }}</h2><button class="m-icon-button" :aria-label="t('Close')" @click="detailDialog.close()"><MobileIcon name="close" /></button></div>
        <p class="m-notice">{{ selected.name }} · {{ selected.item_group }}</p>
        <h3>{{ t('Current stock') }}</h3><p class="m-detail-total">{{ number(selected.actual_qty) }} {{ selected.stock_uom }}</p>
        <p v-if="!selected.is_stock_item" class="m-notice">{{ t('Non-stock item') }}</p>
        <p v-if="result?.errors.stock" class="m-error">{{ result.errors.stock }}</p>
        <div v-for="bin in selected.stock" :key="bin.warehouse" class="m-detail-stock"><strong>{{ bin.warehouse }}</strong><span>{{ number(bin.actual_qty) }} {{ selected.stock_uom }}</span><small>{{ t('Reserved') }} {{ number(bin.reserved_qty) }} · {{ t('Ordered') }} {{ number(bin.ordered_qty) }} · {{ t('Projected') }} {{ number(bin.projected_qty) }}</small></div>
        <h3>{{ t('Selling prices') }}</h3><p v-if="!priceList" class="m-notice">{{ t('Select a price list in Products to see selling prices.') }}</p><p v-else-if="!selected.prices.length" class="m-notice">{{ t('No current price in this price list') }}</p>
        <div v-for="(price, index) in selected.prices" :key="index" class="m-detail-stock"><strong>{{ price.currency }} {{ number(price.price_list_rate) }}</strong><span>{{ price.uom || selected.stock_uom }}</span><small>{{ t('Packing unit') }} {{ number(price.packing_unit || 1) }}</small></div>
      </template>
    </dialog>
  </section>
</template>
<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MobileIcon from './MobileIcon.vue'
import { mobileApi } from '@/lib/mobileApi'
import { exportMobileCsv, number, priceFor, stockStatus } from '@/lib/mobileCatalog'
import { t } from '@/lib/i18n'

const props = defineProps({ inventory: Boolean, online: { type: Boolean, default: true }, refreshKey: Number })
const search = ref(''), category = ref(''), priceList = ref(''), warehouse = ref(''), start = ref(0), stockFilter = ref('all')
const options = ref({ categories: [], warehouses: [], price_lists: [], errors: {} }), result = ref(null), error = ref(''), loading = ref(true), selected = ref(null), detailDialog = ref(null)
const stockChoices = [{ key: 'all', label: 'All stock' }, { key: 'in', label: 'In stock' }, { key: 'out', label: 'Out of stock' }]
const visibleItems = computed(() => (result.value?.items || []).filter(item => stockFilter.value === 'all' || stockStatus(item) === stockFilter.value))
let sequence = 0, timer, disposed = false, initializing = true
function displayPrice(item) { const price = priceFor(item); return price ? `${price.currency} ${number(price.price_list_rate)}` : '—' }
async function load() {
  const id = ++sequence
  error.value = ''; loading.value = true; result.value = null
  detailDialog.value?.close(); selected.value = null
  try {
    if (!props.online) throw new Error(t('Connect to the internet to load current prices and stock.'))
    const data = await mobileApi('lumen_reports.mobile_catalog.get_products', { search: search.value, category: category.value, price_list: priceList.value, warehouse: warehouse.value, start: start.value })
    if (id === sequence && !disposed) result.value = data
  } catch (e) { if (id === sequence && !disposed) error.value = e.message }
  finally { if (id === sequence && !disposed) loading.value = false }
}
function page(direction) { start.value = Math.max(0, start.value + direction * 20); load(); window.scrollTo({ top: 0, behavior: 'instant' }) }
function openDetail(item) { selected.value = item; detailDialog.value.showModal() }
async function exportRows() {
  try { await exportMobileCsv('esafe-products.csv', [['Code', 'Product', 'Category', 'Price', 'Currency', 'Selling UOM', 'Visible actual stock', 'Stock UOM'], ...visibleItems.value.map(item => { const p = priceFor(item); return [item.name, item.item_name, item.item_group, p?.price_list_rate, p?.currency, p?.uom || item.stock_uom, item.actual_qty, item.stock_uom] })]) }
  catch { error.value = t('Could not export. Please try again.') }
}
watch([search, category, priceList, warehouse], () => {
  if (initializing) return
  start.value = 0; sequence++; result.value = null; loading.value = true
  clearTimeout(timer); timer = setTimeout(load, 300)
})
watch(() => [props.refreshKey, props.online], () => { if (!initializing) load() })
onMounted(async () => {
  try {
    options.value = await mobileApi('lumen_reports.mobile_catalog.get_options')
    if (disposed) return
    priceList.value = options.value.price_lists.find(p => p.name === 'Standard Selling')?.name || options.value.price_lists[0]?.name || ''
  } catch (e) { if (!disposed) error.value = e.message }
  await Promise.resolve()
  initializing = false
  if (!disposed) await load()
})
onBeforeUnmount(() => { disposed = true; sequence++; clearTimeout(timer) })
</script>
