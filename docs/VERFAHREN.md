# Verfahren im Detail

Was jedes Verfahren im Lab tut, wie es umgesetzt ist und wo es an Grenzen stößt.
Der Code steht in [`src/py/engine.py`](../src/py/engine.py).

Schreibweise: $Y$ ist die Datenmatrix, $Y_{obs}$ der beobachtete und $Y_{mis}$ der
fehlende Teil, $M$ die Indikatormatrix ($M_{ij}=1$, wenn der Wert fehlt).

## Die Mechanismen

Die Einteilung stammt von Rubin (1976).

| | Definition | Bedeutung |
|---|---|---|
| **MCAR** | $P(M \mid Y) = P(M)$ | Ausfall hängt von nichts ab |
| **MAR** | $P(M \mid Y) = P(M \mid Y_{obs})$ | Ausfall hängt nur von beobachteten Werten ab |
| **MNAR** | $P(M \mid Y)$ hängt von $Y_{mis}$ ab | Ausfall hängt vom fehlenden Wert selbst ab |

MAR und MNAR lassen sich an den Daten allein nicht unterscheiden, denn dazu müsste
man die fehlenden Werte kennen.

### Umsetzung im Lab (`inject_missing`)

Für jede Zeile $i$ wird eine Ausfallwahrscheinlichkeit $p_i$ bestimmt und der Wert
der Zielspalte mit dieser Wahrscheinlichkeit entfernt.

- **MCAR:** $p_i = r$ (der eingestellte Anteil).
- **MAR:** $p_i = \sigma(a + 2{,}5 \cdot z_i)$, wobei $z_i$ der standardisierte Wert
  der Auslöser-Spalte ist und $\sigma$ die logistische Funktion.
- **MNAR:** dieselbe Formel, aber $z_i$ ist der standardisierte Wert der
  **Zielspalte** selbst.

Der Achsenabschnitt $a$ wird per Bisektion so gewählt, dass der Mittelwert aller
$p_i$ genau $r$ ist. So trifft jeder Mechanismus im Mittel denselben Anteil, und
die Ergebnisse sind vergleichbar.

## Deletion

### Listwise Deletion
`df.dropna()` – jede Zeile mit mindestens einem fehlenden Wert wird entfernt.
Unverzerrt nur bei MCAR; bei vielen Spalten gehen schnell viele Zeilen verloren:
Fehlen in $k$ Spalten unabhängig je $p$ der Werte, bleiben nur $(1-p)^k$ der Zeilen.

### Pairwise Deletion
`df.corr(min_periods=1)` – jede Korrelation nutzt alle Zeilen, in denen **beide**
Spalten vorhanden sind. Die Daten selbst bleiben unverändert. Das Lab zeigt je
Paar die Korrelation, die Zahl der genutzten Paare und den Listwise-Wert zum
Vergleich. Nachteil: Jede Zahl beruht auf einer anderen Teilstichprobe.

### Spalten entfernen
Spalten mit einem Anteil fehlender Werte über dem Schwellwert werden gelöscht.

## Einfache Imputation

`SimpleImputer(strategy=…)`, spaltenweise.

| Verfahren | eingesetzter Wert |
|---|---|
| Mean | Mittelwert der beobachteten Werte |
| Median | Median der beobachteten Werte |
| Mode | häufigster Wert (auch für Textspalten) |
| Konstante | frei gewählter Wert |

Alle Lücken einer Spalte bekommen denselben Wert. Folgen: Die Streuung sinkt
(bei Mean und Anteil $r$ ungefähr um den Faktor $\sqrt{1-r}$), Zusammenhänge zu
anderen Spalten werden abgeschwächt, und bei MAR/MNAR ist schon der Mittelwert der
beobachteten Werte verzerrt.

**Indikator-Spalte** (`add_indicator`): Zusätzlich entsteht je Spalte eine
0/1-Spalte „hat gefehlt“. Für Vorhersagemodelle kann das Fehlen selbst eine
nützliche Information sein.

## Ähnlichkeit: KNN

`KNNImputer(n_neighbors=k, weights=…)`.

Für jede Zeile mit Lücke werden die $k$ nächsten Zeilen gesucht, die in der
betreffenden Spalte einen Wert haben. Der Abstand wird nur über Spalten berechnet,
die in beiden Zeilen vorhanden sind (`nan_euclidean`). Eingesetzt wird der
Mittelwert der Nachbarn, bei `weights='distance'` gewichtet mit dem Kehrwert des
Abstands.

- **k:** kleines k folgt lokalen Mustern, ist aber empfindlich gegen Ausreißer;
  großes k glättet und nähert sich dem Spaltenmittel.
- **Standardisieren:** Ohne Skalierung dominieren Spalten mit großen Zahlen den
  Abstand. Das Lab standardisiert vor der Imputation (`StandardScaler`) und rechnet
  danach zurück.

## Modellbasiert

### Regression
Wie im Vorlesungs-Notebook: Für jede Spalte mit Lücken wird eine lineare Regression
auf den Zeilen gelernt, in denen die Spalte vorhanden ist. Prädiktoren sind die
übrigen numerischen Spalten; deren eigene Lücken werden dafür mit dem Mittelwert
gefüllt.

Ohne Zusatz liegen alle eingesetzten Werte exakt auf der Regressionsgeraden –
Zusammenhänge werden überschätzt, die Streuung unterschätzt. Mit der Option
**mit Zufallsrauschen** (stochastische Regressions-Imputation) wird normalverteiltes
Rauschen in Größe der Residuenstreuung addiert.

### Iterative (MICE-artig)
`IterativeImputer(max_iter=…)` mit `BayesianRidge`.

