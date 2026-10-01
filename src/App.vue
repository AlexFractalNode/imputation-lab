<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { categories, datasets, methodById, outlook } from './catalog'
import DataFrameView from './components/DataFrameView.vue'
import HistogramChart from './components/HistogramChart.vue'
import UploadDialog from './components/UploadDialog.vue'
import { bootError, bootStage, bootState, restartEngine, runEngine } from './engineClient'
import type { DatasetSpec, EngineRequest, EngineResult, Matrix } from './types'
import { defaultParams, parseState, serializeState } from './urlState'

const REPO_URL = 'https://github.com/AlexFractalNode/imputation-lab'

const state = reactive(parseState(location.search))
const result = ref<EngineResult | null>(null)
const error = ref('')
const busy = ref(false)
const showUpload = ref(false)
const upload = ref<{ name: string, csv: string } | null>(null)
const copied = ref(false)

if (state.dataset !== 'upload' && !datasets.some(d => d.id === state.dataset))
  state.dataset = 'iris'
if (state.dataset === 'upload') // an uploaded file cannot survive a reload
  state.dataset = 'iris'

const category = ref(categories.find(c => c.methods.some(m => m.id === state.method))?.id ?? 'simple')
const method = computed(() => methodById.get(state.method)!)
const datasetDef = computed(() => datasets.find(d => d.id === state.dataset))
const canInject = computed(() => result.value ? !result.value.has_native_missing : true)
const selectedStats = computed(() => result.value?.stats.find(s => s.column === result.value!.column))

const gapsFirst = ref(true)
const gapRows = computed(() => {
  const t = result.value?.before
  if (!t || !gapsFirst.value)
    return undefined
  return new Set(t.index.filter((_, r) => t.rows[r].includes(null)))
})

const csvCache = new Map<string, string>()

async function datasetSpec(): Promise<DatasetSpec> {
  if (state.dataset === 'upload') {
    if (!upload.value)
      throw new Error('Es ist kein Datensatz geladen.')
    return { kind: 'csv', csv: upload.value.csv }
  }
  const def = datasetDef.value!
  if (def.spec.kind === 'generated')
    return def.spec
  const file = def.spec.file
  if (!csvCache.has(file)) {
    const response = await fetch(`${import.meta.env.BASE_URL}datasets/${file}`)
    if (!response.ok)
      throw new Error(`Datensatz ${file} konnte nicht geladen werden (HTTP ${response.status}).`)
    csvCache.set(file, await response.text())
  }
  return { kind: 'csv', csv: csvCache.get(file)! }
}

async function run() {
  busy.value = true
  try {
    const request: EngineRequest = {
      dataset: await datasetSpec(),
      missing: { mechanism: state.mechanism, rate: state.rate / 100, target: state.target, driver: state.driver },
      method: { id: state.method, params: { ...state.params } },
      column: state.column,
      seed: state.seed,
    }
    const response = await runEngine(request)
    if (response === null) // replaced by a newer request
      return
    if (response.ok) {
      result.value = response
      error.value = ''
      if (response.missing_applied) {
        state.target = response.missing_applied.target
        state.driver = response.missing_applied.driver
      }
      state.column = response.column
    }
    else {
      error.value = response.message
    }
  }
  catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
  finally {
    busy.value = false
  }
}

let timer: ReturnType<typeof setTimeout> | undefined
function schedule() {
  clearTimeout(timer)
  timer = setTimeout(run, 120)
}

watch(
  () => [state.dataset, state.mechanism, state.rate, state.target, state.driver, state.method, JSON.stringify(state.params), state.column, state.seed, upload.value],
  () => {
    history.replaceState(null, '', serializeState(state))
    schedule()
  },
)
run()

function selectDataset(id: string) {
  if (id === 'upload' && !upload.value) {
    showUpload.value = true
    return
  }
  state.dataset = id
  state.target = null
  state.driver = null
  state.column = null
}

function onUploaded(name: string, csv: string) {
  upload.value = { name, csv }
  showUpload.value = false
  state.dataset = 'upload'
  state.target = null
  state.driver = null
  state.column = null
}

function selectCategory(id: string) {
  category.value = id
  const first = categories.find(c => c.id === id)!.methods[0]
  selectMethod(first.id)
}

function selectMethod(id: string) {
  state.method = id
  state.params = defaultParams(id)
}

async function copyCode() {
  if (!result.value)
    return
  try {
    await navigator.clipboard.writeText(result.value.code)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  }
  catch {
    copied.value = false
  }
}

