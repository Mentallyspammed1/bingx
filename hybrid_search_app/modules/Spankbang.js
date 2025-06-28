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
var _GifMixin = require('../core/GifMixin.js');
var _GifMixin2 = _interopRequireDefault(_GifMixin);
var _AbstractModule = require('../core/AbstractModule.js');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL = 'https://www.spankbang.com';

var Spankbang = (function (_AbstractModule$with) { // Renamed class to Spankbang
  (0, _inherits3.default)(Spankbang, _AbstractModule$with); // Renamed class

  function Spankbang() { // Renamed constructor
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    (0, _classCallCheck3.default)(this, Spankbang); // Renamed class
    const _this = (0, _possibleConstructorReturn3.default)(this, (Spankbang.__proto__ || (0, _getPrototypeOf2.default)(Spankbang)).call(this, options));
    _this.name = 'Spankbang'; // Name used in Pornsearch.js (ensure consistency)
    _this.baseUrl = BASE_URL;
    _this.supportsVideos = true;
    _this.supportsGifs = true;
    _this.firstpage = 1;
    logger.debug(`[${_this.name}] Initialized.`);
    return _this;
  }

  (0, _createClass3.default)(Spankbang, [{
    key: 'getVideoSearchUrl',
    value: function getVideoSearchUrl(query, page) {
      if (!query || typeof query !== 'string' || query.trim() === '') {
        throw new Error(`[${this.name}] Video search query is not set.`);
      }
      const encodedQuery = encodeURIComponent(sanitizeText(query).replace(/\s+/g, '+'));
      const pageNum = Math.max(1, parseInt(page, 10) || this.firstpage);
      const pageSegment = pageNum > 1 ? `${pageNum}/` : '';
      const url = `${this.baseUrl}/s/${encodedQuery}/${pageSegment}?o=new`; // o=new for newest
      logger.debug(`[${this.name}] Generated videoUrl: ${url}`);
      return url;
    }
  }, {
    key: 'getGifSearchUrl',
    value: function getGifSearchUrl(query, page) {
      if (!query || typeof query !== 'string' || query.trim() === '') {
        throw new Error(`[${this.name}] GIF search query is not set.`);
      }
      const encodedQuery = encodeURIComponent(sanitizeText(query).replace(/\s+/g, '+'));
      const pageNum = Math.max(1, parseInt(page, 10) || this.firstpage);
      const pageSegment = pageNum > 1 ? `${pageNum}/` : '';
      const url = `${this.baseUrl}/gifs/search/${encodedQuery}/${pageSegment}`;
      logger.debug(`[${this.name}] Generated gifUrl: ${url}`);
      return url;
    }
  }, {
    key: 'parseResults',
    value: function parseResults($, rawHtmlOrJsonData, parserOptions) {
      const { type } = parserOptions;
      const results = [];
      if (!$) {
        logger.error(`[${this.name} Parser] Cheerio instance is null or undefined.`);
        return [];
      }

      const mediaItems = $('div.video-item'); // Spankbang uses 'div.video-item' for both

      if (!mediaItems || mediaItems.length === 0) {
        logger.warn(`[${this.name} Parser] No ${type} items found with current selectors.`);
        return [];
      }

      mediaItems.each((i, el) => {
        const item = $(el);
        const linkElement = item.find('a.thumb').first();
        let relativeUrl = linkElement.attr('href');
        let titleText = linkElement.attr('title')?.trim();

        if (!titleText && type === 'videos') {
             titleText = item.find('div.inf > p > a[href*="/video"]').text()?.trim();
        }
         if (!titleText && relativeUrl) {
             const parts = relativeUrl.split('/');
             const slug = parts.filter(p=> p && p!==type.slice(0,-1) && !/^\d+$/.test(p) && p !== 's').pop();
             if(slug) titleText = slug.replace(/[-_]/g, ' ').trim();
         }


        let id = null;
        if(relativeUrl){
            const idMatch = relativeUrl.match(/^\/([a-zA-Z0-9]+)\//);
            if (idMatch && idMatch[1]) id = idMatch[1];
        }


        const imgElement = item.find('img.lazy, img.thumb_video_screen').first();
        let thumbnailUrl = imgElement.attr('data-src')?.trim() || imgElement.attr('src')?.trim();
        const durationText = type === 'videos' ? item.find('div.l, span.duration').text()?.trim() : undefined;
        let previewVideoUrl = linkElement.attr('data-preview'); // Spankbang specific for previews

        if (!titleText || !relativeUrl || !id ) { // Thumbnail can sometimes be tricky
          logger.warn(`[${this.name} Parser] Item ${i}: Skipping due to missing essential data.`);
          return;
        }

        const absoluteUrl = makeAbsolute(relativeUrl, this.baseUrl);
        const absoluteThumbnailUrl = makeAbsolute(thumbnailUrl, this.baseUrl);
        const finalPreviewVideoUrl = validatePreview(makeAbsolute(previewVideoUrl, this.baseUrl)) ? makeAbsolute(previewVideoUrl, this.baseUrl) : (type === 'gifs' ? absoluteThumbnailUrl : undefined);


        results.push({
          id: id,
          title: sanitizeText(titleText),
          url: absoluteUrl,
          duration: type === 'videos' ? (durationText || 'N/A') : undefined,
          thumbnail: absoluteThumbnailUrl || '',
          preview_video: finalPreviewVideoUrl,
          source: this.name,
          type: type
        });
      });
      logger.debug(`[${this.name} Parser] Parsed ${results.length} items for type '${type}'.`);
      return results;
    }
  }]);

  return Spankbang; // Renamed class
}(_AbstractModule2.default.with(_VideoMixin2.default, _GifMixin2.default)));

exports.default = Spankbang; // Renamed class
module.exports = exports['default'];
