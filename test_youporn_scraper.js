// test_youporn_scraper.js
const YouPornScraper = require('./hybrid_search_app/modules/custom_scrapers/youpornScraper.js')

async function testScraper() {
    const options = {
        query: 'test',
        driverName: 'YouPorn',
        page: 1
    }
    const scraper = new YouPornScraper(options)

    console.log('Testing YouPornScraper with query "test", page 1...')
    try {
        // Set DEBUG environment variable to true for more verbose logging from the scraper
        // This relies on the scraper using process.env.DEBUG, which it might not.
        // The log module used by YouPornScraper might have its own debug enabling mechanism.
        const results = await scraper.searchVideos('test', 1)

        if (results && results.length > 0) {
            console.log(`Found ${results.length} results:`)
            results.slice(0, 5).forEach((item, index) => {
                console.log(`--- Result ${index + 1} ---`)
                console.log(`Title: ${item.title}`)
                console.log(`URL: ${item.url}`)
                console.log(`Thumbnail: ${item.thumbnail}`)
                console.log(`Preview Video: ${item.preview_video !== undefined ? item.preview_video : 'N/A (field missing)'}`)
                console.log(`Duration: ${item.duration}`)
                console.log(`Source: ${item.source}`)
                console.log('--------------------')
            })
            if (results.length > 5) {
                console.log(`(${results.length - 5} more results not printed in detail)`)
            }
        } else if (results && results.length === 0) {
            console.log('No results found. This could be due to selectors, network issues, age gate, or actual lack of results for the query.')
            // Attempt to access any raw HTML that might have been fetched if the scraper stores it (it likely doesn't expose it directly)
            // This part is speculative as AbstractModule's behavior isn't fully known here.
        } else {
            console.log('Results object is undefined or not an array.')
        }

    } catch (error) {
        console.error('Error during scraper test:', error)
    }
}

testScraper()
