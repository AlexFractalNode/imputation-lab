<script setup lang="ts">
import { computed } from 'vue'
import type { Cell, ImputedCell, Table } from '../types'

// A table that looks like `display(df)` in a notebook.
const props = defineProps<{
  unit: string
  title: string
  table: Table
  missingCells: number
  imputed?: ImputedCell[]
  dropped?: Cell[]
  /** Index labels of rows to show first (rows that had gaps). The index column keeps the original labels. */
  priority?: Set<Cell>
}>()

const imputedMap = computed(() => new Map((props.imputed ?? []).map(c => [`${c.row}:${c.col}`, c])))
const droppedSet = computed(() => new Set(props.dropped ?? []))
const order = computed(() => {
  const all = props.table.rows.map((_, r) => r)
  const first = props.priority
  if (!first || !first.size)
    return all
  return [...all.filter(r => first.has(props.table.index[r])), ...all.filter(r => !first.has(props.table.index[r]))]
})
const isFloat = computed(() => props.table.dtypes.map(t => t.startsWith('float')))

function format(value: Cell, col: number): string {
  if (value === null)
    return 'NaN'
  if (typeof value === 'number') {
    if (!isFloat.value[col])
      return String(value)
    const text = Number.isInteger(value) ? value.toFixed(1) : value.toFixed(Math.abs(value) >= 1000 ? 1 : 2)
    return text
  }
  return String(value)
}

function tooltip(cell: ImputedCell | undefined, value: Cell): string | undefined {
  if (!cell)
    return undefined
  const parts = ['imputiert']
  if (cell.truth !== undefined && cell.truth !== null) {
    parts.push(`wahrer Wert: ${cell.truth}`)
    if (typeof value === 'number' && typeof cell.truth === 'number')
      parts.push(`Abweichung: ${(value - cell.truth).toFixed(2)}`)
  }
  if (typeof cell.sd === 'number')
    parts.push(`Streuung über die Läufe: ±${cell.sd.toFixed(2)}`)
  return parts.join(' · ')
}

const state = computed(() => (props.table.rows.length ? 'ready' : 'empty'))
</script>

<template>
  <section
    class="df-view"
    :data-verify-unit="unit"
    :data-verify-state="state"
    :data-verify-count="table.total_rows"
  >
    <header class="df-view__head">
      <h2>{{ title }}</h2>
      <span class="df-view__shape">
        {{ table.total_rows }} Zeilen × {{ table.columns.length }} Spalten ·
        <span :class="{ 'is-missing-count': missingCells > 0 }">{{ missingCells }} NaN</span>
      </span>
    </header>
    <div class="df-view__scroll" tabindex="0" :aria-label="`${title}: Tabelle, scrollbar`">
      <table v-if="state === 'ready'" class="df">
        <thead>
          <tr>
            <th />
            <th v-for="name in table.columns" :key="name" scope="col">{{ name }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in order" :key="r" :class="{ 'is-dropped': droppedSet.has(table.index[r]) }">
            <th scope="row">{{ table.index[r] }}</th>
            <td
              v-for="(value, c) in table.rows[r]"
              :key="c"
              :class="{
                'is-nan': value === null,
                'is-imputed': imputedMap.has(`${r}:${c}`),
                'is-text': typeof value === 'string',
              }"
              :title="tooltip(imputedMap.get(`${r}:${c}`), value)"
            >{{ format(value, c) }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="df-view__empty">Keine Zeilen übrig.</p>
    </div>
    <p v-if="table.total_rows > table.rows.length" class="df-view__more">
      Anzeige: erste {{ table.rows.length }} von {{ table.total_rows }} Zeilen – gerechnet wird mit allen.
    </p>
  </section>
</template>
