<template>
	<Popover v-model:show="open" placement="bottom">
		<template #target="{ togglePopover }">
			<Button
				label="Filter"
				:class="conditions.length ? 'border-blue-300 bg-blue-50' : ''"
				@click="togglePopover"
			>
				<template #prefix>
					<LucideListFilter class="h-4 w-4" :class="conditions.length ? 'text-blue-600' : ''" />
				</template>
				<template #suffix v-if="conditions.length">
					<span
						class="flex h-4 min-w-4 items-center justify-center rounded-full bg-blue-600 px-1 text-[10px] font-semibold tnum text-ink-white"
					>
						{{ conditions.length }}
					</span>
				</template>
			</Button>
		</template>
		<template #body>
			<div class="w-[36rem] rounded-lg border border-outline-gray-2 bg-surface-white p-4 shadow-xl">
				<div class="mb-3 flex items-center justify-between">
					<span class="text-[10px] font-semibold uppercase tracking-wider text-ink-gray-4">Advanced filters</span>
					<span class="text-[10px] text-ink-gray-3">field · operator · value</span>
				</div>

				<div v-if="!draft.length" class="py-8 text-center text-xs text-ink-gray-3">
					No filters yet. Add one to narrow results by any field or attribute.
				</div>

				<div class="space-y-2">
					<template v-for="(cond, i) in draft" :key="i">
						<!-- Conjunction toggle between rows -->
						<div v-if="i > 0" class="flex items-center gap-3 py-0.5">
							<div class="h-px flex-1 bg-outline-gray-1"></div>
							<div class="flex overflow-hidden rounded-md border border-outline-gray-2">
								<button
									class="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide transition-colors"
									:class="cond.conjunction !== 'or'
										? 'bg-surface-gray-4 text-ink-white'
										: 'bg-surface-white text-ink-gray-4 hover:bg-surface-gray-1'"
									@click="cond.conjunction = 'and'"
								>
									AND
								</button>
								<button
									class="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide transition-colors"
									:class="cond.conjunction === 'or'
										? 'bg-amber-500 text-ink-white'
										: 'bg-surface-white text-ink-gray-4 hover:bg-surface-gray-1'"
									@click="cond.conjunction = 'or'"
								>
									OR
								</button>
							</div>
							<div class="h-px flex-1 bg-outline-gray-1"></div>
						</div>

						<!-- Condition row -->
						<div class="flex items-center gap-2">
							<!-- Field selector: columns, or attribute key with badge -->
							<template v-if="cond.field === '__attr__'">
								<div class="flex min-w-0 flex-1 items-center gap-1.5 rounded-md border border-violet-200 bg-violet-50 px-2 py-1.5">
									<LucideTag class="h-3.5 w-3.5 shrink-0 text-violet-500" />
									<span class="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-violet-600">attr</span>
									<div class="min-w-0 flex-1">
										<Select
											size="sm"
											:options="attrKeyOptions()"
											v-model="cond.attrKey"
										/>
									</div>
									<button
										class="shrink-0 rounded p-0.5 text-violet-400 transition-colors hover:bg-violet-100 hover:text-violet-600"
										@click="cond.field = 'product'"
										title="Back to fields"
									>
										<LucideRotateCcw class="h-3 w-3" />
									</button>
								</div>
							</template>
							<template v-else>
								<div class="min-w-0 flex-1">
									<Select
										:options="fieldOptions"
										v-model="cond.field"
										@update:model-value="onFieldChange(cond)"
									/>
								</div>
							</template>

							<div class="w-16 shrink-0">
								<Select :options="opOptions" v-model="cond.op" />
							</div>
							<div class="min-w-0 flex-[1.4]">
								<TextInput
									:placeholder="valuePlaceholder(cond)"
									v-model="cond.value"
									:type="isNumeric(cond) ? 'number' : 'text'"
									@keydown.enter="apply"
								/>
							</div>
							<button
								class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-ink-gray-3 transition-colors hover:bg-surface-gray-1 hover:text-ink-gray-6"
								@click="draft.splice(i, 1)"
								title="Remove"
							>
								<LucideTrash2 class="h-4 w-4" />
							</button>
						</div>
					</template>
				</div>

				<div class="mt-3 flex items-center justify-between border-t border-outline-gray-1 pt-3">
					<div class="flex gap-1.5">
						<Button variant="ghost" size="sm" label="Add field" @click="addRow('field')">
							<template #icon><LucidePlus class="h-3.5 w-3.5" /></template>
						</Button>
						<Button v-if="attrKeys.length" variant="ghost" size="sm" label="Add attribute" @click="addRow('attr')">
							<template #icon><LucideTag class="h-3.5 w-3.5" /></template>
						</Button>
					</div>
					<div class="flex gap-1.5">
						<Button variant="ghost" size="sm" label="Clear" @click="clearAll" />
						<Button variant="solid" size="sm" label="Apply" @click="apply" />
					</div>
				</div>
			</div>
		</template>
	</Popover>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Badge, Button, Popover, Select, TextInput } from 'frappe-ui'
