'use strict';

const AbstractModule = require('../core/AbstractModule');
const { makeAbsolute, extractPreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL = 'https://www.spankbang.com';
const DRIVER_NAME = 'Spankbang';

/**
 * @class SpankbangDriver
 * @classdesc Driver for scraping video and GIF content from Spankbang.
 */
class SpankbangDriver extends AbstractModule {
    constructor(options = {}) {
        super(options);
    }

    hasVideoSupport() {
        return true;
    }

    hasGifSupport() {
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
            throw new Error(`[${this.name}] Search query is not set for video search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        const pageSegment = searchPage > 1 ? `${searchPage}/` : '';
        const searchUrl = new URL(`/s/${encodeURIComponent(query.trim())}/${pageSegment}`, this.baseUrl);
        searchUrl.searchParams.set('o', 'new');
        return searchUrl.href;
    }

    getGifSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for GIF search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        const pageSegment = searchPage > 1 ? `${searchPage}/` : '';
        const searchPath = `/gifs/search/${encodeURIComponent(query.trim())}/${pageSegment}`;
        const searchUrl = new URL(searchPath, this.baseUrl);
        return searchUrl.href;
    }

    getCustomHeaders() {
        return {
            'Upgrade-Insecure-Requests': '1',
            'Cookie': 'age_verified=1; cookies_accepted=1;'
        };
    }

    parseResults($, htmlOrJsonData, parserOptions) {
        if (!$) {
            return [];
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
                return;
            }

            const imgElement = item.find('img.lazy, img.thumb_img').first();
            let thumbnailUrl = imgElement.attr('data-src') || imgElement.attr('src');
            const previewUrl = extractPreview($, item, this.name, this.baseUrl);
            const durationText = isGifSearch ? undefined : sanitizeText(item.find('div.l, span.duration, div.dur').text()?.trim());

            let mediaId = null;
            const idMatch = pageUrl.match(/^\/([a-zA-Z0-9]+)\/(?:video|gif)\//);
            if (idMatch && idMatch[1]) {
                mediaId = idMatch[1];
            } else {
                const parts = pageUrl.split('/');
                if (parts.length > 1) mediaId = parts[1];
            }

            const absoluteUrl = makeAbsolute(pageUrl, this.baseUrl);
            const absoluteThumbnail = makeAbsolute(thumbnailUrl, this.baseUrl);

            if (!absoluteUrl || !title) {
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

        return results;
    }
}

module.exports = SpankbangDriver;
