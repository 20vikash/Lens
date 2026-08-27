<template>
	<div class="flex h-screen flex-col overflow-hidden bg-surface-menu-bar">
		<!-- Toolbar -->
		<header class="shrink-0 border-b border-outline-gray-2 bg-surface-white px-4 py-2.5">
			<div class="flex items-center gap-3">
				<div class="flex items-center gap-2.5 pr-1">
					<div class="flex h-7 w-7 items-center justify-center rounded-md bg-surface-gray-7 shadow-sm">
						<TerminalIcon class="h-4 w-4 text-ink-white" />
					</div>
					<span class="text-sm font-semibold leading-none text-ink-gray-9">Lens</span>
				</div>

				<div class="h-6 w-px bg-outline-gray-2" />

				<Select
					v-if="sources.length > 1"
					class="w-36"
					:options="sources.map((s) => ({ label: s, value: s }))"
					v-model="source"
				/>

				<TextInput
					class="max-w-2xl flex-1"
					placeholder="Search messages…  e.g.  service:api timeout level:ERROR"
					v-model="searchInput"
					@keydown.enter="runSearch(true)"
				>
					<template #prefix>
						<SearchIcon class="h-4 w-4 text-ink-gray-3" />
					</template>
				</TextInput>

				<div class="ml-auto flex items-center gap-2">
					<FilterBuilder
						:conditions="conditions"
						:fields="fieldOptions"
						:attr-keys="attrKeys"
						@apply="applyConditions"
					/>
					<Dropdown :options="rangeOptions" :button="{ label: rangeLabel, iconLeft: 'clock', iconRight: 'chevron-down' }" placement="right" />
					<Tooltip text="Toggle sort order">
						<Button @click="toggleOrder">
							<template #icon>
								<ArrowDownWideNarrow v-if="order === 'desc'" class="h-4 w-4" />
								<ArrowUpNarrowWide v-else class="h-4 w-4" />
							</template>
						</Button>
					</Tooltip>
					<Tooltip text="Auto refresh every 10s">
						<Button :class="autoRefresh ? 'border-ink-gray-500 bg-surface-gray-2' : ''" @click="autoRefresh = !autoRefresh">
							<template #icon>
								<RadioTowerIcon class="h-4 w-4" :class="autoRefresh ? 'text-green-600' : 'text-ink-gray-4'" />
							</template>
						</Button>
					</Tooltip>
					<Button variant="solid" label="Search" @click="runSearch(true)" :loading="result.loading" />
				</div>
			</div>

			<div
				v-if="activeChips.length || conditions.length"
				class="mt-2.5 flex items-center gap-x-3 gap-y-2 border-t border-outline-gray-1 pt-2.5"
			>
				<span class="text-[10px] font-medium uppercase tracking-wider text-ink-gray-3">Filters</span>
				<div class="flex min-w-0 flex-1 items-center gap-x-3 gap-y-2 overflow-x-auto pb-0.5">
					<button
						v-for="chip in activeChips"
						:key="chip.key"
						class="group inline-flex shrink-0 items-center gap-1.5 rounded-full border border-outline-gray-2 bg-surface-gray-1 px-3 py-1 text-xs text-ink-gray-7 transition-colors hover:border-outline-gray-3 hover:bg-surface-gray-2"
						@click="removeChip(chip)"
					>
						<span class="font-medium text-ink-gray-5">{{ chip.field }}:</span>{{ chip.value }}
						<XIcon class="h-3 w-3 text-ink-gray-3 transition-colors group-hover:text-ink-gray-6" />
					</button>
					<template v-for="(cond, i) in conditions" :key="`cond-${i}`">
						<span
							v-if="i > 0"
							class="shrink-0 text-[10px] font-semibold uppercase tracking-wide"
							:class="cond.conjunction === 'or' ? 'text-amber-600' : 'text-ink-gray-3'"
						>
							{{ cond.conjunction === 'or' ? 'or' : 'and' }}
						</span>
						<button
							class="group inline-flex shrink-0 items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs text-blue-700 transition-colors hover:bg-blue-100"
							@click="removeCondition(i)"
						>
							<span class="font-mono font-medium text-blue-500">{{ cond.field }}</span>
							<span class="font-semibold tnum text-blue-400">{{ OP_SYMBOL[cond.op] }}</span>
							<span class="tnum">{{ cond.value }}</span>
							<XIcon class="h-3 w-3 text-blue-300 transition-colors group-hover:text-blue-600" />
						</button>
					</template>
				</div>
				<button class="shrink-0 text-xs text-ink-gray-4 underline-offset-2 hover:text-ink-gray-6 hover:underline" @click="clearAll">
					Clear all
				</button>
			</div>
		</header>

		<div class="flex min-h-0 flex-1">
			<FacetSidebar
				:facets="result.data?.facets || {}"
				:selected="selectedFacets"
				:conditions="conditions"
				@toggle="toggleFacet"
				@toggle-attr="toggleAttr"
				class="hidden md:block"
			/>

			<main class="flex min-w-0 flex-1 flex-col overflow-hidden bg-surface-white">
				<Histogram
					class="shrink-0 px-4 pt-3"
					:data="histogram"
					:start="range.start"
					:end="range.end"
					:bucket-seconds="result.data?.bucket_seconds || 60"
					:total="result.data?.total || 0"
					:loading="result.loading"
					@zoom="zoomToBucket"
				/>

				<!-- Results header -->
				<div class="mt-2 flex shrink-0 items-center justify-between border-y border-outline-gray-1 bg-surface-menu-bar px-4 py-1.5">
					<div class="flex items-center gap-2 text-xs text-ink-gray-4">
						<LoadingIndicator v-if="result.loading && !result.data" class="h-3 w-3" />
						<span v-else class="font-medium tnum text-ink-gray-7">{{ humanCount(result.data?.total || 0) }} <span class="font-normal text-ink-gray-4">results</span></span>
						<span v-if="queryText" class="font-mono text-[11px] text-ink-gray-3">· “{{ queryText }}”</span>
					</div>
					<div class="flex items-center gap-3">
						<div class="hidden items-center gap-2.5 sm:flex">
							<button
								v-for="level in legendLevels"
								:key="level"
								class="flex items-center gap-1.5 text-[10px] font-medium tracking-wide text-ink-gray-5"
							>
								<span class="h-2 w-2 rounded-sm" :style="{ backgroundColor: LEVEL_COLORS[level] }" />
								{{ level }}
							</button>
						</div>
						<span v-if="lastRunAt" class="text-[11px] text-ink-gray-3 tnum">updated {{ formatTs(lastRunAt).split(', ')[1] }}</span>
					</div>
				</div>

				<div class="min-h-0 flex-1 overflow-y-auto" ref="scroller">
					<LogTable :rows="rows" :loading="result.loading" @context="setContextRange" />
					<div v-if="rows.length < result.data?.total" class="flex justify-center border-t border-outline-gray-1 py-3">
						<Button label="Load more" @click="loadMore" :loading="result.loading" />
					</div>
				</div>
			</main>
		</div>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { createResource, Button, Dropdown, Select, TextInput, Tooltip, LoadingIndicator } from 'frappe-ui'
