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
        const itemContainers = $('div.thumb');

        if (itemContainers.length === 0 && typeof rawHtmlOrJsonData === 'string') {
            log.warn(`${this.name} videoParser: Main item selector 'div.thumb' found 0 elements. HTML (first 1000 chars): ${rawHtmlOrJsonData.substring(0, 1000)}`);
            return videos;
        }

        itemContainers.each((i, container) => {
            const itemContainer = $(container);
            try {
                // Filter: Check if it's a video
                if (!itemContainer.hasClass('is-video') && itemContainer.find('.duration, .thumb-duration, .video-duration').filter((idx, el) => $(el).text().trim() !== '').length === 0) {
                    log.debug(`${this.name} videoParser: Skipping item, not identified as video (no 'is-video' class or duration): ${itemContainer.find('a').first().attr('href') || 'No link'}`);
                    return; // Skip if not explicitly a video and no duration found
                }

                const $elem = itemContainer.find('a').first();
                if (!$elem.length) {
                    log.debug(`${this.name} videoParser: Skipping itemContainer, no 'a' tag found.`);
                    return;
                }

                let url = $elem.attr('href');
                if (!url || !/^\/[A-Z0-9]+$/.test(url.split('?')[0].split('#')[0])) { // Check if URL is a direct media link
                    log.debug(`${this.name} videoParser: Skipping item, URL doesn't match media pattern: ${url}`);
                    return;
                }
                url = this._makeAbsolute(url, this.baseUrl);

                const imgTag = $elem.find('img').first();
                const title = (imgTag.attr('alt') || $elem.attr('title') || itemContainer.find('.title, .caption').last().text() || 'Video').trim();
                let thumbnail = imgTag.attr('src');
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                const durationText = (itemContainer.find('.duration, .thumb-duration, .video-duration').first().text() || '').trim();

                let preview_video_url = imgTag.attr('data-preview-url') || imgTag.attr('onmouseover'); // onmouseover sometimes contains a preview URL in JS
                if (preview_video_url && preview_video_url.includes('this.src=')) { // Extract URL from JS in onmouseover
                    const match = preview_video_url.match(/this\.src='([^']+)'/);
                    preview_video_url = match ? match[1] : null;
                }
                preview_video_url = preview_video_url ? this._makeAbsolute(preview_video_url, this.baseUrl) : null;

                if (title && url) {
                    const videoData = { title, url, thumbnail, duration: durationText || "N/A", source: this.name };
                    if (preview_video_url) videoData.preview_video = preview_video_url;
                    videos.push(videoData);
                } else {
                    log.debug(`${this.name} videoParser: Skipped item due to missing title or URL after processing. URL: ${url}, Title: ${title}`);
                }
            } catch (e) {
                log.warn(`${this.name} videoParser: Error parsing video item: ${e.message}`, itemContainer.html().substring(0, 200));
            }
        });

        if (videos.length === 0 && itemContainers.length > 0) {
            log.warn(`${this.name} videoParser: Found ${itemContainers.length} 'div.thumb' items but extracted 0 videos. Filtering or sub-selectors might be the issue.`);
        }
        log.info(`Extracted ${videos.length} video items from ${itemContainers.length} potential containers on ${this.name} page.`);
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
        log.info(`Parsing ${this.name} "GIF" (image) page... Query URL: ${sourceUrl}`);
        const gifs = [];
        const itemContainers = $('div.thumb');

        if (itemContainers.length === 0 && typeof rawHtmlOrJsonData === 'string') {
            log.warn(`${this.name} gifParser: Main item selector 'div.thumb' found 0 elements. HTML (first 1000 chars): ${rawHtmlOrJsonData.substring(0, 1000)}`);
            return gifs;
        }

        itemContainers.each((i, container) => {
            const itemContainer = $(container);
            try {
                // Filter: Check if it's an image/GIF (i.e., NOT a video)
                // Skip if it has 'is-video' class or a non-empty duration span.
                if (itemContainer.hasClass('is-video') || itemContainer.find('.duration, .thumb-duration, .video-duration').filter((idx, el) => $(el).text().trim() !== '').length > 0) {
                    log.debug(`${this.name} gifParser: Skipping item, identified as video: ${itemContainer.find('a').first().attr('href') || 'No link'}`);
                    return;
                }
                 // Also check for is-image class for explicit targeting
                if (!itemContainer.hasClass('is-image') && !itemContainer.hasClass('is-photo')) {
                     // If it's not explicitly an image/photo and also not a video (by previous check), it's ambiguous.
                     // We can decide to process it or skip. For now, let's process if it has an image link.
                     if (itemContainer.find('a > img').length === 0) {
                        log.debug(`${this.name} gifParser: Skipping ambiguous item, not marked as image/photo and no direct img child of link: ${itemContainer.find('a').first().attr('href') || 'No link'}`);
                        return;
                     }
                }


                const $elem = itemContainer.find('a').first();
                if (!$elem.length) {
                    log.debug(`${this.name} gifParser: Skipping itemContainer, no 'a' tag found.`);
                    return;
                }

                let url = $elem.attr('href');
                // Ensure it's a media link (e.g., matches ^/[A-Z0-9]+$) and not a gallery link /GI/
                if (!url || !/^\/[A-Z0-9]+$/.test(url.split('?')[0].split('#')[0]) || url.includes('/GI/')) {
                    log.debug(`${this.name} gifParser: Skipping item, URL doesn't match media pattern or is gallery link: ${url}`);
                    return;
                }
                url = this._makeAbsolute(url, this.baseUrl);

                const imgTag = $elem.find('img').first();
                if (!imgTag.length) {
                     log.debug(`${this.name} gifParser: Skipping item, no 'img' tag found within link: ${url}`);
                     return;
                }

                const title = (imgTag.attr('alt') || $elem.attr('title') || itemContainer.find('.title, .caption').last().text() || 'Image/GIF').trim();
                let thumbnail = imgTag.attr('src');
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                // For Motherless images/GIFs, preview_video is the full image/GIF.
                // data-original-src might exist for higher-res, or it's just the thumbnail (which is often full size for gifs).
                let preview_video = imgTag.attr('data-original-src') || imgTag.attr('data-src') || thumbnail;
                preview_video = this._makeAbsolute(preview_video, this.baseUrl);

                if (title && url && preview_video) { // Ensure preview_video (full image) is present
                    gifs.push({
                        title: title, // No longer adding "(Image/GIF)" as type is 'gifs'
                        url,
                        thumbnail, // This might be low-res, preview_video is key
                        preview_video, // This is the actual full image/GIF
                        source: this.name,
                        type: 'gifs' // Explicitly type it for downstream
                    });
                } else {
                    log.debug(`${this.name} gifParser: Skipped item due to missing title, URL, or preview_video. URL: ${url}, Title: ${title}, Preview: ${preview_video}`);
                }
            } catch (e) {
                log.warn(`${this.name} gifParser: Error parsing image/GIF item: ${e.message}`, itemContainer.html().substring(0, 200));
            }
        });

        if (gifs.length === 0 && itemContainers.length > 0) {
            log.warn(`${this.name} gifParser: Found ${itemContainers.length} 'div.thumb' items but extracted 0 images/GIFs. Filtering or sub-selectors might be the issue.`);
        }
        log.info(`Extracted ${gifs.length} image/GIF items from ${itemContainers.length} potential containers on ${this.name} page.`);
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
