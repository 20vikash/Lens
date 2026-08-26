const FIELD_PATTERN = /^(resource_id|product|service|source|level):(.+)$/

// Parses `service:api timeout level:ERROR` style input into a structured query.
export function parseQuery(input) {
	const text = []
	const filters = {}
	const levels = []

	for (let token of input.trim().split(/\s+/)) {
		token = token.trim()
		if (!token) continue
		const match = token.match(FIELD_PATTERN)
		if (match) {
			const [, field, value] = match
			if (field === 'level') {
				levels.push(value.toUpperCase())
			} else {
				;(filters[field] ||= []).push(value)
			}
		} else {
			text.push(token)
		}
	}

	return { query: text.join(' '), levels, filters }
}
