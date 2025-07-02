'use strict';

// Ensure all necessary babel helpers are available if you are transpiling
// These are typical imports, adjust if your build setup is different.
var _classCallCheck = require('babel-runtime/helpers/classCallCheck');
var _classCallCheck2 = _interopRequireDefault(_classCallCheck);
var _createClass = require('babel-runtime/helpers/createClass');
var _createClass2 = _interopRequireDefault(_createClass);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

// Import core Node.js modules for file system and path manipulation
const fs = require('fs').promises;
const path = require('path');

// Import HTTP client and HTML parser
const axios = require('axios');
const cheerio = require('cheerio');

// Import all your content drivers/modules
var _Pornhub = require('./modules/Pornhub.js');
var _Pornhub2 = _interopRequireDefault(_Pornhub);
var _Redtube = require('./modules/Redtube.js');
var _Redtube2 = _interopRequireDefault(_Redtube);
var _Xhamster = require('./modules/Xhamster.js');
var _Xhamster2 = _interopRequireDefault(_Xhamster);
var _Xvideos = require('./modules/Xvideos.js');
var _Xvideos2 = _interopRequireDefault(_Xvideos);
var _Youporn = require('./modules/Youporn.js');
var _Youporn2 = _interopRequireDefault(_Youporn);
var _Spankbang = require('./modules/Spankbang.js');
var _Spankbang2 = _interopRequireDefault(_Spankbang);
var _Motherless = require('./modules/Motherless.js');
var _Motherless2 = _interopRequireDefault(_Motherless);
var _SexCom = require('./modules/SexCom.js');
var _SexCom2 = _interopRequireDefault(_SexCom);
var _MockScraper = require('./modules/mockScraper.cjs');
var _MockScraper2 = _interopRequireDefault(_MockScraper);

// Corrected Mixin Loading for Prototype Check (if still needed)
// The core issue was `MixinModule.default()` when MixinModule itself is the function.
const VideoMixin = require('./core/VideoMixin.js');
const GifMixin = require('./core/GifMixin.js');
const DummyBaseClassForMixinCheck = class {}; // Dummy class to apply mixin for prototype checking
const VideoMixinPrototype = VideoMixin(DummyBaseClassForMixinCheck).prototype;
const GifMixinPrototype = GifMixin(DummyBaseClassForMixinCheck).prototype;


// Constants for mock data path
const MOCK_DATA_DIR = path.join(__dirname, 'modules', 'mock_html_data');

