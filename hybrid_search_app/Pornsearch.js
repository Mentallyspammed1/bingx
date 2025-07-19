'use strict';

const fs = require('fs').promises;
const path = require('path');
const cheerio = require('cheerio');
const pLimit = require('p-limit'); // For concurrency control

// Attempt to load colorama for neon-themed console output
let colorama;
try {
    const { init, Fore, Style } = require('colorama');
    init({ autoreset: true }); // Initialize colorama for auto-resetting styles
    colorama = { Fore, Style };
} catch (e) {
    // Fallback if colorama is not available (e.g., not in Termux or not installed)
    console.warn("Colorama not found. Install with `npm install colorama` for neon-themed logs.");
    colorama = {
        Fore: {
            RED: '', GREEN: '', YELLOW: '', BLUE: '', MAGENTA: '', CYAN: '', WHITE: '',
            LIGHTRED_EX: '', LIGHTGREEN_EX: '', LIGHTYELLOW_EX: '', LIGHTBLUE_EX: '',
            LIGHTMAGENTA_EX: '', LIGHTCYAN_EX: ''
        },
        Style: { BRIGHT: '', DIM: '', RESET_ALL: '' }
    };
}

const { fetchWithRetry, getRandomUserAgent } = require('./modules/driver-utils.js');

const MOCK_DATA_DIR = path.join(__dirname, 'modules', 'mock_html_data');

/**
 * Custom logger for neon-themed output.
 * @param {string} level - Log level (info, warn, error, debug).
 * @param {string} message - The message to log.
 * @param {string} [component=''] - Optional component name (e.g., 'Pornsearch', 'DriverLoader').
 */
function neonLog(level, message, component = '') {
    const timestamp = new Date().toISOString();
    let prefix = '';
    let color = '';

    switch (level) {
        case 'info':
            color = colorama.Fore.CYAN + colorama.Style.BRIGHT;
            prefix = '[INFO]';
            break;
        case 'warn':
            color = colorama.Fore.YELLOW + colorama.Style.BRIGHT;
            prefix = '[WARN]';
            break;
        case 'error':
            color = colorama.Fore.LIGHTRED_EX + colorama.Style.BRIGHT;
            prefix = '[ERROR]';
            break;
        case 'debug':
            color = colorama.Fore.MAGENTA + colorama.Style.DIM;
            prefix = '[DEBUG]';
            break;
        default:
            color = colorama.Fore.WHITE;
            prefix = '[LOG]';
            break;
    }

    const componentStr = component ? `[${component}] ` : '';
    console.log(`${color}${timestamp} ${prefix} ${componentStr}${message}${colorama.Style.RESET_ALL}`);
}

/**
 * @typedef {object} PornsearchConfig
 * @property {object} global - Global configuration settings.
 * @property {number} global.requestTimeout - Default timeout for HTTP requests in ms.
 * @property {number} global.maxConcurrentSearches - Maximum concurrent driver searches.
 * @property {boolean} global.deduplicateResults - Whether to deduplicate results across drivers.
 * @property {boolean} global.debugMode - Enable debug logging.
 */

class Pornsearch {
    /**
     * @type {PornsearchConfig}
     */
    config;

    /**
     * Stores loaded driver instances.
     * @type {Object.<string, import('./modules/baseDriver').BaseDriver>}
     */
    drivers = {};

    /**
     * @private
     * @param {PornsearchConfig} config - Configuration object for Pornsearch.
     */
    constructor(config) {
        this.config = this._validateConfig(config);
        neonLog('info', 'Orchestrator instance created.', 'Pornsearch');
    }

    /**
     * Validates and merges default configuration.
     * @private
     * @param {object} userConfig
     * @returns {PornsearchConfig}
     */
    _validateConfig(userConfig) {
        const defaultConfig = {
            global: {
                requestTimeout: 20000, // Increased default timeout
                maxConcurrentSearches: 5, // Limit concurrent requests to 5 by default
                deduplicateResults: true,
                debugMode: false,
            }
        };

        const config = {
            ...defaultConfig,
            ...userConfig,
            global: { ...defaultConfig.global, ...(userConfig ? userConfig.global : {}) }
        };

        if (config.global.debugMode) {
            neonLog('debug', 'Debug mode enabled.', 'Config');
        }
        neonLog('info', `Using config: ${JSON.stringify(config.global)}`, 'Config');
        return config;
    }

    /**
     * Static factory method to create and initialize the Pornsearch instance.
     * @param {PornsearchConfig} config - Configuration for the Pornsearch instance.
     * @returns {Promise<Pornsearch>} A promise that resolves to a Pornsearch instance.
     */
    static async create(config) {
        const instance = new Pornsearch(config);
        await instance._initializeAndRegisterDrivers();
        return instance;
    }