const num = (v: number | null | undefined, digits = 2) =>
  v === null || v === undefined ? '–' : Math.abs(v) >= 1000 ? v.toFixed(0) : v.toFixed(digits)

function delta(after: number | null | undefined, reference: number | null | undefined) {
  if (after == null || reference == null || reference === 0)
    return ''
  const pct = ((after - reference) / Math.abs(reference)) * 100
  return `${pct >= 0 ? '+' : ''}${pct.toFixed(0)} %`
}

const pairwise = computed(() => {
  const e = result.value?.extras
  if (!e || !e.corr_pairwise)
    return null
  return { pair: e.corr_pairwise as Matrix, list: e.corr_listwise as Matrix, n: e.n_pairwise as Matrix }
})

const pooled = computed(() => {
  const e = result.value?.extras
  if (!e || !e.pooled_mean || !result.value)
    return null
  const col = result.value.column
  return {
    m: e.m as number,
    mean: (e.pooled_mean as Record<string, number>)[col],
    sd: (e.between_sd as Record<string, number>)[col],
  }
})

// On a slide there is room for a few lines only: show the statements, not the imports.
const shownCode = computed(() => {
  const code = result.value?.code ?? ''
  if (!state.embed)
    return code
  return code.split('\n').filter(l => l.trim() && !/^(from|import) /.test(l)).join('\n')
})

const labState = computed(() => {
  if (bootState.value === 'error')
    return 'error'
  if (bootState.value === 'loading' || !result.value)
    return error.value ? 'error' : 'loading'
  return error.value ? 'error' : 'ready'
})
</script>

