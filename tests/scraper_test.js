"use strict"
Object.defineProperty(exports, "__esModule", { value: true })
const search_flow_1 = require("../src/ai/flows/search-flow")
async function runTests() {
    const drivers = await (0, search_flow_1.getDrivers)()
    const query = 'test' // A simple query that should return results on most platforms
    console.log('--- Starting Scraper Tests ---')
    for (const driver of drivers) {
        if (driver === 'mock') {
            console.log(`[SKIPPING] Mock driver.`)
            continue
        }
        console.log(`[TESTING] Driver: ${driver}`)
        try {
            const searchInput = {
                query,
                driver,
                type: 'videos',
                page: 1,
            }
            const results = await (0, search_flow_1.search)(searchInput)
            if (results.length > 0) {
                console.log(`  [SUCCESS] Found ${results.length} results.`)
            }
            else {
                console.warn(`  [FAILURE] Found 0 results.`)
            }
        }
        catch (error) {
            console.error(`  [ERROR] ${error.message}`)
        }
        console.log('--------------------')
    }
    console.log('--- Scraper Tests Finished ---')
}
runTests()
