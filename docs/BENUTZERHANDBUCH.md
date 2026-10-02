# Benutzerhandbuch

Das Imputation Lab zeigt, was verschiedene Verfahren mit fehlenden Werten machen.
Links stellst du ein, rechts siehst du sofort das Ergebnis. Dieselbe Erklärung in
Kurzform findest du im Tool unter **Hilfe**.

## 1. Der Grundgedanke

Um ein Imputationsverfahren zu beurteilen, muss man wissen, welche Werte eigentlich
richtig gewesen wären. Bei echten Daten weiß das niemand. Das Lab dreht den Spieß
deshalb um:

1. Es nimmt einen **vollständigen** Datensatz.
2. Es **entfernt** absichtlich Werte – nach einem Mechanismus, den du wählst.
3. Es lässt ein Verfahren die Lücken füllen.
4. Es **vergleicht** die eingesetzten mit den ursprünglichen Werten.

Bei Datensätzen mit echten Lücken entfällt Schritt 2 und der Vergleich mit den
wahren Werten; dort siehst du nur, wie sich Verteilung und Kennzahlen ändern.

## 2. Die Oberfläche

### Datensatz

| Datensatz | Zeilen | Besonderheit |
|---|---|---|
| Iris (vollständig) | 150 | vier stark zusammenhängende Messwerte – gut, um den Nutzen modellbasierter Verfahren zu sehen |
| Umfrage (nach Espig, vollständig) | 100 | Age, Income, Satisfaction, **unabhängig** voneinander erzeugt – hier kann kein Verfahren besser sein als der Mittelwert |
| Palmer Penguins | 344 | wenige echte Lücken, auch in einer Textspalte |
| Titanic | 891 | viele echte Lücken (Alter, Deck) |
| Airquality | 153 | echte Lücken in Ozon und Sonneneinstrahlung |
| Stress / Job (nach Espig) | 23 | Job_Satisfaction fehlt bei Stress_Level „Low“ |
| Debt / Savings (nach Espig) | 23 | Savings fehlt bei Debt > 30000 |

**Eigene CSV laden:** Die Datei wird nur im Browser gelesen. Voraussetzungen:

- CSV oder TSV, UTF-8, erste Zeile = Spaltennamen
- höchstens 5 MB, 10 000 Zeilen, 50 Spalten
- mindestens eine numerische Spalte, eindeutige Spaltennamen
- als fehlend gelten: leer, `NA`, `N/A`, `NaN`, `null`, `?`

Enthält deine Datei schon Lücken, wird sie wie ein Datensatz mit echten Lücken
behandelt. Ist sie vollständig, kannst du Lücken erzeugen.

### Fehlende Werte erzeugen

- **Mechanismus** – wovon es abhängt, ob ein Wert fehlt:
  - **MCAR:** von nichts. Jeder Wert fehlt mit derselben Wahrscheinlichkeit.
  - **MAR:** von einer anderen, beobachteten Spalte („abhängig von“). Je größer
    deren Wert, desto eher fehlt der Wert in der Zielspalte.
  - **MNAR:** vom Wert selbst. Große Werte fehlen häufiger.
- **Anteil fehlend** – 5 bis 80 % der Werte der Zielspalte.
- **in Spalte** – die Spalte, in der Werte entfernt werden.
- **Seed** (unter „Verfahren“) – legt die Zufallszahlen fest. Gleicher Seed, gleiche
  Lücken und gleiches Ergebnis; ein anderer Seed zeigt, wie stark das Ergebnis vom
  Zufall abhängt.

### Verfahren

Sechs Kategorien, darunter jeweils die Verfahren und ihre Parameter. Was jedes
Verfahren tut, steht in [VERFAHREN.md](VERFAHREN.md).

### Tabellen „Vorher“ und „Nachher“

Sie sehen aus wie `display(df)` in einem Notebook.

| Darstellung | Bedeutung |
|---|---|
| rotes **NaN** | Wert fehlt |
| türkis unterlegt, punktiert unterstrichen | vom Verfahren eingesetzt; Tooltip zeigt wahren Wert und Abweichung |
| durchgestrichene Zeile (in „Vorher“) | Zeile wurde vom Verfahren gelöscht |
| linke Spalte | ursprünglicher Zeilenindex |

Standardmäßig stehen Zeilen mit Lücken oben, damit man sie sofort sieht. Der Index
verrät die ursprüngliche Position; das Häkchen unter den Tabellen stellt die
Originalreihenfolge wieder her. Angezeigt werden höchstens 200 Zeilen, gerechnet
wird immer mit allen.

### Verteilung

Histogramm der gewählten Spalte mit bis zu drei Reihen:

