
const Pornsearch = require('../Pornsearch.js');

async function testScrapers() {
  const pornsearch = new Pornsearch();
  const scrapers = [
    'pornhub',
    'xvideos',
    'youporn',
    'redtube',
    'motherless',
    'sexcom',
    'spankbang',
    'xhamster'
  ];

  for (const scraper of scrapers) {
    try {
      console.log(`Testing ${scraper}...`);
      const results = await pornsearch.search('test', scraper);
      if (results && results.length > 0) {
        console.log(`  ${scraper} returned ${results.length} results.`);
      } else {
        console.error(`  ${scraper} returned no results.`);
      }
    } catch (error) {
      console.error(`  Error testing ${scraper}:`, error);
    }
  }
}

testScrapers();
