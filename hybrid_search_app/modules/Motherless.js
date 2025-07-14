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
        const itemSelector = 'a.thumb-link';

        $(itemSelector).each((i, el) => {
            const item = $(el);
            const linkElement = item.find('a[href*="/"]').first();
            let pageUrl = linkElement.attr('href');

            let title = sanitizeText(
                item.find('img').attr('alt')?.trim() ||
                linkElement.attr('title')?.trim() ||
                item.find('div.caption, .thumb-title').text()?.trim()
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

            const imgElement = item.find('img').first();
            let thumbnailUrl = imgElement.attr('src') || imgElement.attr('data-src');
            const previewUrl = extractPreview($, item, this.name, this.baseUrl);
            const durationText = isGifSearch ? undefined : sanitizeText(item.find('.video_length').text()?.trim());

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