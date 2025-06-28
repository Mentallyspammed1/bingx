'use strict';

Object.defineProperty(exports, "__esModule", { value: true });

// Re-introducing full Babel helper imports
var _getPrototypeOf = require('babel-runtime/core-js/object/get-prototype-of');
var _getPrototypeOf2 = _interopRequireDefault(_getPrototypeOf);
var _classCallCheck2 = require('babel-runtime/helpers/classCallCheck');
var _classCallCheck3 = _interopRequireDefault(_classCallCheck2);
var _createClass2 = require('babel-runtime/helpers/createClass');
var _createClass3 = _interopRequireDefault(_createClass2);
var _possibleConstructorReturn2 = require('babel-runtime/helpers/possibleConstructorReturn');
var _possibleConstructorReturn3 = _interopRequireDefault(_possibleConstructorReturn2);
var _inherits2 = require('babel-runtime/helpers/inherits');
var _inherits3 = _interopRequireDefault(_inherits2);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

// Core module and mixins (paths relative to modules/youpornScraper.js)
var _VideoMixin = require('../core/VideoMixin.js'); // Corrected path
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
// var _GifMixin = require('../core/GifMixin'); // YouPorn might not have a distinct GIF section
// var _GifMixin2 = _interopRequireDefault(_GifMixin);
var _AbstractModule = require('../core/AbstractModule.js'); // Corrected path
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

// Utility functions from driver-utils.js
const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js'); // Corrected path

const BASE_URL = 'https://www.youporn.com';

/**
 * @typedef {object} MediaResult
 * @property {string} id - Unique identifier for the media item.
 * @property {string} title - The title of the media item.
 * @property {string} url - The URL to the media item's page on Youporn.
 * @property {string} [preview_video] - Optional URL to an animated video preview (WebM or MP4). May be undefined. For GIFs, this would be the .gif URL itself.
 * @property {string} [thumbnail] - Optional URL to a static image thumbnail/poster.
 * @property {string} [duration] - Optional duration of the video (e.g., "10:30"). Undefined for GIFs.
 * @property {string} source - The name of the source (e.g., "Youporn").
 * @property {string} type - The type of media ('videos' or 'gifs').
 */

/**
 * @class Youporn
 * @classdesc Driver for scraping video content from Youporn.com.
 * This driver scrapes HTML, making it vulnerable to site structure changes.
 * YouPorn heavily uses client-side rendering; direct scraping might be insufficient.
 * @extends AbstractModule
 * @mixes VideoMixin
 */
