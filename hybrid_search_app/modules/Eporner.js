'use strict';

const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const { logger, makeAbsolute, extractPreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL_CONST = 'https://www.eporner.com';
const DRIVER_NAME_CONST = 'Eporner';

const BaseEpornerClass = AbstractModule.with(VideoMixin);

class EpornerDriver extends BaseEpornerClass {
    constructor(options = {}) {
        super(options);
        logger.debug(`[${DRIVER_NAME_CONST}] Initialized.`);
    }

    get name() { return DRIVER_NAME_CONST; }
    get baseUrl() { return BASE_URL_CONST; }
    hasVideoSupport() { return true; }
    hasGifSupport() { return false; }
    get firstpage() { return 1; }

    getVideoSearchUrl(query, page) {
        const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
        const searchUrl = new URL('/search/' + encodeURIComponent(query) + '/', this.baseUrl);
        if (pageNumber > 1) {
            searchUrl.pathname += `/${pageNumber}`;
        }
        logger.debug(`[${this.name}] Generated videoUrl: ${searchUrl.href}`);
        return searchUrl.href;
    }

    parseResults($, htmlOrJsonData, parserOptions) {
        const { type, sourceName } = parserOptions;
        const results = [];
        if (!$) {
            logger.error(`[${this.name} Parser] Cheerio instance is null or undefined.`);
            return [];
        }

        const videoItems = $('div.mb');

        if (!videoItems || videoItems.length === 0) {
            logger.warn(`[${this.name} Parser] No video items found with selectors for type '${type}'.`);
            return [];
        }

        videoItems.each((i, el) => {
            const item = $(el);
            const linkElement = item.find('a').first();
            let relativeUrl = linkElement.attr('href');
            let titleText = sanitizeText(item.find('h3').text()?.trim());

            let id = '';
            if (relativeUrl) {
                const idMatch = relativeUrl.match(/\/video-(.*)\//);
                if (idMatch && idMatch[1]) id = idMatch[1];
            }

            const imgElement = item.find('img').first();
            let staticThumbnailUrl = imgElement.attr('src');

            const durationText = sanitizeText(item.find('span.mbtim').text()?.trim());

            let animatedPreviewUrl = extractPreview($, item, this.name, this.baseUrl);

            if (!titleText || !relativeUrl || !id) {
                logger.warn(`[${this.name} Parser] Item ${i}: Skipping due to missing title, URL, or ID. Title: ${titleText}, URL: ${relativeUrl}, ID: ${id}`);
                return;
            }

            const absoluteUrl = makeAbsolute(relativeUrl, this.baseUrl);
            const absoluteThumbnailUrl = makeAbsolute(staticThumbnailUrl, this.baseUrl);
            const finalPreviewVideoUrl = validatePreview(animatedPreviewUrl) ? animatedPreviewUrl : undefined;

            results.push({
                id: id,
                title: titleText,
                url: absoluteUrl,
                duration: durationText || 'N/A',
                thumbnail: absoluteThumbnailUrl || '',
                preview_video: finalPreviewVideoUrl || '',
                source: sourceName,
                type: type
            });
        });
        logger.debug(`[${this.name} Parser] Parsed ${results.length} items for type '${type}'.`);
        return results;
    }
}

module.exports = EpornerDriver;