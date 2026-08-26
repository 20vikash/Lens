import containerQueries from '@tailwindcss/container-queries'
import frappeUIPreset from 'frappe-ui/tailwind'

export default {
	presets: [frappeUIPreset],
	content: [
		'./index.html',
		'./src/**/*.{vue,js,ts,jsx,tsx}',
		'./node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}',
	],
	theme: {
	extend: {
		fontFamily: {
			sans: ['InterVar', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
			mono: ['"JetBrains Mono"', '"Fira Code"', 'ui-monospace', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
		},
		fontSize: {
			'2xs': ['0.625rem', { lineHeight: '0.875rem' }],
		},
	},
	},
	plugins: [containerQueries],
}