import { SearchIcon, XIcon, ArrowDownWideNarrow, ArrowUpNarrowWide, TerminalIcon, RadioTowerIcon } from 'lucide-vue-next'
import Histogram from '../components/Histogram.vue'
import FacetSidebar from '../components/FacetSidebar.vue'
import LogTable from '../components/LogTable.vue'
import FilterBuilder from '../components/FilterBuilder.vue'
import { TIME_RANGES, LEVEL_COLORS, LEVEL_ORDER, humanCount, formatTs } from '../utils/logs'
import { parseQuery } from '../utils/query'

const LIMIT = 100

const sources = ref([])
const source = ref('')
const searchInput = ref('')
const queryText = ref('')
const parsed = reactive({ levels: [], filters: {} })
const selectedFacets = reactive({})
const conditions = ref([])
const order = ref('desc')
const autoRefresh = ref(false)
const lastRunAt = ref(null)
const offset = ref(0)
const rows = ref([])

const now = Date.now()
const range = ref({ start: now - 24 * 3600 * 1000, end: now })
const presetMinutes = ref(1440)

const rangeOptions = TIME_RANGES.map((r) => ({
	label: r.label,
	onClick: () => applyPreset(r.minutes),
}))

const rangeLabel = computed(() => {
	const preset = TIME_RANGES.find((r) => r.minutes === presetMinutes.value)
	return preset ? preset.label : `${formatTs(range.value.start)} → ${formatTs(range.value.end)}`
})

const legendLevels = computed(() => {
	const counts = {}
	for (const bucket of histogram.value) {
		for (const [level, count] of Object.entries(bucket.counts)) {
			counts[level] = (counts[level] || 0) + count
		}
	}
	return LEVEL_ORDER.filter((lv) => counts[lv])
})

function applyPreset(minutes) {
	presetMinutes.value = minutes
	range.value = { start: Date.now() - minutes * 60 * 1000, end: Date.now() }
	runSearch(true)
}

function zoomToBucket(bucketMs) {
	const span = (result.data?.bucket_seconds || 60) * 1000
	presetMinutes.value = null
	range.value = { start: bucketMs, end: bucketMs + span }
	runSearch(true)
}

function setContextRange(row) {
	presetMinutes.value = null
	const around = 10 * 60 * 1000
	range.value = { start: row.ts - around, end: row.ts + around }
	runSearch(true)
}

