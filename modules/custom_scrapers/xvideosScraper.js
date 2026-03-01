// modules/custom_scrapers/xvideosScraper.js
'use strict'

const AbstractModule = require('../../core/AbstractModule')
const VideoMixin = require('../../core/VideoMixin')
const GifMixin = require('../../core/GifMixin')
const cheerio = require('cheerio') // Required for parsing HTML

const log = require('../../core/log')

class XvideosScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options)
        this.baseUrl = 'https://www.xvideos.com'
        log.debug(`XvideosScraper instantiated. Query: "${this.query}", Page: ${this.page}`)
    }

    get name() {
        return 'Xvideos'
    }

    get firstpage() {
        // Xvideos search pagination (param 'p') is 0-indexed in URL,
        // but users/AbstractModule might think in 1-indexed pages.
        // If AbstractModule's 'this.page' is 1-indexed, adjust here.
        // Assuming AbstractModule sends 1 for first page.
        return 0
    }

    // --- Video Search Methods ---
    getVideoSearchUrl(query, page) {
        // Adjust page for 0-indexed Xvideos, assuming 'page' parameter is 1-indexed.
        const xvideosPage = Math.max(0, (parseInt(page, 10) || 1) - 1 + this.firstpage)
        const url = `${this.baseUrl}/?k=${encodeURIComponent(query)}&p=${xvideosPage}`
        log.debug(`Constructed video URL: ${url}`)
        return url
    }

    parseResults($, rawData, options) {
        const results = []
        if (options.type === 'videos') {
            log.info(`Parsing ${this.name} video data...`)
            const items = $('div.thumb-block')
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
            const items = $('div.gif-thumb-block, div.thumb-block')
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

module.exports = XvideosScraper