- **vorher (beobachtet)** – nur die Werte, die nach dem Entfernen noch da sind
- **nachher** – nach Anwendung des Verfahrens
- **wahre Werte** (Linie) – die ursprüngliche Verteilung, falls bekannt

Typische Bilder: Mean erzeugt eine einzelne hohe Säule. Bei MNAR liegt „vorher“
links von der Linie. Ein gutes Verfahren bringt „nachher“ auf die Linie.

### Kennzahlen

Für die gewählte Spalte: Anzahl, Mittelwert, Standardabweichung – jeweils wahr,
vorher, nachher. Die Prozentzahl hinter „nachher“ ist die Abweichung von den
wahren Werten (ohne wahre Werte: von „vorher“).

**Fehler (RMSE):** Wurzel aus dem Mittel der quadrierten Abweichungen zwischen
eingesetzten und wahren Werten. Einheit wie die Spalte, kleiner ist besser.

Bei **Pairwise Deletion** erscheint zusätzlich eine Korrelationstabelle, bei
**Multiple Imputation** der Mittelwert über alle Läufe und dessen Streuung.

### Ausgeführter Python-Code

Der Code, der das Ergebnis erzeugt hat – mit den aktuell eingestellten Parametern.
`cols` steht für die numerischen Spalten.

## 3. Drei Experimente zum Einstieg

**A · Warum der Mittelwert nicht reicht**
Iris, MCAR, 30 %, Spalte `petal_length`, Verfahren *Mean*. Im Histogramm entsteht
eine Säule, die es in den echten Daten nicht gibt; die Standardabweichung sinkt.
Wechsle zu *KNN*: Die Verteilung folgt wieder der Linie, der RMSE fällt von etwa
1,4 auf etwa 0,3.

**B · Was MNAR anrichtet – und wann ein Modell trotzdem hilft**
Umfrage (nach Espig), MNAR, 30 %, Spalte `Income`, Verfahren *Listwise Deletion*:
Der Mittelwert liegt bei rund 50 000 statt 61 000 – die großen Werte fehlen.
*Mean*, *KNN* und *Iterative* ändern daran nichts. Die Spalten sind unabhängig,
also verrät nichts, wie groß der fehlende Wert war.

Jetzt dieselbe Einstellung mit Iris und `petal_length`: Listwise und Mean landen
bei 3,12 statt 3,76. *KNN* und *Iterative* kommen dagegen auf etwa 3,7. Hier
verraten die anderen Messwerte der Blüte, wie groß der fehlende Wert war.

Merksatz: Bei MNAR hilft ein Verfahren nur so weit, wie die beobachteten Spalten
den fehlenden Wert erklären. Ob das so ist, sieht man den echten Daten nicht an.

**C · Wann Modelle nichts nützen**
Umfrage (nach Espig), MCAR, 30 %, Spalte `Income`. Vergleiche *Mean* und
*Iterative*: Der RMSE ist fast gleich. Die Spalten wurden unabhängig erzeugt, also
gibt es nichts, woraus ein Modell lernen könnte.

## 4. Grenzen des Tools

- Lücken werden immer nur in **einer** Spalte erzeugt.
- MAR und MNAR sind als „größere Werte fehlen häufiger“ umgesetzt; andere Formen
  (z. B. Ausfall an beiden Rändern) gibt es nicht.
- Modellbasierte Verfahren nutzen nur numerische Spalten.
- Der RMSE misst, wie gut einzelne Werte getroffen werden. Für statistische
  Aussagen zählt aber auch, ob Streuung und Zusammenhänge stimmen – deshalb immer
  auch Verteilung und Standardabweichung ansehen.
- Deep-Learning-Verfahren laufen nicht im Browser.

## 5. Wenn etwas nicht funktioniert

| Meldung | Ursache und Abhilfe |
|---|---|
| „Python-Laufzeit wird geladen …“ bleibt lange stehen | Beim ersten Aufruf werden rund 40 MB geladen. Bei langsamer Verbindung warten; danach liegt alles im Browser-Cache. |
| „Python konnte nicht gestartet werden“ | Netzwerkfehler oder sehr alter Browser. „Erneut versuchen“ klicken. |
| „Die Datei ist nicht UTF-8-kodiert“ | In Excel als „CSV UTF-8“ speichern. |
| „Es wird mindestens eine numerische Spalte benötigt“ | Zahlen mit Komma als Dezimaltrenner werden als Text gelesen – auf Punkt umstellen. |
| „MAR braucht eine zweite numerische Spalte“ | Der Datensatz hat nur eine Zahlenspalte; MCAR oder MNAR wählen. |
