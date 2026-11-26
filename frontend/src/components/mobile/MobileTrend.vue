<template>
	<div v-if="!values.length" class="trend-empty">{{ t('No sales in this period') }}</div>
	<div v-else class="mobile-trend">
		<svg
			viewBox="0 0 340 150"
			role="img"
			:aria-label="t('Daily net sales for the selected period')"
		>
			<defs>
				<linearGradient id="mobile-sales-fill" x1="0" x2="0" y1="0" y2="1">
					<stop offset="0" stop-color="#008f83" stop-opacity=".32" />
					<stop offset="1" stop-color="#008f83" stop-opacity=".03" />
				</linearGradient>
			</defs>
			<g v-for="tick in ticks" :key="tick.value">
				<line x1="47" x2="330" :y1="tick.y" :y2="tick.y" stroke="var(--border)" />
				<text x="40" :y="tick.y + 4" text-anchor="end">{{ tick.label }}</text>
			</g>
			<path v-if="points.length > 1" :d="area" fill="url(#mobile-sales-fill)" />
			<path
				v-if="points.length > 1"
				:d="line"
				fill="none"
				stroke="#008f83"
				stroke-width="3"
				stroke-linejoin="round"
			/>
			<circle
				v-for="(point, i) in points"
				:key="i"
				:cx="point.x"
				:cy="point.y"
				:r="points.length === 1 ? 5 : 2.5"
				fill="#008f83"
			>
				<title>{{ labels[i] }}: {{ values[i] }}</title>
			</circle>
			<text
				v-for="(point, i) in points"
				v-show="i === 0 || i === points.length - 1 || (points.length < 9 && i % 2 === 0)"
				:key="'label' + i"
				:x="point.x"
				y="144"
				:text-anchor="i === 0 ? 'start' : i === points.length - 1 ? 'end' : 'middle'"
			>
				{{ shortLabel(labels[i]) }}
			</text>
		</svg>
		<p v-if="values.length === 1">
			{{ t('Choose 7 days or Month to see your sales trend.') }}
		</p>
	</div>
</template>
<script setup>
import { computed } from 'vue'
import { t } from '@/lib/i18n'
const props = defineProps({ result: { type: Object, default: null } })
const values = computed(() => (props.result?.values || []).map((value) => Number(value) || 0))
const labels = computed(() => props.result?.labels || [])
const minimum = computed(() => Math.min(0, ...values.value))
const maximum = computed(() => Math.max(1, ...values.value))
const y = (value) => 122 - ((value - minimum.value) / (maximum.value - minimum.value)) * 104
const points = computed(() =>
	values.value.map((value, i) => ({
		x: values.value.length === 1 ? 190 : 47 + (i / (values.value.length - 1)) * 283,
		y: y(value),
	})),
)
const ticks = computed(() =>
	Array.from({ length: 5 }, (_, i) => {
		const value = minimum.value + ((maximum.value - minimum.value) * i) / 4
		return {
			value,
			y: y(value),
			label: Intl.NumberFormat('en', {
				notation: 'compact',
				maximumFractionDigits: 1,
			}).format(value),
		}
	}),
)
const line = computed(() =>
	points.value.map((point, i) => `${i ? 'L' : 'M'}${point.x},${point.y}`).join(' '),
)
const area = computed(
	() => line.value + ` L${points.value.at(-1).x},${y(0)} L${points.value[0].x},${y(0)} Z`,
)
function shortLabel(value) {
	return /^\d{4}-\d{2}-\d{2}$/.test(value) ? value.slice(5) : value
}
</script>
<style scoped>
.mobile-trend svg {
	width: 100%;
	height: auto;
	overflow: visible;
}
.mobile-trend text {
	font: 11px var(--font);
	fill: var(--muted);
}
.mobile-trend p,
.trend-empty {
	font-size: 13px;
	color: var(--muted);
	text-align: center;
	margin: 12px 0;
}
.trend-empty {
	min-height: 190px;
	display: grid;
	place-content: center;
}
</style>
