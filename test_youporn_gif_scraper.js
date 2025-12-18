// test_youporn_gif_scraper.js
const YouPornScraper = require('./hybrid_search_app/modules/custom_scrapers/youpornScraper.js')
const log = require('./hybrid_search_app/core/log.js')

async function testGifScraper() {
    log.info('Initializing YouPornScraper for GIF test...')
    const options = {
        query: 'funny', // Changed query to 'funny'
        driverName: 'YouPorn',
        page: 1
    }
    const scraper = new YouPornScraper(options)

    log.info('Testing YouPornScraper - searchGifs("funny", 1)...') // Updated log
    try {
        if (typeof scraper.searchGifs !== 'function') {
            log.error('scraper.searchGifs is not a function!')
            console.log('scraper.searchGifs is not a function!')
            return
        }

        const results = await scraper.searchGifs('funny', 1) // Using 'funny' query

        log.info(`searchGifs returned: ${JSON.stringify(results, null, 2)}`)
        console.log('--- searchGifs Results ---')
        console.log(JSON.stringify(results, null, 2))
        console.log('--------------------------')

        if (results && results.length > 0) {
            log.info(`Found ${results.length} GIF results.`)
            // Log details of the first result if any
            const firstItem = results[0]
            log.info(`First GIF item details: Title: '${firstItem.title}', URL: '${firstItem.url}', Thumbnail: '${firstItem.thumbnail}', Preview (GIF): '${firstItem.preview_video}'`)
            console.log(`First GIF item preview_video: ${firstItem.preview_video}`)
        } else if (results && results.length === 0) {
            log.info('No GIF results found.')
        } else {
            log.warn('GIF results object is undefined or not an array.')
        }

    } catch (error) {
        log.error('Error during GIF scraper test:', error)
        console.error('Error during GIF scraper test:', error)
    }
}

testGifScraper()
