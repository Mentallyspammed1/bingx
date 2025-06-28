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

const BASE_URL = 'https://www.sex.com';
const DRIVER_NAME = 'Sex.com';

var SexCom = (function (_AbstractModule$with) {
  (0, _inherits3.default)(SexCom, _AbstractModule$with);

  function SexCom() {
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    (0, _classCallCheck3.default)(this, SexCom);
    const _this = (0, _possibleConstructorReturn3.default)(this, (SexCom.__proto__ || (0, _getPrototypeOf2.default)(SexCom)).call(this, options));
    _this.name = DRIVER_NAME;
    _this.baseUrl = BASE_URL;
    _this.supportsVideos = true;
    _this.supportsGifs = true;
    _this.firstpage = 1;
    logger.debug(`[${_this.name}] Initialized.`);
    return _this;
  }

  (0, _createClass3.default)(SexCom, [{
    key: 'getVideoSearchUrl',
    value: function getVideoSearchUrl(query, page) {
      if (!query || typeof query !== 'string' || query.trim() === '') {
        throw new Error('SexComDriver: Search query is not set or is empty for video search.');
      }
      const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
      const searchUrl = new URL('/search/videos', this.baseUrl);
      searchUrl.searchParams.set('query', sanitizeText(query));
      searchUrl.searchParams.set('page', String(pageNumber));
      logger.debug(`[${this.name}] Generated videoUrl: ${searchUrl.href}`);
      return searchUrl.href;
    }
  }, {
    key: 'getGifSearchUrl',
    value: function getGifSearchUrl(query, page) {
      if (!query || typeof query !== 'string' || query.trim() === '') {
        throw new Error('SexComDriver: Search query is not set or is empty for GIF search.');
      }
      const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
      const searchUrl = new URL('/search/gifs', this.baseUrl);
      searchUrl.searchParams.set('query', sanitizeText(query));
      searchUrl.searchParams.set('page', String(pageNumber));
      logger.debug(`[${this.name}] Generated gifUrl: ${searchUrl.href}`);
      return searchUrl.href;
    }
  }, {
    key: 'parseResults',
    value: function parseResults($, htmlOrJsonData, parserOptions) {
      const { type, sourceName } = parserOptions;
      const results = [];
      if (!$) {
        logger.error(`[${this.name} Parser] Cheerio instance is null or undefined.`);
        return [];
      }

      const itemSelector = type === 'videos' ?
        'div.masonry_box.video, div.video_preview_box' :
        'div.masonry_box.gif, div.gif_preview_box';

      $(itemSelector).each((i, el) => {
        const item = $(el);

        const linkElement = item.find('a.image_wrapper, a.box_link, .video_shortlink_container a').first();
        let pageUrl = linkElement.attr('href');

        let title = sanitizeText(
            linkElement.attr('title')?.trim() ||
            item.find('p.title, h2.title, div.video_title').first().text()?.trim()
        );
        if (!title && item.find('p.title a').length) {
            title = sanitizeText(item.find('p.title a').first().text()?.trim() || item.find('p.title a').first().attr('title')?.trim());
        }
        if (!title && item.find('h2.title a').length) { // For h2.title case
             title = sanitizeText(item.find('h2.title a').first().text()?.trim() || item.find('h2.title a').first().attr('title')?.trim());
        }


        let id = item.attr('data-id');
        if (!id && pageUrl) {
            const match = pageUrl.match(/\/(?:video|gifs|pin)\/(\d+)/);
            if (match && match[1]) id = match[1];
        }

        const imgElement = item.find('img.responsive_image, img.main_image').first();
        let thumbnailUrl = imgElement.attr('data-src') || imgElement.attr('src');

        let previewVideoUrl;
        if (type === 'gifs') {
            previewVideoUrl = imgElement.attr('data-gif_url') || imgElement.attr('data-src') || imgElement.attr('src');
        } else {
            previewVideoUrl = item.find('img[data-preview_url]').attr('data-preview_url') ||
                              item.find('video.preview_video').attr('src') ||
                              extractPreview(item, this.baseUrl, false);
        }

        const durationText = type === 'videos' ? sanitizeText(item.find('span.duration, span.video_duration').text()?.trim()) : undefined;

        if (!pageUrl || !title || !id) {
          logger.warn(`[${this.name} Parser] Item ${i} (${type}): Skipping. Missing: ${!pageUrl?'URL ':''}${!title?'Title ':''}${!id?'ID ':''}`);
          return;
        }

        const absoluteUrl = makeAbsolute(pageUrl, this.baseUrl);
        const absoluteThumbnailUrl = makeAbsolute(thumbnailUrl, this.baseUrl);
        let finalPreviewVideoUrl = makeAbsolute(previewVideoUrl, this.baseUrl);

        if (!validatePreview(finalPreviewVideoUrl)) {
            finalPreviewVideoUrl = type === 'gifs' && absoluteThumbnailUrl?.toLowerCase().endsWith('.gif') ? absoluteThumbnailUrl : undefined;
        }
         if (!finalPreviewVideoUrl && type === 'gifs' && absoluteThumbnailUrl) finalPreviewVideoUrl = absoluteThumbnailUrl;


        results.push({
          id: id,
          title: title,
          url: absoluteUrl,
          thumbnail: absoluteThumbnailUrl || '',
          duration: durationText || (type === 'videos' ? 'N/A' : undefined),
          preview_video: finalPreviewVideoUrl || '',
          source: sourceName,
          type: type
        });
      });
      logger.debug(`[${this.name} Parser] Parsed ${results.length} items for type '${type}'.`);
      return results;
    }
  }]);

  return SexCom;
}(_AbstractModule2.default.with(_VideoMixin2.default, _GifMixin2.default)));

exports.default = SexCom;
module.exports = exports['default'];
