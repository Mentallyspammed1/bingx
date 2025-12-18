// server.js - Hybrid Backend Server (Enhanced)
require('dotenv').config()
const express = require('express')
const cors = require('cors')
const path = require('path')
const fs = require('fs')
const helmet = require('helmet')
const rateLimit = require('express-rate-limit')
const log = require('./core/log.js') // Centralized logger
const PornsearchOrchestrator = require('./Pornsearch.js')

// --- Constants & Configurations ---
const app = express()
const PORT = process.env.PORT || 3003
const CACHE_DURATION_MS = parseInt(process.env.CACHE_DURATION_MS || (5 * 60 * 1000), 10)
const CONFIG_FILE_PATH = path.resolve(__dirname, 'config.json')

const cache = new Map()
let appConfig = { defaultStrategy: 'custom', siteOverrides: {}, customScrapersMap: {} }
let pornsearchOrchestrator

/**
 * Loads application configuration from config.json.
 */
function loadConfig() {
    try {
        if (fs.existsSync(CONFIG_FILE_PATH)) {
            const rawConfig = fs.readFileSync(CONFIG_FILE_PATH, 'utf8')
            appConfig = JSON.parse(rawConfig)
            log.info(`[CONFIG] Configuration loaded successfully from ${CONFIG_FILE_PATH}`)
        } else {
            log.warn(`[CONFIG_WARN] config.json not found. Using default configuration.`)
        }
    } catch (err) {
        log.error(`[CONFIG_ERROR] Failed to load or parse config.json: ${err.message}`)
    }
}

/**
 * Watches the config.json file for changes and reloads the configuration.
 */
function watchConfig() {
    fs.watch(CONFIG_FILE_PATH, (eventType, filename) => {
        if (filename && eventType === 'change') {
            log.info(`[CONFIG_WATCH] ${filename} changed. Reloading configuration and re-initializing orchestrator...`)
            loadConfig()
            initializeOrchestrator().catch(err => {
                log.error('[CONFIG_WATCH] Failed to re-initialize orchestrator after config change.', err)
            })
        }
    })
    log.info(`[CONFIG_WATCH] Watching for changes in ${CONFIG_FILE_PATH}`)
}

/**
 * Initializes the Pornsearch Orchestrator.
 */
async function initializeOrchestrator() {
    try {
        const dynamicScrapers = {}
        if (appConfig.customScrapersMap) {
            for (const [platformKey, scraperPath] of Object.entries(appConfig.customScrapersMap)) {
                try {
                    const absoluteScraperPath = path.resolve(__dirname, scraperPath)
                    delete require.cache[require.resolve(absoluteScraperPath)] // Allow hot-reloading
                    dynamicScrapers[platformKey] = require(absoluteScraperPath)
                    log.info(`[ORCHESTRATOR] Loaded custom scraper for '${platformKey}' from ${absoluteScraperPath}`)
                } catch (loadError) {
                    log.error(`[ORCHESTRATOR_ERROR] Failed to load custom scraper for '${platformKey}': ${loadError.message}`)
                }
            }
        }

        pornsearchOrchestrator = await PornsearchOrchestrator.create({
            global: {
                debugMode: process.env.NODE_ENV !== 'production',
                requestTimeout: parseInt(process.env.REQUEST_TIMEOUT, 10) || 20000,
                maxConcurrentSearches: parseInt(process.env.MAX_CONCURRENT_SEARCHES, 10) || 5,
            },
            customScrapers: dynamicScrapers
        })

        log.info('PornsearchOrchestrator created and drivers registered successfully.')
        const platformNames = pornsearchOrchestrator.getAvailablePlatforms().map(p => p.name)
        log.info(`Available Platforms: ${platformNames.join(', ')}`)

    } catch (err) {
        log.error('Failed to create PornsearchOrchestrator:', err)
        throw err // Re-throw to be caught by startup logic
    }
}

// --- Middleware ---
app.use(helmet())
app.use(cors())
app.use(express.json())
app.use('/api/', rateLimit({
    windowMs: 60 * 1000,
    max: 100,
    message: "Too many requests from this IP, please try again after a minute.",
    standardHeaders: true,
    legacyHeaders: false,
}))
app.use(express.static(path.join(__dirname, 'public')))

// --- API Endpoints ---
app.get('/api/search', async (req, res, next) => {
    const { query, driver, type = 'videos', page = '1' } = req.query

    if (!query) {
        return res.status(400).json({ error: 'Missing required parameter: query' })
    }

    const pageNumber = parseInt(page, 10) || 1
    if (pageNumber <= 0) {
        return res.status(400).json({ error: 'Page number must be positive.' })
    }

    const platform = driver ? driver.toLowerCase() : null // null means search all
    const cacheKey = `${platform || 'all'}-${type}-${query}-${pageNumber}`
    const cached = cache.get(cacheKey)

    if (cached && (Date.now() - cached.timestamp < CACHE_DURATION_MS)) {
        log.info(`[CACHE] HIT for key: ${cacheKey}`)
        return res.status(200).json(cached.data)
    }

    try {
        const useMockData = process.env.USE_MOCK_DATA === 'true'
        const resultsData = await pornsearchOrchestrator.search({
            query,
            platform,
            type: type.toLowerCase(),
            page: pageNumber,
            useMockData
        })

        const responsePayload = {
            message: `Results for query '${query}'`,
            query,
            platform: platform || 'all',
            type,
            page: pageNumber,
            results_count: resultsData.length,
            data: resultsData || [],
        }

        cache.set(cacheKey, { timestamp: Date.now(), data: responsePayload })
        log.info(`[SEARCH] Success for key: ${cacheKey}, found ${resultsData.length} results.`)
        res.status(200).json(responsePayload)

    } catch (error) {
        next(error) // Pass to the centralized error handler
    }
})

app.get('/api/drivers', (req, res) => {
    if (!pornsearchOrchestrator) {
        return res.status(503).json({ error: 'Orchestrator not yet available.' })
    }
    const platforms = pornsearchOrchestrator.getAvailablePlatforms()
    res.status(200).json({ platforms })
})

app.get('/api/health', (req, res) => {
    res.status(200).json({
        status: pornsearchOrchestrator ? 'ok' : 'degraded',
        message: pornsearchOrchestrator ? 'Orchestrator is initialized.' : 'Orchestrator not available.',
        uptime: `${process.uptime().toFixed(2)}s`
    })
})

// --- Root and Error Handling ---
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'))
})

app.use((err, req, res, next) => {
    log.error(`[GLOBAL_ERROR] ${err.message}`, { stack: err.stack })
    const statusCode = err.status || 500
    res.status(statusCode).json({
        error: err.message || 'An internal server error occurred.',
        ...(process.env.NODE_ENV !== 'production' && { stack: err.stack })
    })
})

// --- Server Startup ---
function startServer() {
    loadConfig()
    initializeOrchestrator().then(() => {
        watchConfig()
        app.listen(PORT, '0.0.0.0', () => {
            log.info(`Server started on http://localhost:${PORT}`)
            log.info(`Serving frontend from: ${path.join(__dirname, 'public')}`)
        })
    }).catch(err => {
        log.error('FATAL: Failed to start server due to orchestrator initialization error.', err)
        process.exit(1)
    })
}

if (require.main === module) {
    startServer()
}

process.on('SIGINT', () => {
    log.info('SIGINT received. Shutting down gracefully.')
    process.exit(0)
})
process.on('SIGTERM', () => {
    log.info('SIGTERM received. Shutting down gracefully.')
    process.exit(0)
})

module.exports = app