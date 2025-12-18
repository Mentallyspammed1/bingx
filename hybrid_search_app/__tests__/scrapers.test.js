
const Pornsearch = require('../Pornsearch.js')

describe('Scraper Tests', () => {
  let pornsearch

  beforeAll(async () => {
    pornsearch = await Pornsearch.create({ query: 'test' })
  })

  test('Pornhub scraper should return video results', async () => {
    const results = await pornsearch.search({
      query: 'test',
      platform: 'pornhub',
      type: 'videos',
      useMockData: true
    })

    expect(results).toBeInstanceOf(Array)
    expect(results.length).toBeGreaterThan(0)
    const firstResult = results[0]
    expect(firstResult.source).toBe('Pornhub')
    expect(firstResult.type).toBe('videos')
  })
})
