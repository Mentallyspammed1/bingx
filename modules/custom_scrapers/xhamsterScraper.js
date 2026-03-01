// modules/custom_scrapers/xhamsterScraper.js
const AbstractModule = require('../../core/AbstractModule')
const VideoMixin = require('../../core/VideoMixin')
const GifMixin = require('../../core/GifMixin')
const log = require('../../core/log') // Assuming log is in core

class XhamsterScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options)
        this.baseUrl = 'https://xhamster.com'
        log.debug(`${this.name} scraper initialized`)
    }

    get name() {
        return 'Xhamster'
    }

    get firstpage() {
        // Assuming 1-indexed pagination, can be adjusted later
        return 1
    }

    getVideoSearchUrl(query, page) {
        const url = `${this.baseUrl}/search/${encodeURIComponent(query)}?page=${page}`
        log.debug(`${this.name} video URL: ${url}`)
        return url
    }

    parseResults($, rawData, options) {
        const results = []
        if (options.type === 'videos') {
            log.info(`Parsing ${this.name} video page...`)
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
            log.info(`Parsing ${this.name} GIF page...`)
            const items = $('div.gif-thumb')
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

module.exports = XhamsterScraper
