# Imputation Lab

**[Live-Tool öffnen](https://alexfractalnode.github.io/imputation-lab/)**

Fehlende Werte interaktiv behandeln und die Verfahren vergleichen – mit echtem
pandas und scikit-learn, die per [Pyodide](https://pyodide.org) direkt im Browser
laufen. Es gibt keinen Server: Auch eigene Dateien bleiben auf deinem Rechner.

Entstanden als Begleit-Tool zu einem Vortrag über Missing Values (Data Science,
Westsächsische Hochschule Zwickau, Prof. Dr. Mike Espig).

## Was das Tool kann

1. **Datensatz wählen** – eingebaute Beispiele oder eine eigene CSV-Datei.
2. **Fehlende Werte erzeugen** (nur bei vollständigen Daten) – nach MCAR, MAR oder
   MNAR, mit einstellbarem Anteil. Weil die wahren Werte bekannt sind, lässt sich
   der Fehler jedes Verfahrens messen (RMSE).
3. **Verfahren anwenden** und Vorher/Nachher vergleichen: DataFrame, Verteilung,
   Mittelwert, Standardabweichung – dazu der Python-Code, der gerade gelaufen ist.

| Kategorie | Verfahren | Umsetzung |
|---|---|---|
| Deletion | Listwise, Pairwise, Spalten entfernen | pandas |
| Einfach | Mean, Median, Mode, Konstante (+ Indikator-Spalte) | `SimpleImputer` |
| Ähnlichkeit | KNN | `KNNImputer` |
| Modellbasiert | Regression, Iterative (MICE-artig), Random Forest, EM | `LinearRegression`, `IterativeImputer`, eigene EM-Implementierung in numpy |
| Multiple Imputation | m Datensätze | `IterativeImputer(sample_posterior=True)` |
| State of the Art | Gradient Boosting | `IterativeImputer` mit `HistGradientBoostingRegressor` |

Deep-Learning-Verfahren (GAIN, HyperImpute) laufen nicht im Browser und werden
nur als Ausblick genannt.

Modellbasierte Verfahren arbeiten auf den numerischen Spalten; Textspalten lassen
sich mit „Mode“ füllen.

## Dokumentation

- [Benutzerhandbuch](docs/BENUTZERHANDBUCH.md) – Oberfläche, Kennzahlen, drei Experimente zum Einstieg
- [Verfahren im Detail](docs/VERFAHREN.md) – was jedes Verfahren tut und wie es umgesetzt ist
- [Architektur](docs/ARCHITEKTUR.md) – Aufbau, Entscheidungen, Tests

Im Tool selbst erklärt der Knopf **Hilfe** alle Funktionen.

## Eigene Daten

- CSV oder TSV, UTF-8, erste Zeile = Spaltennamen
- höchstens 5 MB, 10 000 Zeilen, 50 Spalten
- mindestens eine numerische Spalte, eindeutige Spaltennamen
- als fehlend gelten: leer, `NA`, `N/A`, `NaN`, `null`, `?`

## Lokal starten

Voraussetzungen: Node.js 24, für die Python-Tests zusätzlich [uv](https://docs.astral.sh/uv/).

```bash
npm install
npm run build      # lädt Pyodide + Pakete nach public/pyodide (ca. 40 MB) und baut nach dist/
npm run preview    # http://localhost:4173 – funktioniert danach ohne Internet
```

Entwicklung: `npm run fetch:pyodide` einmalig, dann `npm run dev`.

Tests: `npm run test:py` (Engine, mit denselben Paketversionen wie im Browser) und `npm test`.

## Aufbau

- `src/py/engine.py` – die gesamte Fachlogik in Python; läuft unverändert im Browser und in den Tests
- `src/worker/` – Web Worker, der Pyodide startet
- `src/` – Oberfläche (Vue 3)
- `scripts/fetch-pyodide.mjs` – holt Pyodide und prüft die Pakete gegen ihre SHA-256-Summen

Versionen im Browser: Pyodide 0.29.5 (Python 3.13), pandas 2.3.3, scikit-learn 1.7.0.

## Datensätze

| Datensatz | Herkunft |
|---|---|
| Iris | R. A. Fisher (1936); Datei aus [seaborn-data](https://github.com/mwaskom/seaborn-data) |
| Palmer Penguins | Horst, Hill & Gorman (2020), CC0; Datei aus seaborn-data |
| Titanic | Datei aus seaborn-data |
| Airquality | R-Paket `datasets` (Chambers et al., 1983); über [Rdatasets](https://vincentarelbundock.github.io/Rdatasets/) |
| Umfrage, Stress/Job, Debt/Savings | nachgebaut nach den Beispielen im Vorlesungs-Notebook von Prof. Dr. Mike Espig |

## Literatur

- D. B. Rubin, „Inference and missing data“, *Biometrika* 63(3), 1976.
- R. J. A. Little, D. B. Rubin, *Statistical Analysis with Missing Data*, Wiley.
- S. van Buuren, *Flexible Imputation of Missing Data*, CRC Press – [online](https://stefvanbuuren.name/fimd/).
- scikit-learn User Guide, [Imputation of missing values](https://scikit-learn.org/stable/modules/impute.html).

## Lizenz

[MIT](LICENSE). Die Beispiel-Datensätze stehen unter ihren jeweiligen Bedingungen (siehe oben).
