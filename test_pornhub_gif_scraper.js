// test_pornhub_gif_scraper.js
const PornhubScraper = require('./hybrid_search_app/modules/custom_scrapers/pornhubScraper.js')
const log = { // Minimal logger for the test script itself
    info: (message) => console.log(`[TestRunner INFO] ${message}`),
    error: (message, ...args) => console.error(`[TestRunner ERROR] ${message}`, ...args),
}

async function testGifScraper() {
    log.info('Initializing PornhubScraper for GIF test...')
    const options = {
        query: 'funny',
        driverName: 'Pornhub',
        page: 1
    }
    // It seems PornhubScraper initializes its own log, so this one might not be used by it.
    // We'll enable DEBUG for the scraper via process.env if its internal log uses it.
    process.env.DEBUG = 'true'

    const scraper = new PornhubScraper(options)

    log.info('Testing PornhubScraper - searchGifs("funny", 1)...')
    try {
        const results = await scraper.searchGifs('funny', 1)

        log.info(`searchGifs returned ${results.length} items.`)
        console.log('--- searchGifs Results ---')
        // console.log(JSON.stringify(results, null, 2)); // Might be too verbose if many results

        if (results && results.length > 0) {
            log.info(`Successfully extracted ${results.length} GIF items.`)
            // Log details of the first few results for inspection
            results.slice(0, 3).forEach((item, index) => {
                console.log(`--- GIF Item ${index + 1} ---`)
                console.log(`Title: ${item.title}`)
                console.log(`URL: ${item.url}`)
                console.log(`Thumbnail (poster): ${item.thumbnail}`)
                console.log(`Preview Video (webm): ${item.preview_video}`)
                console.log(`Source: ${item.source}`)
                console.log('--------------------')
            })
             if (results.length > 3) {
                console.log(`(${results.length - 3} more results not printed in detail)`)
            }
        } else if (results && results.length === 0) {
            log.info('No GIF results found by the scraper.')
        } else {
            log.info('GIF results object is undefined or not an array.')
        }

    } catch (error) {
        log.error('Error during GIF scraper test:', error)
        console.error('Error during GIF scraper test:', error)
    }
}

testGifScraper()
