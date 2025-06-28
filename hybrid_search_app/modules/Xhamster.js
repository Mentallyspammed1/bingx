'use strict';

Object.defineProperty(exports, "__esModule", { value: true });

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

var _GifMixin = require('../core/GifMixin.js'); // Corrected path
var _GifMixin2 = _interopRequireDefault(_GifMixin);
var _VideoMixin = require('../core/VideoMixin.js'); // Corrected path
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _AbstractModule = require('../core/AbstractModule.js'); // Corrected path
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js'); // Corrected path

const BASE_URL = 'https://xhamster.com';

var Xhamster = (function (_AbstractModule$with) {
  (0, _inherits3.default)(Xhamster, _AbstractModule$with);

  function Xhamster() {
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    (0, _classCallCheck3.default)(this, Xhamster);
    // super(options); // Call AbstractModule constructor // This was missing in user's code
    const _this = (0, _possibleConstructorReturn3.default)(this, (Xhamster.__proto__ || (0, _getPrototypeOf2.default)(Xhamster)).call(this, options));
    _this.name = 'Xhamster';
    _this.baseUrl = BASE_URL;
    _this.supportsVideos = true;
    _this.supportsGifs = true;
    _this.firstpage = 1;
    logger.debug(`[${_this.name}] Initialized.`);
    return _this; // Ensure _this is returned
  }

  (0, _createClass3.default)(Xhamster, [{
    key: 'getVideoSearchUrl',
    value: function getVideoSearchUrl(query, page) {
      if (!query || typeof query !== 'string' || query.trim() === '') {
        // Use this.query if query arg is not provided
        query = this.query;
        if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error('XhamsterDriver: Search query is not set or is empty for video search.');
        }
      }
      const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
      const encodedQuery = encodeURIComponent(sanitizeText(query));
      const searchUrl = new URL(`/search/${encodedQuery}`, this.baseUrl);
      searchUrl.searchParams.set('page', String(pageNumber));
      logger.debug(`[${this.name}] Generated videoUrl: ${searchUrl.href}`);
      return searchUrl.href;
    }
  }, {
    key: 'getGifSearchUrl',
    value: function getGifSearchUrl(query, page) {
      if (!query || typeof query !== 'string' || query.trim() === '') {
         query = this.query;
         if (!query || typeof query !== 'string' || query.trim() === '') {
            throw new Error('XhamsterDriver: Search query is not set or is empty for GIF search.');
        }
      }
      const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
      const encodedQuery = encodeURIComponent(sanitizeText(query));
      const searchUrl = new URL(`/search/${encodedQuery}`, this.baseUrl);
      searchUrl.searchParams.set('page', String(pageNumber));
      searchUrl.searchParams.set('filter', 'gifs'); // User's previous code suggested this filter
      logger.debug(`[${this.name}] Generated gifUrl: ${searchUrl.href}`);
      return searchUrl.href;
    }
  }, {
    key: 'parseResults',
    value: function parseResults($, htmlOrJsonData, parserOptions) { // Corrected signature
      const { type, sourceName } = parserOptions; // Use sourceName
      const results = [];

      if (!$) {
        logger.error(`[${this.name} Parser] Cheerio instance is null or undefined.`);
        return [];
      }

      const isGifSearch = type === 'gifs';
      // Selectors based on the mock HTML for Xhamster
      const itemSelector = isGifSearch ?
            'div.photo-thumb, div.gif-thumb, div.gallery-thumb, div.thumb-list__item--gif' :
            'div.video-thumb, div.thumb-list__item:not(.thumb-list__item--photo):not(.thumb-list__item--user), div.video-box';


      $(itemSelector).each((i, el) => {
        const item = $(el);
        let title, pageUrl, thumbnailUrl, previewVideoUrl, durationText, mediaId;

        mediaId = item.attr('data-id');

        if (isGifSearch) {
            const linkElement = item.find('a.photo-thumb__image, a.thumb-image__image, a.gallery-thumb__image-container').first();
            pageUrl = linkElement.attr('href');
            title = sanitizeText(linkElement.attr('title')?.trim() ||
                                 item.find('.photo-thumb__title, .gif-thumb__name, .gallery-thumb__name a').first().text()?.trim() ||
                                 item.find('img').first().attr('alt')?.trim());

            const imgElement = item.find('img.photo-thumb__img, img.thumb-image__image, img.gallery-thumb__image').first();
            thumbnailUrl = imgElement.attr('data-poster') || imgElement.attr('src');
            previewVideoUrl = imgElement.attr('data-src') || imgElement.attr('data-original') || imgElement.attr('src');
            durationText = undefined;

            if (!mediaId && pageUrl) {
                const idMatch = pageUrl.match(/\/photos\/(?:gallery\/[^/]+\/[^/]+-|view\/)?(\d+)|gifs\/(\d+)/);
                if (idMatch) mediaId = idMatch[1] || idMatch[2] || idMatch[3];
            }
        } else { // Video Parsing
            const linkElement = item.find('a.video-thumb__image-container, a.thumb-image__image, a.video-thumb-link').first();
            pageUrl = linkElement.attr('href');
            title = sanitizeText(linkElement.attr('title')?.trim() ||
                                 item.find('.video-thumb__name, .video-title, .video-thumb-info__name, .item-title a').first().text()?.trim() ||
                                 item.find('img').first().attr('alt')?.trim());

            const imgElement = item.find('img.video-thumb__image, img.thumb-image__image').first();
            thumbnailUrl = imgElement.attr('data-src') || imgElement.attr('src');
            durationText = sanitizeText(item.find('.video-thumb__duration, .duration, .video-duration, .time').first().text()?.trim());

            previewVideoUrl = item.find('script.video-thumb__player-container').attr('data-previewvideo') ||
                              linkElement.attr('data-preview-url') ||
                              item.find('video.thumb-preview__video').attr('src') ||
                              linkElement.attr('data-preview');

            if (!mediaId && pageUrl) {
                const idMatch = pageUrl.match(/\/videos\/.*?-(\d+)(?:\.html)?$|\/videos\/(\d+)\//);
                if (idMatch) mediaId = idMatch[1] || idMatch[2];
            }
        }

        if (!mediaId && pageUrl) {
            const parts = pageUrl.split(/[-/]/);
            mediaId = parts.reverse().find(part => /^\d{6,}$/.test(part));
        }

        if (!pageUrl || !title || !mediaId) {
          logger.warn(`[${this.name} Parser] Item ${i} (${type}): Skipping. Missing: ${!pageUrl?'URL ':''}${!title?'Title ':''}${!mediaId?'ID ':''}`);
          return;
        }

        const absoluteUrl = makeAbsolute(pageUrl, this.baseUrl);
        const absoluteThumbnail = makeAbsolute(thumbnailUrl, this.baseUrl);
        let finalPreview = makeAbsolute(previewVideoUrl, this.baseUrl);

        if (!validatePreview(finalPreview)) {
            finalPreview = extractPreview(item, this.baseUrl, isGifSearch);
        }
        if (!validatePreview(finalPreview) && isGifSearch && absoluteThumbnail?.toLowerCase().endsWith('.gif')) {
             finalPreview = absoluteThumbnail;
        }

        results.push({
          id: mediaId,
          title: title,
          url: absoluteUrl,
          thumbnail: absoluteThumbnail || '',
          duration: durationText || (isGifSearch ? undefined : 'N/A'),
          preview_video: validatePreview(finalPreview) ? finalPreview : '',
          source: sourceName, // Use sourceName from parserOptions
          type: type
        });
      });
      logger.debug(`[${this.name} Parser] Parsed ${results.length} items for type '${type}'.`);
      return results;
    }
  }]);

  return Xhamster;
}(_AbstractModule2.default.with(_VideoMixin2.default, _GifMixin2.default))); // Applying both mixins

exports.default = Xhamster;
module.exports = exports['default'];
