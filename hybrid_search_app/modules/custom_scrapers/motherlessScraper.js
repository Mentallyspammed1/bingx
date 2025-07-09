'use strict';

let AbstractModule;
try {
    AbstractModule = require('../core/AbstractModule');
} catch (e) {
    AbstractModule = class {
        constructor(query) { this.query = query; }
        get name() { return 'UnnamedDriver'; }
        get baseUrl() { return ''; }
        get supportsVideos() { return false; }
        get supportsGifs() { return false; }
        get firstpage() { return 1; }
    };
}

const BASE_URL = 'https://motherless.com';
const DRIVER_NAME = 'Motherless'; // Match frontend dropdown

/**
 * @class MotherlessDriver
 * @classdesc Driver for scraping video and image/GIF content from Motherless.
 */
class MotherlessDriver extends AbstractModule {
    constructor(query) {
        super(query);
        this.supportsVideos = true;
        this.supportsGifs = true; // Motherless has distinct sections for images/GIFs
        this.firstpage = 1;
    }

    get name() {
        return DRIVER_NAME;
    }

    get baseUrl() {
        return BASE_URL;
    }

    /**
     * Constructs the URL for searching videos on Motherless.
     * Example: https://motherless.com/term/videos/test?page=1
     * @param {string} query - The search query string.
     * @param {number} page - The page number for search results (1-indexed).
     * @returns {string} The fully qualified URL for video search.
     */
    getVideoSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for video search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        // Motherless uses path-based search for terms, and a 'page' query parameter.
        const searchPath = `/term/videos/${encodeURIComponent(query.trim())}`;
        const searchUrl = new URL(searchPath, this.baseUrl);
        searchUrl.searchParams.set('page', String(searchPage));

        // console.log(`[${this.name}] Generated video URL: ${searchUrl.href}`);
        return searchUrl.href;
    }

    /**
     * Constructs the URL for searching images/GIFs on Motherless.
     * Example: https://motherless.com/term/images/test?page=1
     * @param {string} query - The search query string.
     * @param {number} page - The page number for search results (1-indexed).
     * @returns {string} The fully qualified URL for GIF search.
     */
    getGifSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for GIF search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        const searchPath = `/term/images/${encodeURIComponent(query.trim())}`; // Note: '/images/' for GIFs
        const searchUrl = new URL(searchPath, this.baseUrl);
        searchUrl.searchParams.set('page', String(searchPage));

        // console.log(`[${this.name}] Generated GIF URL: ${searchUrl.href}`);
        return searchUrl.href;
    }

    /**
     * Parses HTML from a Motherless search results page.
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

        // General item selector for Motherless (Galleries or direct items)
        // This is highly speculative and NEEDS VERIFICATION.
        // Motherless structure is often complex with nested thumbs.
        const itemSelector = 'div.content-inner div.thumb';

        $(itemSelector).each((i, el) => {
            const item = $(el);

            const linkElement = item.find('a[href*="/"]').first(); // Find first link, could be to gallery or media
            let pageUrl = linkElement.attr('href');

            // Title might be in various places: alt text of image, a caption, or derived from URL
            let title = item.find('img').attr('alt')?.trim() ||
                        linkElement.attr('title')?.trim() ||
                        item.find('div.caption, .thumb-title').text()?.trim();

            if (!pageUrl) { // If no link, this item might not be what we want
                // console.warn(`[${this.name}] Item ${i} (${parserOptions.type}): Skipping due to missing page URL.`);
                return;
            }
            if (!title && pageUrl) { // Fallback title from URL
                 const parts = pageUrl.split('/');
                 const slug = parts.pop() || parts.pop();
                 if (slug) title = slug.replace(/[-_]/g, ' ').replace(/\.[^/.]+$/, ""); // Remove extension
            }
            if (!title) title = `Motherless Content ${i+1}`;


            const imgElement = item.find('img').first();
            let thumbnailUrl = imgElement.attr('src') || imgElement.attr('data-src');

            // Motherless previews for videos might be complex (e.g. sprite sheets or JS controlled)
            // For GIFs, the thumbnail is often the GIF itself or a static version.
            let previewUrl = thumbnailUrl; // Default preview to thumbnail for GIFs
            if (!isGifSearch) {
                // Video preview logic would be very specific to Motherless's player/preview mechanism
                // This might involve looking for data attributes or specific video tags if they exist.
                // For now, we'll assume no separate animated preview for videos via simple scraping.
                previewUrl = undefined;
            } else { // For GIFs, the main image is usually the preview
                 previewUrl = thumbnailUrl;
            }

            // Duration is typically not available for Motherless galleries in search listings.
            const durationText = undefined;

            // ID extraction: Motherless URLs often have unique codes like /GALLERY/A1B2C3D or /M/A1B2C3D
            let mediaId = null;
            const idMatch = pageUrl.match(/\/([A-Z0-9]{6,})/); // Matches 6+ alphanumeric uppercase chars
            if (idMatch && idMatch[1]) {
                mediaId = idMatch[1];
            } else {
                const parts = pageUrl.split('/');
                mediaId = parts.pop() || parts.pop(); // last part of URL as fallback
            }

            const absoluteUrl = this._makeAbsolute(pageUrl, this.baseUrl);
            const absoluteThumbnail = this._makeAbsolute(thumbnailUrl, this.baseUrl);
            const absolutePreview = this._makeAbsolute(previewUrl, this.baseUrl);

            if (!absoluteUrl || !title) {
                 return;
            }

            results.push({
                id: mediaId || `ml_${parserOptions.type}_${i}`,
                title: title,
                url: absoluteUrl,
                thumbnail: absoluteThumbnail || '',
                duration: isGifSearch ? undefined : (durationText || 'N/A'),
                preview_video: absolutePreview || (isGifSearch ? absoluteThumbnail : ''), // For GIFs, preview can be the thumb
                source: this.name,
                type: parserOptions.type
            });
        });

        // console.log(`[${this.name}] Parsed ${results.length} ${parserOptions.type} items.`);
        return results;
    }

    _makeAbsolute(urlString, baseUrl) {
        if (!urlString || typeof urlString !== 'string' || urlString.trim() === '') return undefined;
        if (urlString.startsWith('data:image/')) return urlString;
        try {
            if (urlString.startsWith('//')) {
                return new URL(`https:${urlString}`).href;
            }
            if (urlString.startsWith('http:') || urlString.startsWith('https:')) {
                return new URL(urlString).href; // Validate and normalize
            }
            return new URL(urlString, baseUrl).href;
        } catch (e) {
            // console.warn(`[${this.name}] Failed to resolve URL: "${urlString}" with base "${baseUrl}"`, e.message);
            return undefined;
        }
    }
}

module.exports = MotherlessDriver;
