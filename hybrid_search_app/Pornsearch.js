'use strict';

var _classCallCheck = require('babel-runtime/helpers/classCallCheck');
var _classCallCheck2 = _interopRequireDefault(_classCallCheck);
var _createClass = require('babel-runtime/helpers/createClass');
var _createClass2 = _interopRequireDefault(_createClass);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

const fs = require('fs').promises;
const path = require('path');
const axios = require('axios');
const cheerio = require('cheerio');

const VideoMixin = require('./core/VideoMixin.js');
const GifMixin = require('./core/GifMixin.js');
const DummyBaseClassForMixinCheck = class {};
const VideoMixinPrototype = VideoMixin(DummyBaseClassForMixinCheck).prototype;
const GifMixinPrototype = GifMixin(DummyBaseClassForMixinCheck).prototype;

const MOCK_DATA_DIR = path.join(__dirname, 'modules', 'mock_html_data');

var Pornsearch = function () {
  function Pornsearch(options, drivers, config) {
    (0, _classCallCheck2.default)(this, Pornsearch);

    this.query = options.query || '';
    this.page = options.page || 1;
    this.pageSize = options.pageSize || 20;
    this.config = config;
    this.allDrivers = drivers;

    this.activeDrivers = [];
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
    } else if (this.allDrivers) {
      this.activeDrivers = Object.values(this.allDrivers);
    }

    if (this.activeDrivers.length === 0) {
      console.warn('[Pornsearch] Warning: No active drivers were loaded. The application may not function as expected.');
    }
    console.log(`[Pornsearch] Initialized with query: "${this.query}", page: ${this.page}`);
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
    key: '_fetch',
    value: async function _fetch(driver, searchUrl, useMockData, page, searchType) {
        let rawContent = '';
        if (useMockData) {
            const normalizedDriverNameForFile = driver.name.toLowerCase().replace(/[\s.]+/g, '');
            const mockFileName = `${normalizedDriverNameForFile}_${searchType}_page${page}.html`;
            const mockFilePath = path.join(MOCK_DATA_DIR, mockFileName);
            try {
                rawContent = await fs.readFile(mockFilePath, 'utf8');
                console.log(`  [${driver.name}] Loaded mock data from: ${mockFilePath}`);
            } catch (fileError) {
                console.error(`  [${driver.name}] ERROR: Failed to load mock data from ${mockFilePath}: ${fileError.message}. Skipping.`);
                return null;
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
        return rawContent;
    }
  }, {
    key: '_parse',
    value: async function _parse(driver, rawContent, parserOptions) {
        let cheerioInstance = null;
        let jsonData = null;

        if (typeof rawContent === 'string' && rawContent.trim().startsWith('<')) {
            cheerioInstance = cheerio.load(rawContent);
            if (parserOptions && !parserOptions.useMockData) {
                const noResultsSelectors = '#videoSearchResult .no-results-found, .no-results-found-container, .noResultsMessage';
                if (cheerioInstance(noResultsSelectors).length > 0) {
                    console.log(`  [${driver.name}] No results found on page.`);
                    return [];
                }
            }
        } else if (typeof rawContent === 'object' || (typeof rawContent === 'string' && rawContent.trim().startsWith('{'))) {
            jsonData = (typeof rawContent === 'string') ? JSON.parse(rawContent) : rawContent;
        } else {
            console.warn(`  [${driver.name}] Unknown content format. Skipping.`);
            return [];
        }

        const results = await driver.parseResults(cheerioInstance, jsonData || rawContent, parserOptions);

        if (Array.isArray(results)) {
            console.log(`  [${driver.name}] Parsed ${results.length} ${parserOptions.type} results.`);
            // Ensure source and type are consistently added if driver didn't do it
            return results.map(r => ({
                ...r,
                source: r.source || driver.name, // Prioritize driver's source, then orchestrator's
                type: r.type || parserOptions.type      // Prioritize driver's type, then orchestrator's
            }));
        } else {
            console.warn(`  [${driver.name}] parseResults did not return an array. Skipping.`);
            return [];
        }
    }
  }, {
    key: 'search',
    value: async function search(searchOptions) {
      const { query, page = 1, type = 'videos', useMockData = false, platform = null } = searchOptions;

      if (!query && !useMockData) {
        throw new Error("Search query cannot be empty.");
      }
      let searchType = type;
      if (!['videos', 'gifs'].includes(searchType)) {
        console.warn(`[Pornsearch] Invalid search type '${searchType}'. Defaulting to 'videos'.`);
        searchType = 'videos';
      }

      console.log(`[Pornsearch] Searching for "${query}" (${searchType}) on page ${page} (Mocking: ${useMockData ? 'YES' : 'NO'})...`);

      let driversToSearch = this.activeDrivers;
      if (!useMockData) {
        driversToSearch = driversToSearch.filter(d => d.name.toLowerCase() !== 'mock');
      }

      if (platform) {
        const normalizedPlatform = platform.toLowerCase() === 'sexcom' ? 'sex.com' : platform.toLowerCase();
        driversToSearch = driversToSearch.filter(d => d.name.toLowerCase() === normalizedPlatform);
        if (driversToSearch.length === 0) {
          console.warn(`[Pornsearch] No active driver found for platform: ${platform}`);
          return [];
        }
      }

      const searchPromises = driversToSearch.map(async driver => {
        try {
          let searchUrl = '';
          const parserOptions = { type: searchType, sourceName: driver.name, query: query, page: page };

          let getUrlMethod;
          if (searchType === 'videos' && typeof driver.hasVideoSupport === 'function' && driver.hasVideoSupport() && typeof driver.getVideoSearchUrl === 'function') {
            getUrlMethod = driver.getVideoSearchUrl;
          } else if (searchType === 'gifs' && typeof driver.hasGifSupport === 'function' && driver.hasGifSupport() && typeof driver.getGifSearchUrl === 'function') {
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

          const rawContent = await this._fetch(driver, searchUrl, useMockData, page, searchType);
          if (!rawContent) {
              return [];
          }

          return await this._parse(driver, rawContent, parserOptions);
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
  }], [{
    key: 'create',
    value: async function create(options) {
      let config;
      try {
          config = require('./config.js');
      } catch (e) {
          console.error("[Pornsearch.js] Critical: Failed to load config.js. Defaulting global settings.", e.message);
          config = { global: { defaultUserAgent: 'Mozilla/5.0', requestTimeout: 15000 }};
      }

      const drivers = await this.loadDrivers(options);
      return new Pornsearch(options, drivers, config);
    }
  }, {
    key: 'loadDrivers',
    value: async function loadDrivers(options) {
      const drivers = {};
      const modulesDirs = [
        path.join(__dirname, 'modules'),
        path.join(__dirname, 'modules', 'custom_scrapers')
      ];

      for (const modulesDir of modulesDirs) {
        try {
          const files = await fs.readdir(modulesDir);
          for (const file of files) {
            if ((file.endsWith('.js') || file.endsWith('.cjs')) && !['driver-utils.js'].includes(file)) {
              try {
                const driverPath = path.join(modulesDir, file);
                let DriverClass = require(driverPath);
                // If it's an object with a 'default' property (Babel transpiled ES6 export)
                if (DriverClass && typeof DriverClass === 'object' && DriverClass.default) {
                  DriverClass = DriverClass.default;
                }
                // If it's still not a function (constructor), something is wrong
                if (typeof DriverClass !== 'function') {
                    throw new TypeError(`DriverClass for ${file} is not a constructor function.`);
                }
                const driverInstance = new DriverClass(options);
                const driverName = driverInstance.name.toLowerCase();
                drivers[driverName] = driverInstance;
              } catch (error) {
                console.error(`Failed to load driver from ${file}:`, error);
              }
            }
          }
        } catch (dirError) {
          console.error(`Failed to read directory ${modulesDir}:`, dirError);
        }
      }
      return drivers;
    }
  }]);

  return Pornsearch;
}();

module.exports = Pornsearch;