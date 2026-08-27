<template>
	<aside class="w-60 shrink-0 overflow-y-auto border-r border-outline-gray-2 bg-surface-white">
		<div class="border-b border-outline-gray-1 px-3.5 py-2.5">
			<span class="text-[10px] font-semibold uppercase tracking-wider text-ink-gray-4">Fields</span>
		</div>

		<details v-for="field in fields" :key="field.name" class="border-b border-outline-gray-1 last:border-0" :open="field.open">
			<summary
				class="flex cursor-pointer list-none items-center justify-between px-3.5 py-1.5 text-left transition-colors hover:bg-surface-gray-1 [&_.chevron]:-rotate-90 open:[&_.chevron]:rotate-0"
			>
				<span class="text-[10px] font-semibold uppercase tracking-wider text-ink-gray-5">{{ field.label }}</span>
				<LucideChevronDown
					class="chevron h-3.5 w-3.5 text-ink-gray-3 transition-transform duration-200"
				/>
			</summary>

			<div class="pb-2 pt-0.5">
				<button
					v-for="item in visibleItems(field)"
					:key="item.value"
					class="group flex w-full items-center justify-between gap-2 px-3.5 py-1 text-left text-xs text-ink-gray-7 transition-colors hover:bg-surface-gray-1"
					:class="isSelected(field, item.value) ? 'bg-surface-gray-1' : ''"
					@click="$emit('toggle', field.key || field.name, item.value)"
				>
					<span class="flex min-w-0 items-center gap-1.5">
						<LucideCheck
							class="h-3 w-3 shrink-0"
							:class="isSelected(field, item.value) ? 'text-ink-gray-7' : 'text-ink-gray-3 opacity-0 group-hover:opacity-100'"
						/>
						<span
							class="min-w-0 truncate"
							:class="isSelected(field, item.value) ? 'font-medium text-ink-gray-9' : 'text-ink-gray-7'"
						>
							{{ field.name === 'level' ? formatLevel(item.value) : (item.value || '(empty)') }}
						</span>
					</span>
					<span class="shrink-0 text-[11px] tnum text-ink-gray-3">{{ humanCount(item.count) }}</span>
				</button>
				<div v-if="!visibleItems(field).length" class="px-3.5 py-1 text-xs text-ink-gray-3">No data</div>
			</div>
		</details>

		<!-- Attribute keys -->
		<div class="border-y border-outline-gray-1 px-3.5 py-2.5">
			<span class="text-[10px] font-semibold uppercase tracking-wider text-ink-gray-4">Attributes</span>
		</div>

		<div v-if="!attributes.length" class="px-3.5 py-2 text-xs text-ink-gray-3">No attributes found</div>

		<details v-for="attr in attributes" :key="attr.key" class="border-b border-outline-gray-1 last:border-0" :open="attr.open">
			<summary
				class="flex cursor-pointer list-none items-center justify-between px-3.5 py-1.5 text-left transition-colors hover:bg-surface-gray-1 [&_.chevron]:-rotate-90 open:[&_.chevron]:rotate-0"
			>
				<span class="flex min-w-0 items-center gap-1.5">
					<LucideTag class="h-3 w-3 shrink-0 text-ink-gray-3" />
					<span class="min-w-0 truncate font-mono text-xs text-ink-gray-6">{{ attr.key }}</span>
				</span>
				<span class="flex shrink-0 items-center gap-1.5">
					<span class="text-[11px] tnum text-ink-gray-3">{{ humanCount(attr.count) }}</span>
					<LucideChevronDown class="chevron h-3.5 w-3.5 text-ink-gray-3 transition-transform duration-200" />
				</span>
			</summary>

			<div class="pb-2 pt-0.5">
				<button
					v-for="item in (attr.values || []).slice(0, 5)"
					:key="item.value"
					class="group flex w-full items-center justify-between gap-2 px-3.5 py-1 text-left text-xs transition-colors hover:bg-surface-gray-1"
					:class="isAttrSelected(attr.key, item.value) ? 'bg-surface-gray-1' : ''"
					@click="$emit('toggleAttr', attr.key, item.value)"
				>
					<span class="flex min-w-0 items-center gap-1.5">
						<LucideCheck
							class="h-3 w-3 shrink-0"
							:class="isAttrSelected(attr.key, item.value) ? 'text-ink-gray-7' : 'text-ink-gray-3 opacity-0 group-hover:opacity-100'"
						/>
						<span
							class="min-w-0 truncate font-mono text-xs"
							:class="isAttrSelected(attr.key, item.value) ? 'font-medium text-ink-gray-9' : 'text-ink-gray-7'"
						>
							{{ item.value || '(empty)' }}
						</span>
					</span>
					<span class="shrink-0 text-[11px] tnum text-ink-gray-3">{{ humanCount(item.count) }}</span>
				</button>
				<div v-if="!(attr.values || []).length" class="px-3.5 py-1 text-xs text-ink-gray-3">No samples</div>
			</div>
		</details>
	</aside>
</template>

<script setup>
import { reactive, watch } from 'vue'
import LucideCheck from '~icons/lucide/check'
import LucideChevronDown from '~icons/lucide/chevron-down'
import LucideTag from '~icons/lucide/tag'
import { humanCount, formatLevel, LEVEL_ORDER } from '../utils/logs'

const props = defineProps({
	facets: { type: Object, default: () => ({}) },
	selected: { type: Object, default: () => ({}) },
	conditions: { type: Array, default: () => [] },
})

const emit = defineEmits(['toggle', 'toggleAttr'])

const FIELDS = [
	{ name: 'product', label: 'Product' },
	{ name: 'service', label: 'Service' },
	{ name: 'level', label: 'Level', key: '__levels' },
	{ name: 'source', label: 'Source' },
	{ name: 'resource_id', label: 'Resource' },
]

const fields = FIELDS.map((f) => ({ ...f, open: true }))

const attrState = reactive({})
const attributes = reactive([])

watch(
	() => props.facets.__attributes__,
	(list = []) => {
		attributes.splice(0, attributes.length)
		for (const a of list) {
			attributes.push({ ...a, open: attrState[a.key] ?? true })
		}
	},
	{ deep: true, immediate: true },
)

function visibleItems(field) {
	const items = props.facets[field.name] || []
	if (field.name === 'level') {
		return [...items].sort(
			(a, b) => LEVEL_ORDER.indexOf(a.value) - LEVEL_ORDER.indexOf(b.value),
		)
	}
	return items.slice(0, 10)
}

function isSelected(field, value) {
	return (props.selected[field.key || field.name] || []).includes(value)
}

function isAttrSelected(key, value) {
	return props.conditions.some(
		(c) => c.field === `attr.${key}` && c.op === 'eq' && c.value === value,
	)
}
</script>
