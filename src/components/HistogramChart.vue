<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Histogram } from '../types'

// Distribution of one column: observed values before, values after the method,
// and (if known) the true distribution as an outline.
const props = defineProps<{ histogram: Histogram | null, column: string }>()

const W = 520
const H = 210
const M = { top: 10, right: 8, bottom: 26, left: 34 }
const hover = ref<number | null>(null)

const series = computed(() => {
  const c = props.histogram?.counts ?? {}
  return {
    before: c.before ?? null,
    after: c.after ?? null,
    truth: c.truth ?? null,
  }
})

const bins = computed(() => (props.histogram ? props.histogram.edges.length - 1 : 0))
const maxCount = computed(() => Math.max(1, ...Object.values(props.histogram?.counts ?? {}).flat()))
const binWidth = computed(() => (W - M.left - M.right) / Math.max(1, bins.value))
const y = (count: number) => M.top + (H - M.top - M.bottom) * (1 - count / maxCount.value)
const x = (bin: number) => M.left + bin * binWidth.value

const truthPath = computed(() => {
  const t = series.value.truth
  if (!t)
    return ''
  let d = `M${x(0)},${y(0)}`
  t.forEach((count, i) => {
    d += ` L${x(i)},${y(count)} L${x(i + 1)},${y(count)}`
  })
  return `${d} L${x(t.length)},${y(0)}`
})

const yTicks = computed(() => {
  const step = Math.max(1, Math.ceil(maxCount.value / 4))
  const ticks = []
  for (let v = 0; v <= maxCount.value; v += step) ticks.push(v)
  return ticks
})

const fmt = (v: number) => (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1))
const xTicks = computed(() => {
  const e = props.histogram?.edges ?? []
  if (!e.length)
    return []
  return [0, Math.round(bins.value / 2), bins.value].map(i => ({ i, label: fmt(e[i]) }))
})

const state = computed(() => (props.histogram ? 'ready' : 'empty'))
</script>

<template>
  <figure class="chart" data-verify-unit="histogram" :data-verify-state="state" :data-verify-count="bins">
    <figcaption class="chart__head">
      <h2>Verteilung: <code>{{ column }}</code></h2>
      <ul class="legend">
        <li v-if="series.before"><span class="swatch swatch--before" />vorher (beobachtet)</li>
        <li v-if="series.after"><span class="swatch swatch--after" />nachher</li>
        <li v-if="series.truth"><span class="swatch swatch--truth" />wahre Werte</li>
      </ul>
    </figcaption>
    <div class="chart__plot">
      <svg v-if="histogram" :viewBox="`0 0 ${W} ${H}`" role="img" :aria-label="`Histogramm der Spalte ${column}, vorher und nachher`">
        <g class="chart__grid">
          <template v-for="t in yTicks" :key="t">
            <line :x1="M.left" :x2="W - M.right" :y1="y(t)" :y2="y(t)" />
            <text :x="M.left - 6" :y="y(t) + 4" text-anchor="end">{{ t }}</text>
          </template>
          <text v-for="t in xTicks" :key="`x${t.i}`" :x="x(t.i)" :y="H - 8" :text-anchor="t.i === 0 ? 'start' : t.i === bins ? 'end' : 'middle'">{{ t.label }}</text>
        </g>
        <g v-for="i in bins" :key="i">
          <rect
            v-if="series.before"
            class="bar bar--before"
            :x="x(i - 1) + 1"
            :width="Math.max(1, binWidth / 2 - 2)"
            :y="y(series.before[i - 1])"
            :height="y(0) - y(series.before[i - 1])"
            rx="1.5"
          />
          <rect
            v-if="series.after"
            class="bar bar--after"
            :x="x(i - 1) + binWidth / 2"
            :width="Math.max(1, binWidth / 2 - 2)"
            :y="y(series.after[i - 1])"
            :height="y(0) - y(series.after[i - 1])"
            rx="1.5"
          />
        </g>
        <path v-if="truthPath" class="truth" :d="truthPath" />
        <rect
          v-for="i in bins"
          :key="`h${i}`"
          class="hit"
          :class="{ 'is-hover': hover === i - 1 }"
          :x="x(i - 1)"
          :width="binWidth"
          :y="M.top"
          :height="H - M.top - M.bottom"
          @mouseenter="hover = i - 1"
          @mouseleave="hover = null"
        />
      </svg>
      <p v-else class="chart__empty">Keine numerischen Werte in dieser Spalte.</p>
      <p v-if="histogram && hover !== null" class="chart__tip" role="status">
        {{ fmt(histogram.edges[hover]) }} – {{ fmt(histogram.edges[hover + 1]) }}:
        <template v-if="series.before">vorher <b>{{ series.before[hover] }}</b></template>
        <template v-if="series.after"> · nachher <b>{{ series.after[hover] }}</b></template>
        <template v-if="series.truth"> · wahr <b>{{ series.truth[hover] }}</b></template>
      </p>
      <p v-else-if="histogram" class="chart__tip chart__tip--idle">Balken überfahren für genaue Werte.</p>
    </div>
  </figure>
</template>
