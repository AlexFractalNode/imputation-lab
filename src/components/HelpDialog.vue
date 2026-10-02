<script setup lang="ts">
import { categories, outlook, uploadRules } from '../catalog'
import { methodHelp } from '../methodHelp'

// In-app help: explains every area of the interface and every method.
defineProps<{ repoUrl: string }>()
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <div class="dialog-backdrop" @click.self="emit('close')" @keydown.esc="emit('close')">
    <section
      class="dialog dialog--wide"
      role="dialog"
      aria-modal="true"
      aria-labelledby="help-title"
      data-verify-unit="help-dialog"
      data-verify-state="ready"
      :data-verify-count="Object.keys(methodHelp).length"
    >
      <header class="dialog__head">
        <h2 id="help-title">Hilfe</h2>
        <button type="button" class="btn btn--small" data-testid="close-help" @click="emit('close')">Schließen</button>
      </header>

      <div class="help">
        <h3>In drei Schritten</h3>
        <ol>
          <li><b>Datensatz wählen.</b> „Vollständig“ heißt: keine Lücken, die wahren Werte sind bekannt. „Echte Lücken“ heißt: Die Werte fehlen wirklich, niemand kennt sie.</li>
          <li><b>Fehlende Werte erzeugen</b> (nur bei vollständigen Daten): Mechanismus, Anteil und Spalte wählen. Das Tool entfernt Werte und merkt sich die Originale.</li>
          <li><b>Verfahren wählen</b> und das Ergebnis vergleichen. Jede Änderung wird sofort neu berechnet.</li>
        </ol>

        <h3>Die Mechanismen</h3>
        <dl>
          <dt>MCAR – Missing Completely at Random</dt>
          <dd>Jeder Wert der Spalte fehlt mit derselben Wahrscheinlichkeit. Der Ausfall hängt von nichts ab.</dd>
          <dt>MAR – Missing at Random</dt>
          <dd>Die Wahrscheinlichkeit hängt von einer <em>anderen, beobachteten</em> Spalte ab („abhängig von“): Je größer deren Wert, desto eher fehlt der Wert in der Zielspalte.</dd>
          <dt>MNAR – Missing Not at Random</dt>
          <dd>Die Wahrscheinlichkeit hängt vom Wert <em>selbst</em> ab: Große Werte fehlen häufiger. Die verbleibenden Werte sind dadurch systematisch zu klein.</dd>
        </dl>
        <p>Der eingestellte Anteil wird im Mittel getroffen. Der Seed legt fest, welche Zeilen es trifft – gleicher Seed, gleiches Ergebnis.</p>

        <h3>Was die Anzeige bedeutet</h3>
        <dl>
          <dt>Tabellen „Vorher“ und „Nachher“</dt>
          <dd>Wie <code>display(df)</code> im Notebook. <span class="help__nan">NaN</span> = fehlender Wert. <span class="help__imputed">Unterlegt</span> = vom Verfahren eingesetzt; der Tooltip zeigt den wahren Wert und die Abweichung. Durchgestrichen = Zeile wurde gelöscht. Die linke Spalte ist der ursprüngliche Zeilenindex.</dd>
          <dt>Verteilung</dt>
          <dd>Histogramm der gewählten Spalte: vorher (nur beobachtete Werte), nachher und – falls bekannt – die wahren Werte als Linie. Ein gutes Verfahren bringt „nachher“ nah an die Linie.</dd>
          <dt>Kennzahlen</dt>
          <dd>Anzahl, Mittelwert und Standardabweichung der gewählten Spalte. Die Prozentangabe ist die Abweichung von den wahren Werten (bzw. von „vorher“, wenn keine wahren Werte bekannt sind).</dd>
          <dt>Fehler (RMSE)</dt>
          <dd>Wurzel der mittleren quadrierten Abweichung zwischen eingesetzten und wahren Werten, in der Einheit der Spalte. Kleiner ist besser. Nur bei vollständigen Datensätzen verfügbar.</dd>
          <dt>Ausgeführter Python-Code</dt>
          <dd>Der Code, mit dem das Ergebnis berechnet wurde – zum Kopieren ins eigene Notebook. <code>cols</code> steht für die numerischen Spalten.</dd>
        </dl>

        <h3>Die Verfahren</h3>
        <template v-for="c in categories" :key="c.id">
          <h4>{{ c.label }}</h4>
          <dl>
            <template v-for="m in c.methods" :key="m.id">
              <dt>{{ m.label }}</dt>
              <dd>
                {{ methodHelp[m.id].how }}<br>
                <b>Geeignet:</b> {{ methodHelp[m.id].good }}<br>
                <b>Grenze:</b> {{ methodHelp[m.id].limit }}
              </dd>
            </template>
          </dl>
        </template>
        <h4>Nicht im Browser ausführbar</h4>
        <dl>
          <template v-for="o in outlook" :key="o.label">
            <dt>{{ o.label }}</dt>
            <dd>{{ o.text }}</dd>
          </template>
        </dl>

        <h3>Eigene Daten</h3>
        <ul>
          <li v-for="rule in uploadRules.text" :key="rule">{{ rule }}</li>
        </ul>
        <p>Die Datei wird nur im Browser gelesen und nirgendwohin übertragen. Nach dem Neuladen der Seite muss sie erneut gewählt werden.</p>

        <h3>Gut zu wissen</h3>
        <ul>
          <li>Modellbasierte Verfahren arbeiten nur auf numerischen Spalten. Textspalten füllt „Mode“.</li>
          <li>Tabellen zeigen höchstens 200 Zeilen; gerechnet wird immer mit allen.</li>
          <li>Der Link in der Adresszeile enthält alle Einstellungen und lässt sich teilen.</li>
          <li>Bei MNAR hilft ein Verfahren nur so weit, wie die anderen Spalten den fehlenden Wert erklären. Probiere MNAR einmal mit „Iris“ (Spalten hängen zusammen) und einmal mit „Umfrage“ (Spalten unabhängig).</li>
        </ul>
        <p>
          Ausführliche Dokumentation:
          <a :href="`${repoUrl}/blob/main/docs/BENUTZERHANDBUCH.md`" target="_blank" rel="noopener">Benutzerhandbuch</a> ·
          <a :href="`${repoUrl}/blob/main/docs/VERFAHREN.md`" target="_blank" rel="noopener">Verfahren im Detail</a> ·
          <a :href="`${repoUrl}/blob/main/docs/ARCHITEKTUR.md`" target="_blank" rel="noopener">Architektur</a>
        </p>
      </div>
    </section>
  </div>
</template>
