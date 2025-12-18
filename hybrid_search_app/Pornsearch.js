'use strict'

const fs = require('fs').promises
const path = require('path')
const cheerio = require('cheerio')
let pLimitModule

// Dynamically import p-limit as it's an ESM module
async function loadPLimit() {
    if (!pLimitModule) {
        pLimitModule = await import('p-limit')
    }
    return pLimitModule.default
}
const log = require('./core/log.js')
const { fetchWithRetry, getRandomUserAgent } = require('./modules/driver-utils.js')

const MOCK_DATA_DIR = path.join(__dirname, 'modules', 'mock_html_data')

/**
 * @typedef {object} PornsearchConfig
 * @property {object} global - Global configuration settings.
 * @property {number} global.requestTimeout - Default timeout for HTTP requests in ms.
 * @property {number} global.maxConcurrentSearches - Maximum concurrent driver searches.
 * @property {boolean} global.deduplicateResults - Whether to deduplicate results across drivers.
 * @property {boolean} global.debugMode - Enable debug logging.
 * @property {object} [customScrapers] - A map of custom scraper classes to register.
 */

class Pornsearch {
    /**
     * @type {PornsearchConfig}
     */
    config

    /**
     * Stores loaded driver instances.
     * @type {Object.<string, import('./core/AbstractModule')>}
     */
    drivers = {}
    logger

