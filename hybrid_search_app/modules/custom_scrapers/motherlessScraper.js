// modules/custom_scrapers/motherlessScraper.js
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const log = require('../../core/log');
const cheerio = require('cheerio');

class MotherlessScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://motherless.com';
        log.debug(`${this.name} scraper initialized - New GIF parser selectors`);
    }

    get name() {
        return 'Motherless';
    }

    get firstpage() {
        return 1;
    }

    // --- Video Search Methods ---
    videoUrl(query, page) {
        const url = `${this.baseUrl}/term/videos/${encodeURIComponent(query)}?page=${page}`;
        log.debug(`${this.name} video URL: ${url}`);
        return url;
    }

    async videoParser($, rawHtmlOrJsonData, sourceUrl = '') {
        log.info(`Parsing ${this.name} video page... Query URL: ${sourceUrl}`);
        const videos = [];
        $('div.thumb.is-video a[href*="/GI"]').each((i, elem) => {
            try {
                const $elem = $(elem);
                const title = $elem.find('img').attr('alt') || $elem.find('.title, .caption').text().trim();
                let url = $elem.attr('href');
                url = this._makeAbsolute(url, this.baseUrl);

                let thumbnail = $elem.find('img').attr('src');
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                const durationElement = $elem.find('.duration, .thumb-duration');
                const duration = durationElement.text().trim();
                let preview_video_url = $elem.find('img').attr('data-preview-url');
                preview_video_url = preview_video_url ? this._makeAbsolute(preview_video_url, this.baseUrl) : null;

                if (title && url && url.includes('/GI')) {
                    const videoData = { title, url, thumbnail, duration: duration || "N/A", source: this.name };
                    if (preview_video_url) videoData.preview_video = preview_video_url;
                    videos.push(videoData);
                } else if (url && !url.includes('/GI')) {
                    log.debug(`Skipping non-gallery item on ${this.name}: ${url}`);
                }
            } catch (e) {
                log.warn(`Error parsing video item on ${this.name}: ${e.message}`);
            }
        });
        log.info(`Found ${videos.length} video items on ${this.name} page.`);
        return videos;
    }

    async searchVideos(query = this.query, page = this.page) {
        const searchUrl = this.videoUrl(query, page);
        if (!searchUrl) {
            log.error(`${this.name}: Video URL could not be constructed.`);
            return [];
        }
        log.info(`${this.name}: Fetching HTML for videos from: ${searchUrl}`);
        try {
            const html = await this._fetchHtml(searchUrl);
            const $ = cheerio.load(html);
            return this.videoParser($, html, searchUrl);
        } catch (error) {
            log.error(`${this.name}: Error in searchVideos: ${error.message}`);
            return [];
        }
    }

    // --- GIF Search Methods (Points to Image Search) ---
    gifUrl(query, page) {
        const pageNumber = page || this.firstpage;
        const url = `${this.baseUrl}/term/images/${encodeURIComponent(query)}?page=${pageNumber}`;
        log.info(`${this.name} GIF search uses general image search URL: ${url}.`);
        return url;
    }

    async gifParser($, rawHtmlOrJsonData, sourceUrl = '') {
        log.info(`Parsing ${this.name} "GIF" (image) page with new selectors... Query URL: ${sourceUrl}`);
        const gifs = [];
        // New main item selector: Search for <a> tags linking to gallery items /GI/
        // Then check if their parent div.thumb has class .is-image or if they contain an image.
        const itemLinks = $('a[href*="/GI/"]');

        log.info(`Found ${itemLinks.length} potential gallery links using 'a[href*="/GI/"]'.`);

        itemLinks.each((i, elem) => {
            const itemLink = $(elem); // itemLink is the <a> tag itself

            // Check if the parent div.thumb has class .is-image
            // Or, more broadly, just ensure it's primarily an image link not a video one if possible
            const parentThumb = itemLink.closest('div.thumb');
            if (parentThumb.length && parentThumb.hasClass('is-video')) {
                log.debug(`Skipping item as its parent div.thumb is marked 'is-video': ${itemLink.attr('href')}`);
                return; // Skip this item, it's likely a video
            }
            // If no 'is-video' class, or no 'div.thumb' parent, proceed with caution.
            // This parser is for images/gifs.

            try {
                const imgTag = itemLink.find('img').first();
                if (!imgTag.length) { // If no image inside the link, skip
                    log.debug(`Skipping gallery link as it contains no img tag: ${itemLink.attr('href')}`);
                    return;
                }

                const title = imgTag.attr('alt') || itemLink.attr('title') || 'Image/GIF'; // Fallback title
                let url = itemLink.attr('href');
                url = this._makeAbsolute(url, this.baseUrl);

                let thumbnail = imgTag.attr('src');
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                // For Motherless images/GIFs, preview_video is likely the same as the main image content.
                // data-original-src might exist for higher-res, or it's just the thumbnail.
                let preview_video = imgTag.attr('data-original-src') || imgTag.attr('data-src') || thumbnail;
                preview_video = this._makeAbsolute(preview_video, this.baseUrl);

                if (title && url) {
                    gifs.push({
                        title: title + " (Image/GIF)",
                        url,
                        thumbnail,
                        preview_video,
                        source: this.name,
                        type: 'gifs'
                    });
                }
            } catch (e) {
                log.warn(`Error parsing image/GIF item on ${this.name} from link ${itemLink.attr('href')}: ${e.message}`);
            }
        });
        log.info(`Extracted ${gifs.length} image/GIF items on ${this.name} page with new selectors.`);
        if (gifs.length === 0 && itemLinks.length > 0) {
             log.warn(`Found ${itemLinks.length} gallery links but extracted 0 items. Sub-selector logic might need refinement or items are filtered out.`);
        }
        if (gifs.length === 0 && typeof rawHtmlOrJsonData === 'string' && rawHtmlOrJsonData.length > 100) {
             if (!itemLinks.length) log.warn(`No gallery links found for ${this.name} on ${sourceUrl}, but received HTML. Main selector 'a[href*="/GI/"]' failed.`);
        }
        return gifs;
    }

    async searchGifs(query = this.query, page = this.page) {
        const searchUrl = this.gifUrl(query, page);
        if (!searchUrl) {
            log.warn(`${this.name} GIF search: No URL returned by gifUrl.`);
            return [];
        }
        log.info(`${this.name}: Fetching HTML for GIFs (images) from: ${searchUrl}`);
        try {
            const html = await this._fetchHtml(searchUrl);
            const $ = cheerio.load(html);
            return this.gifParser($, html, searchUrl);
        } catch (error) {
            log.error(`${this.name}: Error in searchGifs: ${error.message}`);
            if (error.message && error.message.includes('404')) {
                log.warn(`${this.name} GIF search: Received 404 for URL ${searchUrl}.`);
            }
            return [];
        }
    }
}

module.exports = MotherlessScraper;
