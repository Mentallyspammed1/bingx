'use strict';

Object.defineProperty(exports, "__esModule", { value: true });

let AbstractModule;
try {
    AbstractModule = require('../core/AbstractModule.js');
} catch (e) {
    console.error("Failed to load AbstractModule from ../core/, ensure path is correct for mockScraper.", e);
    AbstractModule = class {
        constructor(options = {}) { this.query = options.query; }
        get name() { return 'UnnamedDriver'; }
        get baseUrl() { return ''; }
        get supportsVideos() { return false; }
        get supportsGifs() { return false; }
        get firstpage() { return 1; }
     };
}

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }
var _VideoMixin = require('../core/VideoMixin.js');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _GifMixin = require('../core/GifMixin.js');
var _GifMixin2 = _interopRequireDefault(_GifMixin);
var _AbstractModule2 = _interopRequireDefault(AbstractModule);


const { logger, makeAbsolute, sanitizeText } = require('./driver-utils.js');

const BASE_URL_CONST = 'https://mock.example.com';
const DRIVER_NAME_CONST = 'Mock';

class MockDriver extends _AbstractModule2.default.with(_VideoMixin2.default, _GifMixin2.default) { // Renamed class to MockDriver
    constructor(options = {}) {
        super(options);
        logger.debug(`[${this.name}] Initialized.`); // name will call getter
    }

    get name() { return DRIVER_NAME_CONST; }
    get baseUrl() { return BASE_URL_CONST; }
    get supportsVideos() { return true; }
    get supportsGifs() { return true; }
    get firstpage() { return 1; }


    getVideoSearchUrl(query, page) {
        const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
        logger.debug(`[${this.name}] Generating video URL for query "${query}", page ${pageNumber}`);
        return `${this.baseUrl}/mock-videos/search?q=${encodeURIComponent(query)}&page=${pageNumber}`;
    }

    getGifSearchUrl(query, page) {
        const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
        logger.debug(`[${this.name}] Generating GIF URL for query "${query}", page ${pageNumber}`);
        return `${this.baseUrl}/mock-gifs/search?q=${encodeURIComponent(query)}&page=${pageNumber}`;
    }

    parseResults($, rawData, parserOptions) {
        const { query, page, type, sourceName } = parserOptions;
        const results = [];
        const numResults = 5;

        logger.debug(`[${this.name}] Parsing mock results for type "${type}", query "${query}", page ${page}.`);

        for (let i = 0; i < numResults; i++) {
            const id = `${type.slice(0,3)}-${page}-${i + 1}-${Math.random().toString(16).slice(2, 8)}`;
            const title = sanitizeText(`${type === 'videos' ? 'Mock Video' : 'Mock GIF'} for "${query}" pg ${page} #${i + 1}`);

            const url = makeAbsolute(`/${type}/${id}/${sanitizeText(query)}-item`, this.baseUrl);
            const thumbnail = makeAbsolute(`/thumbs/${id}.jpg`, this.baseUrl);

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
                    source: sourceName,
                    type
                });
            } else {
                logger.warn(`[${this.name}] Skipped malformed mock result: ${id}`);
            }
        }
        return results;
    }
}

module.exports = MockDriver; // Ensure consistent export name
