// server.js - Hybrid Backend Server

// --- Setup & Dependencies ---
require('dotenv').config() // Load environment variables from .env file first
const express = require('express')
const cors = require('cors') // Enable Cross-Origin Resource Sharing
const path = require('path') // Utility for handling file paths
const fs = require('fs') // File system module for reading config.json

// --- Dependencies for Handlers ---
const Pornsearch = require('pornsearch') // Main library for one strategy
// axios and cheerio are now primarily dependencies of the custom scraper modules / AbstractModule
// const axios = require('axios');
// const cheerio = require('cheerio');


// --- Constants ---
const app = express()
const PORT = process.env.PORT || 3000

// --- Global Configuration & Strategy ---
let globalStrategy
let siteStrategies = {}
let loadedCustomScrapers = {}

// Load configuration from config.json
try {
    const configPath = path.resolve(__dirname, 'config.json')
    if (fs.existsSync(configPath)) {
        const rawConfig = fs.readFileSync(configPath)
        const config = JSON.parse(rawConfig)

        globalStrategy = process.env.BACKEND_STRATEGY || config.defaultStrategy || 'custom'
        siteStrategies = config.siteOverrides || {}

        const customScrapersMap = config.customScrapersMap || {}
        for (const key in customScrapersMap) {
            try {
                const scraperPath = path.resolve(__dirname, customScrapersMap[key])
                if (fs.existsSync(scraperPath)) {
                    loadedCustomScrapers[key.toLowerCase()] = require(scraperPath)
                    console.log(`[CONFIG] Successfully loaded custom scraper for ${key} from ${scraperPath}`)
                } else {
                    console.error(`[CONFIG_ERROR] Custom scraper module file not found for ${key}: ${scraperPath}`)
                }
            } catch (err) {
                console.error(`[CONFIG_ERROR] Failed to load custom scraper module for ${key} from ${customScrapersMap[key]}:`, err.message)
            }
        }
        console.log('[CONFIG] Configuration loaded successfully from config.json')
    } else {
        console.warn('[CONFIG_WARN] config.json not found. Using default global strategy and no site overrides or custom scrapers.')
        globalStrategy = process.env.BACKEND_STRATEGY || 'custom' // Fallback if config.json is missing
    }
} catch (err) {
    console.error('[CONFIG_ERROR] Failed to load or parse config.json:', err)
    globalStrategy = process.env.BACKEND_STRATEGY || 'custom' // Fallback in case of error
}


// --- Logging Configuration (Basic) ---
const log = {
    info: (message, ...args) => console.log(`[INFO] ${new Date().toISOString()}: ${message}`, ...args),
    error: (message, ...args) => console.error(`[ERROR] ${new Date().toISOString()}: ${message}`, ...args),
    warn: (message, ...args) => console.warn(`[WARN] ${new Date().toISOString()}: ${message}`, ...args),
    debug: (message, ...args) => { // Only log debug if DEBUG env var is set (e.g., DEBUG=true)
        if (process.env.DEBUG === 'true') {
            console.log(`[DEBUG] ${new Date().toISOString()}: ${message}`, ...args)
        }
    }
}

log.info(`Initial Global Backend Strategy set to: ${globalStrategy}`)
log.info('Site-specific strategies:', siteStrategies)
log.info(`Loaded ${Object.keys(loadedCustomScrapers).length} custom scrapers.`)

// --- Middleware ---
app.use(cors()) // Enable CORS for all origins (consider restricting in production)
app.use(express.json()) // Parse JSON request bodies

// --- Placeholder Handler Functions ---

/**
 * Placeholder for handling requests using the 'pornsearch' library.
 * @param {object} params - Search parameters (query, driver, type, page).
 * @returns {Promise<object>} - A promise that resolves to the search results or error.
 */
async function handlePornsearchRequest(params) {
    log.info(`[Pornsearch Handler] Processing request for driver '${params.driver}' with query '${params.query}', type '${params.type}', page ${params.page}.`)
    try {
        const search = new Pornsearch(params.query, params.driver)
        let results
        if (params.type === 'gifs') {
            results = await search.gifs(params.page)
        } else { // Default to videos
            results = await search.videos(params.page)
        }
        log.info(`[Pornsearch Handler] Found ${results.length} results for ${params.driver}.`)
        return {
            message: `'pornsearch' library results for ${params.query} on ${params.driver}`,
            data: results || [] // Ensure data is always an array
        }
    } catch (error) {
        log.error(`[Pornsearch Handler] Error searching with pornsearch library for driver '${params.driver}':`, error.message)
        // Rethrow as a structured error for the main endpoint handler
        throw { status: 502, message: `Error from pornsearch driver '${params.driver}': ${error.message}` }
    }
}

/**
 * Placeholder for handling requests using custom scraper modules.
 * @param {string} driver - The specific site/driver to use.
 * @param {object} params - Search parameters (query, type, page).
 * @returns {Promise<object>} - A promise that resolves to the search results or error.
 */
