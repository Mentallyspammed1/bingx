// test_spankbang_gif_scraper.js
const SpankbangScraper = require('./hybrid_search_app/modules/custom_scrapers/spankbangScraper.js');
const log = { // Minimal logger for the test script itself
    info: (message) => console.log(`[TestRunner INFO] ${message}`),
    error: (message, ...args) => console.error(`[TestRunner ERROR] ${message}`, ...args),
};

async function testGifScraper() {
    log.info('Initializing SpankbangScraper for GIF test...');
    const options = {
        query: 'funny',
        driverName: 'SpankBang',
        page: 1
    };
    process.env.DEBUG = 'true'; // Enable debug logs from the scraper if it uses this

    const scraper = new SpankbangScraper(options);

    log.info('Testing SpankbangScraper - searchGifs("funny", 1)...');
    try {
        const results = await scraper.searchGifs('funny', 1);

        log.info(`searchGifs returned ${results.length} items.`);
        console.log('--- searchGifs Results ---');
        // console.log(JSON.stringify(results, null, 2)); // Can be too verbose

        if (results && results.length > 0) {
            log.info(`Successfully extracted ${results.length} GIF items.`);
            // Log details of the first few results for inspection
            results.slice(0, 3).forEach((item, index) => {
                console.log(`--- GIF Item ${index + 1} ---`);
                console.log(`Title: ${item.title}`);
                console.log(`URL: ${item.url}`);
                console.log(`Thumbnail (poster): ${item.thumbnail}`);
                console.log(`Preview Video (from data-preview): ${item.preview_video}`); // This is the key field
                console.log(`Source: ${item.source}`);
                console.log('--------------------');
            });
            if (results.length > 3) {
                console.log(`(${results.length - 3} more results not printed in detail)`);
            }
        } else if (results && results.length === 0) {
            log.info('No GIF results found by the scraper. This could be due to selectors, the query, or no GIFs available.');
        } else {
            log.info('GIF results object is undefined or not an array.');
        }

    } catch (error) {
        log.error('Error during GIF scraper test:', error);
        console.error('Error during GIF scraper test:', error);
    }
}

testGifScraper();
