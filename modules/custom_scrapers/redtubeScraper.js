// modules/custom_scrapers/redtubeScraper.js
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const log = require('../../core/log');

class RedtubeScraper extends AbstractModule.with(VideoMixin) { // No GifMixin initially
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.redtube.com';
        log.debug(`${this.name} scraper initialized`);
    }

    get name() {
        return 'Redtube';
    }

    get firstpage() {
        // Assuming 1-indexed pagination
        return 1;
    }

    getVideoSearchUrl(query, page) {
        // Example: https://www.redtube.com/?search=test&page=2 (This is a common pattern)
        // Redtube might use specific paths like /redtube/test/page/2 or query params.
        // The provided example seems plausible.
        const url = `${this.baseUrl}/?search=${encodeURIComponent(query)}&page=${page}`;
        log.debug(`${this.name} video URL: ${url}`);
        return url;
    }

    parseResults($, rawData, options) {
        const results = [];
        if (options.type === 'videos') {
            log.info(`Parsing ${this.name} video page... Query URL: ${$._originalUrl || 'N/A'}`);
            const items = $('li.video_tile_wrapper');
            if (!items.length) {
                log.warn(`[${this.name} parseResults - videos] No video items found.`);
                return results;
            }
            items.each((i, el) => {
                const result = this.mapVideoResult(el, $, this.name, this.baseUrl);
                if (result) {
                    results.push(result);
                }
            });
        } else if (options.type === 'gifs') {
            log.warn(`${this.name} does not support GIF scraping. Returning empty results.`);
        }
        return results;
    }
}

module.exports = RedtubeScraper;
