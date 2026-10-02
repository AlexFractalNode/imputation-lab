# Architektur

Wie das Imputation Lab aufgebaut ist und warum.

## Überblick

```
Browser
├── Oberfläche (Vue 3, Haupt-Thread)
│     App.vue ── Einstellungen ⇄ URL (urlState.ts)
│        │  Anfrage (JSON)            ▲ Antwort (JSON)
│        ▼                            │
│     engineClient.ts ── postMessage ─┤
│                                     │
└── Web Worker (pyodide.worker.ts)    │
      Pyodide = CPython als WebAssembly
      pandas · scikit-learn · numpy
      engine.py: run(request) ────────┘
```

Es gibt keinen Server. Die Seite besteht aus statischen Dateien; gerechnet wird
im Browser des Nutzers.

## Die drei Schichten

### 1. Engine – `src/py/engine.py`

Die gesamte Fachlogik in normalem Python. Einziger Einstieg ist

```python
run(request_json: str) -> str
```

Die Funktion ist zustandslos: Jede Anfrage enthält alles (Datensatz, Mechanismus,
Verfahren, Parameter, Seed), jede Antwort ebenfalls (beide Tabellen, Kennzahlen,
Histogramm, Code, Hinweise). `run` wirft nie eine Ausnahme, sondern liefert bei
Fehlern `{"ok": false, "code": …, "message": …}`.

Ablauf einer Anfrage:

1. `load_dataset` – erzeugt einen Beispiel-Datensatz oder liest und prüft die CSV (`parse_csv`, `validate_frame`).
2. `inject_missing` – entfernt Werte nach MCAR/MAR/MNAR (nur bei vollständigen Daten).
3. `impute` – wendet das gewählte Verfahren an und liefert den passenden Code-Schnipsel.
4. `_run` – berechnet Kennzahlen, RMSE, Histogramm und baut die Antwort.

Weil die Datei keine Browser-Abhängigkeit hat, läuft sie unverändert unter
normalem Python – so wird sie getestet (`tests/test_engine.py`).

### 2. Worker – `src/worker/pyodide.worker.ts`

Lädt Pyodide, dann pandas und scikit-learn, schreibt `engine.py` ins virtuelle
Dateisystem und importiert sie. Danach reicht er Anfragen an `engine.run` weiter.
Python läuft im Worker, damit die Oberfläche während einer Berechnung bedienbar
bleibt.

`src/engineClient.ts` kapselt den Worker: Es läuft immer nur eine Berechnung;
kommt währenddessen eine neue Anfrage, wird nur die jüngste aufgehoben
(„latest wins“). So stauen sich beim Ziehen eines Reglers keine Berechnungen.

### 3. Oberfläche – `src/`

| Datei | Aufgabe |
|---|---|
| `App.vue` | Layout, Zustand, Auslösen der Berechnung |
| `catalog.ts` | Liste der Verfahren mit Parametern, Datensätze, Upload-Regeln |
| `methodHelp.ts` | Erklärtexte für den Hilfe-Dialog |
| `urlState.ts` | Einstellungen ⇄ Adresszeile (teilbare Links, Einbettung) |
| `components/DataFrameView.vue` | Tabelle im `display(df)`-Stil |
| `components/HistogramChart.vue` | Verteilung vorher / nachher / wahr |
| `components/UploadDialog.vue` | lokale Datei wählen und vorprüfen |
| `components/HelpDialog.vue` | Hilfe |

Ein neues Verfahren braucht drei Stellen: einen Zweig in `impute()` (engine.py),
einen Eintrag in `catalog.ts` und einen Erklärtext in `methodHelp.ts`. Ein Test
stellt sicher, dass kein Verfahren ohne Erklärung bleibt.

## Entscheidungen

**Echtes Python statt Nachbau in JavaScript.** Das Tool soll zeigen, was
`SimpleImputer`, `KNNImputer` und `IterativeImputer` wirklich tun. Mit Pyodide
läuft exakt die Bibliothek aus der Vorlesung; der angezeigte Code ist der
ausgeführte Code. Preis: rund 40 MB beim ersten Laden.

**Pyodide selbst gehostet.** `scripts/fetch-pyodide.mjs` kopiert die Laufzeit aus
dem npm-Paket und lädt die Pakete einmalig vom offiziellen CDN nach
`public/pyodide/`, geprüft gegen die SHA-256-Summen aus `pyodide-lock.json`. Zur
Laufzeit wird kein fremder Server gebraucht – das Tool funktioniert nach
`npm run build` auch ohne Internet.

**Feste Versionen.** Pyodide 0.29.5 bringt Python 3.13, pandas 2.3.3 und
scikit-learn 1.7.0 mit. Die Tests laufen mit genau diesen Versionen, damit Browser
und Testumgebung dasselbe rechnen.

**Zustand in der URL.** Jede Einstellung steht in der Adresszeile. Dadurch lassen
sich Zustände verlinken, und die Vortragsfolie kann das Lab mit `?embed=1&…` in
einem definierten Zustand einbetten.

**Maschinenlesbarer Zustand im DOM.** Wichtige Bereiche tragen
`data-verify-unit`, `data-verify-state` (`loading | empty | ready | error`) und
`data-verify-count`. Tests und Automatisierung lesen diese Attribute statt Texte
zu durchsuchen.

## Tests

| Befehl | prüft |
|---|---|
| `npm run test:py` | Engine: Mechanismen treffen den Anteil und hängen von der richtigen Spalte ab; jedes Verfahren füllt alle numerischen Lücken und lässt beobachtete Werte unverändert; EM findet bekannte Parameter wieder; Sonderfälle (leere Spalte, keine Zeile übrig, konstante Spalte, Textspalten); CSV-Regeln; JSON-Vertrag von `run` |
| `npm test` | URL-Zustand, Upload-Vorprüfung, Vollständigkeit von Katalog und Hilfe |
| `npx vue-tsc --noEmit` | Typen |

## Veröffentlichung

`.github/workflows/pages.yml` führt bei jedem Push auf `main` die Tests aus, baut
mit `BASE_PATH=/imputation-lab/` und veröffentlicht `dist/` auf GitHub Pages.
`public/pyodide/` liegt nicht im Repository; der Build holt es jedes Mal neu.
