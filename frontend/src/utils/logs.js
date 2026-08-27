import dayjs from 'dayjs'

export const LEVEL_COLORS = {
	DEBUG: '#999999',
	INFO: '#0289F7',
	WARNING: '#E79913',
	ERROR: '#E03636',
	CRITICAL: '#6846E3',
}

export const LEVEL_ORDER = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']

export const TIME_RANGES = [
	{ label: 'Last 15 minutes', minutes: 15 },
	{ label: 'Last 1 hour', minutes: 60 },
	{ label: 'Last 6 hours', minutes: 360 },
	{ label: 'Last 24 hours', minutes: 1440 },
	{ label: 'Last 3 days', minutes: 4320 },
	{ label: 'Last 7 days', minutes: 10080 },
]

export function formatTs(ms) {
	return dayjs(ms).format('MMM D, HH:mm:ss.SSS')
}

export function formatBucket(ms) {
	return dayjs(ms).format('MMM D HH:mm')
}

export function formatLevel(level) {
	const s = String(level || '')
	return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase()
}

export function humanCount(n) {
	if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
	if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
	return String(n)
}
