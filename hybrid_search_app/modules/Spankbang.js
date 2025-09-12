const AbstractModule = require('../core/AbstractModule');
const VideoMixin = require('../core/VideoMixin');
const GifMixin = require('../core/GifMixin');
const { makeAbsolute, extractPreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL = 'https://www.spankbang.com';
const DRIVER_NAME = 'Spankbang';

const BaseSpankbangClass = AbstractModule.with(VideoMixin, GifMixin);

class SpankbangDriver extends BaseSpankbangClass {
    constructor(options = {}) {
        super(options);
        this.logger = require('../core/log.js').child({ module: 'SpankbangDriver' });
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

    getVideoSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`Search query is not set for video search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        const pageSegment = searchPage > 1 ? `${searchPage}/` : '';
        const searchUrl = new URL(`/s/${encodeURIComponent(query.trim())}/${pageSegment}`, this.baseUrl);
        searchUrl.searchParams.set('o', 'new');
        return searchUrl.href;
    }

    getGifSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`Search query is not set for GIF search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        const pageSegment = searchPage > 1 ? `${searchPage}/` : '';
        const searchPath = `/gifs/search/${encodeURIComponent(query.trim())}/${pageSegment}`;
        const searchUrl = new URL(searchPath, this.baseUrl);
        return searchUrl.href;
    }

    getCustomHeaders() {
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Upgrade-Insecure-Requests': '1',
            'Cookie': 'age_verified=1; cookies_accepted=1;'
        };
    }

    parseResults($, htmlOrJsonData, parserOptions) {
        const { isMock } = parserOptions;
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

        const results = [];
        const isGifSearch = parserOptions.type === 'gifs';
        const itemSelector = 'div.video-item';

        $(itemSelector).each((i, el) => {
            const item = $(el);
            const linkElement = item.find('a.thumb').first();
            let pageUrl = linkElement.attr('href');

            let title = sanitizeText(
                linkElement.attr('title')?.trim() ||
                item.find('div.inf > p > a[href*="/video"]').text()?.trim()
            );

            if (!title && pageUrl) {
                 const parts = pageUrl.split('/');
                 const slug = parts.filter(p => p && p !== 'video' && p !== 'gif').pop();
                 if (slug) title = sanitizeText(slug.replace(/[-_]/g, ' ').replace(/\.\w+$/, ""));
            }
            if (!title) title = `Spankbang Content ${i+1}`;

            if (!pageUrl) {
                this.logger.warn(`Item ${i} (${parserOptions.type}): Skipping due to missing page URL.`);
                return;
            }

            const imgElement = item.find('img.lazy, img.thumb_img').first();
            let thumbnailUrl = imgElement.attr('data-src') || imgElement.attr('src');
            const previewUrl = extractPreview($, item, this.name, this.baseUrl);
            const durationText = isGifSearch ? undefined : sanitizeText(item.find('div.l, span.duration, div.dur').text()?.trim());

            let mediaId = null;
            const idMatch = pageUrl.match(/^\/([a-zA-Z0-9]+)\/(?:video|gif)\/$/);
            if (idMatch && idMatch[1]) {
                mediaId = idMatch[1];
            } else {
                const parts = pageUrl.split('/');
                if (parts.length > 1) mediaId = parts[1];
            }

            const absoluteUrl = makeAbsolute(pageUrl, this.baseUrl);
            const absoluteThumbnail = makeAbsolute(thumbnailUrl, this.baseUrl);

            if (!absoluteUrl || !title) {
                this.logger.warn(`Item ${i}: Failed to resolve absolute URL or title is missing.`);
                return;
            }

            results.push({
                id: mediaId || `sb_${parserOptions.type}_${i}`,
                title: title,
                url: absoluteUrl,
                thumbnail: absoluteThumbnail || '',
                duration: isGifSearch ? undefined : (durationText || 'N/A'),
                preview_video: previewUrl || (isGifSearch ? absoluteThumbnail : ''),
                source: this.name,
                type: parserOptions.type
            });
        });

        this.logger.info(`Parsed ${results.length} ${parserOptions.type} items.`);
        return results;
    }
}

module.exports = SpankbangDriver;