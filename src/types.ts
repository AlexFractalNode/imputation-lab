export type Cell = number | string | boolean | null

export interface Table {
  columns: string[]
  dtypes: string[]
  index: Cell[]
  rows: Cell[][]
  total_rows: number
}

export interface Describe {
  n: number
  mean: number | null
  std: number | null
  min: number | null
  max: number | null
}

export interface ColumnStats {
  column: string
  missing: number
  before: Describe
  after: Describe | null
  truth: Describe | null
  rmse: number | null
}

export interface ImputedCell {
  row: number
  col: number
  truth?: Cell
  sd?: number | null
}

export interface Matrix {
  labels: string[]
  values: (number | null)[][]
}

export interface Histogram {
  edges: number[]
  counts: Partial<Record<'before' | 'after' | 'truth', number[]>>
}

export interface MissingSpec {
  mechanism: 'MCAR' | 'MAR' | 'MNAR'
  rate: number
  target: string | null
  driver: string | null
}

export interface EngineResult {
  ok: true
  before: Table
  after: Table
  dropped_rows: Cell[]
  imputed_cells: ImputedCell[]
  has_truth: boolean
  has_native_missing: boolean
  missing_applied: MissingSpec | null
  numeric_columns: string[]
  column: string
  stats: ColumnStats[]
  histogram: Histogram | null
  corr_before: Matrix | null
  corr_after: Matrix | null
  corr_truth: Matrix | null
  extras: Record<string, unknown>
  code: string
  notes: string[]
  shape_before: [number, number]
  shape_after: [number, number]
  missing_cells_before: number
  missing_cells_after: number
  elapsed_ms: number
}

export interface EngineFailure {
  ok: false
  code: string
  message: string
}

export type EngineResponse = EngineResult | EngineFailure

export type DatasetSpec =
  | { kind: 'generated', name: string }
  | { kind: 'csv', csv: string }

export interface EngineRequest {
  dataset: DatasetSpec
  missing: MissingSpec | null
  method: { id: string, params: Record<string, number | string | boolean> }
  column: string | null
  seed: number
}
