// test_motherless_gif_scraper.js
const MotherlessScraper = require('./hybrid_search_app/modules/custom_scrapers/motherlessScraper.js')
const log = { // Minimal logger for the test script itself
    info: (message) => console.log(`[TestRunner INFO] ${message}`),
    error: (message, ...args) => console.error(`[TestRunner ERROR] ${message}`, ...args),
}

async function testGifScraper() {
    log.info('Initializing MotherlessScraper for GIF (Image) test with query "selfie"...')
    const options = {
        query: 'selfie', // Changed query to 'selfie'
        driverName: 'Motherless',
        page: 1
    }
    process.env.DEBUG = 'true'

    const scraper = new MotherlessScraper(options)

    log.info('Testing MotherlessScraper - searchGifs("selfie", 1)...')
    try {
        const results = await scraper.searchGifs('selfie', 1) // Using 'selfie' query

        log.info(`searchGifs("selfie", 1) returned ${results.length} items.`)
        console.log('--- searchGifs (Image Search) Results ---')

        if (results && results.length > 0) {
            log.info(`Successfully extracted ${results.length} Image/GIF items.`)
            results.slice(0, 3).forEach((item, index) => {
                console.log(`--- Item ${index + 1} ---`)
                console.log(`Title: ${item.title}`)
                console.log(`URL (to page): ${item.url}`)
                console.log(`Thumbnail: ${item.thumbnail}`)
                console.log(`Preview Video (image file): ${item.preview_video}`)
                console.log(`Source: ${item.source}`)
                console.log(`Type: ${item.type}`) // Should be 'gifs' if set by parser
                console.log('--------------------')
            })
            if (results.length > 3) {
                console.log(`(${results.length - 3} more results not printed in detail)`)
            }
        } else if (results && results.length === 0) {
            log.info('No Image/GIF results found by the scraper for "selfie".')
        } else {
            log.info('Image/GIF results object is undefined or not an array.')
        }

    } catch (error) {
        log.error('Error during Image/GIF scraper test:', error)
        console.error('Error during Image/GIF scraper test:', error)
    }
}

testGifScraper()
