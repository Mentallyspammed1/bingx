'use strict';

const AbstractModule = require('../core/AbstractModule');
const { makeAbsolute, extractPreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL = 'https://www.sex.com';
// Frontend driverSelect uses "sex", so orchestrator will likely map "Sex.com" to "sex" or use "sex" as key.
// Let's use "Sex.com" for display name and assume orchestrator handles mapping if its key is "sex".
const DRIVER_NAME = 'Sex.com';

/**
 * @class SexComDriver
 * @classdesc Driver for scraping video and GIF content from Sex.com.
 */
class SexComDriver extends AbstractModule {
    constructor(options = {}) {
        super(options);
    }

    get supportsVideos() {
        return true;
    }

    get supportsGifs() {
        return true;
    }

    get name() {
        return DRIVER_NAME;
    }

    get baseUrl() {
        return BASE_URL;
    }

    /**
     * Constructs the URL for searching videos on Sex.com.
     * Example: https://www.sex.com/search/videos?query=test&page=1
     * @param {string} query - The search query string.
     * @param {number} page - The page number for search results (1-indexed).
     * @returns {string} The fully qualified URL for video search.
     */
    getVideoSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for video search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);

        const searchUrl = new URL('/search/videos', this.baseUrl); // Specific path for videos
        searchUrl.searchParams.set('query', query.trim());
        searchUrl.searchParams.set('page', String(searchPage));

        // console.log(`[${this.name}] Generated video URL: ${searchUrl.href}`);
        return searchUrl.href;
    }

    /**
     * Constructs the URL for searching GIFs on Sex.com.
     * Example: https://www.sex.com/search/gifs?query=test&page=1
     * @param {string} query - The search query string.
     * @param {number} page - The page number for search results (1-indexed).
     * @returns {string} The fully qualified URL for GIF search.
     */
    getGifSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for GIF search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);

        const searchUrl = new URL('/search/gifs', this.baseUrl); // Specific path for gifs
        searchUrl.searchParams.set('query', query.trim());
        searchUrl.searchParams.set('page', String(searchPage));

        // console.log(`[${this.name}] Generated GIF URL: ${searchUrl.href}`);
        return searchUrl.href;
    }

    /**
     * Parses HTML from a Sex.com search results page.
     * @param {CheerioAPI} $ - Cheerio object.
     * @param {string|object} htmlOrJsonData - Raw HTML or JSON data.
     * @param {object} parserOptions - Options including type, sourceName, query, page.
     * @returns {Array<object>} Array of MediaResult objects.
     */
    parseResults($, htmlOrJsonData, parserOptions) {
        if (!$) {
            // console.warn(`[${this.name}] Cheerio object ($) is null. Expecting HTML.`);
            return [];
        }

        const results = [];
        const isGifSearch = parserOptions.type === 'gifs';

        // Selectors for Sex.com are highly speculative and need verification.
        // Common list item classes: 'masonry_box', 'thumb', 'item'
        const itemSelector = 'div.masonry_box';

        $(itemSelector).each((i, el) => {
            const item = $(el);

            const pageUrlFromVideo = item.find('a[href*="/video/"]').attr('href');
            const pageUrlFromGif = item.find('a[href*="/gifs/"]').attr('href');

            if (isGifSearch && !pageUrlFromGif) return;
            if (!isGifSearch && !pageUrlFromVideo) return;

            const linkElement = item.find('a.image_wrapper, a.title_link, a.box_link').first();
            let pageUrl = linkElement.attr('href');

            let title = item.find('p.title, h2.title, div.video_title').text()?.trim() ||
                        linkElement.attr('title')?.trim() ||
                        item.find('img').attr('alt')?.trim();

            if (!pageUrl) {
                 // Try to find a link within a known wrapper if the primary one failed
                const fallbackLink = item.find('.image_wrapper a, .video_shortlink_container a').first();
                pageUrl = fallbackLink.attr('href');
                if (!title) title = fallbackLink.attr('title')?.trim();
            }

            if (!pageUrl || !title) {
                // console.warn(`[${this.name}] Item ${i} (${parserOptions.type}): Skipping due to missing title or page URL.`);
                return;
            }

            const imgElement = item.find('img.responsive_image, img.main_image, img.thumb_image').first();
            let thumbnailUrl = imgElement.attr('data-src') || imgElement.attr('src');

            let previewUrl = extractPreview($, item, this.name, this.baseUrl);

            const durationText = isGifSearch ? undefined : item.find('span.duration, .video_duration').text()?.trim();

            // ID extraction for Sex.com (speculative)
            // URLs might be like /video/123456-title or /gifs/123456-title
            let mediaId = null;
            const idMatch = pageUrl.match(/\/(?:video|gifs)\/(\d+)/);
            if (idMatch && idMatch[1]) {
                mediaId = idMatch[1];
            } else {
                 mediaId = item.attr('data-id') || item.attr('id');
                 if (mediaId && mediaId.includes('_')) mediaId = mediaId.split('_').pop();
            }

            const absoluteUrl = makeAbsolute(pageUrl, this.baseUrl);
            const absoluteThumbnail = makeAbsolute(thumbnailUrl, this.baseUrl);
            const absolutePreview = makeAbsolute(previewUrl, this.baseUrl);

            if (!absoluteUrl || !title) {
                 return;
            }

            results.push({
                id: mediaId || `sexcom_${parserOptions.type}_${i}`,
                title: title,
                url: absoluteUrl,
                thumbnail: absoluteThumbnail || '',
                duration: durationText || (isGifSearch ? undefined : 'N/A'),
                preview_video: absolutePreview || (isGifSearch ? absoluteThumbnail : ''),
                source: this.name,
                type: parserOptions.type
            });
        });

        // console.log(`[${this.name}] Parsed ${results.length} ${parserOptions.type} items.`);
        return results;
    }
}

module.exports = SexComDriver;
