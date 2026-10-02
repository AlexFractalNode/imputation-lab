/** Longer explanations for the help dialog: what happens, when it fits, where it breaks. */
export const methodHelp: Record<string, { how: string, good: string, limit: string }> = {
  listwise: {
    how: 'df.dropna(): Jede Zeile mit mindestens einem NaN wird entfernt. In der Vorher-Tabelle sind diese Zeilen durchgestrichen.',
    good: 'Wenige Lücken, die rein zufällig entstanden sind (MCAR).',
    limit: 'Verliert schnell viele Zeilen. Bei MAR und MNAR ist der Rest nicht mehr repräsentativ – Mittelwerte verschieben sich.',
  },
  pairwise: {
    how: 'Die Daten bleiben unverändert. Für jede Korrelation werden alle Zeilen genutzt, in denen beide Spalten vorhanden sind. Die Tabelle unter den Kennzahlen zeigt Korrelation, Anzahl der Paare und zum Vergleich den Wert nach Listwise Deletion.',
    good: 'Korrelationen oder Kovarianzen berechnen, ohne Zeilen zu verschenken.',
    limit: 'Jede Zahl beruht auf einer anderen Stichprobe. Für Modelle, die vollständige Zeilen brauchen, hilft es nicht.',
  },
  drop_columns: {
    how: 'Entfernt Spalten, deren Anteil fehlender Werte über dem Schwellwert liegt.',
    good: 'Spalten, die fast leer sind (z. B. „deck“ im Titanic-Datensatz).',
    limit: 'Die Information der Spalte geht vollständig verloren; die übrigen Lücken bleiben.',
  },
  mean: {
    how: 'SimpleImputer(strategy="mean"): Jede Lücke bekommt den Mittelwert der beobachteten Werte ihrer Spalte.',
    good: 'Schneller erster Versuch bei wenigen Lücken.',
    limit: 'Alle Lücken erhalten denselben Wert: Im Histogramm entsteht eine Spitze, die Standardabweichung sinkt, Zusammenhänge zu anderen Spalten werden schwächer.',
  },
  median: {
    how: 'Wie Mean, aber mit dem Median.',
    good: 'Schiefe Verteilungen und Ausreißer – der Median wird von Extremwerten nicht verzerrt.',
    limit: 'Dieselbe Schwäche wie Mean: ein einziger Wert für alle Lücken.',
  },
  most_frequent: {
    how: 'Jede Lücke bekommt den häufigsten Wert der Spalte. Einziges Verfahren hier, das auch Textspalten füllt.',
    good: 'Kategoriale Spalten.',
    limit: 'Bläht die häufigste Kategorie auf. Bei stetigen Zahlen ist der häufigste Wert oft zufällig.',
  },
  constant: {
    how: 'Jede Lücke bekommt einen festen Wert, den du vorgibst.',
    good: 'Wenn „fehlt“ eine eigene Bedeutung hat, meist zusammen mit einer Indikator-Spalte.',
    limit: 'Verzerrt Mittelwert und Streuung stark, wenn der Wert nicht zu den Daten passt.',
  },
  knn: {
    how: 'KNNImputer: Für jede Zeile mit Lücke werden die k ähnlichsten Zeilen gesucht (Abstand über die vorhandenen Spalten) und deren Werte gemittelt. Mit „standardisieren“ zählen alle Spalten gleich stark.',
    good: 'Wenn ähnliche Zeilen ähnliche Werte haben, auch bei nichtlinearen Zusammenhängen.',
    limit: 'Hängt von k und der Skalierung ab; bei vielen Zeilen langsam. Kleines k ist unruhig, großes k nähert sich dem Mittelwert.',
  },
  regression: {
    how: 'Für jede Spalte mit Lücken wird eine lineare Regression auf den Zeilen ohne Lücke gelernt; Prädiktoren sind die anderen numerischen Spalten (deren Lücken dafür mit dem Mittelwert gefüllt werden). „Mit Zufallsrauschen“ addiert Rauschen in Größe der Residuen.',
    good: 'Lineare Zusammenhänge zwischen den Spalten.',
    limit: 'Ohne Rauschen liegen alle eingesetzten Werte exakt auf der Regressionsgeraden – Zusammenhänge wirken stärker, als sie sind.',
  },
  iterative: {
    how: 'IterativeImputer: Startet mit Mittelwerten und modelliert dann reihum jede Spalte aus allen anderen (BayesianRidge). Das wiederholt sich, bis sich die Werte kaum noch ändern oder die Iterationen aufgebraucht sind.',
    good: 'Mehrere Spalten mit Lücken, die sich gegenseitig erklären. Das ist die Idee hinter MICE.',
    limit: 'Ein einzelner Lauf liefert einen Datensatz (Single Imputation) und zeigt keine Unsicherheit. Lineares Modell.',
  },
  random_forest: {
    how: 'Wie Iterative, aber jede Spalte wird mit einem Random Forest vorhergesagt (die Idee von missForest).',
    good: 'Nichtlineare Zusammenhänge und Wechselwirkungen.',
    limit: 'Deutlich langsamer; kann keine Werte außerhalb des beobachteten Bereichs vorhersagen.',
  },
  em: {
    how: 'Expectation-Maximization für eine multivariate Normalverteilung: Abwechselnd werden die Lücken durch ihren bedingten Erwartungswert ersetzt (E-Schritt) und Mittelwerte und Kovarianz neu geschätzt (M-Schritt), bis sich nichts mehr ändert. Eigene numpy-Implementierung.',
    good: 'Annähernd normalverteilte, linear zusammenhängende Daten.',
    limit: 'Setzt Normalverteilung voraus. Wie Regression ohne Rauschen: Die eingesetzten Werte streuen zu wenig.',
  },
  multiple: {
    how: 'Der IterativeImputer läuft m-mal mit sample_posterior=True, also mit Zufallsziehung statt bestem Schätzwert. Angezeigt wird der erste Datensatz; der Tooltip jeder Zelle zeigt die Streuung über alle m Läufe.',
    good: 'Statistische Aussagen: jeden der m Datensätze auswerten und die Ergebnisse zusammenführen.',
    limit: 'm-facher Aufwand. Der einzelne eingesetzte Wert ist ungenauer (höherer RMSE) – das ist gewollt: Er soll plausibel streuen, nicht den Erwartungswert treffen.',
  },
  gradient_boosting: {
    how: 'Wie Iterative, aber mit HistGradientBoostingRegressor als Modell. Dieses Modell kann selbst mit NaN in den Prädiktoren umgehen.',
    good: 'Größere Datensätze mit nichtlinearen Zusammenhängen.',
    limit: 'Bei kleinen Datensätzen kein Vorteil gegenüber einfacheren Modellen; schwerer zu erklären.',
  },
}
