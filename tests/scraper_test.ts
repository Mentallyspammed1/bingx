import { search, getDrivers } from '../src/ai/flows/search-flow';
import type { SearchInput } from '../src/ai/types';

async function runTests() {
  const drivers = await getDrivers();
  const query = 'test'; // A simple query that should return results on most platforms

  console.log('--- Starting Scraper Tests ---');

  for (const driver of drivers) {
    if (driver === 'mock') {
        console.log(`[SKIPPING] Mock driver.`);
        continue;
    }

    console.log(`[TESTING] Driver: ${driver}`);
    try {
      const searchInput: SearchInput = {
        query,
        driver,
        type: 'videos',
        page: 1,
      };
      const results = await search(searchInput);
      if (results.length > 0) {
        console.log(`  [SUCCESS] Found ${results.length} results.`);
      } else {
        console.warn(`  [FAILURE] Found 0 results.`);
      }
    } catch (error: any) {
      console.error(`  [ERROR] ${error.message}`);
    }
    console.log('--------------------');
  }

  console.log('--- Scraper Tests Finished ---');
}

runTests();