var Youporn = (function (_AbstractModule$with) {
  (0, _inherits3.default)(Youporn, _AbstractModule$with);

  function Youporn() {
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    (0, _classCallCheck3.default)(this, Youporn);
    // super(options); // Call AbstractModule constructor // This was missing in user's code, AbstractModule needs it.
    const _this = (0, _possibleConstructorReturn3.default)(this, (Youporn.__proto__ || (0, _getPrototypeOf2.default)(Youporn)).call(this, options));
    _this.name = 'Youporn';
    _this.baseUrl = BASE_URL;
    _this.supportsVideos = true;
    _this.supportsGifs = false; // Youporn likely doesn't have distinct GIF search
    _this.firstpage = 1; // Youporn pages are typically 1-indexed
    logger.debug(`[${_this.name}] Initialized.`);
    return _this; // Ensure _this is returned
  }

  (0, _createClass3.default)(Youporn, [{
    key: 'getVideoSearchUrl',
    /**
     * Constructs the URL for searching videos on Youporn.
     * @param {string} query - The search query.
     * @param {number} page - The page number for the search results.
     * @returns {string} The fully qualified URL for video search.
     * @throws {Error} If the search query is not set or is empty.
     */
    value: function getVideoSearchUrl(query, page) {
      if (!query || typeof query !== 'string' || query.trim() === '') {
        // Use this.query if query arg is not provided, consistent with AbstractModule
        query = this.query;
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error('YoupornDriver: Search query is not set or is empty for video search.');
        }
      }
      const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage); // Use parseInt for page

      // Current mock HTML expects '/search' and then query in params
      // User's Pornsearch.js uses '/search/' with 'query' param for YouPorn
      // The provided Youporn.js uses '/search' with 'search' param
      // Let's align with the mock HTML and typical YouPorn structure: /search/ and 'query' param.
      const searchUrl = new URL('/search/', this.baseUrl); // Added trailing slash based on typical YouPorn
      searchUrl.searchParams.set('query', sanitizeText(query)); // Changed 'search' to 'query'
      searchUrl.searchParams.set('page', String(pageNumber));

      logger.debug(`[${this.name}] Generated videoUrl: ${searchUrl.href}`);
      return searchUrl.href;
    }
  }, {
    key: 'getGifSearchUrl',
    /**
     * Constructs the URL for GIF search on Youporn.
     * @returns {string | null} Returns null as GIF search is not supported via a distinct URL.
     */
    value: function getGifSearchUrl(query, page) {
      logger.warn(`[${this.name}] GIF search is not natively supported or not distinct from video search.`);
      return null;
    }
  }, {
    key: 'parseResults',
    /**
     * Parses HTML from a Youporn search results page using Cheerio.
     * Selectors target the mock HTML provided for YouPorn.
     * @param {CheerioAPI} $ - Cheerio object loaded with the page HTML.
     * @param {string} rawHtml - The raw HTML string. (Note: Pornsearch.js passes htmlOrJsonData)
     * @param {object} parserOptions - Contains options like { type: 'videos', sourceName: 'Youporn' }.
     * @returns {Array<MediaResult>} An array of parsed video results.
     */
    value: function parseResults($, htmlOrJsonData, parserOptions) { // Corrected signature
      const { type, sourceName } = parserOptions; // Use sourceName from parserOptions
      const results = [];

      if (!$) {
        logger.error(`[${this.name} Parser] Cheerio instance is null or undefined.`);
        return [];
      }

      // Targetting elements in modules/mock_html_data/youporn_videos_page1.html
      const videoItems = $('div.video-box, li.video-item, div.thumbnail-video-container');

      if (!videoItems || videoItems.length === 0) {
        logger.warn(`[${this.name} Parser] No ${type} items found with selectors. Page structure may have changed or no results.`);
        return [];
      }

      videoItems.each((i, el) => {
        const item = $(el);

        const linkElement = item.find('a.video-link, a.video-box-link, a.video-thumb-link').first();
        let relativeUrl = linkElement.attr('href');
        let titleText = sanitizeText(linkElement.attr('title')?.trim() || item.find('.video-title, .title-text, .title, .videoDetails > p.video-title, .title-wrapper > p.title').first().text()?.trim());

        let id = item.attr('data-id');
        if (!id && relativeUrl) {
            const idMatch = relativeUrl.match(/\/watch\/(\d+)\//);
            if (idMatch && idMatch[1]) id = idMatch[1];
        }

        const imgElement = item.find('img.video-thumbnail, img.thumb, img.video-thumb-img').first();
        let staticThumbnailUrl = imgElement.attr('data-src') || imgElement.attr('src');

        const durationText = sanitizeText(item.find('span.video-duration, span.duration-text, span.duration, span.time').first().text()?.trim());

        let animatedPreviewUrl = extractPreview(item, this.baseUrl); // Using utility

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
          source: sourceName, // Use sourceName from parserOptions
          type: type
        });
      });
      logger.debug(`[${this.name} Parser] Parsed ${results.length} items for type '${type}'.`);
      return results;
    }
  }]);

  return Youporn;
}(_AbstractModule2.default.with(_VideoMixin2.default))); // Applying VideoMixin

exports.default = Youporn;
module.exports = exports['default'];
