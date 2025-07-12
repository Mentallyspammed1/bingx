'use strict';

const AbstractModule = require('../core/AbstractModule.js');
const { makeAbsolute, extractPreview, sanitizeText, validatePreview } = require('./driver-utils.js');

class Eporner extends AbstractModule {
    constructor(options = {}) {
        super(options);
    }

    get name() { return 'Eporner'; }
    get baseUrl() { return 'https://www.eporner.com'; }
    hasVideoSupport() { return true; }
    hasGifSupport() { return false; }

    getVideoSearchUrl(query, page) {
        const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
        let searchPath = `/search/${encodeURIComponent(query)}/`;
        if (pageNumber > 1) {
            searchPath += `${pageNumber}`;
        }
        return new URL(searchPath, this.baseUrl).href;
    }

    parseResults($, htmlOrJsonData, parserOptions) {
        const { type, sourceName } = parserOptions;
        const results = [];
        if (!$) {
            return [];
        }

        const videoItems = $('div.mb');

        if (!videoItems || videoItems.length === 0) {
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
        return results;
    }
}

module.exports = Eporner;