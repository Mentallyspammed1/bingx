'use strict';

Object.defineProperty(exports, "__esModule", { value: true });

var _AbstractModule = require('../core/AbstractModule.js');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);
var _VideoMixin = require('../core/VideoMixin.js');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _GifMixin = require('../core/GifMixin.js');
var _GifMixin2 = _interopRequireDefault(_GifMixin);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

const { logger, makeAbsolute, sanitizeText } = require('./driver-utils.js');

const BASE_URL = 'https://mock.example.com';

class MockScraper extends _AbstractModule2.default.with(_VideoMixin2.default, _GifMixin2.default) {
    constructor(options = {}) { // Added options default
        super(options); // Pass options to AbstractModule
        this.name = 'Mock';
        this.baseUrl = BASE_URL;
        this.supportsVideos = true;
        this.supportsGifs = true;
        this.firstpage = 1;
        logger.debug(`[MockScraper] Initialized.`);
    }

    getVideoSearchUrl(query, page) {
        const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
        logger.debug(`[MockScraper] Generating video URL for query "${query}", page ${pageNumber}`);
        return `${this.baseUrl}/mock-videos/search?q=${encodeURIComponent(query)}&page=${pageNumber}`;
    }

    getGifSearchUrl(query, page) {
        const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
        logger.debug(`[MockScraper] Generating GIF URL for query "${query}", page ${pageNumber}`);
        return `${this.baseUrl}/mock-gifs/search?q=${encodeURIComponent(query)}&page=${pageNumber}`;
    }

    parseResults($, rawData, parserOptions) {
        const { query, page, type, sourceName } = parserOptions;
        const results = [];
        const numResults = 5;

        logger.debug(`[MockScraper] Parsing mock results for type "${type}", query "${query}", page ${page}.`);

        for (let i = 0; i < numResults; i++) {
            const id = `${type.slice(0,3)}-${page}-${i + 1}-${Math.random().toString(16).slice(2, 8)}`;
            const title = sanitizeText(`${type === 'videos' ? 'Mock Video' : 'Mock GIF'} for "${query}" pg ${page} #${i + 1}`);

            // Use makeAbsolute from driver-utils for consistency, though for mock it's less critical
            const url = makeAbsolute(`/${type}/${id}/${sanitizeText(query)}-item`, this.baseUrl);
            const thumbnail = makeAbsolute(`/thumbs/${id}.jpg`, this.baseUrl); // Generic placeholder

            let preview_video, duration;

            if (type === 'videos') {
                preview_video = makeAbsolute(`/previews/vid-${id}.mp4`, this.baseUrl);
                duration = `${String(Math.floor(Math.random() * 15) + 1).padStart(2, '0')}:${String(Math.floor(Math.random() * 60)).padStart(2, '0')}`;
            } else {
                preview_video = makeAbsolute(`/animated-gifs/${id}.gif`, this.baseUrl);
                duration = undefined;
            }

            if (title && url && thumbnail) {
                results.push({
                    id,
                    title,
                    url,
                    thumbnail,
                    preview_video,
                    duration,
                    source: sourceName, // Provided by orchestrator
                    type      // Provided by orchestrator
                });
            } else {
                logger.warn(`[MockScraper] Skipped malformed mock result: ${id}`);
            }
        }
        return results;
    }
}

module.exports = MockScraper;
