// modules/custom_scrapers/sexComScraper.js
const AbstractModule = require('../../core/AbstractModule')
const VideoMixin = require('../../core/VideoMixin')
const GifMixin = require('../../core/GifMixin')
const log = require('../../core/log')

class SexComScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options)
        this.baseUrl = 'https://www.sex.com'
        log.debug(`${this.name} scraper initialized`)
    }

    get name() {
        return 'SexCom'
    }

    get firstpage() {
        // Assuming 1-indexed pagination, can be adjusted later
        return 1
    }

    getVideoSearchUrl(query, page) {
        // Needs verification, example: https://www.sex.com/search/videos?query=test&page=2
        const url = `${this.baseUrl}/search/videos?query=${encodeURIComponent(query)}&page=${page}`
        log.debug(`${this.name} video URL: ${url}`)
        return url
    }

    parseResults($, rawData, options) {
        const results = []
        if (options.type === 'videos') {
            log.info(`Parsing ${this.name} video page...`)
            const items = $('.masonry_item[data-id]')
            if (!items.length) {
                log.warn(`[${this.name} parseResults - videos] No video items found.`)
                return results
            }
            items.each((i, el) => {
                const $elem = $(el)
                // Check if it's a video item, sometimes sites mix content or have ads
                if ($elem.find('.duration, .video_duration_indicator').length === 0 && !$elem.is('article[data-type="video"]')) {
                    return // Not a clear video item, skip
                }
                const result = this.mapVideoResult(el, $, this.name, this.baseUrl)
                if (result) {
                    results.push(result)
                }
            })
        } else if (options.type === 'gifs') {
            log.info(`Parsing ${this.name} GIF page...`)
            const items = $('.masonry_item[data-id]')
            if (!items.length) {
                log.warn(`[${this.name} parseResults - gifs] No GIF items found.`)
                return results
            }
            items.each((i, el) => {
                const $elem = $(el)
                // Check if it's a GIF item, e.g. by data-type or specific class
                if (!$elem.is('article[data-type="gif"]') && $elem.find('img[alt*="GIF"]').length === 0 && !$elem.find('.gif_item_play_icon').length > 0) {
                    return // Not a clear GIF item
                }
                const result = this.mapGifResult(el, $, this.name, this.baseUrl)
                if (result) {
                    results.push(result)
                }
            })
        }
        return results
    }
}

module.exports = SexComScraper
