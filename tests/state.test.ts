import { describe, expect, it } from 'vitest'
import { categories, methodById, precheckUpload } from '../src/catalog'
import { defaultParams, parseState, serializeState } from '../src/urlState'

describe('url state', () => {
  it('uses defaults for an empty query', () => {
    const s = parseState('')
    expect(s.dataset).toBe('iris')
    expect(s.method).toBe('mean')
    expect(s.params).toEqual({ add_indicator: false })
    expect(s.embed).toBe(false)
  })

  it('round-trips a full state', () => {
    const s = parseState('?ds=penguins&mech=MNAR&rate=45&target=body_mass_g&method=knn&p.n_neighbors=9&p.weights=distance&p.scale=0&seed=7&embed=1')
    expect(s).toMatchObject({ dataset: 'penguins', mechanism: 'MNAR', rate: 45, target: 'body_mass_g', method: 'knn', seed: 7, embed: true })
    expect(s.params).toEqual({ n_neighbors: 9, weights: 'distance', scale: false })
    expect(parseState(serializeState(s))).toEqual(s)
  })

  it('ignores invalid values and clamps ranges', () => {
    const s = parseState('?mech=NOPE&rate=999&method=doesnotexist&seed=abc&p.add_indicator=1')
    expect(s.mechanism).toBe('MCAR')
    expect(s.rate).toBe(80)
    expect(s.method).toBe('mean')
    expect(s.seed).toBe(0)
    expect(s.params.add_indicator).toBe(true)
    expect(parseState('?method=knn&p.n_neighbors=500&p.weights=bogus').params).toEqual({ n_neighbors: 25, weights: 'uniform', scale: true })
  })

  it('drops the default target when another dataset is requested', () => {
    expect(parseState('?ds=titanic').target).toBeNull()
  })
})

describe('catalog', () => {
  it('has unique method ids with defaults for every parameter', () => {
    const ids = categories.flatMap(c => c.methods.map(m => m.id))
    expect(new Set(ids).size).toBe(ids.length)
    for (const id of ids)
      expect(Object.keys(defaultParams(id))).toEqual(methodById.get(id)!.params.map(p => p.key))
  })

  it('pre-checks uploads', () => {
    expect(precheckUpload({ name: 'data.csv', size: 100 })).toBeNull()
    expect(precheckUpload({ name: 'DATA.TSV', size: 100 })).toBeNull()
    expect(precheckUpload({ name: 'data.xlsx', size: 100 })).toMatch(/Dateityp/)
    expect(precheckUpload({ name: 'data.csv', size: 0 })).toMatch(/leer/)
    expect(precheckUpload({ name: 'data.csv', size: 6 * 1024 * 1024 })).toMatch(/zu groß/)
  })
})
