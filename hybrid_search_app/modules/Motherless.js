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

    getVideoSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for video search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        const searchPath = `/term/videos/${encodeURIComponent(query.trim())}`;
        const searchUrl = new URL(searchPath, this.baseUrl);
        searchUrl.searchParams.set('page', String(searchPage));
        return searchUrl.href;
    }

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

    parseResults($, htmlOrJsonData, parserOptions) {
        const { type, sourceName } = parserOptions;
        const results = [];
        if (!$) {
            return [];
        }

        const isGifSearch = parserOptions.type === 'gifs';
        const itemSelector = 'div.content-item'; // More generic selector for content items

        $(itemSelector).each((i, el) => {
            const item = $(el);
            let pageUrl = item.find('a.img-action').attr('href'); // Assuming a common link for the item

            let title = sanitizeText(
                item.find('img').attr('alt')?.trim() ||
                item.find('a.img-action').attr('title')?.trim() ||
                item.find('div.title, h5.title').text()?.trim() // Common title selectors
            );

            if (!pageUrl) {
                return;
            }
            if (!title && pageUrl) {
                 const parts = pageUrl.split('/');
                 const slug = parts.pop() || parts.pop();
                 if (slug) title = sanitizeText(slug.replace(/[-_]/g, ' ').replace(/\.[^/.]+$/, ""));
            }
            if (!title) title = `Motherless Content ${i+1}`;

            const imgElement = item.find('img.img-responsive').first(); // Common image class
            let thumbnailUrl = imgElement.attr('src') || imgElement.attr('data-src');
            const previewUrl = extractPreview($, item, this.name, this.baseUrl);
            const durationText = isGifSearch ? undefined : sanitizeText(item.find('.duration, .time').text()?.trim()); // Common duration selectors

            let mediaId = null;
            const idMatch = pageUrl.match(/\/([A-Z0-9]{6,})/);
            if (idMatch && idMatch[1]) {
                mediaId = idMatch[1];
            } else {
                const parts = pageUrl.split('/');
                mediaId = parts.pop() || parts.pop();
            }

            const absoluteUrl = makeAbsolute(pageUrl, this.baseUrl);
            const absoluteThumbnail = makeAbsolute(thumbnailUrl, this.baseUrl);

            if (!absoluteUrl || !title) {
                 return;
            }

            results.push({
                id: mediaId || `ml_${parserOptions.type}_${i}`,
                title: title,
                url: absoluteUrl,
                thumbnail: absoluteThumbnail || '',
                duration: isGifSearch ? undefined : (durationText || 'N/A'),
                preview_video: previewUrl || (isGifSearch ? absoluteThumbnail : ''),
                source: this.name,
                type: parserOptions.type
            });
        });

        return results;
    }
}

module.exports = Motherless;