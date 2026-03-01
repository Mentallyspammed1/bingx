// modules/custom_scrapers/spankbangScraper.js
'use strict'

const AbstractModule = require('../../core/AbstractModule')
const VideoMixin = require('../../core/VideoMixin')
const GifMixin = require('../../core/GifMixin')
const log = require('../../core/log')
const cheerio = require('cheerio') // Will be needed for parsing

class SpankbangScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options)
        this.baseUrl = 'https://www.spankbang.com' // Assuming this is the correct base URL
        log.debug(`${this.name} scraper initialized`)
    }

    get name() {
        return 'SpankBang'
    }

    get firstpage() {
        // SpankBang uses 1-indexed pagination for search results (e.g., /s/query/2/)
        // but the actual page number for the first page is often not explicitly shown as '1'
        // or it might be part of the path without a query param.
        // For /s/query/ (first page) vs /s/query/2/ (second page), 1 seems appropriate.
        return 1
    }

    // --- Video Search Methods ---
    getVideoSearchUrl(query, page) {
        // Example structure: https://www.spankbang.com/s/test/2/?o=new (page 2)
        // First page: https://www.spankbang.com/s/test/?o=new
        // The page number seems to be part of the path.
        // The 'o=new' sorts by new, other options: o=trending, o=popular, o=longest, o=shortest
        const pageSegment = (parseInt(page, 10) || 1) > 1 ? `${(parseInt(page, 10) || 1)}/` : ''
        const url = `${this.baseUrl}/s/${encodeURIComponent(query)}/${pageSegment}?o=new`
        log.debug(`Constructed ${this.name} video URL: ${url}`)
        return url
    }

    parseResults($, rawData, options) {
        const results = []
        if (options.type === 'videos') {
            log.info(`Parsing ${this.name} video data...`)
            const items = $('div.video-item')
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
            log.info(`Parsing ${this.name} GIF data...`)
            const items = $('div.video-item') // SpankBang uses similar item structure for GIFs
            if (!items.length) {
                log.warn(`[${this.name} parseResults - gifs] No GIF items found.`)
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

module.exports = SpankbangScraper
