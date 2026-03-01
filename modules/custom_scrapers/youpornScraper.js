// modules/custom_scrapers/youpornScraper.js
const AbstractModule = require('../../core/AbstractModule')
const VideoMixin = require('../../core/VideoMixin')
const log = require('../../core/log')

class YouPornScraper extends AbstractModule.with(VideoMixin) { // No GifMixin initially
    constructor(options) {
        super(options)
        this.baseUrl = 'https://www.youporn.com'
        log.debug(`${this.name} scraper initialized`)
    }

    get name() {
        return 'YouPorn'
    }

    get firstpage() {
        // Assuming 1-indexed pagination
        return 1
    }

    getVideoSearchUrl(query, page) {
        // Example: https://www.youporn.com/search/?query=test&page=2
        const url = `${this.baseUrl}/search/?query=${encodeURIComponent(query)}&page=${page}`
        log.debug(`${this.name} video URL: ${url}`)
        return url
    }

    parseResults($, rawData, options) {
        const results = []
        if (options.type === 'videos') {
            log.info(`Parsing ${this.name} video page...`)
            const items = $('div[class*="video-card_video-card_"]')
            if (!items.length) {
                log.warn(`[${this.name} parseResults - videos] No video items found.`)
                return results
            }
            items.each((i, el) => {
                const result = this.mapVideoResult(el, $, this.name, this.baseUrl)
                if (result) {
                    results.push(result)
                }
            })
        } else if (options.type === 'gifs') {
            log.warn(`${this.name} does not process GIFs as it lacks a dedicated GIF section. Returning empty results.`)
        }
        return results
    }
}

module.exports = YouPornScraper
