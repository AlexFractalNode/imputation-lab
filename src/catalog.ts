// Everything the UI offers: methods (grouped by category), datasets and upload rules.

export type ParamDef =
  | { key: string, label: string, type: 'range', min: number, max: number, step: number, default: number }
  | { key: string, label: string, type: 'number', default: number }
  | { key: string, label: string, type: 'checkbox', default: boolean }
  | { key: string, label: string, type: 'select', options: { value: string, label: string }[], default: string }

export interface MethodDef {
  id: string
  label: string
  summary: string
  params: ParamDef[]
}

export interface MethodCategory {
  id: string
  label: string
  methods: MethodDef[]
}

const maxIter = (def: number, max: number): ParamDef =>
  ({ key: 'max_iter', label: 'Iterationen', type: 'range', min: 1, max, step: 1, default: def })

export const categories: MethodCategory[] = [
  {
    id: 'deletion',
    label: 'Deletion',
    methods: [
      { id: 'listwise', label: 'Listwise Deletion', summary: 'Entfernt jede Zeile mit mindestens einem fehlenden Wert.', params: [] },
      { id: 'pairwise', label: 'Pairwise Deletion', summary: 'Lässt die Daten unverändert; jede Korrelation nutzt alle verfügbaren Wertepaare.', params: [] },
      {
        id: 'drop_columns',
        label: 'Spalten entfernen',
        summary: 'Entfernt Spalten, deren Anteil fehlender Werte über dem Schwellwert liegt.',
        params: [{ key: 'max_missing_pct', label: 'max. fehlend (%)', type: 'range', min: 0, max: 100, step: 5, default: 30 }],
      },
    ],
  },
  {
    id: 'simple',
    label: 'Einfach',
    methods: [
      { id: 'mean', label: 'Mean', summary: 'Ersetzt Lücken durch den Mittelwert der Spalte.', params: [{ key: 'add_indicator', label: 'Indikator-Spalte', type: 'checkbox', default: false }] },
      { id: 'median', label: 'Median', summary: 'Ersetzt Lücken durch den Median der Spalte – robuster gegen Ausreißer.', params: [{ key: 'add_indicator', label: 'Indikator-Spalte', type: 'checkbox', default: false }] },
      { id: 'most_frequent', label: 'Mode', summary: 'Ersetzt Lücken durch den häufigsten Wert – auch für Textspalten.', params: [{ key: 'add_indicator', label: 'Indikator-Spalte', type: 'checkbox', default: false }] },
      {
        id: 'constant',
        label: 'Konstante',
        summary: 'Ersetzt Lücken durch einen festen Wert.',
        params: [
          { key: 'fill_value', label: 'Füllwert', type: 'number', default: 0 },
          { key: 'add_indicator', label: 'Indikator-Spalte', type: 'checkbox', default: false },
        ],
      },
    ],
  },
  {
    id: 'similarity',
    label: 'Ähnlichkeit',
    methods: [
      {
        id: 'knn',
        label: 'KNN',
        summary: 'Füllt Lücken mit dem Mittel der k ähnlichsten Zeilen.',
        params: [
          { key: 'n_neighbors', label: 'k', type: 'range', min: 1, max: 25, step: 1, default: 5 },
          { key: 'weights', label: 'Gewichtung', type: 'select', default: 'uniform', options: [{ value: 'uniform', label: 'gleich' }, { value: 'distance', label: 'nach Distanz' }] },
          { key: 'scale', label: 'Spalten standardisieren', type: 'checkbox', default: true },
        ],
      },
    ],
  },
  {
    id: 'model',
    label: 'Modellbasiert',
    methods: [
      { id: 'regression', label: 'Regression', summary: 'Sagt jede Lücke per linearer Regression aus den anderen Spalten vorher.', params: [{ key: 'stochastic', label: 'mit Zufallsrauschen', type: 'checkbox', default: false }] },
      { id: 'iterative', label: 'Iterative (MICE-artig)', summary: 'Modelliert reihum jede Spalte aus allen anderen, mehrere Durchgänge.', params: [maxIter(10, 30)] },
      {
        id: 'random_forest',
        label: 'Random Forest',
        summary: 'Wie Iterative, aber mit Random Forest als Modell (missForest-Idee) – erfasst nichtlineare Zusammenhänge.',
        params: [{ key: 'n_estimators', label: 'Bäume', type: 'range', min: 5, max: 100, step: 5, default: 30 }, maxIter(5, 10)],
      },
      { id: 'em', label: 'EM', summary: 'Schätzt Mittelwerte und Kovarianz einer Normalverteilung per Expectation-Maximization und füllt mit dem bedingten Erwartungswert.', params: [maxIter(100, 300)] },
    ],
  },
  {
    id: 'multiple',
    label: 'Multiple Imputation',
    methods: [
      {
        id: 'multiple',
        label: 'm Datensätze',
        summary: 'Erzeugt m plausible Datensätze statt eines einzigen; die Streuung zeigt die Unsicherheit.',
        params: [{ key: 'm', label: 'm', type: 'range', min: 2, max: 20, step: 1, default: 5 }, maxIter(10, 30)],
      },
    ],
  },
  {
    id: 'sota',
    label: 'State of the Art',
    methods: [
      { id: 'gradient_boosting', label: 'Gradient Boosting', summary: 'Iterative Imputation mit HistGradientBoosting – das Modell selbst verarbeitet NaN in den Prädiktoren.', params: [maxIter(5, 10)] },
    ],
  },
]

