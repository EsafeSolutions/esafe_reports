import test from 'node:test'
import assert from 'node:assert/strict'
import { number, priceFor, safeCsv, stockStatus } from '../src/lib/mobileCatalog.js'

test('unavailable stock remains unknown and zero is explicitly out of stock', () => {
  assert.equal(stockStatus({ is_stock_item: 1, actual_qty: null }), 'unknown')
  assert.equal(stockStatus({ is_stock_item: 0, actual_qty: 0 }), 'unknown')
  assert.equal(stockStatus({ is_stock_item: 1, actual_qty: 0 }), 'out')
  assert.equal(stockStatus({ is_stock_item: 1, actual_qty: -2 }), 'out')
  assert.equal(number(null), '—')
})
test('headline price prefers the stock unit and retains an explicit selling unit fallback', () => {
  const prices = [{ uom: 'Box', packing_unit: 10, price_list_rate: 800 }, { uom: 'Box', packing_unit: 1, price_list_rate: 900 }, { uom: 'Nos', packing_unit: 0, price_list_rate: 100 }]
  assert.equal(priceFor({ prices, stock_uom: 'Nos' }).price_list_rate, 100)
  assert.equal(priceFor({ prices: [prices[0]], stock_uom: 'Nos' }).uom, 'Box')
})
test('CSV preserves numeric returns but neutralizes spreadsheet formulas in item text', () => {
  assert.equal(safeCsv([['=CMD()', '@SUM(1)', 'a,"b', -12]]), '"\'=CMD()","\'@SUM(1)","a,""b","-12"')
})