<template>
  <div
    class="lab"
    :class="{ 'lab--embed': state.embed }"
    data-verify-unit="lab"
    :data-verify-state="labState"
    :data-verify-error="labState === 'error' ? (bootError || error) : undefined"
    :data-busy="busy"
  >
    <header v-if="!state.embed" class="lab__header">
      <div>
        <h1>Imputation Lab</h1>
        <p>Fehlende Werte behandeln und vergleichen – mit echtem pandas und scikit-learn im Browser.</p>
      </div>
      <a class="btn" :href="REPO_URL" target="_blank" rel="noopener">Quellcode auf GitHub</a>
    </header>

    <div class="lab__body">
      <aside class="controls" aria-label="Einstellungen">
        <fieldset>
          <legend>1 · Datensatz</legend>
          <label class="field">
            <span class="sr-only">Datensatz</span>
            <select :value="state.dataset" data-testid="dataset" @change="selectDataset(($event.target as HTMLSelectElement).value)">
              <option v-for="d in datasets" :key="d.id" :value="d.id">{{ d.label }}</option>
              <option value="upload">{{ upload ? `Eigene Datei: ${upload.name}` : 'Eigene Datei laden …' }}</option>
            </select>
          </label>
          <p v-if="datasetDef" class="hint">{{ datasetDef.note }} <span class="hint__source">Quelle: {{ datasetDef.source }}</span></p>
          <button type="button" class="btn btn--small" data-testid="open-upload" @click="showUpload = true">Eigene CSV laden</button>
        </fieldset>

        <fieldset :disabled="!canInject">
          <legend>2 · Fehlende Werte erzeugen</legend>
          <p v-if="!canInject" class="hint">Dieser Datensatz hat echte Lücken – es wird nichts zusätzlich entfernt.</p>
          <template v-else>
            <div class="segmented" role="radiogroup" aria-label="Mechanismus">
              <button
                v-for="m in (['MCAR', 'MAR', 'MNAR'] as const)"
                :key="m"
                type="button"
                role="radio"
                :aria-checked="state.mechanism === m"
                :class="{ 'is-active': state.mechanism === m }"
                :data-testid="`mech-${m}`"
                @click="state.mechanism = m"
              >{{ m }}</button>
            </div>
            <label class="field field--range">
              <span>Anteil fehlend <output>{{ state.rate }} %</output></span>
              <input v-model.number="state.rate" type="range" min="5" max="80" step="5" data-testid="rate">
            </label>
            <label class="field">
              <span>in Spalte</span>
              <select v-model="state.target" data-testid="target">
                <option v-for="c in result?.numeric_columns ?? []" :key="c" :value="c">{{ c }}</option>
              </select>
            </label>
            <label v-if="state.mechanism === 'MAR'" class="field">
              <span>abhängig von</span>
              <select v-model="state.driver">
                <option v-for="c in (result?.numeric_columns ?? []).filter(c => c !== state.target)" :key="c" :value="c">{{ c }}</option>
              </select>
            </label>
            <p class="hint">
              <template v-if="state.mechanism === 'MCAR'">Jeder Wert fehlt mit derselben Wahrscheinlichkeit.</template>
              <template v-else-if="state.mechanism === 'MAR'">Je größer <code>{{ state.driver }}</code>, desto eher fehlt <code>{{ state.target }}</code>.</template>
              <template v-else>Je größer <code>{{ state.target }}</code> selbst, desto eher fehlt der Wert.</template>
            </p>
          </template>
        </fieldset>

        <fieldset>
          <legend>3 · Verfahren</legend>
          <div class="chips" role="tablist" aria-label="Kategorie">
            <button
              v-for="c in categories"
              :key="c.id"
              type="button"
              role="tab"
              :aria-selected="category === c.id"
              :class="{ 'is-active': category === c.id }"
              :data-testid="`cat-${c.id}`"
              @click="selectCategory(c.id)"
            >{{ c.label }}</button>
          </div>
          <div class="segmented segmented--wrap" role="radiogroup" aria-label="Verfahren">
            <button
              v-for="m in categories.find(c => c.id === category)!.methods"
              :key="m.id"
              type="button"
              role="radio"
              :aria-checked="state.method === m.id"
              :class="{ 'is-active': state.method === m.id }"
              :data-testid="`method-${m.id}`"
              @click="selectMethod(m.id)"
            >{{ m.label }}</button>
          </div>
          <p class="hint">{{ method.summary }}</p>
          <template v-for="p in method.params" :key="p.key">
            <label v-if="p.type === 'range'" class="field field--range">
              <span>{{ p.label }} <output>{{ state.params[p.key] }}</output></span>
              <input v-model.number="state.params[p.key]" type="range" :min="p.min" :max="p.max" :step="p.step" :data-testid="`param-${p.key}`">
            </label>
            <label v-else-if="p.type === 'number'" class="field">
              <span>{{ p.label }}</span>
              <input v-model.number="state.params[p.key]" type="number">
            </label>
            <label v-else-if="p.type === 'select'" class="field">
              <span>{{ p.label }}</span>
              <select v-model="state.params[p.key]">
                <option v-for="o in p.options" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
            </label>
            <label v-else class="field field--check">
              <input v-model="state.params[p.key]" type="checkbox">
              <span>{{ p.label }}</span>
            </label>
          </template>
          <label class="field field--inline">
            <span>Seed</span>
            <input v-model.number="state.seed" type="number" min="0" max="9999">
          </label>
        </fieldset>

        <details v-if="!state.embed" class="outlook">
          <summary>Ausblick: was im Browser nicht läuft</summary>
          <dl>
            <template v-for="o in outlook" :key="o.label">
              <dt>{{ o.label }}</dt>
              <dd>{{ o.text }}</dd>
            </template>
          </dl>
        </details>
      </aside>

      <main class="results">
        <div v-if="bootState === 'loading'" class="banner" role="status">
          <span class="spinner" aria-hidden="true" /> {{ bootStage }}
          <span class="banner__sub">Beim ersten Aufruf dauert das einige Sekunden.</span>
        </div>
        <div v-else-if="bootState === 'error'" class="banner banner--error" role="alert">
          Python konnte nicht gestartet werden: {{ bootError }}
          <button type="button" class="btn btn--small" @click="restartEngine(); run()">Erneut versuchen</button>
        </div>
        <div v-if="error && bootState !== 'error'" class="banner banner--error" role="alert" data-testid="error">
          {{ error }}
        </div>

        <template v-if="result">
          <div class="frames" :aria-busy="busy">
            <DataFrameView
              unit="dataframe-before"
              title="Vorher"
              :table="result.before"
              :missing-cells="result.missing_cells_before"
              :dropped="result.dropped_rows"
              :priority="gapRows"
            />
            <DataFrameView
              unit="dataframe-after"
              :title="`Nachher · ${method.label}`"
              :table="result.after"
              :missing-cells="result.missing_cells_after"
              :imputed="result.imputed_cells"
              :priority="gapRows"
            />
          </div>
          <label class="field field--check gaps-first">
            <input v-model="gapsFirst" type="checkbox" data-testid="gaps-first">
            <span>Zeilen mit Lücken zuerst anzeigen (der Index bleibt der ursprüngliche)</span>
          </label>

          <ul v-if="result.notes.length" class="notes" data-verify-unit="notes" data-verify-state="ready" :data-verify-count="result.notes.length">
            <li v-for="n in result.notes" :key="n">{{ n }}</li>
          </ul>

          <div class="analysis">
            <HistogramChart :histogram="result.histogram" :column="result.column" />

            <section class="stats" data-verify-unit="stats" data-verify-state="ready" :data-verify-count="result.stats.length">
              <header class="stats__head">
                <h2>Kennzahlen</h2>
                <label class="field field--inline">
                  <span>Spalte</span>
                  <select v-model="state.column" data-testid="column">
                    <option v-for="c in result.numeric_columns" :key="c" :value="c">{{ c }}</option>
                  </select>
                </label>
              </header>
              <table v-if="selectedStats" class="kpi">
                <thead>
                  <tr>
                    <th />
                    <th v-if="selectedStats.truth" scope="col">wahr</th>
                    <th scope="col">vorher</th>
                    <th scope="col">nachher</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th scope="row">Werte (n)</th>
                    <td v-if="selectedStats.truth">{{ selectedStats.truth.n }}</td>
                    <td>{{ selectedStats.before.n }}</td>
                    <td data-testid="n-after">{{ selectedStats.after?.n ?? '–' }}</td>
                  </tr>
                  <tr>
                    <th scope="row">Mittelwert</th>
                    <td v-if="selectedStats.truth">{{ num(selectedStats.truth.mean) }}</td>
                    <td>{{ num(selectedStats.before.mean) }}</td>
                    <td data-testid="mean-after">
                      {{ num(selectedStats.after?.mean) }}
                      <small>{{ delta(selectedStats.after?.mean, (selectedStats.truth ?? selectedStats.before).mean) }}</small>
                    </td>
                  </tr>
                  <tr>
                    <th scope="row">Standardabw.</th>
                    <td v-if="selectedStats.truth">{{ num(selectedStats.truth.std) }}</td>
                    <td>{{ num(selectedStats.before.std) }}</td>
                    <td data-testid="std-after">
                      {{ num(selectedStats.after?.std) }}
                      <small>{{ delta(selectedStats.after?.std, (selectedStats.truth ?? selectedStats.before).std) }}</small>
                    </td>
                  </tr>
                  <tr v-if="selectedStats.truth">
                    <th scope="row">Fehler (RMSE)</th>
                    <td colspan="2" class="kpi__muted">Abstand der imputierten zu den wahren Werten</td>
                    <td data-testid="rmse">{{ num(selectedStats.rmse) }}</td>
                  </tr>
                </tbody>
              </table>
              <p class="hint">
                Prozentangaben: Abweichung gegenüber {{ selectedStats?.truth ? 'den wahren Werten' : 'vorher' }}.
                Zeilen: {{ result.shape_before[0] }} → {{ result.shape_after[0] }} · Rechenzeit {{ result.elapsed_ms }} ms
              </p>
              <p v-if="pooled" class="hint" data-testid="pooled">
                Multiple Imputation (m = {{ pooled.m }}): Mittelwert über alle Läufe {{ num(pooled.mean) }},
                Streuung der Lauf-Mittelwerte ±{{ num(pooled.sd, 3) }}.
              </p>
              <div v-if="pairwise" class="corr">
                <h3>Korrelationen: pairwise (n) / listwise</h3>
                <table>
                  <thead>
                    <tr><th /><th v-for="l in pairwise.pair.labels" :key="l" scope="col">{{ l }}</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, i) in pairwise.pair.values" :key="i">
                      <th scope="row">{{ pairwise.pair.labels[i] }}</th>
                      <td v-for="(v, j) in row" :key="j">
                        {{ num(v) }} <small>({{ pairwise.n.values[i][j] }})</small> / {{ num(pairwise.list.values[i]?.[j]) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          <section class="code" data-verify-unit="code" data-verify-state="ready">
            <header>
              <h2>Ausgeführter Python-Code</h2>
              <button type="button" class="btn btn--small" @click="copyCode">{{ copied ? 'Kopiert' : 'Kopieren' }}</button>
            </header>
            <pre><code>{{ shownCode }}</code></pre>
          </section>
        </template>
        <div v-else-if="bootState !== 'error'" class="skeleton" aria-hidden="true" />
      </main>
    </div>

    <UploadDialog v-if="showUpload" @loaded="onUploaded" @close="showUpload = false" />
  </div>
</template>
