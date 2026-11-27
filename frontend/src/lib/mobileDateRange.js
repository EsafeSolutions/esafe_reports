export function isCalendarDate(value) {
	if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith('0000-')) return false
	const date = new Date(`${value}T00:00:00Z`)
	return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value
}

export function validDateRange(value) {
	return Array.isArray(value) && value.length === 2 && value.every(isCalendarDate) && value[0] <= value[1]
}

export function formatMobileRange(range, locale = 'en') {
	if (!validDateRange(range)) return ''
	const format = value => new Date(`${value}T12:00:00`).toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' })
	return range[0] === range[1] ? format(range[0]) : `${format(range[0])} – ${format(range[1])}`
}
