// modules/custom_scrapers/xvideosScraper.js
'use strict'

const AbstractModule = require('../../core/AbstractModule')
const VideoMixin = require('../../core/VideoMixin')
const GifMixin = require('../../core/GifMixin')
const cheerio = require('cheerio') // Required for parsing HTML

const log = {
    debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[XvideosScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args)},
    info: (message, ...args) => console.log(`[XvideosScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
    warn: (message, ...args) => console.warn(`[XvideosScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
    error: (message, ...args) => console.error(`[XvideosScraper ERROR] ${new Date().toISOString()}: ${message}`, ...args),
}

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
    videoUrl(query, page) {
        // Adjust page for 0-indexed Xvideos, assuming 'page' parameter is 1-indexed.
        const xvideosPage = Math.max(0, (parseInt(page, 10) || 1) - 1 + this.firstpage)
        const url = `${this.baseUrl}/?k=${encodeURIComponent(query)}&p=${xvideosPage}`
        log.debug(`Constructed video URL: ${url}`)
        return url
    }

    async searchVideos(query, page) {
        const url = this.videoUrl(query, page)
        log.info(`Fetching HTML for Xvideos videos from: ${url}`)
        try {
            const html = await this._fetchHtml(url)
            const $ = cheerio.load(html)
            return this.videoParser($, html)
        } catch (error) {
            log.error(`Error in searchVideos for query "${query}" on page ${page}: ${error.message}`)
            return []
        }
    }

    videoParser($, rawData) { // eslint-disable-line no-unused-vars
        log.info(`Parsing Xvideos video data...`)
        const videos = []
        // Selector based on typical Xvideos structure (might need updates)
        $('div.thumb-block').each((i, elem) => {
            const $elem = $(elem)
            const $titleLink = $elem.find('p.title a')
            const title = $titleLink.attr('title')?.trim()
            const videoPageUrl = $titleLink.attr('href')

            const $thumbInside = $elem.find('div.thumb-inside')
            const duration = $thumbInside.find('span.duration').text()?.trim()

            const $imgElement = $thumbInside.find('img')
            // Xvideos uses data-src for lazy-loaded images
            const thumbnail = $imgElement.attr('data-src') || $imgElement.attr('src')

            // Xvideos often uses a JS player that dynamically loads video, direct preview URL might not be in static HTML.
            // Sometimes a low-quality GIF preview is in 'data-videopreview'.
            const previewVideo = $imgElement.attr('data-videopreview') // This is often a .jpg, .gif, or short .mp4

            if (title && videoPageUrl) {
                videos.push({
                    title,
                    url: this._makeAbsolute(videoPageUrl, this.baseUrl),
                    thumbnail: this._makeAbsolute(thumbnail, this.baseUrl),
                    duration: duration || 'N/A',
                    preview_video: this._makeAbsolute(previewVideo, this.baseUrl), // May or may not be a video
                    source: this.name,
                })
            } else {
                log.warn('Skipped an Xvideos video item due to missing title or URL.')
            }
        })
        log.info(`Parsed ${videos.length} video items from Xvideos.`)
        return videos
    }

    // --- GIF Search Methods ---
    gifUrl(query, page) {
        // Adjust page for 0-indexed Xvideos
        const xvideosPage = Math.max(0, (parseInt(page, 10) || 1) - 1 + this.firstpage)
        // Xvideos GIF search URL structure might differ, this is a common pattern
        const url = `${this.baseUrl}/gifs/${encodeURIComponent(query)}/${xvideosPage}`
        log.debug(`Constructed GIF URL: ${url}`)
        return url
    }

    async searchGifs(query, page) {
        const url = this.gifUrl(query, page)
        log.info(`Fetching HTML for Xvideos GIFs from: ${url}`)
        try {
            const html = await this._fetchHtml(url)
            const $ = cheerio.load(html)
            return this.gifParser($, html)
        } catch (error) {
            log.error(`Error in searchGifs for query "${query}" on page ${page}: ${error.message}`)
            return []
        }
    }

    gifParser($, rawData) { // eslint-disable-line no-unused-vars
        log.info(`Parsing Xvideos GIF data...`)
        const gifs = []
        // Selectors for Xvideos GIFs (these are highly speculative as Xvideos GIF section is less standard)
        // This might be similar to video items or completely different.
        $('div.gif-thumb-block, div.thumb-block').each((i, elem) => { // Generalizing selectors
            const $elem = $(elem)
            const $titleLink = $elem.find('p.title a, a.thumb-name') // Try a few common title link selectors
            const title = $titleLink.attr('title')?.trim() || $titleLink.text()?.trim()
            const gifPageUrl = $titleLink.attr('href')

            const $imgElement = $elem.find('div.thumb img, div.thumb-inside img')
            let thumbnail = $imgElement.attr('data-src') || $imgElement.attr('src')
            // For GIFs, the 'preview_video' might be the direct GIF URL itself or a short video clip.
            // Xvideos might store this in 'data-src' of the main image if it's an animated GIF, or 'data-videopreview'
            let previewVideo = $imgElement.attr('data-src') // Assuming data-src is the animated GIF

            if (title && gifPageUrl && previewVideo) { // Ensure previewVideo (actual GIF/video) is found
                gifs.push({
                    title,
                    url: this._makeAbsolute(gifPageUrl, this.baseUrl), // Link to the GIF's page or detail
                    thumbnail: this._makeAbsolute(thumbnail, this.baseUrl), // Static thumbnail if available
                    preview_video: this._makeAbsolute(previewVideo, this.baseUrl), // The animated GIF/video itself
                    source: this.name,
                })
            } else {
                log.warn('Skipped an Xvideos GIF item due to missing title, URL, or preview URL.')
            }
        })
        log.info(`Parsed ${gifs.length} GIF items from Xvideos.`)
        return gifs
    }
}

module.exports = XvideosScraper
