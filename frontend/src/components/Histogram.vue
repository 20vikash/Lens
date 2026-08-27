<template>
	<div class="rounded-lg border border-outline-gray-1 bg-surface-white shadow-sm">
		<div class="flex items-center justify-between px-3 pb-1 pt-2.5 text-[10px] font-medium uppercase tracking-wider text-ink-gray-4">
			<span>Distribution</span>
			<span class="tnum normal-case tracking-normal text-ink-gray-3">{{ humanCount(total) }} events · {{ formatBucket(start) }} → {{ formatBucket(end) }}</span>
		</div>
		<div ref="chart" class="h-32 w-full"></div>
	</div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { LEVEL_COLORS, LEVEL_ORDER, formatBucket, humanCount } from '../utils/logs'

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
	data: { type: Array, default: () => [] },
	start: Number,
	end: Number,
	bucketSeconds: { type: Number, default: 60 },
	total: { type: Number, default: 0 },
	loading: Boolean,
})

const emit = defineEmits(['zoom'])
const chart = ref(null)
let instance = null

function filledData() {
	if (!props.data.length) return []
	const bucketMs = props.bucketSeconds * 1000
	const byBucket = new Map(props.data.map((d) => [d.bucket, d.counts]))
	const start = Math.floor(props.start / bucketMs) * bucketMs
	const end = props.end
	const out = []
	for (let t = start; t <= end; t += bucketMs) {
		out.push({ bucket: t, counts: byBucket.get(t) || {} })
	}
	return out
}

function render() {
	if (!instance) return
	instance.resize()
	const data = filledData()
	const levels = LEVEL_ORDER.filter((lv) => props.data.some((d) => d.counts[lv]))
	instance.setOption(
		{
		animation: false,
		grid: { left: 28, right: 16, top: 18, bottom: 6, containLabel: true },
		tooltip: {
				trigger: 'axis',
				axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(0,0,0,0.04)' } },
				backgroundColor: '#171717',
				borderWidth: 0,
				padding: [8, 12],
				textStyle: { color: '#fafafa', fontSize: 11 },
				formatter(params) {
					const lines = [`<b>${formatBucket(params[0].value[0])}</b>`]
					for (const p of [...params].reverse()) {
						if (!p.value[1]) continue
						lines.push(`${p.marker} ${p.seriesName}&nbsp;&nbsp;<b>${p.value[1]}</b>`)
					}
					lines.push(`<span style="opacity:0.5">click to zoom in</span>`)
					return lines.join('<br/>')
				},
			},
		xAxis: {
			type: 'time',
			min: props.start - (props.bucketSeconds * 1000) / 2,
			max: props.end + (props.bucketSeconds * 1000) / 2,
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: { show: false },
			splitLine: { show: false },
		},
			yAxis: {
				type: 'value',
				splitNumber: 2,
				splitLine: { lineStyle: { color: '#f3f3f3' } },
				axisLabel: {
					width: 38,
					overflow: 'truncate',
					formatter: (v) => humanCount(v),
					fontSize: 10,
					color: '#a3a3a3',
				},
			},
			series: levels.map((level) => ({
				name: level,
				type: 'bar',
				stack: 'logs',
				itemStyle: { color: LEVEL_COLORS[level] },
				barMaxWidth: '100%',
				barMinWidth: 2,
				data: data.map((d) => [d.bucket, d.counts[level] || 0]),
			})),
		},
		true,
	)
}

onMounted(() => {
	instance = echarts.init(chart.value)
	instance.on('click', (params) => emit('zoom', params.value[0]))
	window.addEventListener('resize', resize)
	render()
})
onBeforeUnmount(() => window.removeEventListener('resize', resize))

function resize() {
	instance?.resize()
}

watch(() => [props.data, props.start, props.end], render, { deep: true })
watch(
	() => props.loading,
	(loading) => chart.value && (chart.value.style.opacity = loading ? 0.5 : 1),
)
</script>
