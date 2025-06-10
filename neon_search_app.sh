#!/bin/bash

# ==============================================================================
# NEON SEARCH APP - SETUP SCRIPT
# ==============================================================================
#
# This script generates a Node.js web application for searching adult content.
#
# Key Characteristics:
# --------------------
# 1.  **Backend (`server.js`):**
#     The server handles API requests for searching.
#
# 2.  **Custom Scrapers (`modules/` directory):**
#     The backend relies on custom-written scraper modules (e.g., modules/Pornhub.js,
#     modules/Xvideos.js, etc.). These modules are responsible for fetching and
#     parsing HTML content from the target websites.
#
# 3.  **Scraping Libraries:**
#     The custom scraper modules primarily use:
#       - `axios`: For making HTTP requests to fetch web pages.
#       - `cheerio`: For parsing HTML content (similar to jQuery) to extract data.
#
# 4.  **Maintenance Requirement:**
#     Since this application uses direct HTML scraping, the scraper modules in the
#     `modules/` directory are sensitive to changes in the HTML structure of the
#     target websites. If a target website updates its layout, the corresponding
#     scraper module will likely need to be updated to continue functioning correctly.
#
# Basic Post-Setup Instructions:
# ------------------------------
# 1. Run this script: `bash neon_search_app.sh`
# 2. Navigate to the app directory: `cd neon_search_app` (if not already created by this script)
#    (Note: This script creates files in the current directory. You might want to `mkdir neon_search_app && cd neon_search_app` before running it.)
# 3. Install dependencies: `npm install express cors axios cheerio babel-runtime`
# 4. Run the server: `node server.js`
# 5. Open your browser to `http://localhost:3000` (or your device's IP).
#
# ==============================================================================

# Create necessary directories
echo "Creating directories: core and modules..."
mkdir -p core modules

# Create core files
echo "Creating core/OverwriteError.js..."
cat << 'EOF' > core/OverwriteError.js
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

/**
 * @class OverwriteError
 * @extends Error
 * @classdesc Custom error class for indicating that an abstract method or property
 * must be overridden by a subclass.
 */
var OverwriteError = function (_Error) {
  _inherits(OverwriteError, _Error);

  /**
   * Creates an instance of OverwriteError.
   * @param {string} methodName - The name of the method or property that needs to be overridden.
   */
  function OverwriteError(methodName) {
    _classCallCheck(this, OverwriteError);

    var _this = _possibleConstructorReturn(this, (OverwriteError.__proto__ || Object.getPrototypeOf(OverwriteError)).call(this, `Method or property "${methodName}" must be overridden by subclass.`));

    _this.name = 'OverwriteError';
    return _this;
  }

  return OverwriteError;
}(Error);

exports.default = OverwriteError;
module.exports = exports['default'];
EOF

echo "Creating core/AbstractModule.js..."
cat << 'EOF' > core/AbstractModule.js
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

var _classCallCheck2 = require('babel-runtime/helpers/classCallCheck');
var _classCallCheck3 = _interopRequireDefault(_classCallCheck2);
var _createClass2 = require('babel-runtime/helpers/createClass');
var _createClass3 = _interopRequireDefault(_createClass2);

// Assuming OverwriteError.js is in the same directory or './core/OverwriteError'
// Adjust the path if necessary.
var _OverwriteError = require('./OverwriteError');
var _OverwriteError2 = _interopRequireDefault(_OverwriteError);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * @class AbstractModule
 * @classdesc Base class for all content source drivers.
 * It handles common functionalities like storing the search query and provides a mixin mechanism.
 * Concrete drivers must implement `name` and `firstpage` getters, and URL/parser methods.
 */
var AbstractModule = function () {
  /**
   * Constructor for AbstractModule.
   * @param {object} [options={}] - Configuration options for the driver.
   * @param {string} [options.query=''] - The search query term.
   */
  function AbstractModule() {
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {}; // Expect an options object
    (0, _classCallCheck3.default)(this, AbstractModule);

    // Ensure options is an object and extract the query string
    if (typeof options === 'object' && options !== null && typeof options.query === 'string') {
        this.query = options.query.trim();
    } else {
        this.query = '';
    }

    // Default to an empty object if options is not provided or is not an object
    this.options = options || {};

    // console.log(`[AbstractModule] Initialized with query: "${this.query}"`);
  }

  (0, _createClass3.default)(AbstractModule, [{
    key: 'name',
    /**
     * Abstract getter for the name of the content source driver.
     * This MUST be overridden by concrete driver classes.
     * @abstract
     * @returns {string} The name of the driver (e.g., 'Redtube', 'Xhamster').
     * @throws {OverwriteError} If this getter is not implemented by the consuming class.
     */
    get: function get() {
      throw new _OverwriteError2.default('name');
    }
  }, {
    key: 'firstpage',
    /**
     * Abstract getter for the default starting page number for searches on this platform.
     * This MUST be overridden by concrete driver classes.
     * @abstract
     * @returns {number} The 1-indexed (or 0-indexed, if specified by the platform)
     * default page number for searches.
     * @throws {OverwriteError} If this getter is not implemented by the consuming class.
     */
    get: function get() {
      throw new _OverwriteError2.default('firstpage');
    }
  }, {
    key: 'setQuery',
    /**
     * Optional method to update the query after instantiation.
     * @param {string} newQuery - The new search query string.
     */
    value: function setQuery(newQuery) {
        if (typeof newQuery === 'string') {
            this.query = newQuery.trim();
        } else {
            this.query = '';
        }
        // console.log(`[AbstractModule setQuery] Query updated to: "${this.query}"`);
    }

  }], [{
    key: 'with',
    /**
     * Static helper method to apply mixins to a class.
     * This allows for compositional inheritance (e.g., `class MyDriver extends AbstractModule.with(VideoMixin, GifMixin)`);
     * @param  {...Function} mixins - Mixin functions to apply. Each mixin should be a function
     * that takes a `BaseClass` and returns a new class extending `BaseClass`.
     * @returns {Function} The class with mixins applied.
     */
    value: function _with() {
      // 'this' refers to the class constructor (AbstractModule in this context)
      var baseClass = this;
      for (var _len = arguments.length, mixins = Array(_len), _key = 0; _key < _len; _key++) {
        mixins[_key] = arguments[_key];
      }

      return mixins.reduce(function (extendedClass, mixin) {
        // Ensure mixin is a function before calling it
        if (typeof mixin === 'function') {
          return mixin(extendedClass);
        }
        console.warn('[AbstractModule.with] Encountered a non-function in mixins array:', mixin);
        return extendedClass; // Return original class if mixin is invalid
      }, baseClass);
    }
  }]);
  return AbstractModule;
}();

exports.default = AbstractModule; // Export as default
module.exports = exports['default']; // For CommonJS compatibility
EOF

echo "Creating core/GifMixin.js..."
cat << 'EOF' > core/GifMixin.js
'use strict';

// These are Babel's typical import helpers.
// Assuming OverwriteError.js is in the same directory or accessible via require.
// The _interopRequireDefault handles cases where a module might be ES6 default export
// or a CommonJS module.

Object.defineProperty(exports, "__esModule", {
  value: true
});

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

var _OverwriteError = require('./OverwriteError'); // Assuming this is the correct path
var _OverwriteError2 = _interopRequireDefault(_OverwriteError);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * @file GifMixin.js
 * A mixin factory that enhances a base class with abstract GIF-related methods.
 * Classes applying this mixin are contractually obligated to implement `gifUrl()`
 * and `gifParser()` methods for GIF searching and parsing capabilities.
 */

/**
 * A higher-order function (mixin factory) that adds GIF search and parsing features
 * to any given `BaseClass`. It defines abstract methods `gifUrl` and `gifParser`
 * that must be implemented by the class consuming this mixin.
 *
 * @param {Function} BaseClass - The class to extend with GIF functionalities.
 * @returns {Function} The extended class with GIF features.
 */
var GifMixin = function (BaseClass) {
  // Define an anonymous class that inherits from BaseClass
  var GifFeatureMixin = function (_BaseClass) {
    (0, _inherits3.default)(GifFeatureMixin, _BaseClass); // Set up inheritance chain

    /**
     * Constructor for the mixed-in class. It simply calls the super constructor.
     */
    function GifFeatureMixin() {
      (0, _classCallCheck3.default)(this, GifFeatureMixin); // Check for class instance
      return (0, _possibleConstructorReturn3.default)(this, (GifFeatureMixin.__proto__ || (0, _getPrototypeOf2.default)(GifFeatureMixin)).apply(this, arguments));
    }

    (0, _createClass3.default)(GifFeatureMixin, [{
      key: 'gifUrl',
      /**
       * Abstract method to construct the full URL for a GIF search query.
       * This method MUST be overridden by any class that uses this mixin.
       * It's responsible for generating the specific search URL for a given platform.
       *
       * @abstract
       * @param {string} query - The search query term.
       * @param {number} page - The page number for the search results.
       * @returns {string} The fully qualified URL for GIF search.
       * @throws {OverwriteError} If this method is not implemented by the consuming class.
       */
      value: function gifUrl(query, page) {
        // Instantiates OverwriteError, presumably passing the method name for a specific message.
        throw new _OverwriteError2.default('gifUrl');
      }
    }, {
      key: 'gifParser',
      /**
       * Abstract method to parse raw GIF data or a response containing GIF information.
       * This method MUST be overridden by any class that uses this mixin.
       * It's responsible for extracting relevant GIF information from the raw data
       * and structuring it into an array of `MediaResult` objects (or similar).
       *
       * @abstract
       * @param {CheerioAPI | null} cheerioInstance - A CheerioAPI instance loaded with HTML, or null if the response is JSON/binary.
       * @param {*} rawData - The raw data (e.g., HTML string, JSON object, or a binary buffer) of the GIF response to be parsed.
       * @returns {Array<object>} An array of `MediaResult` objects, where each object should typically include:
       * - id: {string} Unique identifier for the GIF.
       * - title: {string} Title/description of the GIF.
       * - url: {string} Direct URL to the GIF image or page.
       * - thumbnail: {string} URL to a static thumbnail or preview image.
       * - preview_video: {string} (Optional) URL to an animated preview (e.g., WebM/MP4).
       * @throws {OverwriteError} If this method is not implemented by the consuming class.
       */
      value: function gifParser(cheerioInstance, rawData /* Added rawData parameter as parsers need input */) {
        throw new _OverwriteError2.default('gifParser');
      }
    }]);
    return GifFeatureMixin;
  }(BaseClass); // The IIFE receives BaseClass and uses it as _Base

  return GifFeatureMixin; // Return the enhanced class constructor
};

exports.default = GifMixin; // Maintains the original dual export for CommonJS/ESM interop
EOF

echo "Creating core/VideoMixin.js..."
cat << 'EOF' > core/VideoMixin.js
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

// Babel helper imports (assuming they are correctly resolved by your build setup)
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

// Assuming OverwriteError.js is in the same directory or './core/OverwriteError'
// Adjust the path if necessary.
var _OverwriteError = require('./OverwriteError'); // Path to your custom OverwriteError class
var _OverwriteError2 = _interopRequireDefault(_OverwriteError);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * @file VideoMixin.js
 * A mixin factory that enhances a base class with abstract video-related methods.
 * Classes that have this mixin applied are contractually obligated to implement
 * `videoUrl()` and `videoParser()` methods for video searching capabilities.
 */

/**
 * A higher-order function (mixin factory) that adds video search capabilities
 * to any given `BaseClass`. It defines abstract methods `videoUrl` and `videoParser`
 * that must be implemented by the class consuming this mixin.
 *
 * @param {Function} BaseClass - The class to extend with video features.
 * @returns {Function} The extended class with video functionalities.
 */
var VideoMixin = function (BaseClass) {
  // Define an anonymous class that inherits from BaseClass
  var WithVideoFeatures = function (_BaseClass) {
    (0, _inherits3.default)(WithVideoFeatures, _BaseClass); // Set up inheritance chain

    /**
     * Constructor for the mixed-in class. It simply calls the super constructor.
     */
    function WithVideoFeatures() {
      (0, _classCallCheck3.default)(this, WithVideoFeatures); // Check for class instance
      return (0, _possibleConstructorReturn3.default)(this, (WithVideoFeatures.__proto__ || (0, _getPrototypeOf2.default)(WithVideoFeatures)).apply(this, arguments));
    }

    (0, _createClass3.default)(WithVideoFeatures, [{
      key: 'videoUrl',
      /**
       * Abstract method to construct the full URL for a video search query.
       * This method MUST be overridden by any class that uses this mixin.
       * It's responsible for generating the specific search URL for a given platform.
       *
       * @abstract
       * @param {string} query - The search query term.
       * @param {number} page - The page number for the search results.
       * @returns {string} The fully qualified URL for video search.
       * @throws {OverwriteError} If this method is not implemented by the consuming class.
       */
      value: function videoUrl(query, page) { // Added 'page' parameter for JSDoc clarity
        // Pass the method name to OverwriteError for a more specific message
        throw new _OverwriteError2.default('videoUrl');
      }
    }, {
      key: 'videoParser',
      /**
       * Abstract method to parse the raw response (HTML or JSON) from a video search.
       * This method MUST be overridden by any class that uses this mixin.
       * It's responsible for extracting relevant video information from the raw response
       * and structuring it into an array of `MediaResult` objects.
       *
       * @abstract
       * @param {CheerioAPI | null} cheerioInstance - A CheerioAPI instance loaded with HTML, or null if the response is JSON.
       * (e.g., `cheerio.load(htmlContent)` for HTML scraping)
       * @param {string | object} rawBody - The raw string response body (e.g., HTML) or a pre-parsed JSON object.
       * @returns {Array<object>} An array of `MediaResult` objects. Each object should ideally have:
       * - id: {string} Unique identifier for the video.
       * - title: {string} Title of the video.
       * - url: {string} Direct URL to the video page.
       * - duration: {string} (Optional) Duration of the video (e.g., "10:30").
       * - thumbnail: {string} URL to the video thumbnail image.
       * - preview_video: {string} (Optional) URL to a short video preview (e.g., WebM/MP4).
       * @throws {OverwriteError} If this method is not implemented by the consuming class.
       */
      value: function videoParser(cheerioInstance, rawBody) { // Added params for JSDoc
        throw new _OverwriteError2.default('videoParser');
      }
    }]);
    return WithVideoFeatures;
  }(BaseClass); // The IIFE receives BaseClass (which it calls _Base internally)

  return WithVideoFeatures; // Return the enhanced class constructor
};

exports.default = VideoMixin; // Export as default
module.exports = exports['default']; // For CommonJS compatibility
EOF

# Create driver files in the modules directory
echo "Creating modules/Pornhub.js..."
cat << 'EOF' > modules/Pornhub.js
/**
 * IMPORTANT: CSS selectors and URL patterns in this file are speculative and
 * MUST be verified against the live website (www.pornhub.com) using browser
 * developer tools. Websites frequently change their structure.
 *
 * To verify:
 * 1. Go to the website.
 * 2. Perform a search for videos/GIFs.
 * 3. Inspect the HTML structure of result items (e.g., video cards, GIF blocks).
 * 4. Update BASE_PLATFORM_URL, GIF_DOMAIN, VIDEO_SEARCH_PATH, GIF_SEARCH_PATH,
 *    VIDEO_SELECTOR, GIF_SELECTOR, and ID_PATTERN regex as needed.
 */
'use strict';

Object.defineProperty(exports, "__esModule", { value: true });

// Babel helper imports
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

// Core module and mixins
var _GifMixin = require('../core/GifMixin');
var _GifMixin2 = _interopRequireDefault(_GifMixin);
var _VideoMixin = require('../core/VideoMixin');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _AbstractModule = require('../core/AbstractModule');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

// Base URLs
const BASE_PLATFORM_URL = 'https://www.pornhub.com';
const GIF_DOMAIN = 'https://i.pornhub.com';

/**
 * @typedef {object} MediaResult
 * @property {string} id - Unique identifier for the media.
 * @property {string} title - Title of the media.
 * @property {string} url - Direct URL to the media's page on the platform.
 * @property {string} [duration] - Duration of the video (e.g., "10:30"). Undefined for GIFs.
 * @property {string} thumbnail - URL to the media's static thumbnail image.
 * @property {string} [preview_video] - URL to a short animated preview (WebM/MP4 or direct GIF).
 * @property {string} [image_hq] - URL to a high-quality static image (for photos/gifs).
 * @property {string} source - The name of the platform.
 * @property {string} type - 'videos' or 'gifs'.
 */

/**
 * @class PornhubDriver
 * @classdesc Driver for fetching video and GIF content from Pornhub.
 */
