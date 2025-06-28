'use strict';

let AbstractModule;
try {
    AbstractModule = require('../core/AbstractModule.js');
} catch (e) {
    console.error("Failed to load AbstractModule from ../core/, ensure path is correct.", e);
    AbstractModule = class { /* Minimal fallback */
        constructor(options = {}) { this.query = options.query; }
        get name() { return 'UnnamedDriver'; }
        get baseUrl() { return ''; }
        get supportsVideos() { return false; }
        get supportsGifs() { return false; }
        get firstpage() { return 1; }
    };
}

const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL = 'https://www.xvideos.com';
const DRIVER_NAME = 'Xvideos';

class XvideosDriver extends AbstractModule {
    constructor(options = {}) {
        super(options);
        this.name = DRIVER_NAME;
        this.baseUrl = BASE_URL;
        this.supportsVideos = true;
        this.supportsGifs = true;
        this.firstpage = 0;
        logger.debug(`[${this.name}] Initialized.`);
    }

    getVideoSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for video search.`);
        }
        const xvideosPage = Math.max(0, (parseInt(page, 10) || (this.firstpage + 1)) - 1);
        const searchUrl = new URL(this.baseUrl);
        searchUrl.pathname = '/';
        searchUrl.searchParams.set('k', sanitizeText(query));
        searchUrl.searchParams.set('p', String(xvideosPage));
        logger.debug(`[${this.name}] Generated video URL: ${searchUrl.href}`);
        return searchUrl.href;
    }

    getGifSearchUrl(query, page) {
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error(`[${this.name}] Search query is not set for GIF search.`);
        }
        const xvideosPage = Math.max(0, (parseInt(page, 10) || (this.firstpage + 1)) - 1);
        const searchPath = `/gifs/${encodeURIComponent(sanitizeText(query))}/${xvideosPage}`;
        const searchUrl = new URL(searchPath, this.baseUrl);
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

        // Adjusted selectors based on mock HTML for XVideos
        const itemSelector = 'div.thumb-block'; // Common wrapper for both videos and gifs in mock

        $(itemSelector).each((i, el) => {
            const item = $(el);
            let title, pageUrl, thumbnailUrl, previewVideoUrl, durationText, videoId;

            videoId = item.attr('data-id');
            if(!videoId) { // Fallback for ID from item's own id attribute
                 const idAttr = item.attr('id');
                 if(idAttr) videoId = idAttr.replace('video_', '').replace('gif_', '');
            }


            if (isGifSearch) {
                // Ensure this item is actually a GIF item if selectors are broad
                if (!item.hasClass('thumb-block-gif') && !item.hasClass('gif-thumb-block') && !item.attr('id')?.startsWith('gif_')) {
                    // If a general '.thumb-block' was matched but isn't specifically a GIF block, skip it in GIF search
                    if ($(el).find('img.gif_pic').length === 0 && !item.find('a[href*="/gifs/"]').length > 0) {
                         // logger.debug(`[${this.name} Parser] Skipping non-GIF item in GIF search: ${item.attr('id')}`);
                         return; // continue
                    }
                }

                const titleLink = item.find('p.title a, a.thumb-name, div.profile-name a').first();
                title = sanitizeText(titleLink.attr('title')?.trim() || titleLink.text()?.trim());
                pageUrl = titleLink.attr('href');

                const imgElement = item.find('div.thumb img, div.thumb-inside img.gif_pic, img.thumb').first();
                thumbnailUrl = imgElement.attr('src');
                previewVideoUrl = imgElement.attr('data-src'); // data-src is often the animated gif for xvideos

                if (!previewVideoUrl && thumbnailUrl && thumbnailUrl.toLowerCase().endsWith('.gif')) {
                    previewVideoUrl = thumbnailUrl;
                }
                if (previewVideoUrl && (!thumbnailUrl || thumbnailUrl.toLowerCase().endsWith('.gif'))) {
                    // If static thumb is missing or is also the gif, try to create a more static-looking thumb name (won't exist but good for consistency)
                    thumbnailUrl = previewVideoUrl.replace(/\.gif$/i, '.jpg');
                }
                 if (!videoId && pageUrl) { // ID from URL for GIFs: /gifs/12345/...
                    const idMatch = pageUrl.match(/\/gifs\/(\d+)/);
                    if (idMatch && idMatch[1]) videoId = idMatch[1];
                }

            } else { // Video Parsing
                 if (item.attr('id') && !item.attr('id').startsWith('video_')) {
                    // If a general '.thumb-block' was matched but isn't specifically a video block, skip
                    // logger.debug(`[${this.name} Parser] Skipping non-video item in video search: ${item.attr('id')}`);
                    return; // continue
                 }
                const titleLink = item.find('p.title a').first();
                title = sanitizeText(titleLink.attr('title')?.trim() || titleLink.text()?.trim());
                pageUrl = titleLink.attr('href');
                durationText = sanitizeText(item.find('p.metadata span.duration').text()?.trim());

                const imgElement = item.find('div.thumb-inside img').first();
                thumbnailUrl = imgElement.attr('data-src'); // data-src for main thumb
                previewVideoUrl = imgElement.attr('data-videopreview'); // Specific attribute for video preview poster/sprite

                if (!videoId && pageUrl) { // ID from URL for videos: /video1234567/...
                    const idMatch = pageUrl.match(/\/video(\d+)\//);
                    if (idMatch && idMatch[1]) videoId = idMatch[1];
                }
            }

            if (!pageUrl || !title || !videoId) {
                logger.warn(`[${this.name}] Item ${i} (${type}): Skipping. Missing: ${!pageUrl?'URL ':''}${!title?'Title ':''}${!videoId?'ID ':''}`);
                return;
            }

            const absoluteUrl = makeAbsolute(pageUrl, this.baseUrl);
            const absoluteThumbnail = makeAbsolute(thumbnailUrl, this.baseUrl);

            // For XVideos, data-videopreview is often a sprite/static image, not an actual video.
            // extractPreview might be more suitable if actual video previews are available via other attributes.
            let finalPreview = makeAbsolute(previewVideoUrl, this.baseUrl);
            if (!validatePreview(finalPreview) && !isGifSearch) { // If specific video preview is bad, try generic
                 finalPreview = extractPreview(item,this.baseUrl, false);
            } else if (!validatePreview(finalPreview) && isGifSearch && absoluteThumbnail?.toLowerCase().endsWith('.gif')) {
                 finalPreview = absoluteThumbnail; // For GIFs, if data-src was bad, use the src (which might be the .gif)
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

module.exports = XvideosDriver;
