// test_redtube_gif_scraper.js
const RedtubeScraper = require('./hybrid_search_app/modules/custom_scrapers/redtubeScraper.js')
const log = { // Minimal logger for the test script itself
    info: (message) => console.log(`[TestRunner INFO] ${message}`),
    error: (message, ...args) => console.error(`[TestRunner ERROR] ${message}`, ...args),
}

async function testGifScraper() {
    log.info('Initializing RedtubeScraper for GIF test...')
    const options = {
        query: 'funny',
        driverName: 'Redtube',
        page: 1
    }
    const scraper = new RedtubeScraper(options)

    log.info('Testing RedtubeScraper - searchGifs("funny", 1)...')
    try {
        // Ensure the method exists
        if (typeof scraper.searchGifs !== 'function') {
            log.error('scraper.searchGifs is not a function!')
            console.log('scraper.searchGifs is not a function!')
            return
        }

        const results = await scraper.searchGifs('funny', 1)

        log.info(`searchGifs returned: ${JSON.stringify(results, null, 2)}`)
        console.log('--- searchGifs Results ---')
        console.log(JSON.stringify(results, null, 2))
        console.log('--------------------------')

        if (results && results.length > 0) {
            log.info(`Found ${results.length} GIF results.`)
            const firstItem = results[0]
            log.info(`First GIF item details: Title: '${firstItem.title}', URL: '${firstItem.url}', Thumbnail: '${firstItem.thumbnail}', Preview (GIF): '${firstItem.preview_video}'`)
            console.log(`First GIF item preview_video: ${firstItem.preview_video}`)
        } else if (results && results.length === 0) {
            log.info('No GIF results found.')
        } else {
            log.info('GIF results object is undefined or not an array.')
        }

    } catch (error) {
        log.error('Error during GIF scraper test:', error)
        console.error('Error during GIF scraper test:', error)
    }
}

testGifScraper()
