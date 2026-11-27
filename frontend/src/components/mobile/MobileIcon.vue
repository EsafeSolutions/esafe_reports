<template>
	<svg
		:width="size"
		:height="size"
		viewBox="0 0 24 24"
		fill="none"
		stroke="currentColor"
		stroke-width="1.7"
		stroke-linecap="round"
		stroke-linejoin="round"
		aria-hidden="true"
	>
		<template v-for="(path, i) in paths[name] || paths.chart" :key="i">
			<path :d="path" />
		</template>
	</svg>
</template>
<script setup>
defineProps({
	name: { type: String, default: 'chart' },
	size: { type: [Number, String], default: 24 },
})
const paths = {
	home: ['m3 10 9-7 9 7v11h-6v-7H9v7H3Z'],
	box: ['m12 2 9 5v10l-9 5-9-5V7Z', 'm3 7 9 5 9-5M12 12v10M7.5 4.5l9 5'],
	inventory: ['M8 2h8v7H8ZM2 15h8v7H2ZM14 15h8v7h-8ZM12 9v3M6 15v-3h12v3'],
	search: ['M20 20l-5-5M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z'],
	back: ['m10 5-7 7 7 7M3 12h18'],
	chart: ['M4 20V10a1 1 0 0 1 2 0v10M11 20V5a1 1 0 0 1 2 0v15M18 20V2a1 1 0 0 1 2 0v18'],
	reports: ['M7 3h10a3 3 0 0 1 3 3v14l-4-2-4 2-4-2-4 2V6a3 3 0 0 1 3-3Z', 'M8 8h8M8 12h6'],
	receipt: ['M5 2h14v20l-3-2-4 2-4-2-3 2V2Z', 'M8 7h8M8 11h6'],
	bell: ['M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9', 'M10 21h4'],
	settings: [
		'm10 2-.6 2.3-2.1 1.2L5 5l-2 3.5 1.7 1.8v2.4L3 14.5 5 18l2.3-.5 2.1 1.2L10 21h4l.6-2.3 2.1-1.2 2.3.5 2-3.5-1.7-1.8v-2.4L21 8.5 19 5l-2.3.5-2.1-1.2L14 2Z',
		'M16 11.5a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
	],
	calendar: ['M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2Z', 'M7 2v4M17 2v4M3 9h18'],
	chevron: ['m9 5 7 7-7 7'],
	down: ['m6 9 6 6 6-6'],
	clock: ['M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z', 'M12 6v6l4 2'],
	globe: [
		'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',
		'M2 12h20M12 2c-6 6-6 14 0 20 6-6 6-14 0-20Z',
	],
	appearance: ['M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z', 'M12 2v20M12 5a7 7 0 0 1 0 14'],
	store: [
		'M3 9h18l-2-6H5L3 9Z',
		'M4 10v11h16V10M9 21v-7h6v7M2 9a3 3 0 0 0 5 2 3 3 0 0 0 5 0 3 3 0 0 0 5 0 3 3 0 0 0 5-2',
	],
	grid: ['M3 3h7v7H3ZM14 3h7v7h-7ZM3 14h7v7H3ZM14 14h7v7h-7Z'],
	return: ['m8 4-5 5 5 5M3 9h12a6 6 0 0 1 0 12h-3'],
	refresh: ['M20 7a9 9 0 1 0 1 9M20 2v6h-6'],
	close: ['m6 6 12 12M18 6 6 18'],
	download: ['M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5'],
	check: ['m5 12 4 4L19 6'],
	phone: ['M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2ZM10 18h4'],
	share: ['M12 16V2m-4 4 4-4 4 4M7 9H3v13h18V9h-4'],
	offline: [
		'm2 2 20 20M5 12a10 10 0 0 1 4-2m5 0a10 10 0 0 1 5 2M2 8a16 16 0 0 1 3-2m5-2a16 16 0 0 1 12 4M8 16a6 6 0 0 1 8 0M12 20h.01',
	],
}
</script>
