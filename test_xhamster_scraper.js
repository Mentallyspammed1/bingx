// test_xhamster_scraper.js
const XhamsterScraper = require('./hybrid_search_app/modules/custom_scrapers/xhamsterScraper.js')

async function testScraper() {
    const options = {
        query: 'test',
        driverName: 'Xhamster', // Not strictly used by constructor if scraper name is hardcoded
        page: 1
    }
    const scraper = new XhamsterScraper(options)

    console.log('Testing XhamsterScraper with query "test", page 1 for videos...')
    try {
        const results = await scraper.searchVideos('test', 1)

        if (results && results.length > 0) {
            console.log(`Found ${results.length} result(s):`)
            // Print the first few results for detailed inspection
            results.slice(0, 3).forEach((item, index) => {
                console.log(`--- Result ${index + 1} ---`)
                console.log(`Title: ${item.title}`)
                console.log(`URL: ${item.url !== undefined ? item.url : 'N/A (field missing)'}`)
                console.log(`Thumbnail: ${item.thumbnail !== undefined ? item.thumbnail : 'N/A (field missing)'}`)
                console.log(`Preview Video: ${item.preview_video !== undefined ? item.preview_video : 'N/A (field missing)'}`)
                console.log(`Duration: ${item.duration !== undefined ? item.duration : 'N/A (field missing)'}`)
                console.log(`Source: ${item.source}`)
                if (item.error) console.log(`Error Property: ${item.error}`)
                console.log('--------------------')
            })
        } else if (results && results.length === 0) {
            console.log('No results returned (empty array).')
        } else {
            console.log('Results object is undefined or not an array.')
        }

    } catch (error) {
        console.error('Error during scraper test:', error)
    }
}

testScraper()
