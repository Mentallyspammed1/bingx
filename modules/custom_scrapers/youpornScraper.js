// modules/custom_scrapers/youpornScraper.js
const AbstractModule = require('../../core/AbstractModule')
const VideoMixin = require('../../core/VideoMixin')
// const GifMixin = require('../../core/GifMixin'); // Not including for now
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

    videoUrl(query, page) {
        // Example: https://www.youporn.com/search/?query=test&page=2
        const url = `${this.baseUrl}/search/?query=${encodeURIComponent(query)}&page=${page}`
        log.debug(`${this.name} video URL: ${url}`)
        return url
    }

    async videoParser($, rawHtmlOrJsonData) {
        log.info(`Parsing ${this.name} video page...`)
        const videos = []
        // Common selectors: 'div.video-box', 'li.video-thumb-block', '.video-card', '.video-item_item_XXXXX'
        // YouPorn's structure might use elements like 'div[data-id]' or similar for video blocks
        // Let's try a selector that's common for video list items.
        // A specific class from YouPorn seems to be `video-card_video-card_XXXX` where XXXXX is a hash.
        // We can try a partial match or a more generic one.
        $('div[class*="video-card_video-card_"]').each((i, elem) => { // Speculative selector
            try {
                const $elem = $(elem)

                const titleLink = $elem.find('a[data-test-video-tile-title]')
                const title = titleLink.attr('title') || titleLink.text().trim()
                let url = titleLink.attr('href')
                url = this._makeAbsolute(url, this.baseUrl)

                const thumbnailTag = $elem.find('img[data-test-video-tile-img]')
                let thumbnail = thumbnailTag.attr('src') || thumbnailTag.attr('data-src')
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl)

                const durationElement = $elem.find('span[data-test-video-tile-duration], .video-duration') // data-test attribute is good if stable
                const duration = durationElement.first().text().trim()

                // Preview video can be in 'data-preview' or similar on the image or parent
                let preview_video = thumbnailTag.attr('data-preview') || $elem.find('video.preview, source[type="video/mp4"]').attr('src')
                if(!preview_video && thumbnailTag.attr('onmouseover')) { // Check inline scripts (less ideal)
                    const mouseoverContent = thumbnailTag.attr('onmouseover')
                    const urlMatch = mouseoverContent.match(/previewUrl['"]:\s*['"]([^'"]+)['"]/)
                    if(urlMatch && urlMatch[1]) {
                        preview_video = urlMatch[1]
                    }
                }
                preview_video = preview_video ? this._makeAbsolute(preview_video, this.baseUrl) : null

                if (title && url) {
                    const videoData = {
                        title,
                        url,
                        thumbnail,
                        duration,
                        source: this.name,
                    }
                    if (preview_video) {
                        videoData.preview_video = preview_video
                    }
                    videos.push(videoData)
                } else {
                    // log.debug(`Skipping item on ${this.name} due to missing title or URL. HTML: ${$elem.html().substring(0,100)}`);
                }
            } catch (e) {
                log.warn(`Error parsing video item on ${this.name}: ${e.message} - Item HTML: ${$(elem).html().substring(0,100)}`)
            }
        })
        log.info(`Found ${videos.length} videos on ${this.name}`)
        if (videos.length === 0 && rawHtmlOrJsonData && rawHtmlOrJsonData.length > 100) {
            log.warn(`No videos found for ${this.name}, but received HTML. Selectors might be outdated.`)
            // For YouPorn, content might be in <script id="initialState_feature-flags"> or similar JSON blobs
            // This parser currently only handles direct HTML elements.
            if (rawHtmlOrJsonData.includes("initialState")) {
                log.info(`${this.name}: Page seems to contain JSON state, which might hold video data not parsed by current selectors.`)
            }
        }
        return videos
    }

    gifUrl(query, page) {
        log.warn(`${this.name} does not have a dedicated GIF search section. Returning empty URL.`)
        // Returning a non-functional or empty URL as GIF search is not standard here
        return ""
    }

    async gifParser($, rawHtmlOrJsonData) {
        log.warn(`${this.name} does not process GIFs as it lacks a dedicated GIF section.`)
        // Return empty array as no GIFs are expected to be parsed
        return []
    }
}

module.exports = YouPornScraper
