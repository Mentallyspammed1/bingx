'use strict';

const fs = require('fs').promises;
const path =require('path');
const cheerio = require('cheerio');
const { fetchWithRetry, getRandomUserAgent } = require('./modules/driver-utils.js');

const MOCK_DATA_DIR = path.join(__dirname, 'modules', 'mock_html_data');

class Pornsearch {
    constructor(config) {
        this.config = config;
        this.drivers = {}; // Store loaded drivers
        console.log('[Pornsearch] Orchestrator instance created.');
    }

    static async create(config) {
        const instance = new Pornsearch(config);
        await instance._initializeAndRegisterDrivers();
        return instance;
    }

    async _initializeAndRegisterDrivers() {
        console.log('[Pornsearch] Initializing and registering drivers...');
        const modulesDir = path.join(__dirname, 'modules');
        try {
            const files = await fs.readdir(modulesDir);
            for (const file of files) {
                if ((file.endsWith('.js') || file.endsWith('.cjs')) && !['driver-utils.js', 'mockScraper.cjs'].includes(file)) {
                    try {
                        const driverPath = path.join(modulesDir, file);
                        let DriverClass = require(driverPath);
                        if (DriverClass && typeof DriverClass === 'object' && DriverClass.default) {
                            DriverClass = DriverClass.default;
                        }

                        if (typeof DriverClass !== 'function' || !DriverClass.prototype) {
                             console.error(`[DriverLoader] Skipped ${file}: Export is not a valid class/constructor.`);
                             continue;
                        }

                        const driverInstance = new DriverClass(); // Pass any necessary config/options here
                        const driverName = driverInstance.name;

                        if (!driverName || typeof driverName !== 'string') {
                            console.warn(`[DriverLoader] Skipped ${file}: Driver has no name.`);
                            continue;
                        }
                        
                        // Basic validation
                        if (typeof driverInstance.parseResults !== 'function' || !(driverInstance.supportsGifs || driverInstance.supportsVideos)) {
                            console.warn(`[DriverLoader] Skipped ${driverName}: Missing required methods (parseResults) or capabilities (supportsGifs/supportsVideos).`);
                            continue;
                        }

                        this.drivers[driverName.toLowerCase()] = driverInstance;
                        console.log(`[DriverLoader] Successfully registered driver: ${driverName}`);

                    } catch (error) {
                        console.error(`[DriverLoader] Failed to load driver from ${file}:`, error);
                    }
                }
            }
        } catch (dirError) {
            console.error(`[DriverLoader] Failed to read modules directory:`, dirError);
        }
        console.log(`[Pornsearch] Driver registration complete. ${Object.keys(this.drivers).length} drivers loaded.`);
    }

    getAvailablePlatforms() {
        return Object.values(this.drivers).map(driver => driver.name);
    }

    async _fetch(driver, searchUrl, useMockData, page, searchType) {
        if (useMockData) {
            const normalizedDriverName = driver.name.toLowerCase().replace(/[\s.]+/g, '');
            const mockFileName = `${normalizedDriverName}_${searchType}_page${page}.html`;
            const mockFilePath = path.join(MOCK_DATA_DIR, mockFileName);
            try {
                return await fs.readFile(mockFilePath, 'utf8');
            } catch (fileError) {
                console.error(`[FETCH_MOCK_ERROR] Failed for ${driver.name}: ${fileError.message}`);
                return null;
            }
        }

        const options = {
            headers: {
                'User-Agent': getRandomUserAgent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Referer': driver.baseUrl,
                ...(typeof driver.getCustomHeaders === 'function' ? driver.getCustomHeaders() : {})
            },
            timeout: this.config.global.requestTimeout || 15000
        };

        const response = await fetchWithRetry(searchUrl, options);
        return response.data;
    }

    async _parse(driver, rawContent, parserOptions) {
        if (!rawContent) return [];
        
        let cheerioInstance = null;
        let jsonData = null;

        try {
            if (typeof rawContent === 'string' && rawContent.trim().startsWith('<')) {
                cheerioInstance = cheerio.load(rawContent);
            } else if (typeof rawContent === 'object' || (typeof rawContent === 'string' && rawContent.trim().startsWith('{'))) {
                jsonData = (typeof rawContent === 'string') ? JSON.parse(rawContent) : rawContent;
            } else {
                return [];
            }
        } catch (e) {
            console.error(`[PARSE_ERROR] Failed to load content for ${driver.name}: ${e.message}`);
            return [];
        }

        const results = await driver.parseResults(cheerioInstance, jsonData || rawContent, parserOptions);
        
        if (!Array.isArray(results)) {
            console.warn(`[PARSE_WARN] Driver ${driver.name} did not return an array.`);
            return [];
        }

        return results.map(r => ({
            ...r,
            source: r.source || driver.name,
            type: r.type || parserOptions.type
        }));
    }

    async search(options) {
        const { query, page = 1, type = 'videos', useMockData = false, platform = null } = options;

        if (!query) throw new Error("Search query is required.");
        if (!['videos', 'gifs'].includes(type)) throw new Error(`Invalid search type: ${type}`);

        console.log(`[SEARCH] Starting search for "${query}" (type: ${type}, page: ${page}, platform: ${platform || 'all'})`);

        let driversToSearch = Object.values(this.drivers);
        if (platform) {
            const normalizedPlatform = platform.toLowerCase();
            const specificDriver = this.drivers[normalizedPlatform];
            if (!specificDriver) {
                console.warn(`[SEARCH] Platform '${platform}' not found or not loaded.`);
                return [];
            }
            driversToSearch = [specificDriver];
        }

        const searchPromises = driversToSearch.map(async driver => {
            let getUrlMethod;
            if (type === 'videos' && driver.supportsVideos) getUrlMethod = driver.getVideoSearchUrl;
            else if (type === 'gifs' && driver.supportsGifs) getUrlMethod = driver.getGifSearchUrl;
            else return [];

            if (typeof getUrlMethod !== 'function') return [];

            try {
                const searchUrl = getUrlMethod.call(driver, query, page);
                if (!searchUrl) return [];

                const rawContent = await this._fetch(driver, searchUrl, useMockData, page, type);
                return await this._parse(driver, rawContent, { type, sourceName: driver.name, query, page });
            } catch (error) {
                console.error(`[SEARCH_FAIL] Error searching on ${driver.name}:`, error.message);
                return [];
            }
        });

        const settledResults = await Promise.allSettled(searchPromises);
        const successfulResults = settledResults
            .filter(res => res.status === 'fulfilled' && Array.isArray(res.value))
            .flatMap(res => res.value);
            
        console.log(`[SEARCH] Completed. Found a total of ${successfulResults.length} results.`);
        return successfulResults;
    }
}

module.exports = Pornsearch;
