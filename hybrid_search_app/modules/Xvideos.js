'use strict';

const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const GifMixin = require('../core/GifMixin.js');
const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL_CONST = 'https://www.xvideos.com';
const DRIVER_NAME_CONST = 'Xvideos';

const BaseXvideosClass = AbstractModule.with(VideoMixin, GifMixin);

class XvideosDriver extends BaseXvideosClass {
    constructor(options = {}) {
        super(options);
        logger.debug(`[${DRIVER_NAME_CONST}] Initialized.`);
    }

    get name() { return DRIVER_NAME_CONST; }
    get baseUrl() { return BASE_URL_CONST; }
    hasVideoSupport() { return true; }
    hasGifSupport() { return true; }

    getVideoSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for video search.`);
        }
        const xvideosPage = Math.max(0, (parseInt(page, 10) || (this.firstpage + 1)) - 1);
        const searchUrl = new URL(this.baseUrl);
        searchUrl.searchParams.set('k', query);
        if (xvideosPage > 0) {
            searchUrl.searchParams.set('p', xvideosPage);
        }
        logger.debug(`[${this.name}] Generated video URL: ${searchUrl.href}`);
        return searchUrl.href;
    }

    getGifSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for GIF search.`);
        }
        const xvideosPage = Math.max(0, (parseInt(page, 10) || (this.firstpage + 1)) - 1);
        const searchUrl = new URL(this.baseUrl);
        searchUrl.pathname = '/gifs';
        searchUrl.searchParams.set('k', query);
        if (xvideosPage > 0) {
            searchUrl.searchParams.set('p', xvideosPage);
        }
        logger.debug(`[${this.name}] Generated GIF URL: ${searchUrl.href}`);
        return searchUrl.href;
    }

    parseResults($, htmlOrJsonData, parserOptions) {
        if (!$) {
            logger.error(`[${this.name}] Cheerio object ($) is null. Expecting HTML.`);
            return [];
        }

        const results = [];
        const { type, sourceName } = parserOptions;
        const isGifSearch = type === 'gifs';

        const itemSelector = 'div.thumb-block';

        $(itemSelector).each((i, el) => {
            const item = $(el);
            let title, pageUrl, thumbnailUrl, durationText, videoId;

            videoId = item.attr('data-id');
            if(!videoId) {
                 const idAttr = item.attr('id');
                 if(idAttr) videoId = idAttr.replace('video_', '').replace('gif_', '');
            }

            if (isGifSearch) {
                if (!item.hasClass('thumb-block-gif') && !item.hasClass('gif-thumb-block') && !item.attr('id')?.startsWith('gif_')) {
                    if ($(el).find('img.gif_pic').length === 0 && !item.find('a[href*="/gifs/"]').length > 0) {
                         return;
                    }
                }
                const titleLink = item.find('p.title a, a.thumb-name, div.profile-name a').first();
                title = sanitizeText(titleLink.attr('title')?.trim() || titleLink.text()?.trim());
                pageUrl = titleLink.attr('href');
                const imgElement = item.find('div.thumb img, div.thumb-inside img.gif_pic, img.thumb').first();
                thumbnailUrl = imgElement.attr('src');
                 if (!videoId && pageUrl) {
                    const idMatch = pageUrl.match(/\/gifs\/(\d+)/);
                    if (idMatch && idMatch[1]) videoId = idMatch[1];
                }
            } else {
                 if (item.attr('id') && !item.attr('id').startsWith('video_')) {
                    return;
                 }
                const titleLink = item.find('p.title a').first();
                title = sanitizeText(titleLink.attr('title')?.trim() || titleLink.text()?.trim());
                pageUrl = titleLink.attr('href');
                durationText = sanitizeText(item.find('p.metadata span.duration').text()?.trim());
                const imgElement = item.find('div.thumb-inside img').first();
                thumbnailUrl = imgElement.attr('data-src');
                if (!videoId && pageUrl) {
                    const idMatch = pageUrl.match(/\/video(\d+)\//);
                    if (idMatch && idMatch[1]) videoId = idMatch[1];
                }
            }

            if (!pageUrl || !title || !videoId) {
                logger.warn(`[${this.name}] Item ${i} (${type}): Skipping. Missing: ${!pageUrl?'URL ':''}${!title?'Title ':''}${!videoId?'ID ':''}`);
                return;
            }

            const previewVideoUrl = extractPreview($, item, this.name, this.baseUrl);
            const absoluteUrl = makeAbsolute(pageUrl, this.baseUrl);
            const absoluteThumbnail = makeAbsolute(thumbnailUrl, this.baseUrl);

            results.push({
                id: videoId,
                title: title,
                url: absoluteUrl,
                thumbnail: absoluteThumbnail || '',
                duration: isGifSearch ? undefined : (durationText || 'N/A'),
                preview_video: previewVideoUrl || '',
                source: sourceName,
                type: type
            });
        });

        logger.debug(`[${this.name}] Parsed ${results.length} ${type} items.`);
        return results;
    }
}

module.exports = XvideosDriver;