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

var _VideoMixin = require('../core/VideoMixin.js');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _GifMixin = require('../core/GifMixin.js'); // Motherless can have GIFs/image galleries
var _GifMixin2 = _interopRequireDefault(_GifMixin);
var _AbstractModule = require('../core/AbstractModule.js');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL = 'https://motherless.com';

var Motherless = (function (_AbstractModule$with) {
  (0, _inherits3.default)(Motherless, _AbstractModule$with);

  function Motherless() {
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    (0, _classCallCheck3.default)(this, Motherless);
    const _this = (0, _possibleConstructorReturn3.default)(this, (Motherless.__proto__ || (0, _getPrototypeOf2.default)(Motherless)).call(this, options));
    _this.name = 'Motherless';
    _this.baseUrl = BASE_URL;
    _this.supportsVideos = true;
    _this.supportsGifs = true;
    _this.firstpage = 1; // UI page query param is 1-indexed
    logger.debug(`[${_this.name}] Initialized.`);
    return _this;
  }

  (0, _createClass3.default)(Motherless, [{
    key: 'getVideoSearchUrl',
    value: function getVideoSearchUrl(query, page) {
      if (!query || typeof query !== 'string' || query.trim() === '') {
        throw new Error('MotherlessDriver: Search query is not set or is empty for video search.');
      }
      const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
      const searchUrl = new URL(`/term/videos/${encodeURIComponent(sanitizeText(query))}`, this.baseUrl);
      searchUrl.searchParams.set('page', String(pageNumber));
      logger.debug(`[${this.name}] Generated videoUrl: ${searchUrl.href}`);
      return searchUrl.href;
    }
  }, {
    key: 'getGifSearchUrl',
    value: function getGifSearchUrl(query, page) {
      if (!query || typeof query !== 'string' || query.trim() === '') {
        throw new Error('MotherlessDriver: Search query is not set or is empty for gif search.');
      }
      const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
      const searchUrl = new URL(`/term/images/${encodeURIComponent(sanitizeText(query))}`, this.baseUrl);
      searchUrl.searchParams.set('page', String(pageNumber));
      logger.debug(`[${this.name}] Generated gifUrl: ${searchUrl.href}`);
      return searchUrl.href;
    }
  }, {
    key: 'parseResults',
    value: function parseResults($, rawHtmlOrJsonData, parserOptions) {
      const { type, sourceName } = parserOptions;
      const results = [];

      if (!$) {
        logger.error(`[${this.name} Parser] Cheerio instance is null or undefined.`);
        return [];
      }

      // Selectors based on mock HTML structure for Motherless
      const mediaItems = $('div.content-inner div.thumb');

      if (!mediaItems || mediaItems.length === 0) {
        logger.warn(`[${this.name} Parser] No media items found with selector 'div.content-inner div.thumb' for type '${type}'.`);
        return [];
      }

      mediaItems.each((i, el) => {
        const item = $(el);

        // Filter by type based on class if possible, as mock HTML uses 'video' or 'image' class on item
        if (type === 'videos' && !item.hasClass('video')) return;
        if (type === 'gifs' && !item.hasClass('image')) return;

        const linkElement = item.find('a[href]').first();
        let relativeUrl = linkElement.attr('href');

        let titleText = sanitizeText(
            item.find('div.caption').text()?.trim() ||
            item.find('div.thumb-title').text()?.trim() ||
            item.find('div.title').text()?.trim() || // From gallery-tile structure
            linkElement.attr('title')?.trim() ||
            item.find('img').attr('alt')?.trim()
        );

        if (!relativeUrl) {
            logger.warn(`[${this.name} Parser] Item ${i} (${type}): Skipping, no relative URL found.`);
            return;
        }
        if (!titleText) titleText = `Motherless Content ${i + 1}`;

        let id = item.attr('data-id'); // data-id from mock
        if (!id && relativeUrl) { // Fallback ID parsing from URL
            const urlParts = relativeUrl.split('/');
            const potentialId = urlParts.filter(part => /^[A-Z0-9]{6,}$/.test(part)).pop(); // Motherless IDs are often like ABC123XYZ
            if (potentialId) {
                id = potentialId;
            } else {
                id = urlParts.filter(Boolean).pop(); // Last segment as a final fallback
            }
        }

        const imgElement = item.find('img').first();
        let thumbnailUrl = imgElement.attr('src')?.trim() || imgElement.attr('data-src')?.trim();
        // Check for background-image style for thumbnail as in mock item 5
        if (!thumbnailUrl) {
            const bgStyle = item.find('div.preview[style*="background-image"]').attr('style');
            if (bgStyle) {
                const bgMatch = bgStyle.match(/url\(['"]?(.*?)['"]?\)/);
                if (bgMatch && bgMatch[1]) thumbnailUrl = bgMatch[1];
            }
        }

        const durationText = type === 'videos' ? sanitizeText(item.find('.video_length').text()?.trim()) : undefined;

        // For GIFs/images, the thumbnail itself is often the preview.
        // For videos, Motherless previews are not straightforward from search results.
        let previewVideoUrl = type === 'gifs' ? thumbnailUrl : undefined; // Simple assumption for GIFs
        if (type === 'videos') {
            previewVideoUrl = extractPreview(item, this.baseUrl, false); // Attempt to find video preview
        }


        if (!titleText || !relativeUrl || !id) { // Thumbnail can be optional for some logic paths but good to have
          logger.warn(`[${this.name} Parser] Item ${i} (${type}): Skipping due to missing critical data. Title: ${titleText}, URL: ${relativeUrl}, ID: ${id}`);
          return;
        }

        const absoluteUrl = makeAbsolute(relativeUrl, this.baseUrl);
        const absoluteThumbnailUrl = makeAbsolute(thumbnailUrl, this.baseUrl);
        const finalPreviewVideoUrl = validatePreview(makeAbsolute(previewVideoUrl, this.baseUrl)) ? makeAbsolute(previewVideoUrl, this.baseUrl) : (type === 'gifs' && absoluteThumbnailUrl ? absoluteThumbnailUrl : undefined);


        results.push({
          id: id,
          title: titleText,
          url: absoluteUrl,
          duration: type === 'videos' ? (durationText || 'N/A') : undefined,
          thumbnail: absoluteThumbnailUrl || '',
          preview_video: finalPreviewVideoUrl || '',
          source: sourceName,
          type: type
        });
      });
      logger.debug(`[${this.name} Parser] Parsed ${results.length} items for type '${type}'.`);
      return results;
    }
  }]);

  // Applying mixins as per user's new driver examples
  return Motherless;
}(_AbstractModule2.default.with(_VideoMixin2.default, _GifMixin2.default)));

exports.default = Motherless;
module.exports = exports['default'];