var Pornsearch = function () {
  function Pornsearch() {
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    (0, _classCallCheck2.default)(this, Pornsearch);

    this.query = options.query || '';
    this.page = options.page || 1;
    this.pageSize = options.pageSize || 20;

    let config;
    try {
        config = require('./config.js');
    } catch (e) {
        console.error("[Pornsearch.js] Critical: Failed to load config.js. Defaulting global settings.", e.message);
        config = { global: { defaultUserAgent: 'Mozilla/5.0', requestTimeout: 15000 }};
    }
    this.config = config;

    this.allDrivers = {
      'pornhub': new _Pornhub2.default(options),
      'redtube': new _Redtube2.default(options),
      'xhamster': new _Xhamster2.default(options),
      'xvideos': new _Xvideos2.default(options),
      'youporn': new _Youporn2.default(options),
      'spankbang': new _Spankbang2.default(options),
      'motherless': new _Motherless2.default(options),
      'sex.com': new _SexCom2.default(options),
      'mock': new _MockScraper2.default(options)
    };

    if (options.drivers && Array.isArray(options.drivers) && options.drivers.length > 0) {
      this.activeDrivers = options.drivers.reduce((acc, driverName) => {
        const normalizedDriverName = driverName.toLowerCase() === 'sexcom' ? 'sex.com' : driverName.toLowerCase();
        const driver = this.allDrivers[normalizedDriverName];
        if (driver) {
          acc.push(driver);
        } else {
          console.warn(`[Pornsearch] Driver '${driverName}' not found or is invalid. Skipping.`);
        }
        return acc;
      }, []);
    } else {
      this.activeDrivers = Object.values(this.allDrivers);
    }
    console.log(`[Pornsearch] Initialized with query: "${this.query}", page: ${this.page}, drivers: ${this.activeDrivers.map(d => d.name).join(', ')}`);
  }

  (0, _createClass2.default)(Pornsearch, [{
    key: 'setQuery',
    value: function setQuery(newQuery) {
      if (typeof newQuery !== 'string' || newQuery.trim() === '') {
        console.warn("[Pornsearch] Invalid query provided. Query must be a non-empty string.");
        return;
      }
      this.query = newQuery.trim();
      this.activeDrivers.forEach(driver => {
        if (typeof driver.setQuery === 'function') {
          driver.setQuery(this.query);
        } else if (driver.hasOwnProperty('query')) {
            driver.query = this.query;
        }
      });
      console.log(`[Pornsearch] Query updated to: "${this.query}" for all active drivers.`);
    }
  }, {
    key: 'search',
    value: async function search(searchOptions) {
      const { query, page = 1, type = 'videos', useMockData = false } = searchOptions;

      if (!query) {
        throw new Error("Search query cannot be empty.");
      }
      let searchType = type;
      if (!['videos', 'gifs'].includes(searchType)) {
        console.warn(`[Pornsearch] Invalid search type '${searchType}'. Defaulting to 'videos'.`);
        searchType = 'videos';
      }

      console.log(`[Pornsearch] Searching for "${query}" (${searchType}) on page ${page} (Mocking: ${useMockData ? 'YES' : 'NO'})...`);

      const searchPromises = this.activeDrivers.map(async driver => {
        try {
          let searchUrl = '';
          let rawContent = '';
          const parserOptions = { type: searchType, sourceName: driver.name, query: query, page: page };

          let getUrlMethod;
          if (searchType === 'videos' && driver.supportsVideos && typeof driver.getVideoSearchUrl === 'function') {
            getUrlMethod = driver.getVideoSearchUrl;
          } else if (searchType === 'gifs' && driver.supportsGifs && typeof driver.getGifSearchUrl === 'function') {
            getUrlMethod = driver.getGifSearchUrl;
          } else {
            console.warn(`  [${driver.name}] Driver does not support '${searchType}' or missing URL method. Skipping.`);
            return [];
          }

          searchUrl = getUrlMethod.call(driver, query, page);

          if (!searchUrl || typeof searchUrl !== 'string' || searchUrl.trim() === '') {
            console.warn(`  [${driver.name}] Failed to generate valid URL for ${searchType}. Skipping.`);
            return [];
          }

          if (useMockData) {
            // Normalize driver name for filename: lowercase, remove spaces and dots.
            const normalizedDriverNameForFile = driver.name.toLowerCase().replace(/[\s.]+/g, '');
            const mockFileName = `${normalizedDriverNameForFile}_${searchType}_page${page}.html`;
            const mockFilePath = path.join(MOCK_DATA_DIR, mockFileName);
            try {
              rawContent = await fs.readFile(mockFilePath, 'utf8');
              console.log(`  [${driver.name}] Loaded mock data from: ${mockFilePath}`);
            } catch (fileError) {
              console.error(`  [${driver.name}] ERROR: Failed to load mock data from ${mockFilePath}: ${fileError.message}. Skipping.`);
              return [];
            }
          } else {
            console.log(`  [${driver.name}] Fetching live content from: ${searchUrl}`);
            const response = await axios.get(searchUrl, {
              headers: {
                'User-Agent': this.config.global.defaultUserAgent || 'Mozilla/5.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8,application/json;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': driver.baseUrl
              },
              timeout: this.config.global.requestTimeout || 15000
            });
            rawContent = response.data;
          }

          let cheerioInstance = null;
          let jsonData = null;

          if (typeof rawContent === 'string' && rawContent.trim().startsWith('<')) {
              cheerioInstance = cheerio.load(rawContent);
          } else if (typeof rawContent === 'object' || (typeof rawContent === 'string' && rawContent.trim().startsWith('{'))) {
              jsonData = (typeof rawContent === 'string') ? JSON.parse(rawContent) : rawContent;
          } else {
              console.warn(`  [${driver.name}] Unknown content format. Skipping.`);
              return [];
          }

          const results = await driver.parseResults(cheerioInstance, jsonData || rawContent, parserOptions);

          if (Array.isArray(results)) {
            console.log(`  [${driver.name}] Parsed ${results.length} ${searchType} results.`);
            // Ensure source and type are consistently added if driver didn't do it
            return results.map(r => ({
                ...r,
                source: r.source || driver.name, // Prioritize driver's source, then orchestrator's
                type: r.type || searchType      // Prioritize driver's type, then orchestrator's
            }));
          } else {
            console.warn(`  [${driver.name}] parseResults did not return an array. Skipping.`);
            return [];
          }
        } catch (error) {
          console.error(`  [Pornsearch] Error searching ${searchType} on ${driver.name} (Mock: ${useMockData}):`, error.message);
          if (error.response) {
            console.error(`    Status: ${error.response.status}`);
          } else if (error.code === 'ENOENT' && useMockData) {
            console.error(`    Mock file not found. Ensure '${error.path}' exists.`);
          }
          return [];
        }
      });

      const allResults = await Promise.all(searchPromises);
      return [].concat(...allResults);
    }
  }, {
    key: 'listActiveDrivers',
    value: function listActiveDrivers() {
      return this.activeDrivers.map(driver => driver.name);
    }
  }]);

  return Pornsearch;
}();

module.exports = Pornsearch;