    /**
     * Initializes and registers all available drivers from the modules directory.
     * @private
     * @returns {Promise<void>}
     */
    async _initializeAndRegisterDrivers() {
        neonLog('info', 'Initializing and registering drivers...', 'Pornsearch');
        const modulesDir = path.join(__dirname, 'modules');
        try {
            const files = await fs.readdir(modulesDir);
            for (const file of files) {
                // Ensure it's a JS/CJS file and not a utility file
                if ((file.endsWith('.js') || file.endsWith('.cjs')) && !['driver-utils.js', 'mockScraper.cjs'].includes(file)) {
                    try {
                        const driverPath = path.join(modulesDir, file);
                        let DriverClass = require(driverPath);

                        // Handle ES Module default exports in CommonJS context
                        if (DriverClass && typeof DriverClass === 'object' && DriverClass.default) {
                            DriverClass = DriverClass.default;
                        }

                        if (typeof DriverClass !== 'function' || !DriverClass.prototype) {
                            neonLog('error', `Skipped ${file}: Export is not a valid class/constructor.`, 'DriverLoader');
                            continue;
                        }

                        // Instantiate the driver class. Pass config if needed by drivers in future.
                        const driverInstance = new DriverClass();
                        const driverName = driverInstance.name;

                        if (!driverName || typeof driverName !== 'string') {
                            neonLog('warn', `Skipped ${file}: Driver has no 'name' property or it's not a string.`, 'DriverLoader');
                            continue;
                        }

                        // More robust validation for the driver interface
                        const requiredMethods = ['parseResults'];
                        const requiredCapabilities = ['supportsGifs', 'supportsVideos'];

                        const missingMethods = requiredMethods.filter(method => typeof driverInstance[method] !== 'function');
                        const missingCapabilities = requiredCapabilities.filter(cap => typeof driverInstance[cap] === 'undefined');

                        if (missingMethods.length > 0) {
                            neonLog('warn', `Skipped ${driverName}: Missing required methods: ${missingMethods.join(', ')}.`, 'DriverLoader');
                            continue;
                        }
                        if (missingCapabilities.length > 0 || !(driverInstance.supportsGifs || driverInstance.supportsVideos)) {
                            neonLog('warn', `Skipped ${driverName}: Missing required capabilities or neither supportsGifs nor supportsVideos is true.`, 'DriverLoader');
                            continue;
                        }

                        this.drivers[driverName.toLowerCase()] = driverInstance;
                        neonLog('info', `Successfully registered driver: ${driverName}`, 'DriverLoader');

                    } catch (error) {
                        neonLog('error', `Failed to load driver from ${file}: ${error.message}`, 'DriverLoader');
                        if (this.config.global.debugMode) {
                            console.error(error); // Log full stack trace in debug mode
                        }
                    }
                }
            }
        } catch (dirError) {
            neonLog('error', `Failed to read modules directory: ${dirError.message}`, 'DriverLoader');
            if (this.config.global.debugMode) {
                console.error(dirError);
            }
        }
        neonLog('info', `Driver registration complete. ${Object.keys(this.drivers).length} drivers loaded.`, 'Pornsearch');
    }

    /**
     * Returns a list of available platforms (drivers) and their capabilities.
     * @returns {Array<{name: string, supportsVideos: boolean, supportsGifs: boolean}>}
     */
    getAvailablePlatforms() {
        return Object.values(this.drivers).map(driver => ({
            name: driver.name,
            supportsVideos: driver.supportsVideos,
            supportsGifs: driver.supportsGifs,
            // Add other relevant driver info if available, e.g., driver.baseUrl
        }));
    }

    /**
     * Fetches raw HTML content from a given URL or loads from mock data.
     * @private
     * @param {import('./modules/baseDriver').BaseDriver} driver - The driver instance.
     * @param {string} searchUrl - The URL to fetch.
     * @param {boolean|object} useMockData - If true, use mock data. Can be an object like `{ driverName: true }` for granular control.
     * @param {number} page - The current page number.
     * @param {'videos'|'gifs'} searchType - The type of search (videos or gifs).
     * @returns {Promise<string|null>} The raw content or null if fetching fails.
     */
    async _fetch(driver, searchUrl, useMockData, page, searchType) {
        const useMockForThisDriver = typeof useMockData === 'object'
            ? useMockData[driver.name.toLowerCase()]
            : useMockData;

        if (useMockForThisDriver) {
            const normalizedDriverName = driver.name.toLowerCase().replace(/[\s.]+/g, '');
            const mockFileName = `${normalizedDriverName}_${searchType}_page${page}.html`;
            const mockFilePath = path.join(MOCK_DATA_DIR, mockFileName);
            try {
                const mockContent = await fs.readFile(mockFilePath, 'utf8');
                neonLog('debug', `Loaded mock data for ${driver.name} from ${mockFileName}`, 'FETCH_MOCK');
                return mockContent;
            } catch (fileError) {
                neonLog('error', `Failed to load mock data for ${driver.name} (${mockFileName}): ${fileError.message}`, 'FETCH_MOCK_ERROR');
                return null;
            }
        }

        const options = {
            headers: {
                'User-Agent': getRandomUserAgent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Referer': driver.baseUrl || searchUrl, // Use driver's base URL or search URL
                ...(typeof driver.getCustomHeaders === 'function' ? driver.getCustomHeaders() : {})
            },
            timeout: this.config.global.requestTimeout
        };

        try {
            neonLog('debug', `Fetching ${searchUrl} for ${driver.name}`, 'FETCH');
            const response = await fetchWithRetry(searchUrl, options);
            return response.data;
        } catch (error) {
            neonLog('error', `Fetch failed for ${driver.name} at ${searchUrl}: ${error.message}`, 'FETCH_ERROR');
            return null;
        }
    }

