export function number(value, digits = 2) {
  if (value == null || !Number.isFinite(Number(value))) return '—'
  return Intl.NumberFormat('en', { maximumFractionDigits: digits }).format(Number(value))
}

export function priceFor(item) {
  return item.prices?.find(p => !p.uom || p.uom === item.stock_uom) || item.prices?.[0]
}

export function stockStatus(item) {
  if (!item.is_stock_item || item.actual_qty == null) return 'unknown'
  return Number(item.actual_qty) > 0 ? 'in' : 'out'
}

// Product names and item codes are untrusted text when opened in a spreadsheet.
export function safeCsv(rows) {
  return rows.map(row => row.map(value => {
    let s = String(value ?? '')
    if (/^[\s]*[=+@\-]/.test(s) && typeof value !== 'number') s = "'" + s
    return '"' + s.replace(/"/g, '""') + '"'
  }).join(',')).join('\r\n')
}

export async function exportMobileCsv(filename, rows) {
  const content = '\ufeff' + safeCsv(rows)
  if ((window.EsafeNative?.shareCsv || window.webkit?.messageHandlers?.esafeShare) && new TextEncoder().encode(content).length > 2_000_000) throw new Error('Export is too large. Choose a smaller range.')
  // Native shells share a local CSV using their OS share sheet.
  if (window.EsafeNative?.shareCsv) return window.EsafeNative.shareCsv(filename, content)
  if (window.webkit?.messageHandlers?.esafeShare) {
    window.webkit.messageHandlers.esafeShare.postMessage({ filename, content })
    return
  }
  const { downloadFile } = await import('./csv')
  downloadFile(filename, new Blob([content], { type: 'text/csv;charset=utf-8' }))
}