const activeChips = computed(() => {
	const chips = []
	for (const [field, values] of Object.entries(selectedFacets)) {
		if (field === '__levels') continue
		for (const value of values || []) chips.push({ key: `${field}:${value}`, field, value })
	}
	for (const level of parsed.levels) chips.push({ key: `level:${level}`, field: 'level', value: level })
	for (const [field, values] of Object.entries(parsed.filters)) {
		for (const value of values) chips.push({ key: `q-${field}:${value}`, field, value })
	}
	return chips
})

const selectedLevels = computed(() => {
	const fromSidebar = [...(selectedFacets.__levels || [])]
	const seen = new Set(fromSidebar)
	return [...fromSidebar, ...parsed.levels.filter((lv) => !seen.has(lv))]
})

function mergedFilters() {
	const out = {}
	for (const [field, values] of [...Object.entries(parsed.filters), ...Object.entries(selectedFacets)]) {
		if (field === '__levels') continue
		out[field] = [...(out[field] || []), ...(values || [])]
	}
	return out
}

function toggleFacet(field, value) {
	selectedFacets[field] ||= []
	const list = selectedFacets[field]
	const index = list.indexOf(value)
	index >= 0 ? list.splice(index, 1) : list.push(value)
	if (!list.length) delete selectedFacets[field]
	runSearch(true)
}

function toggleAttr(key, value) {
	const field = `attr.${key}`
	const exists = conditions.value.findIndex(
		(c) => c.field === field && c.op === 'eq' && c.value === value,
	)
	if (exists >= 0) conditions.value.splice(exists, 1)
	else conditions.value.push({ field, op: 'eq', value })
	runSearch(true)
}

function removeChip(chip) {
	if (chip.key.startsWith('q-')) return
	if (chip.field === 'level') {
		const fromSidebar = selectedFacets.__levels || []
		if (fromSidebar.includes(chip.value)) toggleFacet('__levels', chip.value)
		else parsed.levels = parsed.levels.filter((lv) => lv !== chip.value)
	} else if (selectedFacets[chip.field]) {
		toggleFacet(chip.field, chip.value)
	} else {
		parsed.filters[chip.field] = (parsed.filters[chip.field] || []).filter((v) => v !== chip.value)
	}
	runSearch(true)
}

function clearAll() {
	for (const field of Object.keys(selectedFacets)) delete selectedFacets[field]
	parsed.levels = []
	parsed.filters = {}
	conditions.value = []
	runSearch(true)
}

function toggleOrder() {
	order.value = order.value === 'desc' ? 'asc' : 'desc'
	runSearch(false)
}

const OP_SYMBOL = { eq: '=', ne: '≠', gt: '>', lt: '<', gte: '≥', lte: '≤', contains: '~' }

const attrKeys = computed(() =>
	(result.data?.facets?.__attributes__ || []).map((a) => a.key),
)

const fieldOptions = computed(() => [
	{ label: 'product', value: 'product' },
	{ label: 'service', value: 'service' },
	{ label: 'level', value: 'level' },
	{ label: 'source', value: 'source' },
	{ label: 'resource_id', value: 'resource_id' },
	{ label: 'message', value: 'message' },
])

function applyConditions(next) {
	conditions.value = next
	runSearch(true)
}

function removeCondition(i) {
	conditions.value.splice(i, 1)
	runSearch(true)
}

const result = createResource({
	url: 'lens.lens.api.search_logs',
	method: 'POST',
	makeParams() {
		return {
			source: source.value,
			start: Math.floor(range.value.start),
			end: Math.floor(range.value.end),
			query: queryText.value,
			levels: selectedLevels.value,
			filters: mergedFilters(),
			conditions: conditions.value,
			limit: LIMIT,
			offset: offset.value,
			order: order.value,
		}
	},
	onSuccess(data) {
		lastRunAt.value = Date.now()
		if (offset.value > 0) rows.value = rows.value.concat(data.rows)
		else rows.value = data.rows
	},
	onError(error) {
		console.error(error)
	},
	transform(data) {
		data.facets ||= {}
		return data
	},
})

const histogram = computed(() => result.data?.histogram || [])

function runSearch(resetOffset = true) {
	if (!source.value) return
	const { query, levels, filters } = parseQuery(searchInput.value)
	queryText.value = query
	parsed.levels = levels
	parsed.filters = filters
	if (resetOffset) {
		offset.value = 0
		rows.value = []
	}
	result.reload()
}

function loadMore() {
	offset.value += LIMIT
	result.reload()
}

let timer = null
watch(autoRefresh, (enabled) => {
	clearInterval(timer)
	if (enabled) timer = setInterval(() => runSearch(true), 10000)
})
onBeforeUnmount(() => clearInterval(timer))

onMounted(async () => {
	const meta = await createResource({
		url: 'lens.lens.api.get_sources',
	}).fetch()
	sources.value = meta.sources
	source.value = meta.sources[0] || ''
	runSearch(true)
})
</script>