import LucideListFilter from '~icons/lucide/list-filter'
import LucidePlus from '~icons/lucide/plus'
import LucideTrash2 from '~icons/lucide/trash-2'
import LucideTag from '~icons/lucide/tag'
import LucideRotateCcw from '~icons/lucide/rotate-ccw'

const props = defineProps({
	conditions: { type: Array, default: () => [] },
	fields: { type: Array, default: () => [] },
	attrKeys: { type: Array, default: () => [] },
})
const emit = defineEmits(['apply'])

const open = ref(false)
const draft = ref([])

const attrKeys = computed(() => props.attrKeys)

watch(
	[open, () => props.conditions],
	([isOpen]) => {
		if (isOpen) draft.value = JSON.parse(JSON.stringify(props.conditions))
	},
	{ immediate: true },
)

const opOptions = [
	{ label: '=', value: 'eq' },
	{ label: '≠', value: 'ne' },
	{ label: '>', value: 'gt' },
	{ label: '<', value: 'lt' },
	{ label: '≥', value: 'gte' },
	{ label: '≤', value: 'lte' },
	{ label: 'contains', value: 'contains' },
]

const fieldOptions = [
	{ label: 'product', value: 'product' },
	{ label: 'service', value: 'service' },
	{ label: 'level', value: 'level' },
	{ label: 'source', value: 'source' },
	{ label: 'resource_id', value: 'resource_id' },
	{ label: 'message', value: 'message' },
]

function attrKeyOptions() {
	return [
		{ label: '← back to fields', value: '__back__' },
		...attrKeys.value.map((k) => ({ label: k, value: k })),
	]
}

watch(
	() => draft.value.map((c) => c.attrKey),
	() => {
		for (const cond of draft.value) {
			if (cond.field === '__attr__' && cond.attrKey === '__back__') {
				cond.field = 'product'
				cond.attrKey = attrKeys.value[0] || ''
			}
		}
	},
)

function isNumeric(cond) {
	return ['gt', 'lt', 'gte', 'lte'].includes(cond.op) && cond.field === '__attr__'
}

function valuePlaceholder(cond) {
	if (isNumeric(cond)) return 'number'
	if (cond.op === 'contains') return 'substring'
	return 'value'
}

function onFieldChange(cond) {
	if (cond.field === 'level' && !['eq', 'ne'].includes(cond.op)) cond.op = 'eq'
	if (cond.field === 'message' && ['gt', 'lt', 'gte', 'lte'].includes(cond.op)) cond.op = 'contains'
}

function addRow(kind) {
	if (kind === 'attr' && attrKeys.value.length) {
		draft.value.push({ field: '__attr__', attrKey: attrKeys.value[0], op: 'eq', value: '', conjunction: 'and' })
	} else {
		draft.value.push({ field: 'product', op: 'eq', value: '', conjunction: 'and' })
	}
}

function clearAll() {
	draft.value = []
	emit('apply', [])
	open.value = false
}

function apply() {
	const out = draft.value
		.filter((c) => {
			if (c.field === '__attr__') return c.attrKey && c.attrKey !== '__back__' && c.value !== ''
			return c.field && c.value !== ''
		})
		.map((c, i) => ({
			field: c.field === '__attr__' ? `attr.${c.attrKey}` : c.field,
			op: c.op,
			value: c.value,
			conjunction: i === 0 ? 'and' : c.conjunction || 'and',
		}))
	emit('apply', out)
	open.value = false
}
</script>
