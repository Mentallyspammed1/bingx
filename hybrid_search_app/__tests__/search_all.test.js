const Pornsearch = require('../Pornsearch.js');

describe('Search All Scrapers Tests', () => {
  let pornsearch;

  beforeAll(async () => {
    pornsearch = await Pornsearch.create({ query: 'test' });
  });

  test('should return results from multiple scrapers when searching all for videos with mock data', async () => {
    const results = await pornsearch.search({
      query: 'test',
      type: 'videos',
      useMockData: true
    });

    expect(results).toBeInstanceOf(Array);
    expect(results.length).toBeGreaterThan(0);

    const sources = new Set(results.map(r => r.source));
    expect(sources.size).toBeGreaterThan(0);
  }, 30000);

  test('should return results from multiple scrapers when searching all for gifs with mock data', async () => {
    const results = await pornsearch.search({
      query: 'test',
      type: 'gifs',
      useMockData: true
    });

    expect(results).toBeInstanceOf(Array);
    expect(results.length).toBeGreaterThan(0);

    const sources = new Set(results.map(r => r.source));
    expect(sources.size).toBeGreaterThan(0);
  }, 30000);
});
