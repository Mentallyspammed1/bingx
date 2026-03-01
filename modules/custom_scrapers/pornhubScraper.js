// modules/custom_scrapers/pornhubScraper.js
'use strict'

const AbstractModule = require('../../core/AbstractModule')
const VideoMixin = require('../../core/VideoMixin')
const GifMixin = require('../../core/GifMixin')
const cheerio = require('cheerio') // Required for parsing HTML

const log = require('../../core/log')

class PornhubScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options)
        this.baseUrl = 'https://www.pornhub.com'
        log.debug(`PornhubScraper instantiated. Query: "${this.query}", Page: ${this.page}`)
    }

    get name() {
        return 'Pornhub'
    }

    get firstpage() {
        return 1
    }

    // --- Video Search Methods ---
    getVideoSearchUrl(query, page) {
        const searchPage = page || this.firstpage
        const url = `${this.baseUrl}/video/search?search=${encodeURIComponent(query)}&page=${searchPage}`
        log.debug(`Constructed video URL: ${url}`)
        return url
    }

    parseResults($, rawData, options) {
        const results = []
        if (options.type === 'videos') {
            log.info(`Parsing ${this.name} video data...`)
            const items = $('ul.videos.search-video-thumbs li.pcVideoListItem')
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
            const items = $('ul.gifs.searchList li.gifVideoBlock')
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

module.exports = PornhubScraper
