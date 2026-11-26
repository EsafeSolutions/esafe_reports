// Same-origin Frappe requests. Reads stay GET; mutations carry the site's CSRF token.
export async function mobileApi(method, params = {}, verb = 'GET') {
	const url = new URL(`/api/method/${method}`, window.location.origin)
	const options = {
		method: verb,
		credentials: 'same-origin',
		headers: { Accept: 'application/json' },
		cache: 'no-store',
	}
	if (verb === 'GET') {
		for (const [key, value] of Object.entries(params)) {
			if (value != null)
				url.searchParams.set(
					key,
					typeof value === 'object' ? JSON.stringify(value) : value,
				)
		}
	} else {
		options.headers['Content-Type'] = 'application/json'
		options.headers['X-Frappe-CSRF-Token'] = window.csrf_token || ''
		options.body = JSON.stringify(params)
	}
	const response = await fetch(url.pathname + url.search, options)
	const body = await response.json().catch(() => ({}))
	if (!response.ok || body.exc) {
		let message =
			response.status === 403
				? 'Your session or permissions need attention. Sign in again and check POS connection.'
				: 'Could not load this information. Please try again.'
		try {
			const messages = JSON.parse(body._server_messages || '[]')
			if (messages.length) message = JSON.parse(messages[0]).message || message
		} catch {
			/* use the readable fallback */
		}
		const error = new Error(String(message).replace(/<[^>]*>/g, ''))
		error.status = response.status
		throw error
	}
	return body.message
}
