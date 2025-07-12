const AbstractModule = require('../core/AbstractModule');
const { makeAbsolute, extractPreview, sanitizeText, validatePreview } = require('./driver-utils.js');

class Motherless extends AbstractModule {
    constructor(options = {}) {
        super(options);
    }

    hasVideoSupport() {
        return true;
    }

    hasGifSupport() {
        return true; // Motherless has distinct sections for images/GIFs
    }

    get name() {
        return 'Motherless';
    }

    get baseUrl() {
        return 'https://motherless.com';
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
        const { type, sourceName } = parserOptions;
        const results = [];
        if (!$) {
            
            return [];
        }

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

            const absoluteUrl = makeAbsolute(pageUrl, this.baseUrl);
            const absoluteThumbnail = makeAbsolute(thumbnailUrl, this.baseUrl);
            const absolutePreview = makeAbsolute(previewUrl, this.baseUrl);

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

        
        return results;
    }

    
}

module.exports = Motherless;