export const methodById = new Map(categories.flatMap(c => c.methods).map(m => [m.id, m]))

/** Methods that exist but cannot run in a browser. Shown as information only. */
export const outlook = [
  { label: 'GAIN', text: 'Generative Adversarial Nets für Imputation (Yoon et al., 2018). Braucht ein Deep-Learning-Framework.' },
  { label: 'HyperImpute', text: 'Wählt pro Spalte automatisch das beste Modell (Jarrett et al., 2022). Braucht PyTorch.' },
  { label: 'Native NaN', text: 'Modelle wie HistGradientBoosting kommen ganz ohne Imputation aus – NaN wird beim Split berücksichtigt.' },
]

export interface DatasetDef {
  id: string
  label: string
  note: string
  source: string
  spec: { kind: 'generated', name: string } | { kind: 'file', file: string }
}

export const datasets: DatasetDef[] = [
  { id: 'iris', label: 'Iris (vollständig)', note: '150 Zeilen, 4 Messwerte – Lücken werden eingestreut, die wahren Werte sind bekannt.', source: 'Fisher (1936), via seaborn-data', spec: { kind: 'file', file: 'iris.csv' } },
  { id: 'notebook_survey', label: 'Umfrage (nach Espig, vollständig)', note: '100 Zeilen: Age, Income, Satisfaction – unabhängig voneinander erzeugt wie im Vorlesungs-Notebook.', source: 'nach M. Espig, Notebook 08_01', spec: { kind: 'generated', name: 'notebook_survey' } },
  { id: 'penguins', label: 'Palmer Penguins (echte Lücken)', note: '344 Zeilen, einige fehlende Messwerte und Geschlechtsangaben.', source: 'Horst, Hill & Gorman (2020), CC0', spec: { kind: 'file', file: 'penguins.csv' } },
  { id: 'titanic', label: 'Titanic (echte Lücken)', note: '891 Zeilen; Alter fehlt bei rund 20 %, Deck bei den meisten.', source: 'via seaborn-data', spec: { kind: 'file', file: 'titanic.csv' } },
  { id: 'airquality', label: 'Airquality (echte Lücken)', note: '153 Tage in New York 1973; Ozon und Sonneneinstrahlung fehlen teilweise.', source: 'R datasets (Chambers et al., 1983)', spec: { kind: 'file', file: 'airquality.csv' } },
  { id: 'notebook_mar', label: 'Stress / Job (nach Espig, MAR)', note: 'Job_Satisfaction fehlt, wenn Stress_Level „Low“ ist.', source: 'nach M. Espig, Notebook 08_01', spec: { kind: 'generated', name: 'notebook_mar' } },
  { id: 'notebook_debt', label: 'Debt / Savings (nach Espig)', note: 'Savings fehlt, wenn Debt > 30000.', source: 'nach M. Espig, Notebook 08_01', spec: { kind: 'generated', name: 'notebook_debt' } },
]

export const uploadRules = {
  maxBytes: 5 * 1024 * 1024,
  maxRows: 10_000,
  maxCols: 50,
  extensions: ['.csv', '.tsv', '.txt'],
  text: [
    'CSV oder TSV, UTF-8, erste Zeile = Spaltennamen',
    'höchstens 5 MB, 10 000 Zeilen und 50 Spalten',
    'mindestens eine numerische Spalte, eindeutige Spaltennamen',
    'als fehlend gelten: leer, NA, N/A, NaN, null, ?',
  ],
}

/** Checks that can be done before the file is handed to Python. Returns an error message or null. */
export function precheckUpload(file: { name: string, size: number }): string | null {
  const name = file.name.toLowerCase()
  if (!uploadRules.extensions.some(ext => name.endsWith(ext)))
    return `Dateityp nicht unterstützt (${uploadRules.extensions.join(', ')}).`
  if (file.size === 0)
    return 'Die Datei ist leer.'
  if (file.size > uploadRules.maxBytes)
    return `Die Datei ist zu groß (${(file.size / 1024 / 1024).toFixed(1)} MB, erlaubt sind 5 MB).`
  return null
}
