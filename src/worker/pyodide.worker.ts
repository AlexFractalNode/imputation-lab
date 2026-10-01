/// <reference lib="webworker" />
import engineSource from '../py/engine.py?raw'

// Runs pandas / scikit-learn (Pyodide) off the main thread.
// Protocol: main -> { id, request }   worker -> { type: 'status' | 'ready' | 'fatal' | 'result', ... }

interface Engine { run: (requestJson: string) => string }

const base = new URL(`${import.meta.env.BASE_URL}pyodide/`, self.location.origin).href

async function boot(): Promise<Engine> {
  postMessage({ type: 'status', stage: 'Python-Laufzeit wird geladen …' })
  const { loadPyodide } = await import(/* @vite-ignore */ `${base}pyodide.mjs`)
  const pyodide = await loadPyodide({ indexURL: base })
  postMessage({ type: 'status', stage: 'pandas und scikit-learn werden geladen …' })
  await pyodide.loadPackage(['pandas', 'scikit-learn'])
  postMessage({ type: 'status', stage: 'Engine wird gestartet …' })
  pyodide.FS.writeFile('/home/pyodide/engine.py', engineSource)
  return pyodide.pyimport('engine') as Engine
}

const engine = boot()
engine.then(
  () => postMessage({ type: 'ready' }),
  (error: unknown) => postMessage({ type: 'fatal', message: error instanceof Error ? error.message : String(error) }),
)

self.onmessage = async (event: MessageEvent<{ id: number, request: unknown }>) => {
  const { id, request } = event.data
  try {
    const json = (await engine).run(JSON.stringify(request))
    postMessage({ type: 'result', id, json })
  }
  catch (error) {
    // boot failure is already reported as 'fatal'; this covers errors thrown by the call itself
    const message = error instanceof Error ? error.message : String(error)
    postMessage({ type: 'result', id, json: JSON.stringify({ ok: false, code: 'worker_error', message }) })
  }
}