async function handleCustomScraperRequest(driver, params) {
    log.info(`[Custom Scraper Handler] Processing request for driver '${driver}' with query '${params.query}', type '${params.type}', page ${params.page}.`)
    const ScraperClass = loadedCustomScrapers[driver.toLowerCase()]

    if (!ScraperClass) {
        log.error(`[Custom Scraper Handler] Custom scraper for driver '${driver}' not found.`)
        throw { status: 404, message: `Custom scraper for driver '${driver}' not found.` }
    }

    try {
        // Pass all relevant params to the constructor, matching AbstractModule
        const scraperInstance = new ScraperClass({
            query: params.query,
            driverName: driver, // Pass the driver name for potential use within the scraper
            page: params.page   // Pass the page for use in URL generation
        })

        let resultsData

        if (params.type === 'gifs') {
            if (typeof scraperInstance.searchGifs !== 'function') {
                throw { status: 501, message: `GIF search (searchGifs method) not implemented by custom scraper for '${driver}'.` }
            }
            log.debug(`[Custom Scraper Handler] Calling searchGifs for ${driver}...`)
            resultsData = await scraperInstance.searchGifs(params.query, params.page)
        } else { // Default to videos
            if (typeof scraperInstance.searchVideos !== 'function') {
                throw { status: 501, message: `Video search (searchVideos method) not implemented by custom scraper for '${driver}'.` }
            }
            log.debug(`[Custom Scraper Handler] Calling searchVideos for ${driver}...`)
            resultsData = await scraperInstance.searchVideos(params.query, params.page)
        }

        log.info(`[Custom Scraper Handler] Custom scraper for ${driver} (type: ${params.type}) returned ${resultsData.length} results.`)
        return {
            message: `Results from custom scraper '${driver}' for query '${params.query}' (type: ${params.type})`,
            data: resultsData || [] // Ensure data is always an array
        }

    } catch (error) {
        log.error(`[Custom Scraper Handler] Error with custom scraper for driver '${driver}' (type: ${params.type}):`, error.message)
        if (error.status) throw error // Rethrow structured errors
        throw { status: 500, message: `Error processing custom scraper for '${driver}': ${error.message}` }
    }
}


// --- API Search Endpoint ---
app.get('/api/search', async (req, res) => {
    log.debug('[/api/search] Received request. Query params:', req.query)
    const { query, driver, type = 'videos', page = '1' } = req.query // Defaults for type and page

    // Basic Validation
    if (!query) {
        log.warn('[/api/search] Bad Request: Missing query parameter.')
        return res.status(400).json({ error: 'Missing required parameter: query' })
    }
    if (!driver) {
        log.warn('[/api/search] Bad Request: Missing driver parameter.')
        return res.status(400).json({ error: 'Missing required parameter: driver (site/source)' })
    }

    const pageNumber = parseInt(page, 10)
    if (isNaN(pageNumber) || pageNumber < 1) {
        log.warn(`[/api/search] Bad Request: Invalid page number '${page}'. Defaulting to 1.`)
        // Although defaulting, it might be better to return 400 for invalid page format.
        // For now, let the handlers manage default page if this slips through.
    }

    const searchParams = { query, driver, type, page: pageNumber }

    // Determine strategy for this specific driver
    const driverKey = driver.toLowerCase()
    const effectiveStrategy = siteStrategies[driverKey] || globalStrategy
    log.info(`[/api/search] Effective strategy for driver '${driver}': ${effectiveStrategy}`)

    try {
        let responsePayload
        if (effectiveStrategy === 'pornsearch') {
            responsePayload = await handlePornsearchRequest(searchParams)
        } else if (effectiveStrategy === 'custom') {
            responsePayload = await handleCustomScraperRequest(driver, searchParams)
        } else {
            log.error(`[/api/search] Unknown or unsupported strategy '${effectiveStrategy}' for driver '${driver}'.`)
            return res.status(501).json({ error: `Strategy '${effectiveStrategy}' not implemented for driver '${driver}'.` })
        }
        res.status(200).json(responsePayload)

    } catch (error) {
        log.error('[/api/search] Error during search processing:', error.message, error.status ? `Status: ${error.status}` : '')
        const statusCode = error.status || 500 // Use status from error if available
        const responseMessage = error.message || 'An internal server error occurred.'
        res.status(statusCode).json({ error: responseMessage })
    }
})

// --- Root Route (Optional - for basic server info) ---
app.get('/', (req, res) => {
    res.status(200).send(
        `Hybrid Backend Server is running.\n` +
        `Global Strategy: ${globalStrategy}\n` +
        `Site Overrides: ${JSON.stringify(siteStrategies)}\n` +
        `Loaded Custom Scrapers: ${Object.keys(loadedCustomScrapers).join(', ') || 'None'}\n` +
        `API Endpoint: /api/search?query=...&driver=...[&type=videos|gifs][&page=1]`
    )
})

// --- Start Server ---
app.listen(PORT, '0.0.0.0', () => {
    log.info(`Hybrid backend server started on http://0.0.0.0:${PORT}`)
    log.info(`Current Global Backend Strategy: ${globalStrategy}`)
    log.info(`Access API at http://localhost:${PORT}/api/search`)
})

// --- Graceful Shutdown ---
process.on('SIGINT', () => {
    log.info('Shutdown signal received, closing server gracefully.')
    process.exit(0) // In a real app, you'd close DB connections, etc.
})

process.on('SIGTERM', () => {
    log.info('Termination signal received, closing server gracefully.')
    process.exit(0)
})