    /**
     * Parses the raw content using the specified driver.
     * @private
     * @param {import('./modules/baseDriver').BaseDriver} driver - The driver instance.
     * @param {string|object} rawContent - The raw HTML string or JSON object.
     * @param {object} parserOptions - Options to pass to the driver's parseResults method.
     * @param {'videos'|'gifs'} parserOptions.type - The type of content being parsed.
     * @param {string} parserOptions.sourceName - The name of the driver.
     * @param {string} parserOptions.query - The original search query.
     * @param {number} parserOptions.page - The original page number.
     * @returns {Promise<Array<object>>} An array of parsed results.
     */
    async _parse(driver, rawContent, parserOptions) {
        if (!rawContent) {
            neonLog('debug', `No raw content to parse for ${driver.name}.`, 'PARSE');
            return [];
        }

        let cheerioInstance = null;
        let jsonData = null;
        let contentType = 'unknown';

        try {
            if (typeof rawContent === 'string') {
                const trimmedContent = rawContent.trim();
                if (trimmedContent.startsWith('<')) {
                    cheerioInstance = cheerio.load(trimmedContent);
                    contentType = 'html';
                } else if (trimmedContent.startsWith('{') || trimmedContent.startsWith('[')) {
                    jsonData = JSON.parse(trimmedContent);
                    contentType = 'json';
                } else {
                    neonLog('warn', `Unrecognized content format for ${driver.name}. Attempting as plain text.`, 'PARSE');
                    // Treat as plain text or fallback to driver's own handling
                    contentType = 'text';
                }
            } else if (typeof rawContent === 'object') {
                jsonData = rawContent;
                contentType = 'json';
            } else {
                neonLog('warn', `Invalid raw content type for ${driver.name}: ${typeof rawContent}.`, 'PARSE');
                return [];
            }
        } catch (e) {
            neonLog('error', `Failed to prepare content for parsing ${driver.name} (type: ${contentType}): ${e.message}`, 'PARSE_ERROR');
            if (this.config.global.debugMode) {
                console.error(e);
            }
            return [];
        }

        try {
            neonLog('debug', `Parsing content for ${driver.name} (type: ${contentType}).`, 'PARSE');
            // Pass both cheerio and original rawContent/jsonData for flexibility
            const results = await driver.parseResults(cheerioInstance, jsonData || rawContent, parserOptions);

            if (!Array.isArray(results)) {
                neonLog('warn', `Driver ${driver.name} did not return an array from parseResults.`, 'PARSE_WARN');
                return [];
            }

            // Standardize and enrich results
            return results.map(r => ({
                id: r.id || this._generateUniqueId(r.url, r.title), // Generate a stable ID
                title: r.title || 'Untitled',
                url: r.url || '',
                thumbnail: r.thumbnail || '',
                duration: r.duration || null, // In seconds or 'HH:MM:SS'
                views: r.views || null,
                source: r.source || driver.name,
                type: r.type || parserOptions.type, // 'videos' or 'gifs'
                tags: Array.isArray(r.tags) ? r.tags : (typeof r.tags === 'string' ? r.tags.split(',').map(tag => tag.trim()) : []),
                // Add any other common fields and ensure their types
            })).filter(r => r.url); // Filter out results without a URL
        } catch (error) {
            neonLog('error', `Error during parsing for ${driver.name}: ${error.message}`, 'PARSE_ERROR');
            if (this.config.global.debugMode) {
                console.error(error);
            }
            return [];
        }
    }

