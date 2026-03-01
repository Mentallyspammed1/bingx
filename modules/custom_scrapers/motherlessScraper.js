// modules/custom_scrapers/motherlessScraper.js
const AbstractModule = require('../../core/AbstractModule')
const VideoMixin = require('../../core/VideoMixin')
const GifMixin = require('../../core/GifMixin') // Including tentatively
const log = require('../../core/log')

class MotherlessScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options)
        this.baseUrl = 'https://motherless.com'
        log.debug(`${this.name} scraper initialized`)
    }

    get name() {
        return 'Motherless'
    }

    get firstpage() {
        // Assuming 1-indexed pagination, adjust if necessary
        return 1
    }

    // Motherless uses "term/videos/<query>" or "term/images/<query>"
    // For videos:
    getVideoSearchUrl(query, page) {
        // Example: https://motherless.com/term/videos/test?page=2
        // Note: Motherless might use different URL structures for general browsing vs. search
        // This assumes a search endpoint structure.
        const url = `${this.baseUrl}/term/videos/${encodeURIComponent(query)}?page=${page}`
        log.debug(`${this.name} video URL: ${url}`)
        return url
    }

    parseResults($, rawData, options) {
        const results = []
        if (options.type === 'videos') {
            log.info(`Parsing ${this.name} video page... Query URL: ${$._originalUrl || 'N/A'}`)
            const items = $('div.thumb.is-video a[href*="/GI"]')
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
            log.info(`Parsing ${this.name} "GIF" (image) page... Query URL: ${$._originalUrl || 'N/A'}`)
            const items = $('div.thumb.is-image a[href*="/GI"]')
            if (!items.length) {
                log.warn(`[${this.name} parseResults - gifs] No image/GIF items found.`)
                return results
            }
            items.each((i, el) => {
                const result = this.mapGifResult(el, $, this.name, this.baseUrl)
                if (result) {
                    results.push(result)
                }
            })
        }
        return results
    }
}

module.exports = MotherlessScraper