    /**
     * @private
     * @param {PornsearchConfig} config - Configuration object for Pornsearch.
     */
    constructor(config) {
        this.config = this._validateConfig(config)
        this.logger = log
        this.logger.info('Orchestrator instance created.')
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
                requestTimeout: 20000,
                maxConcurrentSearches: 5,
                deduplicateResults: true,
                debugMode: false,
            },
            customScrapers: {}
        }

        const config = {
            ...defaultConfig,
            ...userConfig,
            global: { ...defaultConfig.global, ...(userConfig ? userConfig.global : {}) },
            customScrapers: { ...defaultConfig.customScrapers, ...(userConfig ? userConfig.customScrapers : {}) }
        }

        if (config.global.debugMode) {
            log.level = 'debug'
            log.debug('Debug mode enabled.', { component: 'Config' })
        }
        log.info(`Using config: ${JSON.stringify(config.global)}`, { component: 'Config' })
        return config
    }

    /**
     * Static factory method to create and initialize the Pornsearch instance.
     * @param {PornsearchConfig} config - Configuration for the Pornsearch instance.
     * @returns {Promise<Pornsearch>}
     */
    static async create(config) {
        const instance = new Pornsearch(config)
        await instance._initializeAndRegisterDrivers()
        return instance
    }

    /**
     * Registers a driver instance after validation.
     * @private
     * @param {Function} DriverClass - The driver class constructor.
     * @param {string} source - The source of the driver (filename or custom name).
     * @param {object} logger - The logger instance to use.
     */
    _registerDriver(DriverClass, source, logger) {
        let ActualClass = DriverClass
        if (ActualClass && typeof ActualClass === 'object' && ActualClass.default) {
            ActualClass = ActualClass.default
        }

        if (typeof ActualClass !== 'function' || !ActualClass.prototype) {
            logger.error(`Skipped ${source}: Export is not a valid class/constructor.`)
            return
        }

        const driverInstance = new ActualClass()
        const driverName = driverInstance.name

        if (!driverName || typeof driverName !== 'string') {
            logger.warn(`Skipped ${source}: Driver has no 'name' property or it's not a string.`)
            return
        }

        if (!driverInstance.hasVideoSupport() && !driverInstance.hasGifSupport()) {
            logger.warn(`Skipped ${driverName}: Driver must support either videos or GIFs.`)
            return
        }

        if (this.drivers[driverName.toLowerCase()]) {
            logger.warn(`Overwriting already registered driver: ${driverName}`)
        }

        this.drivers[driverName.toLowerCase()] = driverInstance
        logger.info(`Successfully registered driver: ${driverName}`)
    }

    /**
     * Initializes and registers all available drivers.
     * @private
     * @returns {Promise<void>}
     */
    async _initializeAndRegisterDrivers() {
        this.logger.info('Initializing and registering drivers...')
        const driverLoaderLogger = this.logger.child({ component: 'DriverLoader' })

        const modulesDir = path.join(__dirname, 'modules')
        try {
            const files = await fs.readdir(modulesDir)
            for (const file of files) {
                if ((file.endsWith('.js') || file.endsWith('.cjs')) && !['driver-utils.js', 'mockScraper.cjs'].includes(file)) {
                    try {
                        const driverPath = path.join(modulesDir, file)
                        const DriverClass = require(driverPath)
                        this._registerDriver(DriverClass, file, driverLoaderLogger)
                    } catch (error) {
                        driverLoaderLogger.error(`Failed to load driver from ${file}: ${error.message}`)
                        if (this.config.global.debugMode) console.error(error)
                    }
                }
            }
        } catch (dirError) {
            driverLoaderLogger.error(`Failed to read modules directory: ${dirError.message}`)
            if (this.config.global.debugMode) console.error(dirError)
        }

        if (this.config.customScrapers && Object.keys(this.config.customScrapers).length > 0) {
            this.logger.info('Loading custom scrapers from config...')
            for (const [name, DriverClass] of Object.entries(this.config.customScrapers)) {
                try {
                    this._registerDriver(DriverClass, `custom scraper '${name}'`, driverLoaderLogger)
                } catch (error) {
                    driverLoaderLogger.error(`Failed to load custom scraper '${name}': ${error.message}`)
                    if (this.config.global.debugMode) console.error(error)
                }
            }
        }

        this.logger.info(`Driver registration complete. ${Object.keys(this.drivers).length} drivers loaded.`)
    }

    getAvailablePlatforms() {
        return Object.values(this.drivers).map(driver => ({
            name: driver.name,
            supportsVideos: driver.hasVideoSupport(),
            supportsGifs: driver.hasGifSupport(),
        }))
    }

    async _fetch(driver, searchUrl, useMockData, page, searchType) {
        const useMockForThisDriver = typeof useMockData === 'object'
            ? useMockData[driver.name.toLowerCase()]
            : useMockData

        if (useMockForThisDriver) {
            const normalizedDriverName = driver.name.toLowerCase().replace(/[\s.]+/g, '')
            const mockFileName = `${normalizedDriverName}_${searchType}_page${page}.html`
            const mockFilePath = path.join(MOCK_DATA_DIR, mockFileName)
            try {
                const mockContent = await fs.readFile(mockFilePath, 'utf8')
                this.logger.debug(`Loaded mock data for ${driver.name} from ${mockFileName}`, { component: 'FETCH_MOCK' })
                return mockContent
            } catch (fileError) {
                this.logger.error(`Failed to load mock data for ${driver.name} (${mockFileName}): ${fileError.message}`, { component: 'FETCH_MOCK_ERROR' })
                return null // Return null if mock data not found
            }
        } else { // Only fetch from live site if useMockData is false
            const options = {
                headers: {
                    'User-Agent': getRandomUserAgent(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Referer': driver.baseUrl || searchUrl,
                    ...(typeof driver.getCustomHeaders === 'function' ? driver.getCustomHeaders() : {})
                },
                timeout: this.config.global.requestTimeout
            }

            try {
                this.logger.debug(`Fetching ${searchUrl} for ${driver.name}`, { component: 'FETCH' })
                const response = await fetchWithRetry(searchUrl, options)
                return response.data
            } catch (error) {
                this.logger.error(`Fetch failed for ${driver.name} at ${searchUrl}: ${error.message}`, { component: 'FETCH_ERROR' })
                return null
            }
        }
    }

    async _parse(driver, rawContentWrapper, parserOptions) {
        const { content: rawContent, isMock } = rawContentWrapper

        if (!rawContent) {
            this.logger.debug(`No raw content to parse for ${driver.name}.`, { component: 'PARSE' })
            return []
        }

        let cheerioInstance = null
        let jsonData = null

        try {
            if (typeof rawContent === 'string') {
                const trimmedContent = rawContent.trim()
                if (trimmedContent.startsWith('<')) {
                    cheerioInstance = cheerio.load(trimmedContent)
                } else if (trimmedContent.startsWith('{') || trimmedContent.startsWith('[')) {
                    jsonData = JSON.parse(trimmedContent)
                }
            } else if (typeof rawContent === 'object') {
                jsonData = rawContent
            } else {
                this.logger.warn(`Invalid raw content type for ${driver.name}: ${typeof rawContent}.`, { component: 'PARSE' })
                return []
            }
        } catch (e) {
            this.logger.error(`Failed to prepare content for parsing ${driver.name}: ${e.message}`, { component: 'PARSE_ERROR' })
            if (this.config.global.debugMode) console.error(e)
            return []
        }

        try {
            this.logger.debug(`Parsing content for ${driver.name}.`, { component: 'PARSE' })
            const results = await driver.parseResults(cheerioInstance, jsonData || rawContent, parserOptions)

            if (!Array.isArray(results)) {
                this.logger.warn(`Driver ${driver.name} did not return an array from parseResults.`, { component: 'PARSE_WARN' })
                return []
            }

            return results.map(r => ({
                id: r.id || this._generateUniqueId(r.url, r.title),
                title: r.title || 'Untitled',
                url: r.url || '',
                thumbnail: r.thumbnail || '',
                duration: r.duration || null,
                views: r.views || null,
                source: r.source || driver.name,
                type: r.type || parserOptions.type,
                tags: Array.isArray(r.tags) ? r.tags : [],
            })).filter(r => r.url)
        } catch (error) {
            this.logger.error(`Error during parsing for ${driver.name}: ${error.message}`, { component: 'PARSE_ERROR' })
            if (this.config.global.debugMode) console.error(error)
            return []
        }
    }

    _generateUniqueId(url, title) {
        if (url) {
            let hash = 0
            for (let i = 0; i < url.length; i++) {
                hash = ((hash << 5) - hash) + url.charCodeAt(i)
                hash |= 0
            }
            return `url_${Math.abs(hash)}`
        }
        return `anon_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`
    }

    _deduplicateResults(results) {
        if (!this.config.global.deduplicateResults) {
            this.logger.debug('Deduplication skipped (config).', { component: 'Deduplicate' })
            return results
        }

        const seenUrls = new Set()
        const uniqueResults = []
        for (const result of results) {
            if (result.url && !seenUrls.has(result.url)) {
                seenUrls.add(result.url)
                uniqueResults.push(result)
            }
        }
        this.logger.info(`Deduplicated ${results.length - uniqueResults.length} items. Total unique: ${uniqueResults.length}.`, { component: 'Deduplicate' })
        return uniqueResults
    }

    async search(options) {
        const { query, page = 1, type = 'videos', useMockData = false, platform = null } = options

        if (!query) throw new Error("Search query is required.")
        if (!['videos', 'gifs'].includes(type)) throw new Error(`Invalid search type: ${type}. Must be 'videos' or 'gifs'.`)

        const startTime = process.hrtime.bigint()
        this.logger.info(`Starting search for "${query}" (type: ${type}, page: ${page}, platform: ${platform || 'all'})`, { component: 'SEARCH' })

        let driversToSearch = Object.values(this.drivers)
        if (platform) {
            const normalizedPlatform = platform.toLowerCase()
            const specificDriver = this.drivers[normalizedPlatform]
            if (!specificDriver) {
                throw new Error(`Platform '${platform}' not found or not loaded.`)
            }
            driversToSearch = [specificDriver]
        }

        const { default: pLimit } = await loadPLimit()
        const limit = pLimit(this.config.global.maxConcurrentSearches)

        const searchPromises = driversToSearch.map(driver => limit(async () => {
            let getUrlMethod
            let driverSupportsType = false

            if (type === 'videos' && driver.hasVideoSupport()) {
                getUrlMethod = driver.getVideoSearchUrl
                driverSupportsType = true
            } else if (type === 'gifs' && driver.hasGifSupport()) {
                getUrlMethod = driver.getGifSearchUrl
                driverSupportsType = true
            }

            if (!driverSupportsType || typeof getUrlMethod !== 'function') {
                this.logger.debug(`${driver.name} does not support '${type}' searches.`, { component: 'SEARCH' })
                return []
            }

            try {
                const searchUrl = getUrlMethod.call(driver, query, page)
                if (!searchUrl) {
                    this.logger.warn(`${driver.name} returned no search URL for query "${query}" page ${page} type ${type}.`, { component: 'SEARCH' })
                    return []
                }

                const rawContent = await this._fetch(driver, searchUrl, useMockData, page, type)
                return await this._parse(driver, rawContent, { type, sourceName: driver.name, query, page })
            } catch (error) {
                this.logger.error(`Error searching on ${driver.name}: ${error.message}`, { component: 'SEARCH_FAIL' })
                if (this.config.global.debugMode) console.error(error)
                return []
            }
        }))

        const settledResults = await Promise.allSettled(searchPromises)
        let successfulResults = settledResults
            .filter(res => res.status === 'fulfilled' && Array.isArray(res.value))
            .flatMap(res => res.value)

        if (this.config.global.deduplicateResults) {
            successfulResults = this._deduplicateResults(successfulResults)
        }

        const endTime = process.hrtime.bigint()
        const durationMs = Number(endTime - startTime) / 1_000_000
        this.logger.info(`Search completed in ${durationMs.toFixed(2)} ms. Found ${successfulResults.length} results.`, { component: 'SEARCH' })

        return successfulResults
    }
}

module.exports = Pornsearch
