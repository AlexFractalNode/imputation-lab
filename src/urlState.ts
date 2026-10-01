import { methodById } from './catalog'

// The lab's settings live in the URL so that a link (or the talk's iframe) opens a defined state.

export interface LabState {
  dataset: string
  mechanism: 'MCAR' | 'MAR' | 'MNAR'
  rate: number // percent
  target: string | null
  driver: string | null
  method: string
  params: Record<string, number | string | boolean>
  column: string | null
  seed: number
  embed: boolean
}

export const defaults: LabState = {
  dataset: 'iris',
  mechanism: 'MCAR',
  rate: 30,
  target: 'petal_length',
  driver: null,
  method: 'mean',
  params: {},
  column: null,
  seed: 0,
  embed: false,
}

export function defaultParams(method: string): Record<string, number | string | boolean> {
  const def = methodById.get(method)
  return def ? Object.fromEntries(def.params.map(p => [p.key, p.default])) : {}
}

const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, n))

export function parseState(search: string): LabState {
  const q = new URLSearchParams(search)
  const state: LabState = { ...defaults, params: {} }

  const mech = q.get('mech')
  if (mech === 'MCAR' || mech === 'MAR' || mech === 'MNAR')
    state.mechanism = mech
  const rate = Number(q.get('rate'))
  if (q.has('rate') && Number.isFinite(rate))
    state.rate = clamp(Math.round(rate), 5, 80)
  const seed = Number(q.get('seed'))
  if (q.has('seed') && Number.isInteger(seed))
    state.seed = clamp(seed, 0, 9999)
  if (q.get('ds'))
    state.dataset = q.get('ds')!
  if (q.has('ds') && !q.has('target'))
    state.target = null
  if (q.get('target'))
    state.target = q.get('target')
  if (q.get('driver'))
    state.driver = q.get('driver')
  if (q.get('col'))
    state.column = q.get('col')
  if (q.get('method') && methodById.has(q.get('method')!))
    state.method = q.get('method')!
  state.embed = q.get('embed') === '1'

  state.params = defaultParams(state.method)
  for (const def of methodById.get(state.method)?.params ?? []) {
    const raw = q.get(`p.${def.key}`)
    if (raw === null)
      continue
    if (def.type === 'checkbox') {
      state.params[def.key] = raw === '1'
    }
    else if (def.type === 'select') {
      if (def.options.some(o => o.value === raw))
        state.params[def.key] = raw
    }
    else {
      const n = Number(raw)
      if (Number.isFinite(n))
        state.params[def.key] = def.type === 'range' ? clamp(n, def.min, def.max) : n
    }
  }
  return state
}

export function serializeState(state: LabState): string {
  const q = new URLSearchParams()
  q.set('ds', state.dataset)
  q.set('mech', state.mechanism)
  q.set('rate', String(state.rate))
  if (state.target)
    q.set('target', state.target)
  if (state.driver)
    q.set('driver', state.driver)
  q.set('method', state.method)
  for (const [key, value] of Object.entries(state.params))
    q.set(`p.${key}`, typeof value === 'boolean' ? (value ? '1' : '0') : String(value))
  if (state.column)
    q.set('col', state.column)
  if (state.seed)
    q.set('seed', String(state.seed))
  if (state.embed)
    q.set('embed', '1')
  return `?${q.toString()}`
}
