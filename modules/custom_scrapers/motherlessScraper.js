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
    videoUrl(query, page) {
        // Example: https://motherless.com/term/videos/test?page=2
        // Note: Motherless might use different URL structures for general browsing vs. search
        // This assumes a search endpoint structure.
        const url = `${this.baseUrl}/term/videos/${encodeURIComponent(query)}?page=${page}`
        log.debug(`${this.name} video URL: ${url}`)
        return url
    }

    async videoParser($, rawHtmlOrJsonData) {
        log.info(`Parsing ${this.name} video page... Query URL: ${$._originalUrl || 'N/A'}`) // Assuming _originalUrl is set by fetcher
        const videos = []
        // Common selectors for Motherless: '.clip-thumb-container', 'div.thumb', 'article.video-preview'
        // Motherless has a specific structure: div.thumb.is-video or div.thumb.is-image
        $('div.thumb.is-video a[href*="/GI"]').each((i, elem) => { // Target video thumbs specifically, /GI/ seems to be gallery items which can be videos
            try {
                const $elem = $(elem)
                const title = $elem.find('img').attr('alt') || $elem.find('.title, .caption').text().trim()
                let url = $elem.attr('href')
                url = this._makeAbsolute(url, this.baseUrl)

                let thumbnail = $elem.find('img').attr('src')
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl)

                // Duration is often tricky on sites like Motherless, might not be easily available on thumb
                const durationElement = $elem.find('.duration, .thumb-duration')
                const duration = durationElement.text().trim()

                // Preview video: Motherless might have on-hover previews or this might be same as thumbnail.
                // It might also be on the actual video page, not the search results.
                // Let's assume for now it's not readily available on the search/listing page.
                // Attempt to find a preview URL. Common attributes could be 'data-preview-url', 'data-gif-url', 'data-video-src'.
                // For Motherless, often the thumbnail itself might be a GIF, or a specific video preview isn't provided on listings.
                // We will prioritize an explicit preview attribute if found.
                let preview_video_url = $elem.find('img').attr('data-preview-url') // Example: Check for a specific attribute
                // Add more attempts if other attributes are identified, e.g.:
                // if (!preview_video_url) preview_video_url = $elem.find('img').attr('data-gif-preview');

                preview_video_url = preview_video_url ? this._makeAbsolute(preview_video_url, this.baseUrl) : null

                if (title && url && url.includes('/GI')) { // Ensure it's a gallery item link
                    const videoData = {
                        title,
                        url,
                        thumbnail,
                        duration: duration || "N/A",
                        source: this.name,
                    }
                    if (preview_video_url) {
                        videoData.preview_video = preview_video_url
                    }
                    videos.push(videoData)
                } else if (url && !url.includes('/GI')) {
                    log.debug(`Skipping non-gallery item on ${this.name}: ${url}`)
                } else {
                     // log.debug(`Skipping item on ${this.name} due to missing title or URL. HTML: ${$elem.parent().html().substring(0,100)}`);
                }
            } catch (e) {
                log.warn(`Error parsing video item on ${this.name}: ${e.message} - Item HTML: ${$(elem).parent().html().substring(0,100)}`)
            }
        })
        log.info(`Found ${videos.length} video items on ${this.name} page: ${$._originalUrl || 'N/A'}`)
        if (videos.length === 0 && rawHtmlOrJsonData && rawHtmlOrJsonData.length > 100) {
            log.warn(`No videos found for ${this.name} on ${$._originalUrl || 'N/A'}, but received HTML. Selectors might be outdated or page structure changed.`)
        }
        return videos
    }

    // For GIFs, Motherless might categorize them under "images" or not have a separate GIF search
    // Let's assume for now it's similar to videos but with "images" or "gifs" in URL
    gifUrl(query, page) {
        // Option 1: Assume GIFs are searched as images that happen to be animated
        // const url = `${this.baseUrl}/term/images/${encodeURIComponent(query)}?page=${page}&type=gif`; // hypothetical type filter
        // Option 2: Assume a dedicated GIF term path
        // const url = `${this.baseUrl}/term/gifs/${encodeURIComponent(query)}?page=${page}`;
        // For now, let's log that it's uncertain and return a generic image search URL.
        // Users might find GIFs among general images.
        const url = `${this.baseUrl}/term/images/${encodeURIComponent(query)}?page=${page}`
        log.info(`${this.name} GIF search uses general image search URL: ${url}. Specific GIF filtering is assumed not available or part of general image results.`)
        return url
    }

    async gifParser($, rawHtmlOrJsonData) {
        log.info(`Parsing ${this.name} "GIF" (image) page... Query URL: ${$._originalUrl || 'N/A'}`)
        const gifs = []
        // We're looking for images that might be GIFs. Selectors would be for general images.
        $('div.thumb.is-image a[href*="/GI"]').each((i, elem) => { // Target image thumbs
            try {
                const $elem = $(elem)
                const title = $elem.find('img').attr('alt') || $elem.find('.title, .caption').text().trim()
                let url = $elem.attr('href') // Link to the gallery/image page
                url = this._makeAbsolute(url, this.baseUrl)

                let thumbnail = $elem.find('img').attr('src') // This is the static thumbnail
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl)

                // The actual "preview_video" for a GIF would be the animated GIF itself.
                // On Motherless, the linked page (/GI/...) would display the full image.
                // If the thumbnail 'src' itself is the animated GIF, then that's it.
                // Otherwise, preview_video might be the same as thumbnail if it's not directly an animated thumb.
                // Or, it could be a different attribute like 'data-original-src' if thumbs are static.
                // For Motherless, the full image page is what we link to, and that page shows the GIF.
                // So, preview_video can be considered the thumbnail itself or the URL to the image page.
                // Let's assume the thumbnail is static, and the 'url' leads to the view page.
                // 'preview_video' in this context should be the direct link to the .gif if available, else same as thumb.
                // On Motherless, the actual .gif URL might only be on the destination page.
                // For search results, the 'thumbnail' is what we get.
                let preview_video = $elem.find('img').attr('data-original-src') || thumbnail // A common pattern for full version
                preview_video = this._makeAbsolute(preview_video, this.baseUrl)


                if (title && url && url.includes('/GI')) {
                    // We can't confirm it's a GIF from here, but we list it as a potential GIF.
                    // The user will navigate to the `url` and see the content.
                    gifs.push({
                        title: title + " (Image/GIF)", // Indicate it might be an image or GIF
                        url, // Link to the Motherless page for the item
                        thumbnail, // Static thumbnail
                        preview_video, // Best guess for animated version or same as thumbnail
                        source: this.name,
                    })
                } else if (url && !url.includes('/GI')) {
                     log.debug(`Skipping non-gallery image item on ${this.name}: ${url}`)
                }
            } catch (e) {
                log.warn(`Error parsing image/GIF item on ${this.name}: ${e.message} - Item HTML: ${$(elem).parent().html().substring(0,100)}`)
            }
        })
        log.info(`Found ${gifs.length} image/GIF items on ${this.name} page: ${$._originalUrl || 'N/A'}`)
        if (gifs.length === 0 && rawHtmlOrJsonData && rawHtmlOrJsonData.length > 100) {
            log.warn(`No image/GIFs found for ${this.name} on ${$._originalUrl || 'N/A'}, but received HTML. Selectors might be outdated.`)
        }
        return gifs
    }
}

module.exports = MotherlessScraper
