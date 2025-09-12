const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const GifMixin = require('../core/GifMixin.js');
const { makeAbsolute, extractPreview, sanitizeText, validatePreview } = require('./driver-utils.js');

const BaseEpornerClass = AbstractModule.with(VideoMixin, GifMixin);

class Eporner extends BaseEpornerClass {
    constructor(options = {}) {
        super(options);
        this.logger = require('../core/log.js').child({ module: 'Eporner' });
    }

    get name() { return 'Eporner'; }
    get baseUrl() { return 'https://www.eporner.com'; }
    get supportsVideos() { return true; }
    get supportsGifs() { return false; }

    getVideoSearchUrl(query, page) {
        const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
        let searchPath = `/search/${encodeURIComponent(query)}/`;
        if (pageNumber > 1) {
            searchPath += `${pageNumber}`;
        }
        return new URL(searchPath, this.baseUrl).href;
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

        const videoItems = $('div.mb');

        if (!videoItems || videoItems.length === 0) {
            this.logger.warn(`No video items found.`);
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
                this.logger.warn(`Skipping malformed video item (missing essential data): title=${titleText}, url=${relativeUrl}, id=${id}`);
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
        this.logger.info(`Parsed ${results.length} videos.`);
        return results;
    }
}

module.exports = Eporner;