1. Alle Lücken mit dem Spaltenmittel füllen.
2. Reihum jede Spalte mit Lücken als Zielgröße nehmen, aus allen anderen Spalten
   vorhersagen und die Lücken mit der Vorhersage überschreiben.
3. Schritt 2 wiederholen, bis sich kaum noch etwas ändert oder `max_iter` erreicht ist.

Im Unterschied zur einfachen Regression profitieren die Modelle von den bereits
verbesserten Werten der anderen Spalten. Ein einzelner Lauf ist **Single
Imputation**; in der scikit-learn-Dokumentation ist der Imputer als experimentell
gekennzeichnet.

### Random Forest
Derselbe iterative Ablauf, aber mit `RandomForestRegressor` als Modell. Das
entspricht der Idee von missForest (Stekhoven & Bühlmann, 2012). Erfasst
nichtlineare Zusammenhänge; kann nicht über den beobachteten Wertebereich hinaus
vorhersagen.

### EM
Eigene numpy-Implementierung (`em_impute`) für das Modell
$Y \sim \mathcal{N}(\mu, \Sigma)$ (Dempster, Laird & Rubin, 1977).

- **E-Schritt:** Für jede Zeile mit beobachtetem Teil $o$ und fehlendem Teil $m$:

  $$\hat{y}_m = \mu_m + \Sigma_{mo}\Sigma_{oo}^{-1}(y_o - \mu_o)$$

  Dazu kommt die bedingte Kovarianz $\Sigma_{mm} - \Sigma_{mo}\Sigma_{oo}^{-1}\Sigma_{om}$,
  die im M-Schritt zur Kovarianz addiert wird.
- **M-Schritt:** $\mu$ und $\Sigma$ aus den vervollständigten Daten neu schätzen.

Wiederholt wird, bis sich $\mu$ und $\Sigma$ nicht mehr ändern. Eingesetzt wird der
bedingte Erwartungswert. EM schätzt $\mu$ und $\Sigma$ korrekt; die eingesetzten
Einzelwerte streuen aber – wie bei Regression ohne Rauschen – zu wenig.

Im Notebook wird EM über `fancyimpute.IterativeImputer` gezeigt. Dieses Paket ist
in Pyodide nicht verfügbar und setzt auch kein EM im engeren Sinn um; deshalb die
eigene Implementierung.

## Multiple Imputation

`IterativeImputer(sample_posterior=True)`, $m$-mal mit verschiedenen Seeds.

Statt des besten Schätzwerts wird jeder Wert aus der Vorhersageverteilung
**gezogen**. Jeder Lauf ergibt einen anderen plausiblen Datensatz. Das eigentliche
Vorgehen (van Buuren):

1. $m$ Datensätze erzeugen,
2. jeden getrennt auswerten,
3. die $m$ Ergebnisse zusammenführen – die Unterschiede zwischen ihnen zeigen, wie
   unsicher das Ergebnis wegen der fehlenden Werte ist.

Das Lab zeigt den ersten Datensatz, im Tooltip die Streuung jeder Zelle über die
$m$ Läufe und unter den Kennzahlen den Mittelwert über alle Läufe samt Streuung der
Lauf-Mittelwerte. Der RMSE ist hier höher als bei Iterative – das ist gewollt: Die
Werte sollen realistisch streuen, nicht den Erwartungswert treffen.

## State of the Art

### Gradient Boosting
Iterativer Ablauf mit `HistGradientBoostingRegressor`. Das Modell behandelt
fehlende Werte in den Prädiktoren selbst: Beim Aufteilen eines Knotens lernt es,
in welchen Ast Zeilen mit NaN gehören.

### Nur als Ausblick
- **Native NaN-Behandlung:** Wer nur vorhersagen will, kann mit solchen Modellen
  ganz auf Imputation verzichten.
- **GAIN** (Yoon et al., 2018): Ein Generator füllt Lücken, ein Diskriminator
  versucht zu erkennen, welche Werte eingesetzt sind.
- **HyperImpute** (Jarrett et al., 2022): iterative Imputation, die je Spalte
  automatisch das beste Modell wählt.

Beide brauchen ein Deep-Learning-Framework und laufen nicht im Browser.

## Wie das Lab misst

| Kennzahl | Berechnung |
|---|---|
| RMSE | $\sqrt{\tfrac{1}{n}\sum (\hat{y}_i - y_i)^2}$ über die eingesetzten Zellen der Spalte |
| Mittelwert, Standardabweichung | über alle vorhandenen Werte der Spalte (Std. mit $n-1$) |
| Abweichung in % | (nachher − wahr) / \|wahr\| |

## Literatur

- D. B. Rubin (1976). Inference and missing data. *Biometrika* 63(3), 581–592.
- R. J. A. Little, D. B. Rubin. *Statistical Analysis with Missing Data.* Wiley.
- S. van Buuren. *Flexible Imputation of Missing Data.* Chapman & Hall/CRC.
- C. K. Enders (2022). *Applied Missing Data Analysis*, 2. Aufl. Guilford Press.
- A. P. Dempster, N. M. Laird, D. B. Rubin (1977). Maximum likelihood from incomplete data via the EM algorithm. *JRSS B* 39(1), 1–38.
- D. J. Stekhoven, P. Bühlmann (2012). MissForest. *Bioinformatics* 28(1), 112–118.
- J. Yoon, J. Jordon, M. van der Schaar (2018). GAIN. *ICML*, PMLR 80.
- D. Jarrett et al. (2022). HyperImpute. *ICML*, PMLR 162.
- scikit-learn User Guide: Imputation of missing values.
