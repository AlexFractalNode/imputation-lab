<script setup lang="ts">
import { ref } from 'vue'
import { precheckUpload, uploadRules } from '../catalog'

// Lets the user pick a local CSV. The file is read in the browser only.
const emit = defineEmits<{ loaded: [name: string, csv: string], close: [] }>()

const error = ref('')
const reading = ref(false)

async function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  error.value = ''
  if (!file)
    return
  const problem = precheckUpload(file)
  if (problem) {
    error.value = problem
    input.value = ''
    return
  }
  reading.value = true
  try {
    const text = await file.text()
    if (text.includes('�')) {
      error.value = 'Die Datei ist nicht UTF-8-kodiert. Bitte als UTF-8 speichern.'
      return
    }
    emit('loaded', file.name, text)
  }
  catch (e) {
    error.value = `Die Datei konnte nicht gelesen werden: ${e instanceof Error ? e.message : String(e)}`
  }
  finally {
    reading.value = false
    input.value = ''
  }
}
</script>

<template>
  <div class="dialog-backdrop" @click.self="emit('close')" @keydown.esc="emit('close')">
    <section
      class="dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-title"
      data-verify-unit="upload-dialog"
      :data-verify-state="error ? 'error' : reading ? 'loading' : 'ready'"
      :data-verify-error="error || undefined"
    >
      <h2 id="upload-title">Eigenen Datensatz laden</h2>
      <p>Die Datei bleibt in deinem Browser – es wird nichts hochgeladen.</p>
      <ul class="dialog__rules">
        <li v-for="rule in uploadRules.text" :key="rule">{{ rule }}</li>
      </ul>
      <label class="dialog__file">
        <span>Datei auswählen</span>
        <input type="file" :accept="uploadRules.extensions.join(',')" :disabled="reading" data-testid="upload-input" @change="onFile">
      </label>
      <p v-if="error" class="dialog__error" role="alert">{{ error }}</p>
      <div class="dialog__actions">
        <button type="button" class="btn" @click="emit('close')">Schließen</button>
      </div>
    </section>
  </div>
</template>
