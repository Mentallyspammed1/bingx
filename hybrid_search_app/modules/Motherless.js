const AbstractModule = require('../core/AbstractModule');
const VideoMixin = require('../core/VideoMixin');
const GifMixin = require('../core/GifMixin');
const { makeAbsolute, extractPreview, sanitizeText, validatePreview } = require('./driver-utils.js');

const BaseMotherlessClass = AbstractModule.with(VideoMixin, GifMixin);

class Motherless extends BaseMotherlessClass {
    constructor(options = {}) {
        super(options);
        this.logger = require('../core/log.js').child({ module: 'Motherless' });
    }

    get supportsVideos() {
        return true;
    }

    get supportsGifs() {
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
            throw new Error(`Search query is not set for video search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        const searchPath = `/term/videos/${encodeURIComponent(query.trim())}`;
        const searchUrl = new URL(searchPath, this.baseUrl);
        searchUrl.searchParams.set('page', String(searchPage));
        return searchUrl.href;
    }

    getGifSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`Search query is not set for GIF search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        const searchPath = `/term/images/${encodeURIComponent(query.trim())}`; // Note: '/images/' for GIFs
        const searchUrl = new URL(searchPath, this.baseUrl);
        searchUrl.searchParams.set('page', String(searchPage));
        return searchUrl.href;
    }

    parseResults($, htmlOrJsonData, parserOptions) {
        const { type, sourceName, isMock } = parserOptions;
        const results = [];
        if (!$) {
            this.logger.warn(`Cheerio instance not provided for HTML parsing.`);
            return [];
        }

        if (!isMock) {
            // Check for common indicators of no results or a block page
            const noResultsText = $('div.no-results-message, p.no-results').text();
            if (noResultsText.length > 0) {
                this.logger.warn(`No results found or block page detected for query: "${parserOptions.query}". Message: ${noResultsText.trim().substring(0, 100)}`);
                return [];
            }

            // Check for Cloudflare or other common block page elements
            if ($('#cf-wrapper').length > 0 || $('body:contains("Attention Required!")').length > 0) {
                this.logger.error(`Cloudflare or similar block page detected for query: "${parserOptions.query}".`);
                return [];
            }
        }

        const isGifSearch = parserOptions.type === 'gifs';
        const itemSelector = isGifSearch ? 'div.thumb.image > a' : 'div.thumb.video > a';

        $(itemSelector).each((i, el) => {
            const item = $(el);
            let pageUrl = item.attr('href');

            let title = sanitizeText(
                item.attr('title')?.trim() ||
                item.find('img').attr('alt')?.trim() ||
                item.find('div.caption, div.thumb-title, div.title, h5.title').text()?.trim()
            );

            if (!pageUrl) {
                this.logger.warn(`Skipping item ${i}: missing page URL.`);
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
                this.logger.warn(`Skipping item ${i}: missing absolute URL or title.`);
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

        this.logger.info(`Parsed ${results.length} ${type} items.`);
        return results;
    }
}

module.exports = Motherless;