'use strict';

const AbstractModule = require('../core/AbstractModule.js');
const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js');

class RedtubeDriver extends AbstractModule {
    constructor(options = {}) {
        super(options);
        logger.debug(`[${this.name}] Initialized.`);
    }

    get name() { return 'Redtube'; }
    get baseUrl() { return 'https://www.redtube.com'; }
    get supportsVideos() { return true; }
    get supportsGifs() { return false; }
    get firstpage() { return 1; }

    getVideoSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for video search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        const searchUrl = new URL(this.baseUrl);
        searchUrl.searchParams.set('search', sanitizeText(query));
        searchUrl.searchParams.set('page', String(searchPage));
        logger.debug(`[${this.name}] Generated video URL: ${searchUrl.href}`);
        return searchUrl.href;
    }

    getGifSearchUrl(query, page) {
        logger.warn(`[${this.name}] GIF search is not supported.`);
        return null;
    }

    parseResults($, htmlOrJsonData, parserOptions) {
        if (!$) {
            logger.error(`[${this.name}] Cheerio object ($) is null. Expecting HTML.`);
            return [];
        }

        const results = [];
        const { type, sourceName } = parserOptions;

        const videoItems = $('div.video_bloc, li.video_item, div.video-tile, div.videoBlock');

        if (!videoItems || videoItems.length === 0) {
            logger.warn(`[${this.name}] No video items found with speculative selectors.`);
            return [];
        }

        videoItems.each((i, el) => {
            const item = $(el);

            const linkElement = item.find('a.video_link, a.video-tile_thumbnail_link, a.video_title_link, a.videoLink').first();
            let relativeUrlToPage = linkElement.attr('href');
            let titleText = sanitizeText(item.find('span.video_title_text, strong.video_title_strong, p.video-tile_title, .videoTitle').first().text()?.trim() || linkElement.attr('title')?.trim());

            if (!titleText && relativeUrlToPage) {
                const parts = relativeUrlToPage.split('/');
                const slug = parts.filter(p => p && !/^\d+$/.test(p)).pop();
                if (slug) titleText = sanitizeText(slug.replace(/[_-]/g, ' '));
            }

            let videoId = item.attr('data-id') || item.attr('data-video_id');
            if (!videoId && relativeUrlToPage) {
                const idMatch = relativeUrlToPage.match(/\/(\d+)$/);
                if (idMatch && idMatch[1]) videoId = idMatch[1];
            }

            if (!titleText || !relativeUrlToPage || !videoId) {
                logger.warn(`[${this.name}] Item ${i}: Skipping due to missing title, URL or ID.`);
                return;
            }

            const durationText = sanitizeText(item.find('span.duration, span.video_duration, span.video-tile_duration, var.duration').first().text()?.trim());

            const imageElement = item.find('img.video_thumbnail_img, img.video-tile_thumbnail_img, img.thumb').first();
            let staticThumbnailUrl = imageElement.attr('data-src') || imageElement.attr('src');
            if (staticThumbnailUrl && staticThumbnailUrl.startsWith('data:image/')) {
                 staticThumbnailUrl = imageElement.attr('data-thumb_url') || imageElement.attr('data-mediumthumb');
            }

            let animatedPreviewUrl = extractPreview(item, this.baseUrl);

            const absoluteUrl = makeAbsolute(relativeUrlToPage, this.baseUrl);
            const absoluteThumbnail = makeAbsolute(staticThumbnailUrl, this.baseUrl);
            const finalPreview = validatePreview(animatedPreviewUrl) ? animatedPreviewUrl : '';

            results.push({
                id: videoId,
                title: titleText,
                url: absoluteUrl,
                thumbnail: absoluteThumbnail || '',
                duration: durationText || 'N/A',
                preview_video: finalPreview,
                source: sourceName,
                type: type
            });
        });

        logger.debug(`[${this.name}] Parsed ${results.length} ${type} items.`);
        return results;
    }
}

module.exports = RedtubeDriver;
