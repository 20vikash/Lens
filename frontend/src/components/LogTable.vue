<template>
	<div class="font-mono text-xs leading-tight">
		<!-- Column header -->
		<div class="sticky top-0 z-10 flex items-center gap-2 border-b border-outline-gray-1 bg-surface-gray-1 px-4 py-1.5 font-sans text-[10px] font-semibold uppercase tracking-wider text-ink-gray-4">
			<span class="w-4 shrink-0" />
			<span class="w-40 shrink-0">Timestamp</span>
			<span class="w-[5.5rem] shrink-0">Level</span>
			<span class="hidden w-28 shrink-0 lg:inline">Service</span>
			<span class="min-w-0 flex-1">Message</span>
		</div>

		<!-- Loading skeleton -->
		<div v-if="loading && !rows.length">
			<div v-for="i in 12" :key="i" class="flex items-center gap-2 border-b border-outline-gray-1 px-4 py-1.5">
				<div class="h-3 w-4 animate-pulse rounded bg-surface-gray-2" />
				<div class="h-3 w-36 animate-pulse rounded bg-surface-gray-2" />
				<div class="h-3 w-14 animate-pulse rounded bg-surface-gray-2" />
				<div class="h-3 w-24 animate-pulse rounded bg-surface-gray-2" />
				<div class="h-3 flex-1 animate-pulse rounded bg-surface-gray-2" />
			</div>
		</div>

		<div v-else-if="!rows.length" class="flex flex-col items-center gap-1.5 py-20 font-sans text-ink-gray-3">
			<LucideSearchX class="h-8 w-8 text-ink-gray-2" />
			<span class="text-sm font-medium">No logs found for the current filters</span>
			<span class="text-xs">Try widening the time range or clearing filters</span>
		</div>

		<div
			v-for="(row, i) in rows"
			:key="i"
			class="group border-b border-outline-gray-1"
			:class="open.has(i) ? 'bg-surface-gray-1' : 'hover:bg-surface-menu-bar'"
		>
			<button
				class="flex w-full items-center gap-2 px-4 py-1 text-left"
				@click="toggle(i)"
			>
				<LucideChevronRight
					class="h-3.5 w-3.5 shrink-0 text-ink-gray-3 transition-transform duration-150 group-hover:text-ink-gray-5"
					:class="{ 'rotate-90': open.has(i) }"
				/>
				<span class="w-40 shrink-0 tnum text-ink-gray-5">{{ formatTs(row.ts) }}</span>
				<span class="w-[5.5rem] shrink-0">
					<span class="inline-flex items-center gap-1.5 rounded-full bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-5">
						<span class="h-2 w-2 shrink-0 rounded-full" :style="{ backgroundColor: levelColor(row.level) }" />
						<span class="capitalize">{{ formatLevel(row.level) }}</span>
					</span>
				</span>
				<span class="hidden w-28 shrink-0 truncate text-ink-gray-5 lg:inline">{{ row.service }}</span>
				<span
					class="min-w-0 flex-1 truncate text-ink-gray-8"
					:class="open.has(i) ? 'whitespace-pre-wrap break-all' : ''"
				>
					{{ row.message }}
				</span>
			</button>

			<div v-if="open.has(i)" class="px-4 pb-2.5">
				<div class="ml-6 rounded-md border border-outline-gray-1 bg-surface-white p-3 shadow-sm">
					<div class="mb-1.5 flex items-center justify-between">
						<span class="font-sans text-[10px] font-semibold uppercase tracking-wider text-ink-gray-4">Event details</span>
						<Button variant="ghost" size="sm" label="Show context ±10m" @click.stop="$emit('context', row)" />
					</div>
					<div class="grid grid-cols-1 gap-x-8 gap-y-1 sm:grid-cols-2">
						<div v-for="(value, key) in allFields(row)" :key="key" class="flex items-baseline gap-2.5 min-w-0">
							<span class="w-24 shrink-0 truncate text-right font-sans text-[10px] uppercase tracking-wide text-ink-gray-3">{{ key }}</span>
							<span class="min-w-0 flex-1 break-all text-ink-gray-8">{{ value }}</span>
							<LucideCheck v-if="copied.has(`${i}-${key}`)" class="h-3 w-3 shrink-0 text-green-600" />
							<LucideCopy
								v-else
								class="h-3 w-3 shrink-0 cursor-pointer text-ink-gray-2 transition-colors hover:text-ink-gray-6"
								@click.stop="copy(value, `${i}-${key}`)"
							/>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { reactive } from 'vue'
import LucideCheck from '~icons/lucide/check'
import LucideChevronRight from '~icons/lucide/chevron-right'
import LucideCopy from '~icons/lucide/copy'
import LucideSearchX from '~icons/lucide/search-x'
import { Button } from 'frappe-ui'
import { formatTs, formatLevel, LEVEL_COLORS } from '../utils/logs'

function levelColor(level) {
	return LEVEL_COLORS[level] || LEVEL_COLORS.INFO
}

defineProps({
	rows: { type: Array, default: () => [] },
	loading: Boolean,
})

const emit = defineEmits(['context'])
const open = reactive(new Set())

function toggle(index) {
	open.has(index) ? open.delete(index) : open.add(index)
}

function allFields(row) {
	return {
		product: row.product,
		service: row.service,
		source: row.source,
		resource_id: row.resource_id,
		...Object.fromEntries(Object.entries(row.attributes || {}).map(([k, v]) => [`attr.${k}`, v])),
	}
}

const copied = reactive(new Set())

async function copy(value, key) {
	await navigator.clipboard.writeText(String(value))
	copied.add(key)
	setTimeout(() => copied.delete(key), 1500)
}
</script>
