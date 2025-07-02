'use strict';

let AbstractModule;
try {
    AbstractModule = require('../core/AbstractModule.js');
} catch (e) {
    console.error("Failed to load AbstractModule from ../core/, ensure path is correct.", e);
    AbstractModule = class {
        constructor(options = {}) { this.query = options.query; }
        // Stubs for AbstractModule getters that drivers will override
        get name() { return 'UnnamedDriver'; }
        get baseUrl() { return ''; }
        get supportsVideos() { return false; }
        get supportsGifs() { return false; }
        get firstpage() { return 1; }
    };
}

const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL_CONST = 'https://www.pornhub.com'; // Renamed to avoid conflict with getter
const DRIVER_NAME_CONST = 'Pornhub'; // Renamed to avoid conflict with getter

class PornhubDriver extends AbstractModule {
    constructor(options = {}) {
        super(options);
        // Properties are now defined by getters below
        logger.debug(`[${this.name}] Initialized.`); // Now 'this.name' will call the getter
    }

    get name() { return DRIVER_NAME_CONST; }
    get baseUrl() { return BASE_URL_CONST; }
    get supportsVideos() { return true; }
    get supportsGifs() { return true; }
    get firstpage() { return 1; }

    getVideoSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for video search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        // Use this.baseUrl which calls the getter
        const searchUrl = new URL('/video/search', this.baseUrl);
        searchUrl.searchParams.set('search', sanitizeText(query));
        searchUrl.searchParams.set('page', String(searchPage));
        logger.debug(`[${this.name}] Generated video URL: ${searchUrl.href}`);
        return searchUrl.href;
    }

    getGifSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for GIF search.`);
        }
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        const searchUrl = new URL('/gifs/search', this.baseUrl);
        searchUrl.searchParams.set('search', sanitizeText(query));
        searchUrl.searchParams.set('page', String(searchPage));
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

        const itemSelector = isGifSearch ?
            'ul.gifs.gifLink li.gifVideoBlock' :
            'ul.videos.search-video-thumbs li.pcVideoListItem';

        $(itemSelector).each((i, el) => {
            const item = $(el);
            let title, pageUrl, thumbnailUrl, previewVideoUrl, durationText, videoId;

            videoId = item.attr('data-id');

            if (isGifSearch) {
                const linkA = item.find('a').first();
                pageUrl = linkA.attr('href');
                title = sanitizeText(linkA.attr('title')?.trim() || item.find('span.title, div.title').first().text()?.trim());

                const videoElement = item.find('video').first();
                thumbnailUrl = videoElement.attr('poster');
                if (!thumbnailUrl) {
                    const imgThumb = item.find('img.thumb').first();
                    thumbnailUrl = imgThumb.attr('data-src') || imgThumb.attr('src');
                }
                previewVideoUrl = videoElement.attr('data-webm') || videoElement.find('source[type="video/webm"]').first().attr('src');
                 if (!previewVideoUrl) {
                    const imgThumb = item.find('img.thumb').first();
                    if(imgThumb.attr('src')?.toLowerCase().endsWith('.gif')) previewVideoUrl = imgThumb.attr('src');
                    else if(imgThumb.attr('data-src')?.toLowerCase().endsWith('.gif')) previewVideoUrl = imgThumb.attr('data-src');
                 }

                if (!videoId && pageUrl) {
                    const idMatch = pageUrl.match(/\/gif\/(\w+)/);
                    if (idMatch && idMatch[1]) videoId = idMatch[1];
                }
            } else {
                const titleLink = item.find('span.title a').first();
                title = sanitizeText(titleLink.attr('title')?.trim());
                pageUrl = titleLink.attr('href');
                durationText = sanitizeText(item.find('var.duration').text()?.trim());

                const imgTag = item.find('div.phimage img').first();
                thumbnailUrl = imgTag.attr('data-mediumthumb') || imgTag.attr('data-src') || imgTag.attr('src');

                previewVideoUrl = item.find('a.linkVideoThumb').attr('data-mediabook') ||
                                  imgTag.attr('data-mediabook') ||
                                  imgTag.attr('data-previewvideo');

                if (!videoId && pageUrl) {
                    const idMatch = pageUrl.match(/viewkey=([a-zA-Z0-9]+)/);
                    if (idMatch && idMatch[1]) videoId = idMatch[1];
                }
            }

            if (!pageUrl || !title || !videoId) {
                logger.warn(`[${this.name}] Item ${i} (${type}): Skipping. Missing: pageUrl: ${!pageUrl}, title: ${!title}, videoId: ${!videoId}`);
                return;
            }

            const absoluteUrl = makeAbsolute(pageUrl, this.baseUrl); // Use getter this.baseUrl
            const absoluteThumbnail = makeAbsolute(thumbnailUrl, this.baseUrl); // Use getter this.baseUrl

            let finalPreview = makeAbsolute(previewVideoUrl, this.baseUrl); // Use getter this.baseUrl
            if (!validatePreview(finalPreview)) {
                finalPreview = extractPreview(item, this.baseUrl, isGifSearch); // Use getter this.baseUrl
            }
            if (!validatePreview(finalPreview) && isGifSearch && absoluteThumbnail?.toLowerCase().endsWith('.gif')) {
                 finalPreview = absoluteThumbnail;
            }

            results.push({
                id: videoId,
                title: title,
                url: absoluteUrl,
                thumbnail: absoluteThumbnail || '',
                duration: isGifSearch ? undefined : (durationText || 'N/A'),
                preview_video: validatePreview(finalPreview) ? finalPreview : '',
                source: sourceName,
                type: type
            });
        });

        logger.debug(`[${this.name}] Parsed ${results.length} ${type} items from mock.`);
        return results;
    }
}

module.exports = PornhubDriver;
