// Puts a self-contained Pyodide distribution into public/pyodide so the lab works
// without a CDN at runtime: core files come from the npm package, the package
// wheels (pandas, scikit-learn and their dependencies) from the official CDN and
// are verified against the sha256 hashes in pyodide-lock.json.
import { createHash } from 'node:crypto'
import { copyFile, mkdir, readFile, stat, writeFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT_PACKAGES = ['pandas', 'scikit-learn']
const CORE_FILES = ['pyodide.mjs', 'pyodide.asm.js', 'pyodide.asm.wasm', 'python_stdlib.zip', 'pyodide-lock.json']

const require = createRequire(import.meta.url)
const pkgDir = dirname(require.resolve('pyodide/package.json'))
const { version } = JSON.parse(await readFile(join(pkgDir, 'package.json'), 'utf8'))
const outDir = fileURLToPath(new URL('../public/pyodide/', import.meta.url))
const cdn = `https://cdn.jsdelivr.net/pyodide/v${version}/full/`

await mkdir(outDir, { recursive: true })
for (const file of CORE_FILES)
  await copyFile(join(pkgDir, file), join(outDir, file))

const lock = JSON.parse(await readFile(join(pkgDir, 'pyodide-lock.json'), 'utf8'))
const needed = new Set()
const queue = [...ROOT_PACKAGES]
while (queue.length) {
  const name = queue.pop()
  if (needed.has(name))
    continue
  const entry = lock.packages[name]
  if (!entry)
    throw new Error(`fetch-pyodide: package "${name}" is not in pyodide-lock.json`)
  needed.add(name)
  queue.push(...entry.depends)
}

const sha256 = buffer => createHash('sha256').update(buffer).digest('hex')

let downloaded = 0
for (const name of [...needed].sort()) {
  const { file_name: fileName, sha256: expected } = lock.packages[name]
  const target = join(outDir, fileName)
  try {
    await stat(target)
    if (sha256(await readFile(target)) === expected)
      continue
  }
  catch (e) {
    if (e.code !== 'ENOENT')
      throw e
  }
  const response = await fetch(cdn + fileName)
  if (!response.ok)
    throw new Error(`fetch-pyodide: ${cdn + fileName} -> HTTP ${response.status}`)
  const buffer = Buffer.from(await response.arrayBuffer())
  if (sha256(buffer) !== expected)
    throw new Error(`fetch-pyodide: checksum mismatch for ${fileName}`)
  await writeFile(target, buffer)
  downloaded++
}

console.log(`fetch-pyodide: Pyodide ${version}, ${needed.size} packages ready (${downloaded} downloaded) in public/pyodide`)
