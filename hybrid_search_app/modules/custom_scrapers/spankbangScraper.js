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

const BASE_URL = 'https://www.spankbang.com';
// Frontend driverSelect does not list Spankbang. Assuming "Spankbang" or "SpankBang" would be its name.
const DRIVER_NAME = 'Spankbang';

/**
 * @class SpankbangDriver
 * @classdesc Driver for scraping video and GIF content from Spankbang.
 */
class SpankbangDriver extends AbstractModule {
    constructor(query) {
        super(query);
        this.name = DRIVER_NAME;
        this.baseUrl = BASE_URL;
        this.supportsVideos = true;
        this.supportsGifs = true;
        this.firstpage = 1; // Spankbang pagination is 1-indexed in the path
    }

    /**
     * Constructs the URL for searching videos on Spankbang.
     * Example: https://www.spankbang.com/s/test/2/?o=new (page 2)
     * First page: https://www.spankbang.com/s/test/?o=new
     * @param {string} query - The search query string.
     * @param {number} page - The page number for search results (1-indexed).
     * @returns {string} The fully qualified URL for video search.
     */
    getVideoSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for video search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        const pageSegment = searchPage > 1 ? `${searchPage}/` : '';
        // The `o=new` sorts by newest. Other options exist (trending, popular).
        const searchUrl = new URL(`/s/${encodeURIComponent(query.trim())}/${pageSegment}`, this.baseUrl);
        searchUrl.searchParams.set('o', 'new');

        // console.log(`[${this.name}] Generated video URL: ${searchUrl.href}`);
        return searchUrl.href;
    }

    /**
     * Constructs the URL for searching GIFs on Spankbang.
     * Example: https://spankbang.com/gifs/search/test/2/
     * @param {string} query - The search query string.
     * @param {number} page - The page number for search results (1-indexed).
     * @returns {string} The fully qualified URL for GIF search.
     */
    getGifSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for GIF search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        const pageSegment = searchPage > 1 ? `${searchPage}/` : '';
        // Path for GIFs: /gifs/search/QUERY/PAGE/
        const searchPath = `/gifs/search/${encodeURIComponent(query.trim())}/${pageSegment}`;
        const searchUrl = new URL(searchPath, this.baseUrl);

        // console.log(`[${this.name}] Generated GIF URL: ${searchUrl.href}`);
        return searchUrl.href;
    }

    /**
     * Parses HTML from a Spankbang search results page.
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

        // Selectors adapted from the original spankbangScraper.js
        // These MUST BE VERIFIED against live Spankbang HTML.
        // Spankbang uses 'div.video-item' for both videos and GIFs in their respective search results.
        const itemSelector = 'div.video-item';

        $(itemSelector).each((i, el) => {
            const item = $(el);
            let title, pageUrl, thumbnailUrl, previewUrl, durationText, mediaId;

            const linkElement = item.find('a.thumb').first();
            pageUrl = linkElement.attr('href');
            title = linkElement.attr('title')?.trim();

            if (!title && !isGifSearch) { // Fallback for video titles if not on <a>
                title = item.find('div.inf > p > a[href*="/video"]').text()?.trim();
            }
             if (!title && pageUrl) { // Generic title fallback from URL
                 const parts = pageUrl.split('/');
                 const slug = parts.filter(p => p && p !== 'video' && p !== 'gif').pop();
                 if (slug) title = slug.replace(/[-_]/g, ' ').replace(/\.\w+$/, "");
            }
            if (!title) title = `Spankbang Content ${i+1}`;

            if (!pageUrl) {
                // console.warn(`[${this.name}] Item ${i} (${parserOptions.type}): Skipping due to missing page URL.`);
                return;
            }

            const imgElement = item.find('img.lazy, img.thumb_img').first(); // Added .thumb_img as potential fallback
            thumbnailUrl = imgElement.attr('data-src') || imgElement.attr('src');

            // Preview: Spankbang uses 'data-preview' on the <a> tag.
            previewUrl = linkElement.attr('data-preview');
            if (!previewUrl && !isGifSearch) { // Fallback for videos if not on <a>
                previewUrl = item.find('picture > source[type="video/mp4"]').attr('data-preview');
            }

            if (!isGifSearch) {
                durationText = item.find('div.l, span.duration, div.dur').text()?.trim(); // .dur is another common class
            }

            // ID extraction: URLs like /<id>/video/ or /<id>/gif/
            const idMatch = pageUrl.match(/^\/([a-zA-Z0-9]+)\/(?:video|gif)\//);
            if (idMatch && idMatch[1]) {
                mediaId = idMatch[1];
            } else { // Fallback if specific pattern fails
                const parts = pageUrl.split('/');
                if (parts.length > 1) mediaId = parts[1]; // Second segment is often the ID
            }

            const absoluteUrl = this._makeAbsolute(pageUrl, this.baseUrl);
            const absoluteThumbnail = this._makeAbsolute(thumbnailUrl, this.baseUrl);
            const absolutePreview = this._makeAbsolute(previewUrl, this.baseUrl);

            if (!absoluteUrl || !title) {
                 return;
            }

            results.push({
                id: mediaId || `sb_${parserOptions.type}_${i}`,
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
                return new URL(urlString).href;
            }
            // Spankbang hrefs are often relative from root
            return new URL(urlString, baseUrl).href;
        } catch (e) {
            // console.warn(`[${this.name}] Failed to resolve URL: "${urlString}" with base "${baseUrl}"`, e.message);
            return undefined;
        }
    }
}

module.exports = SpankbangDriver;
