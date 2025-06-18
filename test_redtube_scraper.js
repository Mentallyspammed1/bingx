// test_redtube_scraper.js
const RedtubeScraper = require('./hybrid_search_app/modules/custom_scrapers/redtubeScraper.js');

async function testScraper() {
    // Mock options that might be passed by the main app, if necessary for scraper initialization
    const options = {
        query: 'test', // Default query for the instance if used internally, though searchVideos overrides
        driverName: 'Redtube',
        page: 1 // Default page for the instance
    };
    const scraper = new RedtubeScraper(options);

    console.log('Testing RedtubeScraper with query "test", page 1...');
    try {
        // Set DEBUG environment variable to true for more verbose logging from the scraper
        process.env.DEBUG = 'true';
        const results = await scraper.searchVideos('test', 1); // Explicit query and page

        if (results && results.length > 0) {
            console.log(`Found ${results.length} results:`);
            // Print the first few results for detailed inspection
            results.slice(0, 5).forEach((item, index) => {
                console.log(`--- Result ${index + 1} ---`);
                console.log(`Title: ${item.title}`);
                console.log(`URL: ${item.url}`);
                console.log(`Thumbnail: ${item.thumbnail}`);
                console.log(`Preview Video: ${item.preview_video}`);
                console.log(`Duration: ${item.duration}`);
                console.log(`Source: ${item.source}`);
                console.log('--------------------');
            });
            if (results.length > 5) {
                console.log(`(${results.length - 5} more results not printed in detail)`);
            }
        } else if (results && results.length === 0) {
            console.log('No results found. This could be due to selectors, network issues, or actual lack of results for the query.');
        } else {
            console.log('Results object is undefined or not an array.');
        }

    } catch (error) {
        console.error('Error during scraper test:', error);
    }
}

testScraper();