    /**
     * Generates a stable unique ID for a result.
     * @private
     * @param {string} url
     * @param {string} title
     * @returns {string}
     */
    _generateUniqueId(url, title) {
        if (url) {
            // Simple hash for URL
            let hash = 0;
            for (let i = 0; i < url.length; i++) {
                const char = url.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash |= 0; // Convert to 32bit integer
            }
            return `url_${Math.abs(hash)}`;
        }
        // Fallback, less reliable
        return `anon_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    }

    /**
     * Deduplicates search results based on URL.
     * @private
     * @param {Array<object>} results - Array of raw search results.
     * @returns {Array<object>} Deduplicated results.
     */
    _deduplicateResults(results) {
        if (!this.config.global.deduplicateResults) {
            neonLog('debug', 'Deduplication skipped (config).', 'Deduplicate');
            return results;
        }

        const seenUrls = new Set();
        const uniqueResults = [];
        for (const result of results) {
            if (result.url && !seenUrls.has(result.url)) {
                seenUrls.add(result.url);
                uniqueResults.push(result);
            }
        }
        neonLog('info', `Deduplicated ${results.length - uniqueResults.length} items. Total unique: ${uniqueResults.length}.`, 'Deduplicate');
        return uniqueResults;
    }

    /**
     * Performs a search across configured platforms.
     * @param {object} options - Search options.
     * @param {string} options.query - The search query.
     * @param {number} [options.page=1] - The page number to retrieve.
     * @param {'videos'|'gifs'} [options.type='videos'] - The type of content to search for ('videos' or 'gifs').
     * @param {boolean|object} [options.useMockData=false] - Whether to use mock data. Can be a boolean or an object like `{ driverName: true }`.
     * @param {string} [options.platform=null] - Specific platform to search on (e.g., 'Pornhub'). If null, search all.
     * @returns {Promise<Array<object>>} An array of search results.
     * @throws {Error} If query is missing or type is invalid.
     */
    async search(options) {
        const { query, page = 1, type = 'videos', useMockData = false, platform = null } = options;

        if (!query) throw new Error("Search query is required.");
        if (!['videos', 'gifs'].includes(type)) throw new Error(`Invalid search type: ${type}. Must be 'videos' or 'gifs'.`);

        const startTime = process.hrtime.bigint();
        neonLog('info', `Starting search for "${query}" (type: ${type}, page: ${page}, platform: ${platform || 'all'})`, 'SEARCH');

        let driversToSearch = Object.values(this.drivers);
        if (platform) {
            const normalizedPlatform = platform.toLowerCase();
            const specificDriver = this.drivers[normalizedPlatform];
            if (!specificDriver) {
                neonLog('warn', `Platform '${platform}' not found or not loaded. Searching all available platforms instead.`, 'SEARCH');
                // Optionally throw an error or return empty if strict platform is desired
                // throw new Error(`Platform '${platform}' not found or not loaded.`);
            } else {
                driversToSearch = [specificDriver];
            }
        }

        const limit = pLimit(this.config.global.maxConcurrentSearches); // Initialize concurrency limiter

        const searchPromises = driversToSearch.map(driver => limit(async () => {
            let getUrlMethod;
            let driverSupportsType = false;

            if (type === 'videos' && driver.supportsVideos) {
                getUrlMethod = driver.getVideoSearchUrl;
                driverSupportsType = true;
            } else if (type === 'gifs' && driver.supportsGifs) {
                getUrlMethod = driver.getGifSearchUrl;
                driverSupportsType = true;
            }

            if (!driverSupportsType || typeof getUrlMethod !== 'function') {
                neonLog('debug', `${driver.name} does not support '${type}' searches.`, 'SEARCH');
                return [];
            }

            try {
                const searchUrl = getUrlMethod.call(driver, query, page);
                if (!searchUrl) {
                    neonLog('warn', `${driver.name} returned no search URL for query "${query}" page ${page} type ${type}.`, 'SEARCH');
                    return [];
                }

                const rawContent = await this._fetch(driver, searchUrl, useMockData, page, type);
                return await this._parse(driver, rawContent, { type, sourceName: driver.name, query, page });
            } catch (error) {
                neonLog('error', `Error searching on ${driver.name}: ${error.message}`, 'SEARCH_FAIL');
                if (this.config.global.debugMode) {
                    console.error(error);
                }
                return [];
            }
        }));

        const settledResults = await Promise.allSettled(searchPromises);
        let successfulResults = settledResults
            .filter(res => res.status === 'fulfilled' && Array.isArray(res.value))
            .flatMap(res => res.value);

        if (this.config.global.deduplicateResults) {
            successfulResults = this._deduplicateResults(successfulResults);
        }

        const endTime = process.hrtime.bigint();
        const durationMs = Number(endTime - startTime) / 1_000_000;
        neonLog('info', `Search completed in ${durationMs.toFixed(2)} ms. Found a total of ${successfulResults.length} results.`, 'SEARCH');

        return successfulResults;
    }
}

module.exports = Pornsearch;