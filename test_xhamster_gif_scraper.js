// test_xhamster_gif_scraper.js
const XhamsterScraper = require('./hybrid_search_app/modules/custom_scrapers/xhamsterScraper.js');
const log = { // Minimal logger for the test script itself
    info: (message) => console.log(`[TestRunner INFO] ${message}`),
    error: (message, ...args) => console.error(`[TestRunner ERROR] ${message}`, ...args),
};

async function testGifScraper() {
    log.info('Initializing XhamsterScraper for GIF test...');
    const options = {
        query: 'funny',
        driverName: 'Xhamster',
        page: 1
    };
    const scraper = new XhamsterScraper(options);

    log.info('Testing XhamsterScraper - searchGifs("funny", 1)...');
    try {
        // Ensure the method exists, though it should based on current xhamsterScraper.js
        if (typeof scraper.searchGifs !== 'function') {
            log.error('scraper.searchGifs is not a function!');
            console.log('scraper.searchGifs is not a function!');
            return;
        }

        const results = await scraper.searchGifs('funny', 1);

        log.info(`searchGifs returned: ${JSON.stringify(results, null, 2)}`);
        console.log('--- searchGifs Results ---');
        console.log(JSON.stringify(results, null, 2));
        console.log('--------------------------');

        if (results && results.length > 0 && results[0].title.includes('Not Fully Implemented')) {
            log.info('Received expected placeholder data for non-implemented GIF search.');
        } else if (results && results.length > 0) {
            log.info(`Found ${results.length} GIF results (unexpected for current placeholder).`);
        } else {
            log.info('No GIF results returned (empty array), or results format unexpected.');
        }

    } catch (error) {
        log.error('Error during GIF scraper test:', error);
        console.error('Error during GIF scraper test:', error); // Also to stdout
    }
}

testGifScraper();
