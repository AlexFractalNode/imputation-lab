import { ref } from 'vue'
import type { EngineRequest, EngineResponse } from './types'

// Thin wrapper around the Pyodide worker. Only the newest request matters:
// while one is running, at most one follow-up is kept and older ones are dropped.

export const bootState = ref<'loading' | 'ready' | 'error'>('loading')
export const bootStage = ref('Python-Laufzeit wird geladen …')
export const bootError = ref('')

let worker: Worker
let nextId = 0
let running: { id: number, resolve: (r: EngineResponse | null) => void } | null = null
let queued: { request: EngineRequest, resolve: (r: EngineResponse | null) => void } | null = null

function send(request: EngineRequest, resolve: (r: EngineResponse | null) => void) {
  running = { id: ++nextId, resolve }
  worker.postMessage({ id: running.id, request })
}

function start() {
  worker = new Worker(new URL('./worker/pyodide.worker.ts', import.meta.url), { type: 'module' })
  worker.onmessage = (event) => {
    const msg = event.data
    if (msg.type === 'status') {
      bootStage.value = msg.stage
    }
    else if (msg.type === 'ready') {
      bootState.value = 'ready'
    }
    else if (msg.type === 'fatal') {
      bootState.value = 'error'
      bootError.value = msg.message
    }
    else if (msg.type === 'result' && running && msg.id === running.id) {
      let response: EngineResponse
      try {
        response = JSON.parse(msg.json)
      }
      catch {
        response = { ok: false, code: 'bad_json', message: 'Die Engine hat keine gültige Antwort geliefert.' }
      }
      running.resolve(response)
      running = null
      if (queued) {
        const next = queued
        queued = null
        send(next.request, next.resolve)
      }
    }
  }
  worker.onerror = (event) => {
    bootState.value = 'error'
    bootError.value = event.message || 'Der Worker konnte nicht gestartet werden.'
  }
}

/** Resolves with the response, or with null if a newer request replaced this one. */
export function runEngine(request: EngineRequest): Promise<EngineResponse | null> {
  return new Promise((resolve) => {
    if (!running) {
      send(request, resolve)
      return
    }
    queued?.resolve(null)
    queued = { request, resolve }
  })
}

/** Stops a long computation by restarting the worker (Python has to load again). */
export function restartEngine() {
  worker.terminate()
  running?.resolve(null)
  queued?.resolve(null)
  running = null
  queued = null
  bootState.value = 'loading'
  bootStage.value = 'Python-Laufzeit wird neu geladen …'
  bootError.value = ''
  start()
}

start()