var PornhubDriver = (function (_AbstractModule$with) {
  (0, _inherits3.default)(PornhubDriver, _AbstractModule$with);

  function PornhubDriver() {
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    (0, _classCallCheck3.default)(this, PornhubDriver);
    return (0, _possibleConstructorReturn3.default)(this, (PornhubDriver.__proto__ || (0, _getPrototypeOf2.default)(PornhubDriver)).call(this, options));
  }

  (0, _createClass3.default)(PornhubDriver, [{
    key: 'videoUrl',
    value: function videoUrl(query, page) {
      const encodedQuery = encodeURIComponent(query.trim());
      const pageNumber = Math.max(1, page || this.firstpage);
      const url = new URL('/video/search', BASE_PLATFORM_URL);
      url.searchParams.set('search', encodedQuery);
      url.searchParams.set('page', String(pageNumber));
      return url.href;
    }
  }, {
    key: 'videoParser',
    value: function videoParser($, rawBody) {
      const results = [];
      const videoItems = $('div.phimage');

      if (!videoItems.length) {
        console.warn(`[${this.name} Video Parser] No video items found with current selectors.`);
        return [];
      }

      videoItems.each((index, element) => {
        const item = $(element);
        const linkElement = item.find('a').first();
        let videoUrl = linkElement.attr('href');
        let videoId = videoUrl ? videoUrl.match(/viewkey=([a-zA-Z0-9]+)/)?.[1] : null;
        if (!videoId && videoUrl) {
          const pathSegments = videoUrl.split('/');
          const potentialId = pathSegments[pathSegments.length - 2];
          if (potentialId && /^\\d+$/.test(potentialId)) {
            videoId = potentialId;
          }
        }

        let title = linkElement.attr('title') || item.find('span.title').text().trim() || item.attr('data-video-title');
        const thumbElement = item.find('img').first();
        let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
        if (thumbnailUrl && thumbnailUrl.includes('nothumb')) thumbnailUrl = undefined;
        let duration = item.find('var.duration, span.duration').text().trim();
        let previewVideoUrl = linkElement.attr('data-mediabook') || linkElement.attr('data-preview-src') || item.find('video').attr('data-src');

        if (videoUrl) videoUrl = this._makeAbsolute(videoUrl, BASE_PLATFORM_URL);
        if (thumbnailUrl) thumbnailUrl = this._makeAbsolute(thumbnailUrl, BASE_PLATFORM_URL);
        if (previewVideoUrl) previewVideoUrl = this._makeAbsolute(previewVideoUrl, BASE_PLATFORM_URL);

        if (!videoUrl || !title || !thumbnailUrl || !videoId) {
          console.warn(`[${this.name} Video Parser] Skipping malformed video item:`, { title, videoUrl, thumbnailUrl, videoId, index });
          return;
        }

        results.push({
          id: videoId,
          title: title || 'Untitled Video',
          url: videoUrl,
          duration: duration || 'N/A',
          thumbnail: thumbnailUrl,
          preview_video: previewVideoUrl,
          source: this.name,
          type: 'videos'
        });
      });
      return results;
    }
  }, {
    key: 'gifUrl',
    value: function gifUrl(query, page) {
      const encodedQuery = encodeURIComponent(query.trim());
      const pageNumber = Math.max(1, page || this.firstpage);
      const url = new URL('/gifs/search', BASE_PLATFORM_URL);
      url.searchParams.set('search', encodedQuery);
      url.searchParams.set('page', String(pageNumber));
      return url.href;
    }
  }, {
    key: 'gifParser',
    value: function gifParser($, rawBody) {
      const results = [];
      const gifItems = $('div.gifImageBlock, div.img-container');

      if (!gifItems.length) {
        console.warn(`[${this.name} GIF Parser] No GIF items found with current selectors.`);
        return [];
      }

      gifItems.each((index, element) => {
        const item = $(element);
        const linkElement = item.find('a').first();
        let gifPageUrl = linkElement.attr('href');
        let gifId = item.attr('data-id') || (gifPageUrl ? gifPageUrl.match(/\/(\d+)\//)?.[1] : null);
        let title = item.find('img').attr('alt') || linkElement.attr('title') || 'Untitled GIF';
        let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
        if (animatedGifUrl && animatedGifUrl.endsWith('.gif')) {
          animatedGifUrl = this._makeAbsolute(animatedGifUrl, GIF_DOMAIN);
        } else {
          const videoPreview = item.find('video source').attr('src') || item.find('video').attr('data-src');
          if (videoPreview) {
            animatedGifUrl = this._makeAbsolute(videoPreview, BASE_PLATFORM_URL);
          }
        }
        let staticThumbnailUrl = item.find('img').attr('data-thumb') || item.find('img').attr('src');
        if (!staticThumbnailUrl && animatedGifUrl && animatedGifUrl.endsWith('.gif')) {
          staticThumbnailUrl = animatedGifUrl;
        }
        if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, BASE_PLATFORM_URL);

        if (!gifPageUrl || !title || !animatedGifUrl || !gifId) {
          console.warn(`[${this.name} GIF Parser] Skipping malformed GIF item:`, { title, gifPageUrl, animatedGifUrl, gifId, index });
          return;
        }

        gifPageUrl = this._makeAbsolute(gifPageUrl, BASE_PLATFORM_URL);

        results.push({
          id: gifId,
          title: title,
          url: gifPageUrl,
          thumbnail: staticThumbnailUrl,
          preview_video: animatedGifUrl,
          source: this.name,
          type: 'gifs'
        });
      });
      return results;
    }
  }, {
    key: '_makeAbsolute',
    value: function _makeAbsolute(urlString, baseUrl) {
      if (!urlString || typeof urlString !== 'string') return undefined;
      if (urlString.startsWith('data:')) return urlString;
      if (urlString.startsWith('//')) return `https:${urlString}`;
      if (urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString;
      try {
        return new URL(urlString, baseUrl).href;
      } catch (e) {
        return undefined;
      }
    }
  }, {
    key: 'name',
    get: function get() {
      return 'Pornhub';
    }
  }, {
    key: 'firstpage',
    get: function get() {
      return 1;
    }
  }]);
  return PornhubDriver;
}(_AbstractModule2.default.with(_VideoMixin2.default, _GifMixin2.default)));

export default PornhubDriver;
EOF

echo "Creating modules/Xvideos.js..."
cat << 'EOF' > modules/Xvideos.js
/**
 * IMPORTANT: CSS selectors and URL patterns in this file are speculative and
 * MUST be verified against the live website (www.xvideos.com) using browser
 * developer tools. Websites frequently change their structure.
 *
 * To verify:
 * 1. Go to the website.
 * 2. Perform a search for videos/GIFs.
 * 3. Inspect the HTML structure of result items (e.g., video cards, GIF blocks).
 * 4. Update BASE_PLATFORM_URL, GIF_DOMAIN, VIDEO_SEARCH_PATH, GIF_SEARCH_PATH,
 *    VIDEO_SELECTOR, GIF_SELECTOR, and ID_PATTERN regex as needed.
 */
'use strict';

Object.defineProperty(exports, "__esModule", { value: true });

// Babel helper imports
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

// Core module and mixins
var _GifMixin = require('../core/GifMixin');
var _GifMixin2 = _interopRequireDefault(_GifMixin);
var _VideoMixin = require('../core/VideoMixin');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _AbstractModule = require('../core/AbstractModule');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

// Base URLs
const BASE_PLATFORM_URL = 'https://www.xvideos.com';
const GIF_DOMAIN = 'https://img-hw.xvideos-cdn.com';

/**
 * @typedef {object} MediaResult
 * @property {string} id - Unique identifier for the media.
 * @property {string} title - Title of the media.
 * @property {string} url - Direct URL to the media's page on the platform.
 * @property {string} [duration] - Duration of the video (e.g., "10:30"). Undefined for GIFs.
 * @property {string} thumbnail - URL to the media's static thumbnail image.
 * @property {string} [preview_video] - URL to a short animated preview (WebM/MP4 or direct GIF).
 * @property {string} [image_hq] - URL to a high-quality static image (for photos/gifs).
 * @property {string} source - The name of the platform.
 * @property {string} type - 'videos' or 'gifs'.
 */

/**
 * @class XvideosDriver
 * @classdesc Driver for fetching video and GIF content from Xvideos.
 */
var XvideosDriver = (function (_AbstractModule$with) {
  (0, _inherits3.default)(XvideosDriver, _AbstractModule$with);

  function XvideosDriver() {
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    (0, _classCallCheck3.default)(this, XvideosDriver);
    return (0, _possibleConstructorReturn3.default)(this, (XvideosDriver.__proto__ || (0, _getPrototypeOf2.default)(XvideosDriver)).call(this, options));
  }

  (0, _createClass3.default)(XvideosDriver, [{
    key: 'videoUrl',
    value: function videoUrl(query, page) {
      const encodedQuery = encodeURIComponent(query.trim());
      const pageNumber = Math.max(1, page || this.firstpage);
      const url = new URL('/video-search', BASE_PLATFORM_URL);
      url.searchParams.set('k', encodedQuery); // Xvideos uses 'k' for query
      url.searchParams.set('p', String(pageNumber - 1)); // Xvideos pages start at 0
      return url.href;
    }
  }, {
    key: 'videoParser',
    value: function videoParser($, rawBody) {
      const results = [];
      const videoItems = $('div.thumb-block');

      if (!videoItems.length) {
        console.warn(`[${this.name} Video Parser] No video items found with current selectors.`);
        return [];
      }

      videoItems.each((index, element) => {
        const item = $(element);
        const linkElement = item.find('a').first();
        let videoUrl = linkElement.attr('href');
        let videoId = videoUrl ? videoUrl.match(/\/video(\d+)\//)?.[1] : null;
        if (!videoId && videoUrl) {
          const pathSegments = videoUrl.split('/');
          const potentialId = pathSegments[pathSegments.length - 2];
          if (potentialId && /^\\d+$/.test(potentialId)) {
            videoId = potentialId;
          }
        }

        let title = linkElement.attr('title') || item.find('p.title').text().trim() || item.attr('data-title');
        const thumbElement = item.find('img').first();
        let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
        if (thumbnailUrl && thumbnailUrl.includes('nothumb')) thumbnailUrl = undefined;
        let duration = item.find('span.duration').text().trim();
        let previewVideoUrl = thumbElement.attr('data-src') || item.find('video').attr('data-src');

        if (videoUrl) videoUrl = this._makeAbsolute(videoUrl, BASE_PLATFORM_URL);
        if (thumbnailUrl) thumbnailUrl = this._makeAbsolute(thumbnailUrl, BASE_PLATFORM_URL);
        if (previewVideoUrl) previewVideoUrl = this._makeAbsolute(previewVideoUrl, BASE_PLATFORM_URL);

        if (!videoUrl || !title || !thumbnailUrl || !videoId) {
          console.warn(`[${this.name} Video Parser] Skipping malformed video item:`, { title, videoUrl, thumbnailUrl, videoId, index });
          return;
        }

        results.push({
          id: videoId,
          title: title || 'Untitled Video',
          url: videoUrl,
          duration: duration || 'N/A',
          thumbnail: thumbnailUrl,
          preview_video: previewVideoUrl,
          source: this.name,
          type: 'videos'
        });
      });
      return results;
    }
  }, {
    key: 'gifUrl',
    value: function gifUrl(query, page) {
      const encodedQuery = encodeURIComponent(query.trim());
      const pageNumber = Math.max(1, page || this.firstpage);
      const url = new URL('/gifs', BASE_PLATFORM_URL);
      url.searchParams.set('k', encodedQuery);
      url.searchParams.set('p', String(pageNumber - 1));
      return url.href;
    }
  }, {
    key: 'gifParser',
    value: function gifParser($, rawBody) {
      const results = [];
      const gifItems = $('div.thumb-block, div.img-block');

      if (!gifItems.length) {
        console.warn(`[${this.name} GIF Parser] No GIF items found with current selectors.`);
        return [];
      }

      gifItems.each((index, element) => {
        const item = $(element);
        const linkElement = item.find('a').first();
        let gifPageUrl = linkElement.attr('href');
        let gifId = item.attr('data-id') || (gifPageUrl ? gifPageUrl.match(/\/gif(\d+)\//)?.[1] : null);
        let title = item.find('img').attr('alt') || linkElement.attr('title') || 'Untitled GIF';
        let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
        if (animatedGifUrl && animatedGifUrl.endsWith('.gif')) {
          animatedGifUrl = this._makeAbsolute(animatedGifUrl, GIF_DOMAIN);
        } else {
          const videoPreview = item.find('video source').attr('src') || item.find('video').attr('data-src');
          if (videoPreview) {
            animatedGifUrl = this._makeAbsolute(videoPreview, BASE_PLATFORM_URL);
          }
        }
        let staticThumbnailUrl = item.find('img').attr('data-thumb') || item.find('img').attr('src');
        if (!staticThumbnailUrl && animatedGifUrl && animatedGifUrl.endsWith('.gif')) {
          staticThumbnailUrl = animatedGifUrl;
        }
        if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, BASE_PLATFORM_URL);

        if (!gifPageUrl || !title || !animatedGifUrl || !gifId) {
          console.warn(`[${this.name} GIF Parser] Skipping malformed GIF item:`, { title, gifPageUrl, animatedGifUrl, gifId, index });
          return;
        }

        gifPageUrl = this._makeAbsolute(gifPageUrl, BASE_PLATFORM_URL);

        results.push({
          id: gifId,
          title: title,
          url: gifPageUrl,
          thumbnail: staticThumbnailUrl,
          preview_video: animatedGifUrl,
          source: this.name,
          type: 'gifs'
        });
      });
      return results;
    }
  }, {
    key: '_makeAbsolute',
    value: function _makeAbsolute(urlString, baseUrl) {
      if (!urlString || typeof urlString !== 'string') return undefined;
      if (urlString.startsWith('data:')) return urlString;
      if (urlString.startsWith('//')) return `https:${urlString}`;
      if (urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString;
      try {
        return new URL(urlString, baseUrl).href;
      } catch (e) {
        return undefined;
      }
    }
  }, {
    key: 'name',
    get: function get() {
      return 'Xvideos';
    }
  }, {
    key: 'firstpage',
    get: function get() {
      return 1;
    }
  }]);
  return XvideosDriver;
}(_AbstractModule2.default.with(_VideoMixin2.default, _GifMixin2.default)));

export default XvideosDriver;
EOF

echo "Creating modules/Youporn.js..."
cat << 'EOF' > modules/Youporn.js
/**
 * IMPORTANT: CSS selectors and URL patterns in this file are speculative and
 * MUST be verified against the live website (www.youporn.com) using browser
 * developer tools. Websites frequently change their structure.
 *
 * To verify:
 * 1. Go to the website.
 * 2. Perform a search for videos/GIFs.
 * 3. Inspect the HTML structure of result items (e.g., video cards, GIF blocks).
 * 4. Update BASE_PLATFORM_URL, GIF_DOMAIN, VIDEO_SEARCH_PATH, GIF_SEARCH_PATH,
 *    VIDEO_SELECTOR, GIF_SELECTOR, and ID_PATTERN regex as needed.
 */
'use strict';

Object.defineProperty(exports, "__esModule", { value: true });

// Babel helper imports
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

// Core module and mixins
var _GifMixin = require('../core/GifMixin');
var _GifMixin2 = _interopRequireDefault(_GifMixin);
var _VideoMixin = require('../core/VideoMixin');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _AbstractModule = require('../core/AbstractModule');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

// Base URLs
const BASE_PLATFORM_URL = 'https://www.youporn.com';
const GIF_DOMAIN = 'https://cdn.youporn.com';

/**
 * @typedef {object} MediaResult
 * @property {string} id - Unique identifier for the media.
 * @property {string} title - Title of the media.
 * @property {string} url - Direct URL to the media's page on the platform.
 * @property {string} [duration] - Duration of the video (e.g., "10:30"). Undefined for GIFs.
 * @property {string} thumbnail - URL to the media's static thumbnail image.
 * @property {string} [preview_video] - URL to a short animated preview (WebM/MP4 or direct GIF).
 * @property {string} [image_hq] - URL to a high-quality static image (for photos/gifs).
 * @property {string} source - The name of the platform.
 * @property {string} type - 'videos' or 'gifs'.
 */

/**
 * @class YoupornDriver
 * @classdesc Driver for fetching video and GIF content from Youporn.
 */
var YoupornDriver = (function (_AbstractModule$with) {
  (0, _inherits3.default)(YoupornDriver, _AbstractModule$with);

  function YoupornDriver() {
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    (0, _classCallCheck3.default)(this, YoupornDriver);
    return (0, _possibleConstructorReturn3.default)(this, (YoupornDriver.__proto__ || (0, _getPrototypeOf2.default)(YoupornDriver)).call(this, options));
  }

  (0, _createClass3.default)(YoupornDriver, [{
    key: 'videoUrl',
    value: function videoUrl(query, page) {
      const encodedQuery = encodeURIComponent(query.trim());
      const pageNumber = Math.max(1, page || this.firstpage);
      const url = new URL('/search', BASE_PLATFORM_URL);
      url.searchParams.set('query', encodedQuery);
      url.searchParams.set('page', String(pageNumber));
      return url.href;
    }
  }, {
    key: 'videoParser',
    value: function videoParser($, rawBody) {
      const results = [];
      const videoItems = $('div.video-box');

      if (!videoItems.length) {
        console.warn(`[${this.name} Video Parser] No video items found with current selectors.`);
        return [];
      }

      videoItems.each((index, element) => {
        const item = $(element);
        const linkElement = item.find('a').first();
        let videoUrl = linkElement.attr('href');
        let videoId = videoUrl ? videoUrl.match(/\/watch\/(\d+)\//)?.[1] : null;
        if (!videoId && videoUrl) {
          const pathSegments = videoUrl.split('/');
          const potentialId = pathSegments[pathSegments.length - 2];
          if (potentialId && /^\\d+$/.test(potentialId)) {
            videoId = potentialId;
          }
        }

        let title = linkElement.attr('title') || item.find('span.title').text().trim() || item.attr('data-title');
        const thumbElement = item.find('img').first();
        let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
        if (thumbnailUrl && thumbnailUrl.includes('nothumb')) thumbnailUrl = undefined;
        let duration = item.find('span.duration').text().trim();
        let previewVideoUrl = linkElement.attr('data-preview') || item.find('video').attr('data-src');

        if (videoUrl) videoUrl = this._makeAbsolute(videoUrl, BASE_PLATFORM_URL);
        if (thumbnailUrl) thumbnailUrl = this._makeAbsolute(thumbnailUrl, BASE_PLATFORM_URL);
        if (previewVideoUrl) previewVideoUrl = this._makeAbsolute(previewVideoUrl, BASE_PLATFORM_URL);

        if (!videoUrl || !title || !thumbnailUrl || !videoId) {
          console.warn(`[${this.name} Video Parser] Skipping malformed video item:`, { title, videoUrl, thumbnailUrl, videoId, index });
          return;
        }

        results.push({
          id: videoId,
          title: title || 'Untitled Video',
          url: videoUrl,
          duration: duration || 'N/A',
          thumbnail: thumbnailUrl,
          preview_video: previewVideoUrl,
          source: this.name,
          type: 'videos'
        });
      });
      return results;
    }
  }, {
    key: 'gifUrl',
    value: function gifUrl(query, page) {
      const encodedQuery = encodeURIComponent(query.trim());
      const pageNumber = Math.max(1, page || this.firstpage);
      const url = new URL('/gifs', BASE_PLATFORM_URL);
      url.searchParams.set('query', encodedQuery);
      url.searchParams.set('page', String(pageNumber));
      return url.href;
    }
  }, {
    key: 'gifParser',
    value: function gifParser($, rawBody) {
      const results = [];
      const gifItems = $('div.gif-box, div.img-container');

      if (!gifItems.length) {
        console.warn(`[${this.name} GIF Parser] No GIF items found with current selectors.`);
        return [];
      }

      gifItems.each((index, element) => {
        const item = $(element);
        const linkElement = item.find('a').first();
        let gifPageUrl = linkElement.attr('href');
        let gifId = item.attr('data-id') || (gifPageUrl ? gifPageUrl.match(/\/gif\/(\d+)\//)?.[1] : null);
        let title = item.find('img').attr('alt') || linkElement.attr('title') || 'Untitled GIF';
        let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
        if (animatedGifUrl && animatedGifUrl.endsWith('.gif')) {
          animatedGifUrl = this._makeAbsolute(animatedGifUrl, GIF_DOMAIN);
        } else {
          const videoPreview = item.find('video source').attr('src') || item.find('video').attr('data-src');
          if (videoPreview) {
            animatedGifUrl = this._makeAbsolute(videoPreview, BASE_PLATFORM_URL);
          }
        }
        let staticThumbnailUrl = item.find('img').attr('data-thumb') || item.find('img').attr('src');
        if (!staticThumbnailUrl && animatedGifUrl && animatedGifUrl.endsWith('.gif')) {
          staticThumbnailUrl = animatedGifUrl;
        }
        if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, BASE_PLATFORM_URL);

        if (!gifPageUrl || !title || !animatedGifUrl || !gifId) {
          console.warn(`[${this.name} GIF Parser] Skipping malformed GIF item:`, { title, gifPageUrl, animatedGifUrl, gifId, index });
          return;
        }

        gifPageUrl = this._makeAbsolute(gifPageUrl, BASE_PLATFORM_URL);

        results.push({
          id: gifId,
          title: title,
          url: gifPageUrl,
          thumbnail: staticThumbnailUrl,
          preview_video: animatedGifUrl,
          source: this.name,
          type: 'gifs'
        });
      });
      return results;
    }
  }, {
    key: '_makeAbsolute',
    value: function _makeAbsolute(urlString, baseUrl) {
      if (!urlString || typeof urlString !== 'string') return undefined;
      if (urlString.startsWith('data:')) return urlString;
      if (urlString.startsWith('//')) return `https:${urlString}`;
      if (urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString;
      try {
        return new URL(urlString, baseUrl).href;
      } catch (e) {
        return undefined;
      }
    }
  }, {
    key: 'name',
    get: function get() {
      return 'Youporn';
    }
  }, {
    key: 'firstpage',
    get: function get() {
      return 1;
    }
  }]);
  return YoupornDriver;
}(_AbstractModule2.default.with(_VideoMixin2.default, _GifMixin2.default)));

export default YoupornDriver;
EOF

echo "Creating modules/Xhamster.js..."
cat << 'EOF' > modules/Xhamster.js
/**
 * IMPORTANT: CSS selectors and URL patterns in this file are speculative and
 * MUST be verified against the live website (xhamster.com) using browser
 * developer tools. Websites frequently change their structure.
 *
 * To verify:
 * 1. Go to the website.
 * 2. Perform a search for videos/GIFs.
 * 3. Inspect the HTML structure of result items (e.g., video cards, GIF blocks).
 * 4. Update BASE_PLATFORM_URL, GIF_DOMAIN, VIDEO_SEARCH_PATH, GIF_SEARCH_PATH,
 *    VIDEO_SELECTOR, GIF_SELECTOR, and ID_PATTERN regex as needed.
 */
'use strict';

Object.defineProperty(exports, "__esModule", { value: true });

// Babel helper imports
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

// Core module and mixins
var _GifMixin = require('../core/GifMixin');
var _GifMixin2 = _interopRequireDefault(_GifMixin);
var _VideoMixin = require('../core/VideoMixin');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _AbstractModule = require('../core/AbstractModule');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

// Base URLs
const BASE_PLATFORM_URL = 'https://xhamster.com';
const GIF_DOMAIN = 'https://static.xhamster.com';

/**
 * @typedef {object} MediaResult
 * @property {string} id - Unique identifier for the media.
 * @property {string} title - Title of the media.
 * @property {string} url - Direct URL to the media's page on the platform.
 * @property {string} [duration] - Duration of the video (e.g., "10:30"). Undefined for GIFs.
 * @property {string} thumbnail - URL to the media's static thumbnail image.
 * @property {string} [preview_video] - URL to a short animated preview (WebM/MP4 or direct GIF).
 * @property {string} [image_hq] - URL to a high-quality static image (for photos/gifs).
 * @property {string} source - The name of the platform.
 * @property {string} type - 'videos' or 'gifs'.
 */

/**
 * @class XhamsterDriver
 * @classdesc Driver for fetching video and GIF content from Xhamster.
 */
var XhamsterDriver = (function (_AbstractModule$with) {
  (0, _inherits3.default)(XhamsterDriver, _AbstractModule$with);

  function XhamsterDriver() {
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    (0, _classCallCheck3.default)(this, XhamsterDriver);
    return (0, _possibleConstructorReturn3.default)(this, (XhamsterDriver.__proto__ || (0, _getPrototypeOf2.default)(XhamsterDriver)).call(this, options));
  }

  (0, _createClass3.default)(XhamsterDriver, [{
    key: 'videoUrl',
    value: function videoUrl(query, page) {
      const encodedQuery = encodeURIComponent(query.trim());
      const pageNumber = Math.max(1, page || this.firstpage);
      const url = new URL('/search', BASE_PLATFORM_URL);
      url.searchParams.set('q', encodedQuery);
      url.searchParams.set('p', String(pageNumber));
      return url.href;
    }
  }, {
    key: 'videoParser',
    value: function videoParser($, rawBody) {
      const results = [];
      const videoItems = $('div.video');

      if (!videoItems.length) {
        console.warn(`[${this.name} Video Parser] No video items found with current selectors.`);
        return [];
      }

      videoItems.each((index, element) => {
        const item = $(element);
        const linkElement = item.find('a').first();
        let videoUrl = linkElement.attr('href');
        let videoId = videoUrl ? videoUrl.match(/\/videos\/([a-zA-Z0-9-]+)\//)?.[1] : null;
        if (!videoId && videoUrl) {
          const pathSegments = videoUrl.split('/');
          const potentialId = pathSegments[pathSegments.length - 2];
          if (potentialId && /^[a-zA-Z0-9-]+$/.test(potentialId)) {
            videoId = potentialId;
          }
        }

        let title = linkElement.attr('title') || item.find('span.title').text().trim() || item.attr('data-title');
        const thumbElement = item.find('img').first();
        let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
        if (thumbnailUrl && thumbnailUrl.includes('nothumb')) thumbnailUrl = undefined;
        let duration = item.find('span.duration').text().trim();
        let previewVideoUrl = linkElement.attr('data-preview') || item.find('video').attr('data-src');

        if (videoUrl) videoUrl = this._makeAbsolute(videoUrl, BASE_PLATFORM_URL);
        if (thumbnailUrl) thumbnailUrl = this._makeAbsolute(thumbnailUrl, BASE_PLATFORM_URL);
        if (previewVideoUrl) previewVideoUrl = this._makeAbsolute(previewVideoUrl, BASE_PLATFORM_URL);

        if (!videoUrl || !title || !thumbnailUrl || !videoId) {
          console.warn(`[${this.name} Video Parser] Skipping malformed video item:`, { title, videoUrl, thumbnailUrl, videoId, index });
          return;
        }

        results.push({
          id: videoId,
          title: title || 'Untitled Video',
          url: videoUrl,
          duration: duration || 'N/A',
          thumbnail: thumbnailUrl,
          preview_video: previewVideoUrl,
          source: this.name,
          type: 'videos'
        });
      });
      return results;
    }
  }, {
    key: 'gifUrl',
    value: function gifUrl(query, page) {
      const encodedQuery = encodeURIComponent(query.trim());
      const pageNumber = Math.max(1, page || this.firstpage);
      const url = new URL('/gifs', BASE_PLATFORM_URL);
      url.searchParams.set('q', encodedQuery);
      url.searchParams.set('p', String(pageNumber));
      return url.href;
    }
  }, {
    key: 'gifParser',
    value: function gifParser($, rawBody) {
      const results = [];
      const gifItems = $('div.gif');

      if (!gifItems.length) {
        console.warn(`[${this.name} GIF Parser] No GIF items found with current selectors.`);
        return [];
      }

      gifItems.each((index, element) => {
        const item = $(element);
        const linkElement = item.find('a').first();
        let gifPageUrl = linkElement.attr('href');
        let gifId = item.attr('data-id') || (gifPageUrl ? gifPageUrl.match(/\/gifs\/([a-zA-Z0-9-]+)\//)?.[1] : null);
        let title = item.find('img').attr('alt') || linkElement.attr('title') || 'Untitled GIF';
        let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
        if (animatedGifUrl && animatedGifUrl.endsWith('.gif')) {
          animatedGifUrl = this._makeAbsolute(animatedGifUrl, GIF_DOMAIN);
        } else {
          const videoPreview = item.find('video source').attr('src') || item.find('video').attr('data-src');
          if (videoPreview) {
            animatedGifUrl = this._makeAbsolute(videoPreview, BASE_PLATFORM_URL);
          }
        }
        let staticThumbnailUrl = item.find('img').attr('data-thumb') || item.find('img').attr('src');
        if (!staticThumbnailUrl && animatedGifUrl && animatedGifUrl.endsWith('.gif')) {
          staticThumbnailUrl = animatedGifUrl;
        }
        if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, BASE_PLATFORM_URL);

        if (!gifPageUrl || !title || !animatedGifUrl || !gifId) {
          console.warn(`[${this.name} GIF Parser] Skipping malformed GIF item:`, { title, gifPageUrl, animatedGifUrl, gifId, index });
          return;
        }

        gifPageUrl = this._makeAbsolute(gifPageUrl, BASE_PLATFORM_URL);

        results.push({
          id: gifId,
          title: title,
          url: gifPageUrl,
          thumbnail: staticThumbnailUrl,
          preview_video: animatedGifUrl,
          source: this.name,
          type: 'gifs'
        });
      });
      return results;
    }
  }, {
    key: '_makeAbsolute',
    value: function _makeAbsolute(urlString, baseUrl) {
      if (!urlString || typeof urlString !== 'string') return undefined;
      if (urlString.startsWith('data:')) return urlString;
      if (urlString.startsWith('//')) return `https:${urlString}`;
      if (urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString;
      try {
        return new URL(urlString, baseUrl).href;
      } catch (e) {
        return undefined;
      }
    }
  }, {
    key: 'name',
    get: function get() {
      return 'Xhamster';
    }
  }, {
    key: 'firstpage',
    get: function get() {
      return 1;
    }
  }]);
  return XhamsterDriver;
}(_AbstractModule2.default.with(_VideoMixin2.default, _GifMixin2.default)));

export default XhamsterDriver;
EOF

echo "Creating modules/Sex.js..."
cat << 'EOF' > modules/Sex.js
/**
 * IMPORTANT: CSS selectors and URL patterns in this file are speculative and
 * MUST be verified against the live website (www.sex.com) using browser
 * developer tools. Websites frequently change their structure.
 *
 * To verify:
 * 1. Go to the website.
 * 2. Perform a search for videos/GIFs.
 * 3. Inspect the HTML structure of result items (e.g., video cards, GIF blocks).
 * 4. Update BASE_PLATFORM_URL, GIF_DOMAIN, VIDEO_SEARCH_PATH, GIF_SEARCH_PATH,
 *    VIDEO_SELECTOR, GIF_SELECTOR, and ID_PATTERN regex as needed.
 */
'use strict';

Object.defineProperty(exports, "__esModule", { value: true });

// Babel helper imports
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

// Core module and mixins
var _GifMixin = require('../core/GifMixin');
var _GifMixin2 = _interopRequireDefault(_GifMixin);
var _VideoMixin = require('../core/VideoMixin');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _AbstractModule = require('../core/AbstractModule');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

// Base URLs
const BASE_PLATFORM_URL = 'https://www.sex.com';
const GIF_DOMAIN = 'https://cdn.sex.com';

/**
 * @typedef {object} MediaResult
 * @property {string} id - Unique identifier for the media.
 * @property {string} title - Title of the media.
 * @property {string} url - Direct URL to the media's page on the platform.
 * @property {string} [duration] - Duration of the video (e.g., "10:30"). Undefined for GIFs.
 * @property {string} thumbnail - URL to the media's static thumbnail image.
 * @property {string} [preview_video] - URL to a short animated preview (WebM/MP4 or direct GIF).
 * @property {string} [image_hq] - URL to a high-quality static image (for photos/gifs).
 * @property {string} source - The name of the platform.
 * @property {string} type - 'videos' or 'gifs'.
 */

/**
 * @class SexDriver
 * @classdesc Driver for fetching video and GIF content from Sex.com.
 */
var SexDriver = (function (_AbstractModule$with) {
  (0, _inherits3.default)(SexDriver, _AbstractModule$with);

  function SexDriver() {
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    (0, _classCallCheck3.default)(this, SexDriver);
    return (0, _possibleConstructorReturn3.default)(this, (SexDriver.__proto__ || (0, _getPrototypeOf2.default)(SexDriver)).call(this, options));
  }

  (0, _createClass3.default)(SexDriver, [{
    key: 'videoUrl',
    value: function videoUrl(query, page) {
      const encodedQuery = encodeURIComponent(query.trim());
      const pageNumber = Math.max(1, page || this.firstpage);
      const url = new URL('/search/videos', BASE_PLATFORM_URL);
      url.searchParams.set('q', encodedQuery);
      url.searchParams.set('page', String(pageNumber));
      return url.href;
    }
  }, {
    key: 'videoParser',
    value: function videoParser($, rawBody) {
      const results = [];
      const videoItems = $('div.pin');

      if (!videoItems.length) {
        console.warn(`[${this.name} Video Parser] No video items found with current selectors.`);
        return [];
      }

      videoItems.each((index, element) => {
        const item = $(element);
        const linkElement = item.find('a').first();
        let videoUrl = linkElement.attr('href');
        let videoId = videoUrl ? videoUrl.match(/\/video\/(\d+)\//)?.[1] : null;
        if (!videoId && videoUrl) {
          const pathSegments = videoUrl.split('/');
          const potentialId = pathSegments[pathSegments.length - 2];
          if (potentialId && /^\\d+$/.test(potentialId)) {
            videoId = potentialId;
          }
        }

        let title = linkElement.attr('title') || item.find('span.title').text().trim() || item.attr('data-title');
        const thumbElement = item.find('img').first();
        let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
        if (thumbnailUrl && thumbnailUrl.includes('nothumb')) thumbnailUrl = undefined;
        let duration = item.find('span.duration').text().trim();
        let previewVideoUrl = linkElement.attr('data-preview') || item.find('video').attr('data-src');

        if (videoUrl) videoUrl = this._makeAbsolute(videoUrl, BASE_PLATFORM_URL);
        if (thumbnailUrl) thumbnailUrl = this._makeAbsolute(thumbnailUrl, BASE_PLATFORM_URL);
        if (previewVideoUrl) previewVideoUrl = this._makeAbsolute(previewVideoUrl, BASE_PLATFORM_URL);

        if (!videoUrl || !title || !thumbnailUrl || !videoId) {
          console.warn(`[${this.name} Video Parser] Skipping malformed video item:`, { title, videoUrl, thumbnailUrl, videoId, index });
          return;
        }

        results.push({
          id: videoId,
          title: title || 'Untitled Video',
          url: videoUrl,
          duration: duration || 'N/A',
          thumbnail: thumbnailUrl,
          preview_video: previewVideoUrl,
          source: this.name,
          type: 'videos'
        });
      });
      return results;
    }
  }, {
    key: 'gifUrl',
    value: function gifUrl(query, page) {
      const encodedQuery = encodeURIComponent(query.trim());
      const pageNumber = Math.max(1, page || this.firstpage);
      const url = new URL('/search/gifs', BASE_PLATFORM_URL);
      url.searchParams.set('q', encodedQuery);
      url.searchParams.set('page', String(pageNumber));
      return url.href;
    }
  }, {
    key: 'gifParser',
    value: function gifParser($, rawBody) {
      const results = [];
      const gifItems = $('div.pin');

      if (!gifItems.length) {
        console.warn(`[${this.name} GIF Parser] No GIF items found with current selectors.`);
        return [];
      }

      gifItems.each((index, element) => {
        const item = $(element);
        const linkElement = item.find('a').first();
        let gifPageUrl = linkElement.attr('href');
        let gifId = item.attr('data-id') || (gifPageUrl ? gifPageUrl.match(/\/gif\/(\d+)\//)?.[1] : null);
        let title = item.find('img').attr('alt') || linkElement.attr('title') || 'Untitled GIF';
        let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
        if (animatedGifUrl && animatedGifUrl.endsWith('.gif')) {
          animatedGifUrl = this._makeAbsolute(animatedGifUrl, GIF_DOMAIN);
        } else {
          const videoPreview = item.find('video source').attr('src') || item.find('video').attr('data-src');
          if (videoPreview) {
            animatedGifUrl = this._makeAbsolute(videoPreview, BASE_PLATFORM_URL);
          }
        }
        let staticThumbnailUrl = item.find('img').attr('data-thumb') || item.find('img').attr('src');
        if (!staticThumbnailUrl && animatedGifUrl && animatedGifUrl.endsWith('.gif')) {
          staticThumbnailUrl = animatedGifUrl;
        }
        if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, BASE_PLATFORM_URL);

        if (!gifPageUrl || !title || !animatedGifUrl || !gifId) {
          console.warn(`[${this.name} GIF Parser] Skipping malformed GIF item:`, { title, gifPageUrl, animatedGifUrl, gifId, index });
          return;
        }

        gifPageUrl = this._makeAbsolute(gifPageUrl, BASE_PLATFORM_URL);

        results.push({
          id: gifId,
          title: title,
          url: gifPageUrl,
          thumbnail: staticThumbnailUrl,
          preview_video: animatedGifUrl,
          source: this.name,
          type: 'gifs'
        });
      });
      return results;
    }
  }, {
    key: '_makeAbsolute',
    value: function _makeAbsolute(urlString, baseUrl) {
      if (!urlString || typeof urlString !== 'string') return undefined;
      if (urlString.startsWith('data:')) return urlString;
      if (urlString.startsWith('//')) return `https:${urlString}`;
      if (urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString;
      try {
        return new URL(urlString, baseUrl).href;
      } catch (e) {
        return undefined;
      }
    }
  }, {
    key: 'name',
    get: function get() {
      return 'Sex.com';
    }
  }, {
    key: 'firstpage',
    get: function get() {
      return 1;
    }
  }]);
  return SexDriver;
}(_AbstractModule2.default.with(_VideoMixin2.default, _GifMixin2.default)));

export default SexDriver;
EOF

echo "Creating modules/Redtube.js..."
cat << 'EOF' > modules/Redtube.js
/**
 * IMPORTANT: CSS selectors and URL patterns in this file are speculative and
 * MUST be verified against the live website (www.redtube.com) using browser
 * developer tools. Websites frequently change their structure.
 *
 * To verify:
 * 1. Go to the website.
 * 2. Perform a search for videos/GIFs.
 * 3. Inspect the HTML structure of result items (e.g., video cards, GIF blocks).
 * 4. Update BASE_PLATFORM_URL, GIF_DOMAIN, VIDEO_SEARCH_PATH, GIF_SEARCH_PATH,
 *    VIDEO_SELECTOR, GIF_SELECTOR, and ID_PATTERN regex as needed.
 */
'use strict';

Object.defineProperty(exports, "__esModule", { value: true });

// Babel helper imports
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

// Core module and mixins
var _GifMixin = require('../core/GifMixin');
var _GifMixin2 = _interopRequireDefault(_GifMixin);
var _VideoMixin = require('../core/VideoMixin');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _AbstractModule = require('../core/AbstractModule');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

// Base URLs
const BASE_PLATFORM_URL = 'https://www.redtube.com';
const GIF_DOMAIN = 'https://img.redtube.com';

/**
 * @typedef {object} MediaResult
 * @property {string} id - Unique identifier for the media.
 * @property {string} title - Title of the media.
 * @property {string} url - Direct URL to the media's page on the platform.
 * @property {string} [duration] - Duration of the video (e.g., "10:30"). Undefined for GIFs.
 * @property {string} thumbnail - URL to the media's static thumbnail image.
 * @property {string} [preview_video] - URL to a short animated preview (WebM/MP4 or direct GIF).
 * @property {string} [image_hq] - URL to a high-quality static image (for photos/gifs).
 * @property {string} source - The name of the platform.
 * @property {string} type - 'videos' or 'gifs'.
 */

/**
 * @class RedtubeDriver
 * @classdesc Driver for fetching video and GIF content from Redtube.
 */
var RedtubeDriver = (function (_AbstractModule$with) {
  (0, _inherits3.default)(RedtubeDriver, _AbstractModule$with);

  function RedtubeDriver() {
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    (0, _classCallCheck3.default)(this, RedtubeDriver);
    return (0, _possibleConstructorReturn3.default)(this, (RedtubeDriver.__proto__ || (0, _getPrototypeOf2.default)(RedtubeDriver)).call(this, options));
  }

  (0, _createClass3.default)(RedtubeDriver, [{
    key: 'videoUrl',
    value: function videoUrl(query, page) {
      const encodedQuery = encodeURIComponent(query.trim());
      const pageNumber = Math.max(1, page || this.firstpage);
      const url = new URL('/search', BASE_PLATFORM_URL);
      url.searchParams.set('search', encodedQuery);
      url.searchParams.set('page', String(pageNumber));
      return url.href;
    }
  }, {
    key: 'videoParser',
    value: function videoParser($, rawBody) {
      const results = [];
      const videoItems = $('div.video');

      if (!videoItems.length) {
        console.warn(`[${this.name} Video Parser] No video items found with current selectors.`);
        return [];
      }

      videoItems.each((index, element) => {
        const item = $(element);
        const linkElement = item.find('a').first();
        let videoUrl = linkElement.attr('href');
        let videoId = videoUrl ? videoUrl.match(/\/(\d+)\//)?.[1] : null;
        if (!videoId && videoUrl) {
          const pathSegments = videoUrl.split('/');
          const potentialId = pathSegments[pathSegments.length - 2];
          if (potentialId && /^\\d+$/.test(potentialId)) {
            videoId = potentialId;
          }
        }

        let title = linkElement.attr('title') || item.find('span.title').text().trim() || item.attr('data-title');
        const thumbElement = item.find('img').first();
        let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
        if (thumbnailUrl && thumbnailUrl.includes('nothumb')) thumbnailUrl = undefined;
        let duration = item.find('span.duration').text().trim();
        let previewVideoUrl = linkElement.attr('data-preview') || item.find('video').attr('data-src');

        if (videoUrl) videoUrl = this._makeAbsolute(videoUrl, BASE_PLATFORM_URL);
        if (thumbnailUrl) thumbnailUrl = this._makeAbsolute(thumbnailUrl, BASE_PLATFORM_URL);
        if (previewVideoUrl) previewVideoUrl = this._makeAbsolute(previewVideoUrl, BASE_PLATFORM_URL);

        if (!videoUrl || !title || !thumbnailUrl || !videoId) {
          console.warn(`[${this.name} Video Parser] Skipping malformed video item:`, { title, videoUrl, thumbnailUrl, videoId, index });
          return;
        }

        results.push({
          id: videoId,
          title: title || 'Untitled Video',
          url: videoUrl,
          duration: duration || 'N/A',
          thumbnail: thumbnailUrl,
          preview_video: previewVideoUrl,
          source: this.name,
          type: 'videos'
        });
      });
      return results;
    }
  }, {
    key: 'gifUrl',
    value: function gifUrl(query, page) {
      const encodedQuery = encodeURIComponent(query.trim());
      const pageNumber = Math.max(1, page || this.firstpage);
      const url = new URL('/gifs', BASE_PLATFORM_URL);
      url.searchParams.set('search', encodedQuery);
      url.searchParams.set('page', String(pageNumber));
      return url.href;
    }
  }, {
    key: 'gifParser',
    value: function gifParser($, rawBody) {
      const results = [];
      const gifItems = $('div.gif');

      if (!gifItems.length) {
        console.warn(`[${this.name} GIF Parser] No GIF items found with current selectors.`);
        return [];
      }

      gifItems.each((index, element) => {
        const item = $(element);
        const linkElement = item.find('a').first();
        let gifPageUrl = linkElement.attr('href');
        let gifId = item.attr('data-id') || (gifPageUrl ? gifPageUrl.match(/\/gif\/(\d+)\//)?.[1] : null);
        let title = item.find('img').attr('alt') || linkElement.attr('title') || 'Untitled GIF';
        let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
        if (animatedGifUrl && animatedGifUrl.endsWith('.gif')) {
          animatedGifUrl = this._makeAbsolute(animatedGifUrl, GIF_DOMAIN);
        } else {
          const videoPreview = item.find('video source').attr('src') || item.find('video').attr('data-src');
          if (videoPreview) {
            animatedGifUrl = this._makeAbsolute(videoPreview, BASE_PLATFORM_URL);
          }
        }
        let staticThumbnailUrl = item.find('img').attr('data-thumb') || item.find('img').attr('src');
        if (!staticThumbnailUrl && animatedGifUrl && animatedGifUrl.endsWith('.gif')) {
          staticThumbnailUrl = animatedGifUrl;
        }
        if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, BASE_PLATFORM_URL);

        if (!gifPageUrl || !title || !animatedGifUrl || !gifId) {
          console.warn(`[${this.name} GIF Parser] Skipping malformed GIF item:`, { title, gifPageUrl, animatedGifUrl, gifId, index });
          return;
        }

        gifPageUrl = this._makeAbsolute(gifPageUrl, BASE_PLATFORM_URL);

        results.push({
          id: gifId,
          title: title,
          url: gifPageUrl,
          thumbnail: staticThumbnailUrl,
          preview_video: animatedGifUrl,
          source: this.name,
          type: 'gifs'
        });
      });
      return results;
    }
  }, {
    key: '_makeAbsolute',
    value: function _makeAbsolute(urlString, baseUrl) {
      if (!urlString || typeof urlString !== 'string') return undefined;
      if (urlString.startsWith('data:')) return urlString;
      if (urlString.startsWith('//')) return `https:${urlString}`;
      if (urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString;
      try {
        return new URL(urlString, baseUrl).href;
      } catch (e) {
        return undefined;
      }
    }
  }, {
    key: 'name',
    get: function get() {
      return 'Redtube';
    }
  }, {
    key: 'firstpage',
    get: function get() {
      return 1;
    }
  }]);
  return RedtubeDriver;
}(_AbstractModule2.default.with(_VideoMixin2.default, _GifMixin2.default)));

export default RedtubeDriver;
EOF

# Main application files
echo "Creating server.js..."
cat << 'EOF' > server.js
#!/usr/bin/env node

const express = require('express');
const cors = require('cors'); // Import cors
const app = express();
const path = require('path');
const axios = require('axios');
const cheerio = require('cheerio');
const { URL } = require('url');

// Import core modules and mixins
const AbstractModule = require('./core/AbstractModule');
const VideoMixin = require('./core/VideoMixin');
const GifMixin = require('./core/GifMixin');

// Import all specific drivers
const Redtube = require('./modules/Redtube');
const Pornhub = require('./modules/Pornhub');
const Xvideos = require('./modules/Xvideos');
const Xhamster = require('./modules/Xhamster');
const Youporn = require('./modules/Youporn');
const Sex = require('./modules/Sex'); // Import Sex.com driver

// Map driver names to their classes
const drivers = {
    'redtube': Redtube,
    'pornhub': Pornhub,
    'xvideos': Xvideos,
    'xhamster': Xhamster,
    'youporn': Youporn,
    'sex': Sex, // Add Sex.com driver
    // Add a mock driver for testing
    'mock': class MockDriver extends AbstractModule.with(VideoMixin, GifMixin) {
        constructor(options) { super(options); }
        get name() { return 'Mock'; }
        get firstpage() { return 1; }
        videoUrl(query, page) { return `http://mock.com/videos?q=${query}&page=${page}`; }
        videoParser(cheerioInstance, rawBody) {
            console.log('Mock Video Parser called.');
            const results = [];
            for (let i = 0; i < 5; i++) {
                results.push({
                    id: `mock-video-${i}-${Date.now()}`,
                    title: `Mock Video ${this.query} - Page ${this.page} - Item ${i + 1}`,
                    url: `http://mock.com/video/${i}`,
                    duration: '0:30',
                    thumbnail: `https://placehold.co/320x180/00e5ff/000000?text=Mock+Video+${i+1}`,
                    preview_video: `https://www.w3schools.com/html/mov_bbb.mp4`, // A common test video
                    source: 'Mock.com'
                });
            }
            return results;
        }
        gifUrl(query, page) { return `http://mock.com/gifs?q=${query}&page=${page}`; }
        gifParser(cheerioInstance, rawData) { // Ensure gifParser also accepts cheerioInstance
            console.log('Mock GIF Parser called.');
            const results = [];
            for (let i = 0; i < 5; i++) {
                results.push({
                    id: `mock-gif-${i}-${Date.now()}`,
                    title: `Mock GIF ${this.query} - Page ${this.page} - Item ${i + 1}`,
                    url: `http://mock.com/gif/${i}`,
                    thumbnail: `https://placehold.co/320x180/ff00aa/000000?text=Mock+GIF+${i+1}`,
                    preview_video: `https://i.giphy.com/media/VbnUQpnihPSIgIXuZv/giphy.gif`, // A sample GIF
                    source: 'Mock.com'
                });
            }
            return results;
        }
    }
};

// Middleware
app.use(cors()); // Enable CORS for all routes
app.use(express.static(__dirname)); // Serve static files from the current directory (for index.html)

// API endpoint for search
app.get('/api/search', async (req, res) => {
    const { query, driver: driverName, type, page } = req.query;

    if (!query || !driverName || !type) {
        return res.status(400).json({ error: 'Missing query, driver, or type parameters.' });
    }

    const DriverClass = drivers[driverName.toLowerCase()];
    if (!DriverClass) {
        return res.status(400).json({ error: `Unsupported driver: ${driverName}.` });
    }

    try {
        const driverInstance = new DriverClass({ query });
        driverInstance.setQuery(query);
        driverInstance.page = parseInt(page, 10) || driverInstance.firstpage;

        let results = [];
        let url = '';
        let rawContent;

        // Axios request configuration
        const axiosConfig = {
            timeout: 30000, // 30 seconds timeout
            headers: {
                // Some sites might require a common User-Agent
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        };

        if (type === 'videos' && typeof driverInstance.videoUrl === 'function' && typeof driverInstance.videoParser === 'function') {
            url = driverInstance.videoUrl(query, driverInstance.page);
            console.log(`[Backend] Fetching video from ${driverName}: ${url}`);
            const response = await axios.get(url, axiosConfig);
            rawContent = response.data;

            // Cheerio is passed for drivers that parse HTML, null otherwise (e.g., API-based drivers)
            // The list-based check is a bit fragile; a driver property would be better for future.
            if (['pornhub', 'xvideos', 'xhamster', 'youporn', 'sex'].includes(driverName.toLowerCase())) {
                const $ = cheerio.load(rawContent);
                results = await driverInstance.videoParser($, rawContent);
            } else {
                results = await driverInstance.videoParser(null, rawContent); // e.g., Redtube (JSON API), Mock
            }
        } else if (type === 'gifs' && typeof driverInstance.gifUrl === 'function' && typeof driverInstance.gifParser === 'function') {
            url = driverInstance.gifUrl(query, driverInstance.page);
            console.log(`[Backend] Fetching GIF from ${driverName}: ${url}`);
            const response = await axios.get(url, axiosConfig);
            rawContent = response.data;

            if (['pornhub', 'xhamster', 'sex', 'youporn'].includes(driverName.toLowerCase())) { // Mock also uses null for cheerio
                const $ = cheerio.load(rawContent);
                results = await driverInstance.gifParser($, rawContent);
            } else {
                results = await driverInstance.gifParser(null, rawContent); // Pass null for cheerioInstance if not HTML scraping
            }
        } else {
            return res.status(400).json({ error: `Unsupported search type '${type}' for driver '${driverName}'.` });
        }

        results = results.map(item => ({
            ...item,
            source: driverInstance.name // Ensure source is set from driver
        }));

        res.json(results);

    } catch (error) {
        console.error(`[Backend] Error during search for ${driverName} (${type}):`, error.message);
        if (error.response) {
            console.error(`[Backend] Response status: ${error.response.status}, data:`, error.response.data);
            res.status(error.response.status).json({ error: `Failed to fetch results from ${driverName}. Server responded with ${error.response.status}. ${error.response.data.error || ''}` });
        } else if (error.request) {
             console.error(`[Backend] No response received for request to ${driverName}.`);
             res.status(504).json({ error: `Failed to fetch results from ${driverName}. No response from upstream server.` });
        } else {
            res.status(500).json({ error: `Failed to fetch results from ${driverName}. ${error.message}` });
        }
    }
});

// Serve index.html for the root path
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});


const PORT = process.env.PORT || 3000;
app.listen(PORT, '0.0.0.0', () => { // Listen on 0.0.0.0 to be accessible on network
    console.log(`Neon Video Search App backend API server running on http://0.0.0.0:${PORT}`);
    console.log(`Frontend should be accessible at http://localhost:${PORT} or http://<your-device-ip>:${PORT}`);
});
EOF

echo "Creating index.html..."
cat << 'EOF' > index.html
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Neon Search | Find Videos & GIFs</title>
    <meta name="description" content="Search for videos and GIFs with a vibrant neon-themed interface. Features history and local favorites.">
    <meta name="keywords" content="video search, gif search, neon theme, online media, adult entertainment search, favorites, history">
    <meta name="author" content="Neon Search Project">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>💡</text></svg>">

    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">

    <style>
        /* --- CSS Variables for Enhanced Neon Theme --- */
        /* Define your primary neon colors and background shades */
        :root {
            --neon-pink: #ff00aa;
            /* Slightly deeper pink */
            --neon-cyan: #00e5ff;
            /* Brighter cyan */
            --neon-green: #39ff14;
            /* A bright green */
            --neon-purple: #9d00ff;
            /* Added another neon color for variety */
            --dark-bg-start: #0d0c1d;
            /* Even darker start for a deep space feel */
            --dark-bg-end: #101026;
            /* Darker end for the gradient */
            --input-bg: #0a0a1a;
            /* Dark background for input fields */
            --text-color: #f0f0f0;
            /* Brighter text */
            --card-bg: rgba(10, 10, 26, 0.8);
            /* Slightly more opaque dark background for cards */
            --modal-bg: rgba(5, 5, 15, 0.96);
            /* Very dark, almost opaque background for modal overlay */
            --error-bg: rgba(255, 20, 100, 0.88);
            /* Semi-transparent red for error messages */
            --error-border: var(--neon-pink);
            /* Neon pink border for errors */
            --disabled-opacity: 0.4;
            /* Reduce opacity for disabled elements */
            --focus-outline-color: var(--neon-green);
            /* Green outline for focus states */
            --link-color: var(--neon-cyan);
            /* Cyan color for links */
            --link-hover-color: var(--neon-green);
            /* Green color on link hover */
            --favorite-btn-color: #aaa;
            /* Default grey color for favorite button */
            --favorite-btn-active-color: var(--neon-pink);
            /* Neon pink color when favorited */
        }

        /* --- Base Styles & Scrollbar --- */
        html {
            scroll-behavior: smooth;
            /* Smooth scrolling for better UX */
        }

        body {
            /* Background gradient using defined neon dark shades */
            background: linear-gradient(145deg, var(--dark-bg-start) 0%, var(--dark-bg-end) 100%);
            color: var(--text-color);
            /* Default text color */
            font-family: 'Roboto', sans-serif;
            /* Use the imported font */
            margin: 0;
            padding: 0;
            overflow-x: hidden;
            /* Prevent horizontal scroll */
            min-height: 100vh;
            /* Ensure body covers the full viewport height */
            /* Custom scrollbar styling for Firefox */
            scrollbar-color: var(--neon-pink) var(--input-bg);
            scrollbar-width: thin;
        }

        /* Custom scrollbar styling for Webkit browsers (Chrome, Safari, Edge) */
        ::-webkit-scrollbar {
            width: 10px;
        }

        ::-webkit-scrollbar-track {
            background: var(--input-bg);
            /* Dark track */
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb {
            /* Gradient thumb matching neon colors */
            background: linear-gradient(var(--neon-pink), var(--neon-purple));
            border-radius: 5px;
            border: 1px solid var(--dark-bg-end);
        }

        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(var(--neon-purple), var(--neon-pink));
            /* Reverse gradient on hover */
        }

        /* --- Layout & Main Title --- */
        /* Styling for the main search container with neon border and glow */
        .search-container {
            background: rgba(10, 10, 25, 0.9);
            /* Slightly transparent dark background */
            border: 2px solid var(--neon-pink);
            /* Neon pink border */
            /* Multiple box shadows for a layered neon glow effect */
            box-shadow: 0 0 20px var(--neon-pink), 0 0 40px var(--neon-cyan), 0 0 60px var(--neon-purple), inset 0 0 15px rgba(255, 0, 170, 0.5);
            border-radius: 16px;
            /* More rounded corners */
            animation: searchContainerGlow 6s infinite alternate ease-in-out;
            /* Animation for pulsing glow */
        }

        /* Keyframes for the main search container glow animation */
        @keyframes searchContainerGlow {
            0% {
                box-shadow: 0 0 20px var(--neon-pink), 0 0 40px var(--neon-cyan), 0 0 60px var(--neon-purple), inset 0 0 15px rgba(255, 0, 170, 0.5);
                border-color: var(--neon-pink);
            }

            50% {
                box-shadow: 0 0 30px var(--neon-cyan), 0 0 50px var(--neon-purple), 0 0 70px var(--neon-pink), inset 0 0 20px rgba(0, 229, 255, 0.5);
                border-color: var(--neon-cyan);
            }

            100% {
                box-shadow: 0 0 20px var(--neon-purple), 0 0 40px var(--neon-pink), 0 0 60px var(--neon-cyan), inset 0 0 15px rgba(157, 0, 255, 0.5);
                border-color: var(--neon-purple);
            }
        }

        /* Styling for the main title with neon text shadow */
        .title-main {
            text-shadow: 0 0 10px var(--neon-pink), 0 0 20px var(--neon-cyan), 0 0 30px var(--neon-purple), 0 0 40px #fff;
        }

        /* Styling for the subtitle with neon text shadow */
        .title-sub {
            text-shadow: 0 0 5px var(--neon-cyan);
        }

        /* --- Form Elements (Enhanced Neon) --- */
        /* Wrapper for the input to position the clear button */
        .input-wrapper {
            position: relative;
            display: flex;
            align-items: center;
            flex: 1;
            /* Allows input to take available space */
        }

        /* Styling for the main search input with neon effects */
        .input-neon {
            background: var(--input-bg);
            color: var(--text-color);
            border: 2px solid var(--neon-cyan);
            /* Cyan border */
            box-shadow: 0 0 10px var(--neon-cyan), inset 0 0 8px rgba(0, 229, 255, 0.25);
            /* Cyan glow */
            transition: all 0.3s ease;
            padding: 0.75rem 1rem;
            padding-right: 2.8rem;
            /* Space for the clear button */
            font-size: 1rem;
            line-height: 1.5;
            border-radius: 0.6rem;
            /* Slightly rounded corners */
            width: 100%;
        }

        .input-neon::placeholder {
            color: var(--text-color);
            opacity: 0.6;
            /* Make placeholder text slightly faded */
        }

        /* Styles when the input is focused */
        .input-neon:focus {
            border-color: var(--neon-green);
            /* Green border on focus */
            /* More intense glow with green and cyan */
            box-shadow: 0 0 18px var(--neon-green), 0 0 30px var(--neon-cyan), inset 0 0 10px rgba(57, 255, 20, 0.4);
            outline: none;
            /* Remove default outline */
            animation: focusPulseNeon 1.2s infinite alternate;
            /* Pulsing animation on focus */
        }

        /* Styling for the clear button inside the input */
        .clear-input-btn {
            position: absolute;
            right: 0.5rem;
            top: 50%;
            transform: translateY(-50%);
            background: transparent;
            border: none;
            color: var(--neon-pink);
            /* Neon pink color */
            font-size: 1.8rem;
            line-height: 1;
            cursor: pointer;
            display: none;
            /* Hidden by default */
            padding: 0.25rem;
            transition: color 0.2s ease, transform 0.2s ease;
            z-index: 10;
        }

        /* Show the clear button when the input has text */
        .input-wrapper input:not(:placeholder-shown)+.clear-input-btn {
            display: block;
        }

        /* Hover effect for the clear button */
        .clear-input-btn:hover {
            color: var(--neon-green);
            /* Change color to green on hover */
            transform: translateY(-50%) scale(1.15) rotate(90deg);
            /* Slight scale and rotation on hover */
        }

        /* Styling for the select dropdown with neon effects */
        .select-neon {
            background: var(--input-bg);
            color: var(--text-color);
            border: 2px solid var(--neon-pink);
            /* Pink border */
            box-shadow: 0 0 10px var(--neon-pink), inset 0 0 8px rgba(255, 0, 170, 0.25);
            /* Pink glow */
            transition: all 0.3s ease;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            line-height: 1.5;
            border-radius: 0.6rem;
            /* Slightly rounded corners */
            -webkit-appearance: none;
            /* Remove default arrow in Chrome */
            -moz-appearance: none;
            /* Remove default arrow in Firefox */
            appearance: none;
            /* Remove default arrow */
            /* Custom SVG arrow with neon pink color */
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%23ff00aa'%3E%3Cpath fill-rule='evenodd' d='M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z' clip-rule='evenodd'/%3E%3Csvg%3E");
            background-repeat: no-repeat;
            background-position: right 0.75rem center;
            background-size: 0.9em auto;
            padding-right: 2.8rem;
            /* Space for the custom arrow */
        }

        /* Styles when the select is focused */
        .select-neon:focus {
            border-color: var(--neon-green);
            /* Green border on focus */
            /* Intense glow with green and pink */
            box-shadow: 0 0 18px var(--neon-green), 0 0 30px var(--neon-pink), inset 0 0 10px rgba(57, 255, 20, 0.4);
            outline: none;
            /* Remove default outline */
            animation: focusPulseNeon 1.2s infinite alternate;
            /* Pulsing animation on focus */
        }

        /* Keyframes for the pulsing animation on input/select focus */
        @keyframes focusPulseNeon {
            0% {
                box-shadow: 0 0 18px var(--neon-green), 0 0 30px var(--neon-cyan), inset 0 0 10px rgba(57, 255, 20, 0.4);
            }

            50% {
                box-shadow: 0 0 25px var(--neon-green), 0 0 40px var(--neon-cyan), inset 0 0 15px rgba(57, 255, 20, 0.6);
            }

            100% {
                box-shadow: 0 0 18px var(--neon-green), 0 0 30px var(--neon-cyan), inset 0 0 10px rgba(57, 255, 20, 0.4);
            }
        }

        /* Styles for disabled input/select elements */
        .input-neon:disabled,
        .select-neon:disabled {
            cursor: not-allowed;
            opacity: var(--disabled-opacity);
            box-shadow: none;
            border-color: #444;
            /* Muted border color */
            animation: none;
            /* Stop any animations */
        }

        /* Styling for the search button with gradient background and neon glow */
        .btn-neon {
            background: linear-gradient(55deg, var(--neon-pink), var(--neon-purple), var(--neon-cyan));
            background-size: 200% 200%;
            /* Make background larger for animation */
            border: 2px solid transparent;
            /* Transparent border, glow provides the visual border */
            color: #ffffff;
            /* White text */
            /* Text shadow for neon text effect */
            text-shadow: 0 0 6px #fff, 0 0 12px var(--neon-pink), 0 0 18px var(--neon-cyan);
            /* Box shadow for overall button glow */
            box-shadow: 0 0 12px var(--neon-pink), 0 0 24px var(--neon-cyan), 0 0 36px var(--neon-purple), inset 0 0 10px rgba(255, 255, 255, 0.3);
            transition: all 0.35s cubic-bezier(0.25, 0.1, 0.25, 1);
            /* Smooth transition */
            position: relative;
            overflow: hidden;
            /* Hide background animation overflow */
            border-radius: 0.6rem;
            /* Slightly rounded corners */
            cursor: pointer;
            animation: idleButtonGlow 3s infinite alternate;
            /* Idle pulsing animation */
        }

        /* Keyframes for the idle button glow animation */
        @keyframes idleButtonGlow {
            0% {
                background-position: 0% 50%;
                box-shadow: 0 0 12px var(--neon-pink), 0 0 24px var(--neon-cyan), 0 0 36px var(--neon-purple), inset 0 0 10px rgba(255, 255, 255, 0.3);
            }

            50% {
                background-position: 100% 50%;
                box-shadow: 0 0 15px var(--neon-cyan), 0 0 30px var(--neon-purple), 0 0 45px var(--neon-pink), inset 0 0 12px rgba(255, 255, 255, 0.4);
            }

            100% {
                background-position: 0% 50%;
                box-shadow: 0 0 12px var(--neon-pink), 0 0 24px var(--neon-cyan), 0 0 36px var(--neon-purple), inset 0 0 10px rgba(255, 255, 255, 0.3);
            }
        }

        /* Styles for the button on hover (when not disabled) */
        .btn-neon:hover:not(:disabled) {
            transform: scale(1.04) translateY(-3px);
            /* Slight lift and scale */
            /* More intense glow with green as a highlight */
            box-shadow: 0 0 18px var(--neon-green), 0 0 36px var(--neon-cyan), 0 0 54px var(--neon-pink), inset 0 0 15px rgba(255, 255, 255, 0.6);
            border-color: var(--neon-green);
            /* Green border on hover */
            /* Text shadow changes with hover */
            text-shadow: 0 0 8px #fff, 0 0 18px var(--neon-green), 0 0 24px var(--neon-cyan);
            animation-play-state: paused;
            /* Pause the idle glow animation */
        }

        /* Styles for the button when actively pressed (when not disabled) */
        .btn-neon:active:not(:disabled) {
            transform: scale(0.97);
            /* Slight press down */
            box-shadow: 0 0 8px var(--neon-pink), 0 0 15px var(--neon-cyan), inset 0 0 5px rgba(0, 0, 0, 0.2);
            /* Reduced glow */
        }

        /* Focus visible styles for accessibility */
        .btn-neon:focus-visible {
            outline: 3px solid var(--focus-outline-color);
            outline-offset: 3px;
            animation-play-state: paused;
        }

        /* Styles for disabled button */
        .btn-neon:disabled {
            cursor: not-allowed;
            opacity: var(--disabled-opacity);
            box-shadow: none;
            border-color: #444;
            /* Muted border color */
            text-shadow: none;
            background: #222;
            /* Dark background */
            animation: none;
            /* Stop all animations */
        }

        /* Styling for the loading spinner inside the button */
        .btn-neon .spinner {
            border: 3px solid rgba(255, 255, 255, 0.2);
            /* Semi-transparent white border */
            border-radius: 50%;
            /* Top and right borders with neon colors for a rotating effect */
            border-top-color: var(--neon-pink);
            border-right-color: var(--neon-cyan);
            width: 1.1rem;
            height: 1.1rem;
            animation: spin 0.8s linear infinite;
            /* Rotation animation */
            display: inline-block;
            vertical-align: middle;
        }

        /* Keyframes for the spinner rotation */
        @keyframes spin {
            to {
                transform: rotate(360deg);
            }
        }

        /* --- Results Grid (Cards) --- */
        /* Styling for individual result cards */
        .card {
            background: var(--card-bg);
            /* Semi-transparent dark background */
            border: 2px solid var(--neon-cyan);
            /* Cyan border */
            /* Glow effect for the card */
            box-shadow: 0 0 12px var(--neon-cyan), 0 0 24px var(--neon-pink), inset 0 0 10px rgba(10, 10, 26, 0.6);
            /* Smooth transitions for hover effects */
            transition: transform 0.35s cubic-bezier(0.25, 0.1, 0.25, 1), box-shadow 0.4s ease, border-color 0.3s ease;
            overflow: hidden;
            /* Hide content that exceeds bounds */
            cursor: pointer;
            /* Indicate clickable */
            height: 300px;
            /* Fixed height for consistent grid layout */
            display: flex;
            flex-direction: column;
            /* Stack media and info vertically */
            border-radius: 10px;
            color: inherit;
            /* Inherit text color from body */
            position: relative;
            /* Added for favorite button positioning */
        }

        /* Styles for cards on hover or when focused internally */
        .card:hover,
        .card:focus-visible {
            transform: translateY(-8px) scale(1.03);
            /* Lift and slightly scale up */
            border-color: var(--neon-green);
            /* Green border on hover/focus */
            /* More intense glow with green highlight */
            box-shadow: 0 0 22px var(--neon-green), 0 0 40px var(--neon-cyan), 0 0 60px var(--neon-pink), inset 0 0 15px rgba(10, 10, 26, 0.4);
            outline: none;
            /* Remove default outline */
        }

        /* Favorite button overlay on the card */
        .favorite-btn {
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            background: rgba(0, 0, 0, 0.5);
            border: none;
            color: var(--favorite-btn-color);
            /* Default grey */
            font-size: 1.5rem;
            line-height: 1;
            cursor: pointer;
            z-index: 60;
            /* Above media, below close button */
            display: flex;
            justify-content: center;
            align-items: center;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            transition: color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
            box-shadow: 0 0 8px rgba(0, 0, 0, 0.3);
        }

        .favorite-btn:hover {
            color: var(--favorite-btn-active-color);
            /* Neon pink on hover */
            transform: scale(1.2);
            box-shadow: 0 0 12px var(--favorite-btn-active-color);
        }

        /* Style for the favorite button when the item is favorited */
        .favorite-btn.is-favorite {
            color: var(--favorite-btn-active-color);
            /* Neon pink */
            text-shadow: 0 0 8px var(--favorite-btn-active-color);
            animation: favoritePulse 1.5s infinite alternate;
            /* Pulsing animation */
        }

        /* Keyframes for the favorite button pulse animation */
        @keyframes favoritePulse {
            0% {
                text-shadow: 0 0 8px var(--favorite-btn-active-color);
                box-shadow: 0 0 12px var(--favorite-btn-active-color);
            }

            100% {
                text-shadow: 0 0 15px var(--favorite-btn-active-color), 0 0 25px var(--favorite-btn-active-color);
                box-shadow: 0 0 18px var(--favorite-btn-active-color), 0 0 30px var(--favorite-btn-active-color);
            }
        }

        /* Container for media (thumbnail/preview) inside the card */
        .card-media-container {
            height: 200px;
            background-color: var(--input-bg);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            position: relative;
            overflow: hidden;
            border-radius: 6px 6px 0 0;
            /* Rounded top corners */
        }

        /* Base styles for media elements (img, video) within the container */
        .card-media-container>img,
        .card-media-container>video {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
            background-color: #05080f;
            /* Darker placeholder for media loading */
        }

        /* Static thumbnail image (poster) */
        .card-media-container img.static-thumb {
            position: absolute;
            top: 0;
            left: 0;
            opacity: 1;
            z-index: 1;
            transition: opacity 0.3s ease-in-out;
        }

        /* Animated preview (video or direct GIF image if styled as such) */
        .card-media-container video.preview-video,
        .card-media-container img.preview-gif-image {
            /* Class for direct GIFs to be revealed */
            position: absolute;
            top: 0;
            left: 0;
            opacity: 0;
            pointer-events: none;
            z-index: 5;
            transition: opacity 0.3s ease-in-out;
        }

        /* Show animated preview on hover/focus */
        .card-media-container:hover .preview-video,
        /* General for video tags */
        .card:focus-within .card-media-container .preview-video,
        .card-media-container:hover .preview-gif-image,
        /* For direct GIF images */
        .card:focus-within .card-media-container .preview-gif-image {
            opacity: 1;
            pointer-events: auto;
            /* Allow interaction if it was a video */
        }

        /* Dim static thumb when animated preview is active */
        .card-media-container:hover img.static-thumb,
        .card:focus-within .card-media-container img.static-thumb {
            opacity: 0.1;
        }


        /* Container for text information below the media */
        .card-info {
            height: 100px;
            /* Fixed height for info area */
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            /* Space out title and link */
            padding: 0.75rem;
            flex-grow: 1;
            overflow: hidden;
            /* Hide overflowing text */
        }

        /* Styling for the card title */
        .card-title {
            font-size: 1rem;
            font-weight: 600;
            /* Semi-bold */
            margin-bottom: 0.25rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            /* Prevent title wrap, show ellipsis */
            /* Text shadow for title glow */
            text-shadow: 0 0 6px var(--neon-cyan), 0 0 10px var(--neon-pink);
        }

        /* Styling for the source link in the card */
        .card-link {
            color: var(--link-color);
            /* Cyan link color */
            text-shadow: 0 0 4px var(--neon-pink);
            /* Pink text shadow */
            font-size: 0.875rem;
            /* Smaller font size */
            transition: color 0.25s ease, text-shadow 0.25s ease;
            align-self: flex-start;
            /* Align link to the start */
            margin-top: auto;
            /* Push link to the bottom */
            text-decoration: none;
            /* No underline by default */
        }

        /* Link hover/focus styles */
        .card-link:hover,
        .card-link:focus {
            color: var(--link-hover-color);
            /* Green on hover */
            text-shadow: 0 0 6px var(--neon-green), 0 0 8px var(--neon-cyan);
            /* Green/cyan shadow on hover */
            text-decoration: underline;
            /* Underline on hover */
            outline: none;
        }

        /* Placeholder for media loading errors */
        .media-error-placeholder {
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: rgba(255, 0, 79, 0.2);
            /* Light red transparent background */
            color: var(--error-border);
            /* Neon pink text */
            font-weight: bold;
            text-align: center;
            padding: 1rem;
            font-size: 0.9rem;
        }

        /* Overlay for video duration (if applicable) */
        .duration-overlay {
            position: absolute;
            bottom: 0.5rem;
            right: 0.5rem;
            background: rgba(0, 0, 0, 0.6);
            color: white;
            font-size: 0.75rem;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            z-index: 10;
        }


        /* --- Modal Styles --- */
        /* Full screen modal overlay */
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: var(--modal-bg);
            /* Very dark, semi-transparent background */
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 100;
            /* Ensure it's on top */
            opacity: 0;
            /* Hidden by default */
            visibility: hidden;
            transition: opacity 0.3s ease, visibility 0.3s ease;
        }

        /* Styles when the modal is open */
        .modal.is-open {
            opacity: 1;
            visibility: visible;
        }

        /* Container for the modal content */
        .modal-container {
            position: relative;
            background: var(--input-bg);
            /* Dark background */
            border: 3px solid var(--neon-pink);
            /* Pink border */
            /* Intense multi-color glow for the modal */
            box-shadow: 0 0 30px var(--neon-pink), 0 0 60px var(--neon-cyan), 0 0 90px var(--neon-purple), inset 0 0 20px rgba(5, 5, 15, 0.6);
            max-width: 95vw;
            /* Allow slightly larger modal */
            max-height: 95vh;
            /* Allow slightly taller modal */
            display: flex;
            flex-direction: column;
            align-items: center;
            overflow: hidden;
            border-radius: 12px;
            /* Initial transform for bouncy open effect */
            transform: scale(0.95);
            transition: transform 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }

        /* Apply scale 1 when modal is open */
        .modal.is-open .modal-container {
            transform: scale(1);
        }

        /* Area for the actual media content inside the modal */
        .modal-content {
            flex-grow: 1;
            /* Allow content area to grow */
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100%;
            max-height: calc(95vh - 80px);
            /* Max height considering link/close button area */
            overflow: auto;
            /* Add scrollbars if content exceeds max height */
            padding: 1.5rem;
            /* Padding around the media */
            position: relative;
            /* For error placeholder positioning */
        }

        /* Styles for media (img, video) displayed in the modal */
        .modal-content img,
        .modal-content video {
            display: block;
            max-width: 100%;
            /* Ensure media fits within the container */
            max-height: 100%;
            width: auto;
            height: auto;
            object-fit: contain;
            border-radius: 6px;
            box-shadow: 0 0 15px rgba(0, 229, 255, 0.3);
        }

        /* Placeholder for media errors in the modal */
        .modal-content .media-error-placeholder {
            /* Inherits styles from .media-error-placeholder */
        }


        /* Container for the source link below the media in the modal */
        .modal-link-container {
            width: 100%;
            padding: 1rem 1.5rem;
            /* Padding top/bottom and left/right */
            border-top: 2px solid rgba(255, 255, 255, 0.1);
            /* Separator line */
            text-align: center;
            box-shadow: inset 0 10px 15px rgba(0, 0, 0, 0.2);
            /* Inner shadow at the top */
        }

        /* Styling for the source link in the modal */
        .modal-link {
            color: var(--link-color);
            /* Cyan color */
            font-weight: 600;
            text-decoration: none;
            transition: color 0.2s ease, text-shadow 0.2s ease;
            display: block;
            text-shadow: 0 0 5px var(--neon-pink);
        }

        /* Hover/focus styles for the modal link */
        .modal-link:hover,
        .modal-link:focus {
            color: var(--link-hover-color);
            /* Green on hover */
            text-decoration: underline;
            text-shadow: 0 0 8px var(--neon-green);
            outline: none;
        }

        /* Close button for the modal */
        .close-button {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.6);
            color: white;
            border: none;
            border-radius: 50%;
            width: 34px;
            /* Slightly larger */
            height: 34px;
            /* Slightly larger */
            font-size: 1.9rem;
            /* Slightly larger icon */
            line-height: 1;
            cursor: pointer;
            z-index: 110;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: background 0.2s ease, transform 0.2s ease;
            box-shadow: 0 0 8px rgba(0, 0, 0, 0.3);
        }

        /* Hover effect for close button */
        .close-button:hover {
            background: rgba(255, 20, 100, 0.8);
            /* Match error color */
            transform: rotate(90deg) scale(1.1);
        }


        /* --- Error Message Area --- */
        /* Styling for the error message paragraph */
        #errorMessage {
            background: var(--error-bg);
            border: 2px solid var(--error-border);
            box-shadow: 0 0 18px var(--error-border), 0 0 30px var(--neon-pink), inset 0 0 10px var(--neon-pink);
            color: #ffffff;
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.8);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            font-weight: bold;
            word-break: break-word;
            /* Prevent long URLs/messages overflowing */
        }

        /* Ensure error message is displayed when not hidden */
        #errorMessage:not(.hidden) {
            display: block;
        }


        /* --- Skeleton Loaders --- */
        /* Base style for skeleton cards */
        .skeleton-card {
            background: var(--card-bg);
            border: 2px solid #333959;
            border-radius: 10px;
            height: 300px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            animation: pulse 1.5s infinite ease-in-out;
        }

        /* Skeleton media area */
        .skeleton-img {
            height: 200px;
            background-color: #1f253d;
        }

        /* Skeleton info area */
        .skeleton-info {
            flex-grow: 1;
            padding: 0.75rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        /* Skeleton text lines */
        .skeleton-text {
            height: 1em;
            background-color: #1f253d;
            border-radius: 4px;
            margin-bottom: 0.5rem;
            width: 90%;
        }

        /* Skeleton link placeholder */
        .skeleton-link {
            height: 0.8em;
            background-color: #1f253d;
            border-radius: 4px;
            width: 40%;
            margin-top: auto;
        }

        /* Keyframes for the pulsing animation */
        @keyframes pulse {

            0%,
            100% {
                opacity: 1;
            }

            50% {
                opacity: .5;
            }
        }

        /* --- Utility & Responsive --- */
        /* Standard hidden class */
        .hidden {
            display: none !important;
        }

        /* Responsive adjustments for smaller screens */
        @media (max-width: 640px) {

            body {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .search-container,
            #resultsDiv,
            #paginationControls {
                padding-left: 0.5rem;
                padding-right: 0.5rem;
            }

            .modal-content {
                padding: 1rem;
            }

            .modal-link-container {
                padding: 0.75rem 1rem;
            }
        }
    </style>
</head>

<body class="min-h-screen flex flex-col items-center py-6 px-2 sm:px-4">

    <header class="w-full max-w-5xl search-container p-4 sm:p-6 md:p-8 mb-8" role="search" aria-labelledby="search-heading">
        <h1 id="search-heading" class="title-main text-3xl sm:text-4xl font-bold text-center mb-6">
            Neon Search
            <span class="title-sub text-lg block font-normal opacity-80">(Find Videos & GIFs)</span>
        </h1>
        <div
            class="search-controls flex flex-col sm:flex-row items-stretch sm:space-y-4 sm:space-y-0 sm:space-x-3 md:space-x-4 mb-6">
            <div class="input-wrapper mb-4 sm:mb-0">
                <label for="searchInput" class="sr-only">Search Query</label>
                <input id="searchInput" type="text" placeholder="Enter search query..." class="input-neon"
                    autocomplete="off">
                <button type="button" id="clearSearchBtn" class="clear-input-btn" aria-label="Clear search query"
                    title="Clear search">×</button>
            </div>
            <div class="relative mb-4 sm:mb-0">
                <label for="typeSelect" class="sr-only">Search Type</label>
                <select id="typeSelect" aria-label="Select Search Type" class="select-neon w-full sm:w-auto">
                    <option value="videos" selected>Videos</option>
                    <option value="gifs">GIFs</option>
                </select>
            </div>
            <div class="relative mb-4 sm:mb-0">
                <label for="driverSelect" class="sr-only">Search Provider</label>
                <select id="driverSelect" aria-label="Select Search Provider" class="select-neon w-full sm:w-auto">
                    <option value="pornhub">Pornhub</option>
                    <option value="sex">Sex.com</option>
                    <option value="redtube" selected>Redtube</option>
                    <option value="xvideos">XVideos</option>
                    <option value="xhamster">Xhamster</option>
                    <option value="youporn">Youporn</option> <option value="mock">Mock (Test)</option>
                </select>
            </div>
            <button id="searchBtn" type="button"
                class="btn-neon px-6 py-3 font-semibold text-base flex items-center justify-center w-full sm:w-auto"
                aria-controls="resultsDiv" aria-describedby="errorMessage">
                <span id="searchBtnText">Search</span> <span id="loadingIndicator" class="hidden ml-2"
                    aria-hidden="true"><span class="spinner"></span></span>
            </button>
        </div>
        <p id="errorMessage" class="text-white text-center p-3 hidden" role="alert" aria-live="assertive"
            aria-hidden="true"></p>
        <div class="flex justify-center mb-6">
            <button id="toggleFavoritesBtn" type="button"
                class="btn-neon px-6 py-3 font-semibold text-base" aria-controls="resultsDiv favoritesView">
                <span id="toggleFavoritesBtnText">View Favorites</span> <span id="favoritesCount" class="ml-1">(0)</span>
            </button>
        </div>
    </header>

    <main class="w-full max-w-5xl flex-grow">
        <div id="resultsDiv" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 px-2 sm:px-4" aria-live="polite"
            aria-busy="false">
            <p id="initialMessage" class="text-center text-xl col-span-full text-gray-400 py-10"
                style="text-shadow: 0 0 5px var(--neon-cyan);">Enter a query and select options to search...</p>
            </div>

        <div id="favoritesView" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 px-2 sm:px-4 hidden" aria-live="polite" aria-busy="false">
            <p id="noFavoritesMessage" class="text-center text-xl col-span-full text-gray-400 py-10"
                style="text-shadow: 0 0 5px var(--neon-pink);">No favorites added yet.</p>
        </div>

        <nav id="paginationControls"
            class="w-full max-w-5xl mt-8 flex flex-col sm:flex-row justify-center items-center sm:space-x-4 pagination-controls px-2 sm:px-4 hidden"
            role="navigation" aria-label="Pagination">
            <button id="prevBtn" type="button" aria-label="Previous Page"
                class="btn-neon px-4 py-2 text-sm font-semibold w-full sm:w-auto mb-2 sm:mb-0" disabled>< Prev</button>
            <span id="pageIndicator" class="font-semibold text-lg mx-2 sm:mx-4 my-2 sm:my-0"
                style="text-shadow: 0 0 8px var(--neon-cyan);" aria-live="polite">Page 1</span>
            <button id="nextBtn" type="button" aria-label="Next Page"
                class="btn-neon px-4 py-2 text-sm font-semibold w-full sm:w-auto" disabled>Next ></button>
        </nav>
    </main>

    <div id="mediaModal" class="modal" role="dialog" aria-modal="true" aria-hidden="true" tabindex="-1">
        <div class="modal-container">
            <button type="button" id="closeModalBtn" class="close-button" title="Close" aria-label="Close Modal">×</button>
            <div id="modalContent" class="modal-content">
                </div>
            <div id="modalLinkContainer" class="modal-link-container">
                </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/axios@1.7.2/dist/axios.min.js"></script>
    <script>
        'use strict'; // Enforce strict JavaScript rules

        // --- Constants ---
        const API_BASE_URL = '/api/search'; // The endpoint on your backend Node.js server for search requests
        const HOVER_PLAY_DELAY_MS = 200; // Delay in milliseconds before attempting to play video preview on card hover
        const HOVER_PAUSE_DELAY_MS = 100; // Delay in milliseconds before pausing video preview on hover out
        const API_TIMEOUT_MS = 30000; // Timeout for backend API requests in milliseconds (30 seconds)
        const SKELETON_COUNT = 6; // Number of skeleton loaders to display while waiting for results
        // Heuristic for results per page. This helps determine when to enable the "Next" button.
        // It's updated after the first successful search based on the actual number of results received.
        const RESULTS_PER_PAGE_HEURISTIC = 10;
        // A tiny transparent GIF data URI. Used as a fallback placeholder for broken or missing images.
        const PLACEHOLDER_GIF_DATA_URI = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
        // Key used for storing and retrieving favorite items from the browser's localStorage.
        const FAVORITES_STORAGE_KEY = 'neonSearchFavorites';

        // --- DOM Element References ---
        // Get references to all necessary HTML elements using their IDs for easy access in JavaScript.
        const searchInput = document.getElementById('searchInput');
        const clearSearchBtn = document.getElementById('clearSearchBtn');
        const typeSelect = document.getElementById('typeSelect');
        const driverSelect = document.getElementById('driverSelect');
        const searchBtn = document.getElementById('searchBtn');
        const searchBtnText = document.getElementById('searchBtnText');
        const loadingIndicator = document.getElementById('loadingIndicator');
        const resultsDiv = document.getElementById('resultsDiv'); // The div where search result cards are placed.
        const initialMessage = document.getElementById('initialMessage'); // The message shown before any search is performed.
        const errorMessage = document.getElementById('errorMessage'); // The paragraph for displaying error messages to the user.
        const mediaModal = document.getElementById('mediaModal'); // The full-screen modal overlay div.
        const modalContent = document.getElementById('modalContent'); // The div inside the modal where media (video/image) is loaded.
        const modalLinkContainer = document.getElementById('modalLinkContainer'); // The div inside the modal for the source link.
        const closeModalBtn = document.getElementById('closeModalBtn'); // The button to close the modal.
        const paginationControls = document.getElementById('paginationControls'); // The div containing the pagination buttons.
        const prevBtn = document.getElementById('prevBtn'); // The button to go to the previous page.
        const nextBtn = document.getElementById('nextBtn'); // The button to go to the next page.
        const pageIndicator = document.getElementById('pageIndicator'); // The span displaying the current page number.

        // DOM references for the Favorites feature (now enabled).
        const toggleFavoritesBtn = document.getElementById('toggleFavoritesBtn'); // Button to switch between search and favorites view.
        const favoritesCountSpan = document.getElementById('favoritesCount'); // Span to display the number of favorites.
        const favoritesView = document.getElementById('favoritesView'); // The container div for the favorites display.
        const noFavoritesMessage = document.getElementById('noFavoritesMessage'); // Message shown when there are no favorites.


        // --- Application State ---
        // Object to hold the current state of the frontend application. Essential for managing UI based on asynchronous operations and user actions.
        const appState = {
            isLoading: false, // Boolean flag: true if a search is currently in progress.
            currentPage: 1, // The current page number being displayed in the search results.
            currentQuery: '', // The search query used for the current search.
            currentDriver: '', // The selected driver name for the current search.
            currentType: '', // The selected search type ('videos' or 'gifs') for the current search.
            resultsCache: [], // Array to store the results from the last successful API call for the current page. Used for history state and potentially rendering favorites if they point to cached items.
            lastFocusedElement: null, // Stores the DOM element that had focus before the modal was opened. Used to return focus for accessibility.
            // Estimate of results per page. Helps predict if there is a "Next" page. Updated dynamically.
            maxResultsHeuristic: RESULTS_PER_PAGE_HEURISTIC,
            // Timers for controlling the delay before playing/pausing video previews on card hover/focus.
            hoverPlayTimeout: null,
            hoverPauseTimeout: null,
            // AbortController instance to cancel ongoing fetch requests if a new search is initiated. Prevents race conditions and unnecessary network activity.
            currentAbortController: null,
            favorites: [], // Array to store favorited items. Each item should ideally contain enough data to re-render its card and open its modal.
            showingFavorites: false, // Boolean flag: true if the favorites view is currently displayed instead of search results.
        };

        // --- Utility Functions ---

        /**
         * Debounce function to limit how often a function can be called.
         * Useful for events like 'input' or 'resize' to prevent excessive calls.
         * @param {Function} func - The function to debounce.
         * @param {number} delay - The delay in milliseconds.
         * @returns {Function} A new function that, when called, will only execute `func` after `delay` milliseconds have passed since the last call.
         */
        function debounce(func, delay) {
            let timeout;
            return function(...args) {
                const context = this;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), delay);
            };
        }

        // --- Logging Utility (Enhanced) ---
        // Custom console logging functions with colors to make debugging in the browser console more readable and organized.
        const log = {
            info: (message, ...args) => console.info(`%c[FE INFO] ${message}`, 'color: #00ffff; font-weight: bold;', ...args), // Cyan for informational messages.
            warn: (message, ...args) => console.warn(`%c[FE WARN] ${message}`, 'color: #ff8800; font-weight: bold;', ...args), // Orange for warnings.
            error: (message, ...args) => console.error(`%c[FE ERROR] ${message}`, 'color: #ff00ff; font-weight: bold;', ...args), // Pink for errors.
            api: (message, ...args) => console.log(`%c[API REQ] ${message}`, 'color: #39ff14;', ...args), // Green for API request initiation.
            apiSuccess: (message, ...args) => console.log(`%c[API OK] ${message}`, 'color: #39ff14; font-weight: bold;', ...args), // Bold green for successful API responses.
            apiError: (message, ...args) => console.error(`%c[API FAIL] ${message}`, 'color: #ff3333; font-weight: bold;', ...args), // Red for API call failures.
            modal: (message, ...args) => console.log(`%c[MODAL] ${message}`, 'color: #9d00ff;', ...args), // Purple for modal actions (open, close).
            favorites: (message, ...args) => console.log(`%c[FAV] ${message}`, 'color: #ff00aa;', ...args), // Pink for favorites management actions.
        };

        // --- Local Storage Favorites Management ---
        /**
         * Loads favorite items from the browser's local storage when the application starts.
         * Initializes the `appState.favorites` array.
         */
        function loadFavorites() {
            try {
                const storedFavorites = localStorage.getItem(FAVORITES_STORAGE_KEY);
                // Parse the stored JSON string into a JavaScript array. Default to an empty array if nothing is stored.
                appState.favorites = storedFavorites ? JSON.parse(storedFavorites) : [];
                log.favorites(`Loaded ${appState.favorites.length} favorites from localStorage.`);
                updateFavoritesCount(); // Update the favorite count displayed in the UI.
            } catch (e) {
                // Log any errors that occur during loading (e.g., malformed JSON).
                log.error('Failed to load favorites from localStorage:', e);
                appState.favorites = []; // Ensure favorites is an empty array in case of error.
            }
        }

        /**
         * Saves the current `appState.favorites` array to the browser's local storage.
         * Should be called whenever the favorites list is modified.
         */
        function saveFavorites() {
            try {
                // Convert the `appState.favorites` array into a JSON string and store it.
                localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(appState.favorites));
                log.favorites(`Saved ${appState.favorites.length} favorites to localStorage.`);
                updateFavoritesCount(); // Update the favorite count displayed in the UI.
            } catch (e) {
                // Log any errors that occur during saving (e.g., storage limit reached).
                log.error('Failed to save favorites to localStorage:', e);
            }
        }

        /**
         * Checks if a given item exists in the current `appState.favorites` list.
         * Assumes items have a unique identifier, such as a `url` property, for comparison.
         * @param {object} item - The item object to check for existence in favorites.
         * @returns {boolean} Returns `true` if the item is found in the favorites list, `false` otherwise.
         */
        function isFavorite(item) {
            // Use the Array.prototype.some() method to check if at least one element's URL matches the item's URL.
            return appState.favorites.some(fav => fav.url === item.url);
        }

        /**
         * Toggles the favorite status of a given item. If the item is currently favorited, it removes it. If not, it adds it.
         * Calls `saveFavorites` after modifying the list.
         * @param {object} item - The item object to add or remove from favorites.
         */
        function toggleFavorite(item) {
            if (isFavorite(item)) {
                // If the item is already a favorite, filter it out of the favorites array.
                appState.favorites = appState.favorites.filter(fav => fav.url !== item.url);
                log.favorites('Removed item from favorites:', item.title);
            } else {
                // If the item is not a favorite, add it to the favorites array.
                // Create a shallow copy to avoid adding references to potentially temporary card DOM data.
                // Ensure the copied item includes all data needed for display (card and modal).
                const itemCopy = {
                    url: item.url, // Main media URL
                    title: item.title,
                    source: item.source,
                    thumbnail: item.thumbnail, // Thumbnail URL for card preview
                    preview_video: item.preview_video, // Preview video URL for card preview
                    image_hq: item.image_hq, // High quality image URL (fallback for modal or if main URL isn't video)
                    duration: item.duration, // Video duration (if applicable)
                    type: item.type || appState.currentType // Store the original type ('videos' or 'gifs')
                };
                appState.favorites.push(itemCopy);
                log.favorites('Added item to favorites:', item.title);
            }
            saveFavorites(); // Save the updated favorites list to local storage.

            // Update the appearance of the favorite button on the card currently displayed (if it exists).
            // This provides immediate visual feedback.
            const cardElement = document.querySelector(`.card[data-url="${item.url}"]`);
            if (cardElement) {
                const favBtn = cardElement.querySelector('.favorite-btn');
                if (favBtn) {
                    // Toggle the 'is-favorite' class based on the item's new favorite status.
                    favBtn.classList.toggle('is-favorite', isFavorite(item));
                }
            }
            // If the user is currently viewing the favorites list, refresh the display to show the change.
            if (appState.showingFavorites) {
                displayFavorites(); // Re-render favorites to show changes.
            }
        }

        /**
         * Updates the text displaying the current number of favorites.
         */
        function updateFavoritesCount() {
            if (favoritesCountSpan) {
                favoritesCountSpan.textContent = `(${appState.favorites.length})`;
            }
            // Also toggle visibility of the "No favorites added yet" message if in favorites view.
            if (appState.showingFavorites && noFavoritesMessage) {
                 noFavoritesMessage.classList.toggle('hidden', appState.favorites.length > 0);
            }
        }

        /**
         * Switches the display from search results to the favorites list.
         */
        function displayFavorites() {
            // Prevent switching views if a search is currently loading.
            if (appState.isLoading) {
                 log.favorites('Cannot display favorites while loading.');
                 return;
            }
            appState.showingFavorites = true; // Update state flag.
            resultsDiv.classList.add('hidden'); // Hide the search results grid.
            paginationControls.classList.add('hidden'); // Hide the pagination controls.
            favoritesView.classList.remove('hidden'); // Show the favorites view container.
            initialMessage?.classList.add('hidden'); // Hide initial message

            // Render the favorite items into the dedicated favorites grid.
            renderItems(appState.favorites, favoritesView, 'favorites'); // Use 'favorites' override type

            log.favorites('Displaying favorites.');
            // Update the text/state of the toggle favorites button.
            if (toggleFavoritesBtnText) toggleFavoritesBtnText.textContent = 'Back to Search';
            // Update the URL for history state.
            updateURL(true); // Replace current history state with favorites view
            favoritesView.focus(); // Set focus to the favorites view for accessibility
        }

        /**
         * Hides the favorites list and shows search results.
         */
        function hideFavorites() {
            appState.showingFavorites = false; // Update state flag.
            favoritesView.classList.add('hidden'); // Hide the favorites view container.
            resultsDiv.classList.remove('hidden'); // Show the search results grid.

            // Re-render the cached search results if they exist to show the last search state.
            if (appState.resultsCache.length > 0) {
                renderResults(appState.resultsCache); // This will also update pagination buttons.
            } else {
                // If no search results cached (e.g., first load or after clearing search), show the initial message.
                resultsDiv.innerHTML = ''; // Clear the grid.
                initialMessage?.classList.remove('hidden'); // Show the initial introductory message.
                 paginationControls.classList.add('hidden'); // Hide pagination.
            }

            log.favorites('Hiding favorites, returning to search results.');
            // Update the text/state of the toggle favorites button.
            if (toggleFavoritesBtnText) toggleFavoritesBtnText.textContent = `View Favorites`;
            // Update the URL to reflect returning to the search state (use replaceState).
            updateURL(true);
            searchInput.focus(); // Return focus to search input
        }


        // --- API Communication ---
        /**
         * Sends a search request to the backend API using Axios.
         * Handles loading state, request parameters, timeouts, and request cancellation using AbortController.
         * @param {string} query - The search query string.
         * @param {string} driver - The name of the driver (search provider) to use.
         * @param {string} type - The type of content to search for ('videos' or 'gifs').
         * @param {number} page - The page number of results to request.
         * @returns {Promise<{success: boolean, data?: Array<object>, error?: string, isAbort?: boolean}>}
         * A Promise that resolves with an object indicating success/failure and containing data or error details.
         */
        async function fetchResultsFromApi(query, driver, type, page) {
            // If there's an existing AbortController, it means a previous request is pending. Abort it.
            if (appState.currentAbortController) {
                appState.currentAbortController.abort();
                log.api('Previous API request aborted due to new search.');
            }
            // Create a new AbortController instance for this specific request.
            appState.currentAbortController = new AbortController();

            // Define the parameters to be sent as query string in the GET request.
            const params = {
                query,
                driver,
                type,
                page
            };
            log.api(`-> Fetching: ${API_BASE_URL}`, params); // Log the outgoing API request and its parameters.

            try {
                // Use Axios to make the asynchronous HTTP GET request.
                const response = await axios.get(API_BASE_URL, {
                    params, // Attach the search parameters to the request URL.
                    timeout: API_TIMEOUT_MS, // Set the maximum time to wait for a response.
                    signal: appState.currentAbortController.signal, // Link the request to the AbortController's signal, allowing it to be cancelled.
                });

                // If the Promise resolves, the API call was successful (status code 2xx).
                // The response.data property contains the body of the response (expected to be an array of result objects).
                // Ensure data is an array, default to an empty array if the response format is unexpected.
                const data = Array.isArray(response.data) ? response.data : [];
                // Update the heuristic for the number of results per page based on the actual count received.
                // This makes the pagination "Next" button logic more accurate.
                appState.maxResultsHeuristic = data.length > 0 ? data.length : RESULTS_PER_PAGE_HEURISTIC;
                log.apiSuccess(`<- Success (${response.status}): ${data.length} results. Heuristic set to ${appState.maxResultsHeuristic}`);
                // Return an object indicating success and providing the received data.
                return {
                    success: true,
                    data
                };
            } catch (error) {
                // If the Promise rejects, an error occurred during the API call (network error, timeout, server error response).
                // Check if the error was specifically an Axios cancellation error (due to our AbortController).
                if (axios.isCancel(error)) {
                    log.apiError('Request canceled by AbortController.');
                    // Return a specific error object indicating that the request was aborted.
                    return {
                        success: false,
                        error: 'Search operation was canceled.',
                        isAbort: true // Custom property to identify abort errors.
                    };
                }

                // Log other types of API errors for debugging.
                log.apiError('<- API Call Error:', error.message, error.response || error.request || error);
                // Prepare a user-friendly error message based on the type of error received from Axios.
                let userMessage = 'An unexpected error occurred. Please try again.';
                if (error.code === 'ECONNABORTED' || error.message.toLowerCase().includes('timeout')) {
                    // Handle specific timeout errors reported by Axios.
                    userMessage = `API request timed out. The server might be overloaded or down.`;
                } else if (error.response) {
                    // Handle errors where a response was received, but it indicates an error status (e.g., 404, 500).
                    // Try to use an 'error' message from the response data if available, otherwise use the status code.
                    userMessage = `API Error: ${error.response.data?.error || `Server responded with status ${error.response.status}`}.`;
                } else if (error.request) {
                    // Handle errors where the request was sent but no response was received (e.g., network down, server not running).
                    userMessage = 'Network Error: Unable to connect to the API. Check your connection or if the server is running.';
                }
                // Return an object indicating failure and providing the user-friendly error message.
                return {
                    success: false,
                    error: userMessage
                };
            } finally {
                // This block executes regardless of success or failure.
                // Reset the `currentAbortController` state to null as the request is no longer pending.
                appState.currentAbortController = null;
                 // Reset the UI loading state after the fetch operation is complete.
                 setSearchState(false);
            }
        }

        // --- UI Manipulation ---
        /**
         * Displays a specific error message in the designated error message area (`#errorMessage`).
         * Makes the error message visible and sets its text content.
         * @param {string} message - The error message text to display.
         */
        function showError(message) {
            errorMessage.textContent = message; // Set the text content of the error element.
            errorMessage.classList.remove('hidden'); // Remove the 'hidden' class to make it visible.
            errorMessage.setAttribute('aria-hidden', 'false'); // Update ARIA attribute for accessibility (screen readers).
            log.error('Error Displayed:', message); // Log the error message to the console.
            // Hide the initial message or results area when an error is displayed for clarity.
             initialMessage?.classList.add('hidden');
             // You might also want to clear the results grid here if it's not already cleared by renderResults([]).
             // resultsDiv.innerHTML = '';
        }

        /**
         * Hides the error message area (`#errorMessage`).
         */
        function hideError() {
            // Check if the error message is currently visible before attempting to hide it.
            if (!errorMessage.classList.contains('hidden')) {
                errorMessage.classList.add('hidden'); // Add the 'hidden' class to hide it.
                errorMessage.setAttribute('aria-hidden', 'true'); // Update ARIA attribute.
                errorMessage.textContent = ''; // Clear the text content.
            }
        }

        /**
         * Displays a placeholder message for media loading errors within a given container element.
         * This is used in both the card media container and the modal content area.
         * @param {HTMLElement} container - The DOM element where the error placeholder should be placed.
         * @param {string} message - The specific error message text to display in the placeholder.
         */
        function renderMediaErrorPlaceholder(container, message) {
            container.innerHTML = ''; // Clear any existing content within the container (e.g., a broken image or video).
            const errorDiv = document.createElement('div');
            errorDiv.className = 'media-error-placeholder absolute inset-0'; // Apply CSS styles for the placeholder, positioning it absolutely to cover the container.
            errorDiv.textContent = message; // Set the error message text.
            container.appendChild(errorDiv); // Add the placeholder element to the container.
            log.warn('Media placeholder shown:', message); // Log that a placeholder was displayed.
        }


        /**
         * Clears current results from the display and shows skeleton loading placeholders.
         * @param {number} [count=SKELETON_COUNT] - The number of skeleton loaders to display. Defaults to SKELETON_COUNT.
         */
        function showSkeletons(count = SKELETON_COUNT) {
            resultsDiv.innerHTML = ''; // Clear existing content in the results grid.
            initialMessage?.classList.add('hidden'); // Hide the initial message if it's there.
            favoritesView.classList.add('hidden'); // Hide favorites view when showing search skeletons.
            resultsDiv.classList.remove('hidden'); // Ensure the results grid is visible.

            resultsDiv.setAttribute('aria-busy', 'true'); // Indicate that the results area is busy (for accessibility).
            resultsDiv.removeAttribute('aria-live'); // Temporarily remove polite live region to avoid screen readers announcing skeletons being added.

            // Add a small delay before showing skeletons. This prevents a quick flicker
            // if the API response is very fast, making the transition smoother.
            setTimeout(() => {
                // Only show skeletons if the application is still in a loading state after the delay.
                if (appState.isLoading) {
                    const fragment = document.createDocumentFragment(); // Use a DocumentFragment for efficient appending.
                    for (let i = 0; i < count; i++) {
                        const skeleton = document.createElement('div');
                        skeleton.className = 'skeleton-card'; // Apply skeleton card styling.
                        skeleton.setAttribute('aria-hidden', 'true'); // Hide skeleton elements from screen readers.
                        // Inner HTML for the skeleton structure (placeholder blocks for image and text).
                        skeleton.innerHTML =
                            `<div class="skeleton-img"></div><div class="skeleton-info"><div class="skeleton-text"></div><div class="skeleton-link"></div></div>`;
                        fragment.appendChild(skeleton); // Add the skeleton card to the fragment.
                    }
                    resultsDiv.appendChild(fragment); // Append all skeleton cards to the DOM grid at once.
                    log.info(`Showing ${count} skeletons.`); // Log the number of skeletons shown.
                }
            }, 100); // 100 milliseconds delay.


            // Hide pagination controls while the content is loading.
            paginationControls.classList.add('hidden');
        }

        /**
         * Sets the overall UI state based on whether the application is currently loading data.
         * Disables input fields and buttons, and toggles the loading indicator.
         * @param {boolean} loading - True if the application is in a loading state, false otherwise.
         */
        function setSearchState(loading) {
            appState.isLoading = loading; // Update the application's loading state flag.
            // Disable or enable the search input, type/driver selects, and search button based on the loading state.
            [searchInput, typeSelect, driverSelect, searchBtn].forEach(el => el.disabled = loading);
            resultsDiv.setAttribute('aria-busy', String(loading)); // Update ARIA busy status on the results area.

            // Disable pagination buttons while loading data.
            prevBtn.disabled = true;
            nextBtn.disabled = true;
            // Disable the favorites toggle button while loading.
            if (toggleFavoritesBtn) toggleFavoritesBtn.disabled = loading;


            // Toggle the visibility of the search button text and the loading spinner.
            if (loading) {
                searchBtnText.style.display = 'none'; // Hide the "Search" text.
                loadingIndicator.classList.remove('hidden'); // Show the loading spinner.
                showSkeletons(); // Display skeleton loaders immediately when loading starts.
            } else {
                searchBtnText.style.display = 'inline'; // Show the "Search" text.
                loadingIndicator.classList.add('hidden'); // Hide the loading spinner.
                // Skeleton loaders are cleared when results are rendered or an error message is shown.
                 resultsDiv.setAttribute('aria-live', 'polite'); // Restore polite live region once loading is finished.
            }
        }

        /**
         * Updates the state (enabled/disabled status) of the pagination buttons.
         * Also updates the current page indicator text.
         */
        function updatePaginationButtons() {
            // Pagination controls are only relevant and visible in the search results view when not loading.
            if (appState.showingFavorites || appState.isLoading) {
                paginationControls.classList.add('hidden'); // Hide pagination controls if showing favorites or loading.
                return; // Exit the function.
            }

            // Determine if pagination controls should be shown at all based on whether results exist or we are on a page > 1.
            const hasResults = appState.resultsCache.length > 0 || appState.currentPage > 1;
            // Estimate if there is a next page based on whether we received the maximum expected number of results.
            const hasNextPage = appState.resultsCache.length === appState.maxResultsHeuristic && appState.maxResultsHeuristic > 0; // Also ensure heuristic is positive


            if (!hasResults) {
                paginationControls.classList.add('hidden'); // Hide pagination if there are no results and we're on the first page.
                return; // Exit the function.
            }


            // If there are results, show the pagination controls and set button disabled states.
            paginationControls.classList.remove('hidden'); // Make pagination controls visible.
            prevBtn.disabled = appState.currentPage <= 1; // Disable "Prev" button if on the first page (page 1 or less).
            nextBtn.disabled = !hasNextPage; // Disable "Next" button if we don't expect a next page based on the heuristic.

            // Update the text displaying the current page number.
            pageIndicator.textContent = `Page ${appState.currentPage}`;
            // Update the ARIA label for the page indicator for screen readers.
            pageIndicator.setAttribute('aria-label', `Current page, Page ${appState.currentPage}`);
        }

        /**
         * Creates the media container for a search result card. This container holds the thumbnail and the animated preview.
         * It intelligently decides whether to use a <video> tag (for WebM/MP4 previews) or an <img> tag (for direct GIF previews).
         * Handles loading errors and displays a placeholder if media cannot be loaded.
         * @param {object} item - The result item object from the API response. Expected to have `thumbnail`, `preview_video`, `title`, `duration`, `type`.
         * @param {string} [itemRenderTypeOverride=null] - Optional override for the item's type (e.g., if rendering a favorite item where type might be stored).
         * @returns {HTMLElement} The created `div` element with class `card-media-container`, containing the appropriate media elements.
         */
        function createMediaContainer(item, itemRenderTypeOverride = null) {
            // Create the main container div.
            const mediaContainer = document.createElement('div');
            mediaContainer.className = 'card-media-container';
            // Determine the item type to use for display logic. Prioritize the override, then the type from the item data, then the app's current search type.
            const typeForDisplay = itemRenderTypeOverride || item.type || appState.currentType;
            // Generate an ARIA label for accessibility, using the item title or a default based on type.
            const itemTitleForAria = item.title || (typeForDisplay === 'gifs' ? 'GIF Preview' : 'Video Preview');
            mediaContainer.setAttribute('role', 'figure'); // Semantic role for content that is referenced from the main flow.
            mediaContainer.setAttribute('aria-label', itemTitleForAria); // Provide a descriptive label for screen readers.

            let hasVisualMediaElement = false; // Flag to track if we successfully added a visual media element (img or video).
            // The URL for the animated preview in the card. Expected to be WebM/MP4 or a direct .gif.
            const animatedPreviewUrl = item.preview_video;
            // The URL for the static image thumbnail (used as a poster for videos or default image).
            const staticThumbnailUrl = item.thumbnail;

            // 1. Add static thumbnail (poster) if available and not the empty placeholder URI.
            // This image is usually visible by default behind the animated preview.
            if (staticThumbnailUrl && staticThumbnailUrl !== PLACEHOLDER_GIF_DATA_URI) {
                const img = document.createElement('img');
                img.src = staticThumbnailUrl;
                img.alt = ''; // Keep alt text empty as it's primarily decorative; the container has the ARIA label.
                img.loading = 'lazy'; // Use lazy loading to improve initial page load performance.
                img.className = 'static-thumb'; // Apply CSS class for styling (absolute positioning, layering).
                // Add an error handler for the static thumbnail. If it fails to load:
                img.onerror = () => {
                    log.warn(`Static thumbnail load failed: ${staticThumbnailUrl} for "${item.title}".`);
                    img.remove(); // Remove the broken image element from the DOM.
                    // If no animated preview is successfully added later, show a media error placeholder.
                    if (!mediaContainer.querySelector('.preview-video, .preview-gif-image')) {
                        renderMediaErrorPlaceholder(mediaContainer, 'Thumbnail Error');
                    }
                };
                mediaContainer.appendChild(img); // Add the image to the container.
                hasVisualMediaElement = true; // Mark that we successfully added at least the static thumbnail.
            } else {
                 // If no static thumbnail URL is provided, add a generic dark background placeholder div.
                 // This prevents the media container from being empty and ensures a consistent size/look.
                 const placeholderDiv = document.createElement('div');
                 placeholderDiv.className = 'absolute inset-0 bg-gray-800'; // Tailwind class for absolute positioning and dark gray background.
                 mediaContainer.appendChild(placeholderDiv);
                 // While not "media", it fills the space visually, so we can consider it a fallback element present.
                 // We still need to check if animated media loads successfully.
            }


            // 2. Add animated preview (video or GIF) if an `animatedPreviewUrl` is provided.
            if (animatedPreviewUrl) {
                // Determine if the animated preview URL points to a direct GIF image file based on extension and type.
                // Some video drivers might provide WebM/MP4 previews for GIFs, while GIF-specific drivers might provide direct .gif.
                const isDirectGif = typeForDisplay === 'gifs' && animatedPreviewUrl.toLowerCase().endsWith('.gif');

                if (isDirectGif) {
                    // If it's a direct GIF, create an <img> tag. Direct images animate automatically once loaded.
                    const gifImg = document.createElement('img');
                    gifImg.src = animatedPreviewUrl;
                    gifImg.alt = `Animated GIF Preview: ${item.title || 'GIF'}`; // Alt text for the animated GIF.
                    gifImg.loading = 'lazy'; // Lazy load the GIF, as they can be large.
                    // Apply the 'preview-gif-image' class. This class should have CSS for absolute positioning,
                    // opacity transition (to fade in on hover/focus), and z-index to layer above the static thumb.
                    gifImg.className = 'preview-gif-image';
                    // Add an error handler for the GIF image. If it fails to load:
                    gifImg.onerror = () => {
                        log.warn(`Direct GIF image load failed: ${animatedPreviewUrl} for "${item.title}".`);
                        gifImg.remove(); // Remove the broken image element.
                        // If the static thumbnail also failed or wasn't present, show a media error placeholder.
                        if (!mediaContainer.querySelector('img.static-thumb')) {
                            renderMediaErrorPlaceholder(mediaContainer, 'GIF Load Error');
                        }
                    };
                    mediaContainer.appendChild(gifImg); // Add the GIF image to the container.
                } else {
                    // If it's not a direct GIF (assumed to be a video preview, like WebM/MP4), create a <video> tag.
                    const video = document.createElement('video');
                    video.src = animatedPreviewUrl; // Set the video source URL.
                    // Use the static thumbnail URL as the poster attribute for the video.
                    if (staticThumbnailUrl && staticThumbnailUrl !== PLACEHOLDER_GIF_DATA_URI) {
                        video.poster = staticThumbnailUrl;
                    }
                    video.muted = true; // Mute previews so they can autoplay without disturbing the user with sound.
                    video.loop = true; // Loop the video preview continuously while hovered/focused.
                    video.playsInline = true; // Important attribute for autoplay on many mobile browsers.
                    video.preload = 'metadata'; // Only preload metadata (duration, dimensions) initially, not the whole video file.
                    // Apply the 'preview-video' class. This class should have CSS for absolute positioning,
                    // opacity transition, and z-index. It's also targeted by the JS hover play/pause logic.
                    video.className = 'preview-video';
                    // Add an error handler for the video element. If it fails to load:
                    video.onerror = (e) => {
                        log.warn(`Animated preview <video> load failed: ${animatedPreviewUrl} for "${item.title}".`, e);
                        video.remove(); // Remove the broken video element.
                        // If the static thumbnail also failed or wasn't present, show a media error placeholder.
                        if (!mediaContainer.querySelector('img.static-thumb')) {
                            renderMediaErrorPlaceholder(mediaContainer, 'Preview Error');
                        }
                    };
                    mediaContainer.appendChild(video); // Add the video element to the container.

                    // Note: The JavaScript event listeners for hover/focus play/pause will be attached to the card element later
                    // in the `createCardElement` function. These listeners will find and control elements with the '.preview-video' class.
                }
                hasVisualMediaElement = true; // Mark that we successfully added an animated preview element.
            }

            // Add a duration overlay for videos if a duration property is provided in the item data.
            // This overlay is typically shown for video results.
            // Check if item.duration property exists and is not an empty string or "00:00".
            if (typeForDisplay === 'videos' && item.duration && item.duration !== '00:00') {
                const durationOverlay = document.createElement('span');
                durationOverlay.className = 'duration-overlay'; // Apply CSS class for styling and positioning.
                durationOverlay.textContent = item.duration; // Set the text content (assuming duration is already formatted).
                mediaContainer.appendChild(durationOverlay); // Add the duration overlay to the container.
            }

            // Final check: if, after attempting to add the static thumbnail and animated preview,
            // there are still no visual media elements inside the container, display a generic error placeholder.
            if (!mediaContainer.querySelector('img.static-thumb, .preview-video, .preview-gif-image')) {
                renderMediaErrorPlaceholder(mediaContainer, `No Media Available`); // Display the placeholder.
                log.warn(`No visible media elements created for item:`, item); // Log a warning.
            }


            return mediaContainer; // Return the fully constructed media container element.
        }


        /**
         * Creates a single DOM element for a search result or favorite item card.
         * This function assembles the media container, title, source link, and favorite button.
         * Attaches event listeners for hover/focus preview playback and click to open the modal.
         * @param {object} item - The result item object containing data like `url`, `title`, `thumbnail`, `preview_video`, etc.
         * @param {string} [itemRenderTypeOverride=null] - Optional override for the item's type (used when rendering favorites).
         * @returns {HTMLElement} The created `div` element with class `card` representing a single result card.
         */
        function createCardElement(item, itemRenderTypeOverride = null) {
            // Create the main card container div.
            const card = document.createElement('div');
            card.className = 'card'; // Apply CSS card styling.
            card.setAttribute('tabindex', '0'); // Make the card focusable using the keyboard (allows focus/blur events and improves accessibility).
            card.setAttribute('role', 'article'); // Assign a semantic role for accessibility.
            // Store essential result data as `data-*` attributes on the card element. This makes the data easily accessible later (e.g., when clicking to open the modal).
            // Avoid storing the entire potentially large item object if possible.
            card.dataset.url = item.url; // Main media URL.
            card.dataset.title = item.title; // Item title.
            card.dataset.source = item.source; // Source website name.
            card.dataset.previewUrl = item.preview_video; // Store the preview URL.
            card.dataset.thumbnailUrl = item.thumbnail; // Store the thumbnail URL.
            card.dataset.type = itemRenderTypeOverride || item.type || appState.currentType; // Store the type of the item for correct handling.

            // Create and append the media container using the dedicated function `createMediaContainer`.
            const mediaContainer = createMediaContainer(item, card.dataset.type); // Pass the determined type to the media container function.
            card.appendChild(mediaContainer);

            // Create the info container div for the title and source link.
            const infoContainer = document.createElement('div');
            infoContainer.className = 'card-info'; // Apply CSS info container styling.

            // Create the title element (h3).
            const title = document.createElement('h3');
            title.className = 'card-title'; // Apply CSS title styling.
            title.textContent = item.title || 'Untitled Result'; // Set the text content, using a default if title is missing.
            title.setAttribute('title', item.title || 'Untitled Result'); // Add a title attribute so the full title is shown on hover/focus.

            infoContainer.appendChild(title); // Add the title to the info container.

            // Create the source link element (<a>).
            const sourceLink = document.createElement('a');
            sourceLink.className = 'card-link'; // Apply CSS link styling.
            sourceLink.href = item.url || '#'; // Set the link URL to the item's main URL, falling back to '#' if missing.
            sourceLink.textContent = item.source || 'View Source'; // Set the link text, using the source name or a default.
            sourceLink.target = '_blank'; // Open the link in a new browser tab.
            sourceLink.rel = 'noopener noreferrer'; // Security best practice when using target="_blank".
            // Stop the click event on the link from propagating up to the card's click handler (which opens the modal).
            sourceLink.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent the event from bubbling up to the card.
            });

            infoContainer.appendChild(sourceLink); // Add the source link to the info container.

            // Assemble the card by adding the info container below the media container.
            card.appendChild(infoContainer);

            // --- Add Favorite Button ---
            const favoriteBtn = document.createElement('button');
            favoriteBtn.className = 'favorite-btn'; // Apply CSS styling for the favorite button.
            favoriteBtn.setAttribute('aria-label', 'Toggle Favorite'); // ARIA label for accessibility.
            favoriteBtn.innerHTML = '&#9733;'; // Set the button content to a star icon (Unicode character).
            // Set the initial state of the favorite button based on whether the item is currently a favorite.
            if (isFavorite(item)) {
                favoriteBtn.classList.add('is-favorite'); // Add the 'is-favorite' class for styling if it's a favorite.
            }
            // Add a click listener to the favorite button to toggle the item's favorite status.
            favoriteBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // Stop the click event from propagating to the card and opening the modal.
                toggleFavorite(item); // Call the function to toggle the item's favorite status.
            });
            card.appendChild(favoriteBtn); // Add the favorite button to the card.


            // --- Add Hover/Focus Play/Pause Logic for Video Previews ---
            // Find the video element specifically used for the preview within this card's media container.
            // This element has the class 'preview-video'.
            const previewVideoElement = mediaContainer.querySelector('video.preview-video');

            // Attach event listeners ONLY if a video preview element was successfully created in createMediaContainer.
            // Direct GIF images ('preview-gif-image') do not need this JS logic for playback control as they animate automatically via CSS/browser.
            if (previewVideoElement) {
                // Add event listener for mouse entering the media container area.
                mediaContainer.addEventListener('mouseenter', () => {
                    clearTimeout(appState.hoverPauseTimeout); // Clear any pending pause timeout.
                    // Check if the video element has loaded enough data to potentially play.
                    // readyState > 0 means metadata is available. networkState === NETWORK_IDLE means it has a source but hasn't loaded yet.
                    if (previewVideoElement.readyState > 0 || previewVideoElement.networkState === HTMLMediaElement.NETWORK_IDLE) {
                        // Set a timeout before attempting to play. This prevents accidental plays on quick mouse movements.
                        appState.hoverPlayTimeout = setTimeout(() => {
                            previewVideoElement.play().catch(e => {
                                // Catch and log potential errors if play() fails (e.g., browser blocking autoplay, no user gesture).
                                if (e.name !== 'AbortError') { // Ignore AbortErrors which happen when play() is cancelled
                                    log.warn('Video play prevented (hover):', e);
                                }
                            });
                        }, HOVER_PLAY_DELAY_MS);
                    }
                });

                // Add event listener for mouse leaving the media container area.
                mediaContainer.addEventListener('mouseleave', () => {
                    clearTimeout(appState.hoverPlayTimeout); // Clear any pending play timeout.
                    // Only attempt to pause if the video is currently playing or paused (not ended or in an error state).
                    if (!previewVideoElement.paused && !previewVideoElement.ended) {
                         // Set a timeout before pausing. This gives a small buffer to prevent pausing immediately if the mouse briefly leaves.
                        appState.hoverPauseTimeout = setTimeout(() => {
                            previewVideoElement.pause(); // Pause the video playback.
                        }, HOVER_PAUSE_DELAY_MS);
                    }
                });

                // Also handle keyboard focus events for accessibility.
                // When the card gains focus (e.g., via Tab key), attempt to play the preview video.
                card.addEventListener('focus', () => {
                    // Use a small delay to allow the browser's focus event loop to settle.
                    // Check if the card itself or something inside the media container gained focus (but not the source link or favorite button directly).
                    setTimeout(() => {
                        const active = document.activeElement;
                        if (active === card || mediaContainer.contains(active)) {
                             clearTimeout(appState.hoverPauseTimeout); // Clear any pending pause.
                              if (previewVideoElement.readyState > 0 || previewVideoElement.networkState === HTMLMediaElement.NETWORK_IDLE) {
                                  appState.hoverPlayTimeout = setTimeout(() => {
                                      previewVideoElement.play().catch(e => {
                                           if (e.name !== 'AbortError') {
                                               log.warn('Video play prevented (focus):', e);
                                           }
                                      });
                                  }, HOVER_PLAY_DELAY_MS);
                              }
                        }
                    }, 10); // 10ms delay.
                });

                // When focus leaves the card (e.g., via Tab key), pause the preview video.
                card.addEventListener('blur', () => {
                    // Use a small delay to allow the browser's focus change to register.
                    setTimeout(() => {
                        // Check if the element that now has focus is outside of the current card.
                        if (!card.contains(document.activeElement)) {
                            clearTimeout(appState.hoverPlayTimeout); // Clear any pending play.
                             if (!previewVideoElement.paused && !previewVideoElement.ended) {
                                  appState.hoverPauseTimeout = setTimeout(() => {
                                      previewVideoElement.pause(); // Pause the video.
                                  }, HOVER_PAUSE_DELAY_MS);
                             }
                        }
                    }, 10); // 10ms delay.
                });
            }
             // Direct GIF images (`.preview-gif-image`) are not handled by this JS block as they animate based on their `src` attribute once visible (controlled by CSS opacity).


            // --- Add Click Listener to the Card to Open the Modal ---
            // Add a click listener to the entire card element.
            card.addEventListener('click', () => {
                // When the card is clicked, check if the item has a valid URL for displaying the full media in the modal.
                // Use the main `item.url` as the primary source, or `item.image_hq` as a fallback for high-quality images.
                 if (item.url || item.image_hq) { // Check if item has a main URL or high-quality image URL
                     // If a valid URL exists, call the `openModal` function.
                     // Pass the original item data and the card element that was clicked (for returning focus when the modal closes).
                     openModal(item, card);
                 } else {
                     // If no valid URL is available for the modal, log a warning.
                     log.warn('Card click ignored: No valid media URL available for modal.', item);
                     // Optionally display a temporary message to the user indicating media is not available.
                 }
            });


            return card; // Return the fully constructed card element.
        }

        /**
         * Renders an array of items (either search results or favorite items) into a specified container element.
         * Clears the container before adding the new items.
         * Displays a "No results" or "No favorites" message if the items array is empty.
         * @param {Array<object>} items - An array of item objects to render.
         * @param {HTMLElement} container - The DOM element (e.g., `resultsDiv` or `favoritesGrid`) where the cards should be rendered.
         * @param {string} [itemRenderTypeOverride=null] - Optional override for the item's type when creating cards (e.g., 'favorites' to influence rendering logic).
         */
        function renderItems(items, container, itemRenderTypeOverride = null) {
            container.innerHTML = ''; // Clear any existing content within the container (previous results, skeletons, messages).
            // Hide initial messages for both results and favorites views if they are visible.
            if (container === resultsDiv && initialMessage) initialMessage.classList.add('hidden');
            if (container === favoritesView && noFavoritesMessage) noFavoritesMessage.classList.add('hidden');


            if (!items || items.length === 0) {
                // If the items array is empty or null, display a message indicating no results or no favorites.
                // Determine the appropriate message based on the container element.
                const message = container === resultsDiv ?
                                'No results found for your query.' : // Message for search results grid.
                                'No favorites added yet.'; // Message for favorites grid.

                const messageElement = document.createElement('p'); // Create a paragraph element for the message.
                messageElement.className = 'text-center text-xl col-span-full text-gray-400 py-10'; // Apply styling for centering and appearance.
                // Set text shadow color based on the container (optional theming touch).
                messageElement.style.textShadow = `0 0 5px ${container === resultsDiv ? 'var(--neon-purple)' : 'var(--neon-pink)'}`;
                messageElement.textContent = message; // Set the text content of the message.
                container.appendChild(messageElement); // Add the message element to the container.
                log.info(`No items to render in ${container.id}. Displaying "${message}".`); // Log that no items were rendered.
            } else {
                // If there are items in the array, create a card for each item and add them to the container.
                const fragment = document.createDocumentFragment(); // Use a DocumentFragment for efficient DOM manipulation.
                items.forEach(item => {
                    // Create a card element for the current item using the `createCardElement` function.
                    // Pass the override type if provided, otherwise the createCardElement function will determine it.
                    const card = createCardElement(item, itemRenderTypeOverride);
                    fragment.appendChild(card); // Add the created card to the fragment.
                });
                container.appendChild(fragment); // Append all created cards to the DOM grid at once.
                log.info(`Rendered ${items.length} items in ${container.id}.`); // Log the number of items rendered.
            }
            // Update pagination buttons only if the rendered container is the results grid.
            if (container === resultsDiv) {
                updatePaginationButtons(); // Update the state of pagination buttons based on the rendered results.
                resultsDiv.setAttribute('aria-busy', 'false'); // Indicate that the results area is no longer busy.
            }
            // If rendering favorites grid, mark it as not busy.
            if (container === favoritesView) {
                favoritesView.setAttribute('aria-busy', 'false');
            }
        }


        /**
         * Renders the search results into the `resultsDiv`.
         * This is a wrapper function specifically for rendering search results after an API call.
         * @param {Array<object>} results - An array of search result objects from the API.
         */
        function renderResults(results) {
            // Call the generic `renderItems` function, specifying `resultsDiv` as the container and using the current search type.
            renderItems(results, resultsDiv, appState.currentType);
        }

        /**
         * Renders the favorites list into the `favoritesView`.
         * This is a wrapper function specifically for rendering favorite items.
         */
        function renderFavorites() {
             // Call the generic `renderItems` function, specifying `favoritesView` as the container.
             // When rendering favorites, we assume each favorite item object itself contains enough data
             // to determine its type ('videos' or 'gifs') within `createCardElement`.
             renderItems(appState.favorites, favoritesView, 'favorites'); // Pass 'favorites' as override
        }


        // --- Modal Handling ---
        /**
         * Opens the full media modal and loads the content (video or image) based on the item data.
         * Handles deciding whether to display a video player or an image tag in the modal.
         * @param {object} item - The item object containing data for the full media display (expected to have `url` or `image_hq`).
         * @param {HTMLElement} triggerElement - The DOM element (typically the card) that triggered the modal opening. Used to return focus when the modal closes for accessibility.
         */
        function openModal(item, triggerElement) {
            log.modal('Opening modal for:', item); // Log that the modal is being opened and for which item.
            hideError(); // Hide any active error message when the modal opens, as it's a new context.

            // Clear any previous content from the modal's media and link containers.
            modalContent.innerHTML = '';
            modalLinkContainer.innerHTML = '';

            let mediaElement; // Variable to hold the created media element (<video> or <img>).
            // Determine the primary URL for the full media in the modal. Prefer `item.url`, fall back to `item.image_hq`.
            const mainMediaUrl = item.url || item.image_hq;
            // Get the item type from the item data or the app's current search type as a fallback.
            const itemType = item.type || appState.currentType;

            // Proceed only if a main media URL is available.
            if (mainMediaUrl) {
                // Decide whether to use a <video> tag or an <img> tag for the modal content.
                // Check if the item type is explicitly 'videos' or if the URL has common video file extensions,
                // while explicitly checking it's NOT a direct '.gif' extension. This handles cases where video drivers might use WebM/MP4 for GIF previews.
                const isVideo = (itemType === 'videos' && !mainMediaUrl.toLowerCase().endsWith('.gif')) ||
                    (/\.(mp4|webm|ogv|mov|avi|flv|wmv|mkv)$/i.test(mainMediaUrl) && !mainMediaUrl.toLowerCase().endsWith('.gif')); // Basic video extension check excluding .gif

                if (isVideo) {
                    // If it's a video URL, create a <video> element.
                    mediaElement = document.createElement('video');
                    mediaElement.controls = true; // Add the browser's native video controls (play, pause, volume, seek, fullscreen).
                    mediaElement.autoplay = true; // Attempt to autoplay the video when the modal opens.
                    mediaElement.loop = false; // Ensure the main video in the modal does not loop.
                    mediaElement.playsInline = true; // Important attribute for autoplay on many mobile browsers.

                    const source = document.createElement('source'); // Create a <source> element for the video URL.
                    source.src = mainMediaUrl; // Set the source URL.
                    // Attempt to set the MIME type based on the file extension for better browser compatibility.
                    if (/\.mp4$/i.test(mainMediaUrl)) source.type = 'video/mp4';
                    else if (/\.webm$/i.test(mainMediaUrl)) source.type = 'video/webm';
                    else if (/\.ogv$/i.test(mainMediaUrl)) source.type = 'video/ogv';
                    // Add other potential video types if needed.
                    else source.type = 'video/mp4'; // Default assumption if extension is unknown.

                    mediaElement.appendChild(source); // Add the source element to the video element.

                    // Add an error handler for the video element. If it fails to load:
                    mediaElement.onerror = (e) => {
                        log.error('Failed to load video in modal:', mainMediaUrl, e); // Log the error.
                        // Display a media error placeholder within the modal content area.
                        renderMediaErrorPlaceholder(modalContent, 'Failed to load video.');
                    };

                } else {
                    // If it's not a video URL (assumed to be a direct image, potentially a GIF), create an <img> tag.
                    mediaElement = document.createElement('img');
                    mediaElement.alt = `Full Media: ${item.title || 'Result'}`; // Set descriptive alt text for accessibility.
                    // Add basic styling to ensure the image fits within the modal content area.
                    mediaElement.style.maxWidth = '100%';
                    mediaElement.style.maxHeight = '100%';
                    mediaElement.style.objectFit = 'contain'; // Ensure the image is contained within the bounds.

                    // Add an error handler for the image element. If it fails to load:
                    mediaElement.onerror = () => {
                        log.error('Failed to load image in modal:', mainMediaUrl); // Log the error.
                        // Display a media error placeholder within the modal content area.
                        renderMediaErrorPlaceholder(modalContent, 'Failed to load image.');
                    };
                    mediaElement.src = mainMediaUrl; // Set the image source URL.
                }
            } else {
                // If no main media URL is available in the item data, log an error and display a placeholder.
                log.error('Attempted to open modal without a main media URL:', item);
                renderMediaErrorPlaceholder(modalContent, 'Media Not Available');
            }


            // If a media element (<video> or <img>) was successfully created, add it to the modal content area.
            if (mediaElement) {
                modalContent.appendChild(mediaElement);
            }


            // Add the source link below the media in the modal. Use `item.url` for the link if available.
            if (item.url) {
                const modalLink = document.createElement('a'); // Create an anchor element for the link.
                modalLink.className = 'modal-link'; // Apply CSS styling for the modal link.
                modalLink.href = item.url; // Set the link's destination URL to the item's main URL.
                modalLink.textContent = `View on ${item.source || 'Source Website'}`; // Set the link text, using the source name or a default.
                modalLink.target = '_blank'; // Open the link in a new tab.
                modalLink.rel = 'noopener noreferrer'; // Security best practice.
                modalLinkContainer.appendChild(modalLink); // Add the link to the modal link container.
            }


            // --- Display the Modal and Manage Focus/Accessibility ---
            mediaModal.classList.add('is-open'); // Add the 'is-open' class to the modal overlay to make it visible (CSS handles display/opacity).
            mediaModal.setAttribute('aria-hidden', 'false'); // Update ARIA attribute to indicate the modal is now visible to screen readers.
            appState.lastFocusedElement = triggerElement; // Store the element that had focus before the modal opened. This is typically the card that was clicked.
            closeModalBtn.focus(); // Programmatically move focus to the close button when the modal opens. This is a common accessibility pattern for modals.

            // Add event listener to close the modal if the user clicks outside the modal container (on the dark overlay).
            // Use a small setTimeout to ensure the click event that *opened* the modal finishes propagating before adding this listener.
            setTimeout(() => {
                mediaModal.addEventListener('click', closeModalOnOutsideClick);
            }, 0);

            // Add a keyboard listener to the document to handle modal interactions, such as closing with the Escape key and potentially focus trapping.
            document.addEventListener('keydown', handleModalKeyPress);
        }

        /**
         * Closes the full media modal and cleans up its content and state.
         */
        function closeModal() {
            log.modal('Closing modal.'); // Log that the modal is being closed.
            // If a video is playing in the modal, pause it and reset its source to stop playback and free up resources.
            const modalVideo = modalContent.querySelector('video');
            if (modalVideo) {
                modalVideo.pause(); // Pause playback.
                // Remove the source(s) and reload the video element. This is a robust way to stop loading/buffering.
                modalVideo.removeAttribute('src');
                const sources = modalVideo.querySelectorAll('source');
                sources.forEach(source => source.remove()); // Remove all source elements.
                modalVideo.load(); // Reset the video element.
            }
            // Clear the HTML content of the modal's media and link containers.
            modalContent.innerHTML = '';
            modalLinkContainer.innerHTML = '';

            // Hide the modal overlay.
            mediaModal.classList.remove('is-open'); // Remove the 'is-open' class (CSS handles opacity/visibility).
            mediaModal.setAttribute('aria-hidden', 'true'); // Update ARIA attribute to indicate the modal is hidden.

            // Return focus to the element that had focus before the modal was opened, for better accessibility.
            if (appState.lastFocusedElement) {
                appState.lastFocusedElement.focus();
                appState.lastFocusedElement = null; // Clear the stored element.
            }

            // Remove event listeners that were specific to the modal being open.
            mediaModal.removeEventListener('click', closeModalOnOutsideClick); // Remove listener for clicking outside the modal.
            document.removeEventListener('keydown', handleModalKeyPress); // Remove the global keydown listener for modal interactions.
        }

        /**
         * Event handler function to close the modal if a click occurs directly on the modal overlay, outside the modal container.
         * @param {MouseEvent} event - The click event object.
         */
        function closeModalOnOutsideClick(event) {
            // Check if the target of the click event is the modal overlay div itself, not one of its children within the container.
            if (event.target === mediaModal) {
                closeModal(); // If it is the overlay, close the modal.
            }
        }

        /**
         * Global keyboard event handler function used when the modal is open.
         * Handles closing the modal with the Escape key and can be extended for focus trapping.
         * @param {KeyboardEvent} event - The keyboard event object.
         */
        function handleModalKeyPress(event) {
            // If the pressed key is 'Escape' and the modal is currently open:
            if (event.key === 'Escape' && mediaModal.classList.contains('is-open')) {
                event.preventDefault(); // Prevent the default browser action for the Escape key (e.g., stopping media).
                closeModal(); // Close the modal.
            }
            // --- Basic Focus Trap (Optional but good for accessibility) ---
            // To implement a robust focus trap, you would add logic here to:
            // 1. Identify the first and last focusable elements within the modal when it opens.
            // 2. On Tab (event.key === 'Tab'), if the user is on the last focusable element, move focus to the first one.
            // 3. On Shift+Tab (event.key === 'Tab' and event.shiftKey), if the user is on the first focusable element, move focus to the last one.
            // This prevents focus from leaving the modal while it's open. The current implementation relies on the browser's default behavior and simply returns focus when the modal closes.
        }


        // --- URL State Management (Allows browser back/forward navigation and bookmarking) ---
        /**
         * Updates the browser's URL to reflect the current search parameters or favorites view.
         * Uses `history.pushState` for new searches/pagination and `history.replaceState` for initial loads or restoring state.
         * This integrates the application state with the browser's history API.
         * @param {boolean} [replace=false] - If true, uses `history.replaceState` to replace the current history entry. If false (default), uses `history.pushState` to add a new entry.
         */
        function updateURL(replace = false) {
            let newUrl;
            if (appState.showingFavorites) {
                newUrl = `${window.location.pathname}#favorites`;
            } else {
                // Get the current search parameters from the application state.
                const {
                    currentQuery,
                    currentDriver,
                    currentType,
                    currentPage
                } = appState;
                // Create a URLSearchParams object to easily build the query string.
                const params = new URLSearchParams();
                // Add parameters if they have non-empty values.
                if (currentQuery) params.set('q', currentQuery);
                if (currentDriver) params.set('driver', currentDriver);
                if (currentType) params.set('type', currentType);
                // Only add the 'page' parameter if it's greater than 1 (page 1 is the default and doesn't need to be explicitly in the URL).
                if (currentPage > 1) params.set('page', currentPage);

                // Construct the new URL. It consists of the current path followed by the query string (if any parameters exist).
                newUrl = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`; // Add '?' only if there are parameters.
            }


            // Decide whether to push a new state or replace the current one based on the `replace` flag.
            if (replace) {
                // Use replaceState when the state is being restored (from initial load or popstate) to avoid cluttering history.
                // Store a minimal representation of the state (parameters needed to reconstruct) in the history entry.
                // Avoid storing the large resultsCache directly in history state to prevent performance issues.
                window.history.replaceState({
                    currentQuery: appState.currentQuery,
                    currentDriver: appState.currentDriver,
                    currentType: appState.currentType,
                    currentPage: appState.currentPage,
                    showingFavorites: appState.showingFavorites
                }, '', newUrl);
                log.info('Replaced history state:', newUrl); // Log the action and the new URL.
            } else {
                // Use pushState for user-initiated navigation (new search, pagination) to add a new entry to history.
                window.history.pushState({
                    currentQuery: appState.currentQuery,
                    currentDriver: appState.currentDriver,
                    currentType: appState.currentType,
                    currentPage: appState.currentPage,
                    showingFavorites: appState.showingFavorites
                }, '', newUrl); // Store the same minimal state.
                log.info('Pushed history state:', newUrl); // Log the action and the new URL.
            }
        }

        /**
         * Handles loading the application state from the browser's URL or a history state object.
         * This function is called on initial page load and when the `popstate` event fires (back/forward buttons).
         * It parses the URL/state, updates the UI input fields, and triggers a search if a query is found.
         * @param {object} [state=history.state] - The history state object. If omitted, uses the current `history.state`.
         * When called by `popstate`, this argument is automatically provided by the browser.
         */
        async function handleUrlOrState(state = history.state) {
            log.info('handleUrlOrState triggered.'); // Log that the function was called.
            const params = new URLSearchParams(window.location.search); // Get URL query parameters.

            const urlHasFavoritesHash = window.location.hash === '#favorites';

            // Determine the search parameters by prioritizing: 1. URL parameters, 2. History state properties, 3. Default values (or current UI values).
            const query = params.get('q') || state?.currentQuery || searchInput.value.trim();
            const driver = params.get('driver') || state?.currentDriver || driverSelect.value;
            const type = params.get('type') || state?.currentType || typeSelect.value;
            const page = parseInt(params.get('page'), 10) || state?.currentPage || 1; // Parse page number as integer, default to 1.
            const showingFavoritesFromState = state?.showingFavorites || urlHasFavoritesHash;

            // Update the UI input elements to reflect the loaded parameters.
            searchInput.value = query;
            driverSelect.value = driver;
            typeSelect.value = type;
            // Note: `appState.currentPage` will be updated within the `performSearch` function if a search is triggered.


            // Determine if we should perform a search based on the loaded parameters.
            const shouldLoadSearch = query || (state && (state.currentQuery || state.resultsCache?.length > 0));
            // Check if this is the very first page load *without* any query parameters or hash in the URL.
            const isInitialLoadWithoutParamsOrHash = state === history.state && !window.location.search && !window.location.hash;

            log.info('Parsed URL/State:', {
                query,
                driver,
                type,
                page,
                shouldLoadSearch,
                isInitialLoadWithoutParamsOrHash,
                showingFavoritesFromState
            });

            if (showingFavoritesFromState) {
                displayFavorites();
                // If it was loaded from URL hash, replace the state to ensure it's properly stored.
                if (window.location.hash === '#favorites' && !state?.showingFavorites) {
                    updateURL(true);
                }
                return; // Exit if showing favorites.
            }


            // If `shouldLoadSearch` is true AND it's not the initial load without parameters or hash:
            if (shouldLoadSearch && !isInitialLoadWithoutParamsOrHash) {
                // Update the application's internal state with the parameters for the search about to be performed.
                // Update these *before* the API call.
                appState.currentQuery = query;
                appState.currentDriver = driver;
                appState.currentType = type;
                // Note: `appState.currentPage` will be correctly set by `performSearch` itself.
                appState.showingFavorites = false; // Ensure not in favorites view.

                // Check if the history `state` object contains cached results that match the current parameters.
                // If so, we can restore from cache instead of making an API call.
                // Added check for state.resultsCache being an array before checking length.
                 if (state?.resultsCache && Array.isArray(state.resultsCache) && state.resultsCache.length > 0 && state.currentQuery === query && state.currentDriver === driver && state.currentType === type && state.currentPage === page) {
                    log.info('Restoring results from history state cache.');
                    appState.resultsCache = state.resultsCache; // Restore the cached results into `appState.resultsCache`.
                    renderResults(appState.resultsCache); // Render these cached results immediately.
                    setSearchState(false); // Ensure the UI is not in a loading state.
                    appState.currentPage = page; // Set the current page from the state.
                    updatePaginationButtons(); // Update the state of pagination buttons.
                    hideError(); // Ensure any previous error messages are hidden.
                 } else if (query) { // If a query exists but no matching cache, perform a new search
                      // If there's no matching cached data in the state, perform a new search by calling `performSearch`.
                      log.info('No matching cache found in state or initial load with params, performing new search.');
                      // Call `performSearch`, marking it as NOT user-initiated (`false`). This tells `performSearch`
                      // to use `history.replaceState` *after* a successful fetch to update the history entry with the results/state.
                      await performSearch(page, false);
                 } else {
                     // Edge case: state exists but no query and no cached results. Treat as initial load.
                     log.info('State found but no query or cache, treating as initial load.');
                     resultsDiv.innerHTML = '';
                     initialMessage?.classList.remove('hidden');
                     paginationControls.classList.add('hidden');
                     hideError();
                     setSearchState(false); // Ensure not in loading state
                     appState.currentPage = 1; // Reset page
                     appState.currentQuery = ''; // Clear state query
                     appState.resultsCache = []; // Clear state cache
                 }

            } else {
                // If `shouldLoadSearch` is false, or it's the initial load without parameters or hash, show the initial message.
                log.info('No query in URL/state or initial load without params/hash, showing initial message.');
                resultsDiv.innerHTML = ''; // Clear any default content in the results area.
                initialMessage?.classList.remove('hidden'); // Show the initial introductory message.
                paginationControls.classList.add('hidden'); // Hide pagination controls.
                hideError(); // Ensure no error message is displayed.
                setSearchState(false); // Ensure the UI is not in a loading state.
                // Reset application state relevant to search.
                appState.currentPage = 1;
                appState.currentQuery = '';
                appState.resultsCache = [];
                appState.showingFavorites = false;
                // If it's the very first load and no params/hash, ensure URL is clean
                 if (isInitialLoadWithoutParamsOrHash && (window.location.search || window.location.hash)) {
                     window.history.replaceState({}, '', window.location.pathname);
                 }
            }
        }


        // --- Core Search Functionality ---
        /**
         * Orchestrates the process of performing a search.
         * Reads input values, updates state, calls the API, renders results, and updates browser history.
         * @param {number} [page=1] - The page number to search for. Defaults to 1.
         * @param {boolean} [isUserInitiated=true] - True if the search was triggered by a user action (button click, Enter key, select change). False if triggered by URL/state loading.
         */
        async function performSearch(page = 1, isUserInitiated = true) {
             // Prevent initiating a new search if the application is already in a loading state or showing favorites.
             if (appState.isLoading || appState.showingFavorites) {
                  log.info('performSearch prevented: Application is busy or showing favorites.');
                  return; // Exit the function early.
             }

            // Get the current values from the search input and select dropdowns.
            const query = searchInput.value.trim(); // Get search query and remove leading/trailing whitespace.
            const driver = driverSelect.value; // Get the selected driver name.
            const type = typeSelect.value; // Get the selected search type.

            // Basic validation (only for user-initiated searches)
            if (isUserInitiated && !query) {
                showError('Please enter a search query.'); // Display an error message if no query is provided.
                return; // Exit the function early.
            }

             // If user initiated and it's a new query/type/driver combo, reset page to 1
             if (isUserInitiated && (query !== appState.currentQuery || driver !== appState.currentDriver || type !== appState.currentType)) {
                 page = 1; // Always go to page 1 for a new search
                 log.info('New search query or parameters detected, resetting to page 1.');
             }

            // Update the application's state with the parameters for the search about to be performed.
            // Update these *before* the API call.
            appState.currentQuery = query;
            appState.currentDriver = driver;
            appState.currentType = type;
            appState.currentPage = page; // Set the target page in the application state.
            appState.resultsCache = []; // Clear the results cache as we are fetching new results.
            appState.showingFavorites = false; // Ensure we are not in favorites view when performing a search.

            hideError(); // Hide any previous error messages that might be displayed.
            setSearchState(true); // Set the UI state to 'loading' (disables controls, shows skeletons).

            // Call the asynchronous function to fetch results from the backend API. Wait for the response.
            const response = await fetchResultsFromApi(query, driver, type, page);

            // Note: `setSearchState(false)` (resetting UI from loading) is handled in the `finally` block of `WorkspaceResultsFromApi`.

            // Check the response from the API call.
            if (response.success) {
                // If the API call was successful:
                appState.resultsCache = response.data; // Store the received array of results in the application state cache.
                renderResults(appState.resultsCache); // Render the results into the results grid.
                // Update the browser's URL and history state.
                // If the search was NOT user-initiated (i.e., loaded from URL/popstate), use `replaceState` to update the current history entry.
                // If it WAS user-initiated (new search or pagination click), use `pushState` to add a new history entry.
                updateURL(!isUserInitiated); // The `!isUserInitiated` boolean value correctly determines whether to use `replaceState` (true) or `pushState` (false).
            } else if (!response.isAbort) {
                // If the API call failed AND it was NOT due to a request being aborted:
                renderResults([]); // Clear any previously displayed results (renderItems handles showing "No results" message if the array is empty).
                showError(response.error); // Display the user-friendly error message returned by `WorkspaceResultsFromApi`.
                // Note: The URL is generally not updated in history when a search fails.
            }
            // If the response indicated the request was aborted (`response.isAbort` is true), do nothing further here.
            // The user has already triggered a new search, and that subsequent `performSearch` call will handle the UI update.

            // Ensure pagination state is correct after search attempt (This is also called in fetchResultsFromApi finally, but doesn't hurt to ensure).
            // updatePaginationButtons();
        }


        // --- Event Listeners ---
        // Add an event listener to the Search button.
        searchBtn.addEventListener('click', () => performSearch(1, true)); // When clicked, perform a new search starting on page 1, marked as user-initiated.

        // Debounced search input handler
        const debouncedPerformSearch = debounce(() => {
            if (!appState.isLoading) { // Only trigger if not already loading
                performSearch(1, true);
            }
        }, 500); // 500ms debounce delay

        // Add an event listener to the search input field to allow searching by pressing the Enter key.
        searchInput.addEventListener('keypress', (event) => {
            // Check if the pressed key is 'Enter' (key code 13) AND the application is not currently loading.
            if (event.key === 'Enter' && !appState.isLoading) {
                event.preventDefault(); // Prevent the default browser action (e.g., form submission and page reload).
                debouncedPerformSearch.cancel(); // Cancel any pending debounced call
                performSearch(1, true); // Perform a new search immediately
            }
        });

        // Add an event listener for 'input' events on the search input field for debounced search.
        searchInput.addEventListener('input', () => {
            // Only trigger debounced search if not showing favorites
            if (!appState.showingFavorites) {
                debouncedPerformSearch();
            }
        });

        // Add an event listener to the clear search input button ('×').
        clearSearchBtn.addEventListener('click', () => {
            searchInput.value = ''; // Clear the value of the search input field.
            // Manually dispatch an 'input' event on the search input. This triggers any listeners on the input,
            // specifically the CSS rule `:not(:placeholder-shown)` which controls the clear button's visibility.
            searchInput.dispatchEvent(new Event('input'));
            searchInput.focus(); // Set focus back to the search input field after clearing.
            // Also clear the displayed results and show the initial message.
            resultsDiv.innerHTML = ''; // Clear the results grid content.
            initialMessage?.classList.remove('hidden'); // Show the initial introductory message.
            paginationControls.classList.add('hidden'); // Hide pagination controls.
            hideError(); // Hide any active error message.
            // Reset app state query/page here
            appState.currentQuery = '';
            appState.currentPage = 1;
            appState.resultsCache = [];
            updateURL(true); // Update URL to reflect cleared search
        });

        // Add event listeners to the Type and Driver select dropdowns.
        // Changing the type or driver should trigger a new search starting from page 1.
        typeSelect.addEventListener('change', () => performSearch(1, true)); // Perform new search on type change, user-initiated.
        driverSelect.addEventListener('change', () => performSearch(1, true)); // Perform new search on driver change, user-initiated.


        // Add event listeners to the pagination buttons.
        prevBtn.addEventListener('click', () => {
            // Allow navigating to the previous page only if not currently loading, the current page is greater than 1, and not showing favorites.
            if (!appState.isLoading && appState.currentPage > 1 && !appState.showingFavorites) {
                performSearch(appState.currentPage - 1, true); // Perform search for the previous page, user-initiated.
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                }); // Scroll the viewport smoothly to the top of the page.
            } else {
                log.info('Previous page search prevented.'); // Log if the action was prevented.
            }
        });

        nextBtn.addEventListener('click', () => {
            // Allow navigating to the next page only if not currently loading, if the previous search returned enough results to indicate a next page, and not showing favorites.
            // `appState.resultsCache.length === appState.maxResultsHeuristic` checks if the last page was potentially full, suggesting there's more content.
            if (!appState.isLoading && appState.resultsCache.length === appState.maxResultsHeuristic && appState.maxResultsHeuristic > 0 && !appState.showingFavorites) {
                 performSearch(appState.currentPage + 1, true); // Perform search for the next page, user-initiated.
                 window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                }); // Scroll the viewport smoothly to the top of the page.
            } else {
                log.info('Next page search prevented.'); // Log if the action was prevented.
            }
        });


        // Add event listener to the modal's close button.
        closeModalBtn.addEventListener('click', closeModal); // When clicked, call the closeModal function.

        // Add an event listener for the 'popstate' event on the window object.
        // This event fires when the active history entry changes, typically when the user clicks the browser's back or forward buttons.
        window.addEventListener('popstate', (event) => {
            log.info('Popstate event triggered.'); // Log that the popstate event occurred.
            // The `event.state` property contains the state object that was passed to `pushState` or `replaceState`.
            // Call `handleUrlOrState` with this state object to restore the application's state to the previous history entry.
            handleUrlOrState(event.state);
        });

        // --- Favorites Toggle Listener ---
        if (toggleFavoritesBtn) {
            toggleFavoritesBtn.addEventListener('click', () => {
                 if (appState.showingFavorites) {
                     hideFavorites(); // If currently showing favorites, switch back to search results.
                 } else {
                     displayFavorites(); // If showing search results, switch to display favorites.
                 }
            });
        }


        // --- Initial Setup on Load ---
        // Add an event listener for the 'DOMContentLoaded' event. This fires when the initial HTML document has been completely loaded and parsed, without waiting for stylesheets, images, and subframes to finish loading.
        window.addEventListener('DOMContentLoaded', () => {
            log.info('DOMContentLoaded event fired. Frontend script loaded.'); // Log script loading confirmation.
            loadFavorites(); // Load any saved favorite items from local storage when the page loads.
            // Call `handleUrlOrState` immediately on page load. This checks if the page was loaded with URL parameters (e.g., from a bookmark or refresh)
            // or if there's a history state object to restore from (e.g., after a hard refresh on a URL generated by pushState).
            handleUrlOrState();
        });

    </script>

</body>

</html>
EOF

echo "All files created successfully."
echo "--------------------------------------------------------------------------------"
echo "NEXT STEPS:"
echo "1. Install dependencies: 'npm install express cors axios cheerio babel-runtime'"
echo "2. Run the backend server: 'node server.js'"
echo "3. Open your browser to 'http://localhost:3000' or 'http://<your-device-ip>:3000'"
echo ""
echo "IMPORTANT: The CSS selectors and URL patterns in the driver files (modules/*.js)"
echo "are speculative and MUST be verified against the live websites. Websites frequently"
echo "change their HTML structure, which can break the scraping logic."
echo ""
echo "To verify a driver:"
echo "   a. Go to the respective website (e.g., www.pornhub.com)."
echo "   b. Perform a search manually."
echo "   c. Use your browser's developer tools (F12) to 'Inspect' the HTML elements"
echo "      of the video/GIF results (e.g., the main div containing a video card)."
echo "   d. Compare the actual HTML structure and element classes/IDs with the"
echo "      'VIDEO_SELECTOR', 'GIF_SELECTOR', and URL patterns in the driver's parser methods."
echo "   e. Adjust the selectors and regex patterns in the driver file if necessary."
echo "--------------------------------------------------------------------------------"
