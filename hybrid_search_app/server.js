// server.js - Hybrid Backend Server

// --- Setup & Dependencies ---
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const Pornsearch = require('pornsearch');
// axios and cheerio are primarily dependencies of the custom scraper modules / AbstractModule

// --- Constants ---
const app = express();
const PORT = process.env.PORT || 3000;

// --- Global Configuration & Strategy ---
let globalStrategy = 'custom'; // Default if config loading fails
let siteStrategies = {};
let loadedCustomScrapers = {};

// Load configuration from config.json
try {
    const configPath = path.resolve(__dirname, 'config.json');
    if (fs.existsSync(configPath)) {
        const rawConfig = fs.readFileSync(configPath);
        const config = JSON.parse(rawConfig);

        globalStrategy = process.env.BACKEND_STRATEGY || config.defaultStrategy || 'custom';
        siteStrategies = config.siteOverrides || {};

        const customScrapersMap = config.customScrapersMap || {};
        for (const key in customScrapersMap) {
            try {
                const scraperPath = path.resolve(__dirname, customScrapersMap[key]);
                if (fs.existsSync(scraperPath)) {
                    loadedCustomScrapers[key.toLowerCase()] = require(scraperPath); // Ensure keys are lowercase for lookup
                    console.log(`[CONFIG] Successfully loaded custom scraper for ${key} from ${scraperPath}`);
                } else {
                    console.error(`[CONFIG_ERROR] Custom scraper module file not found for ${key}: ${scraperPath}`);
                }
            } catch (err) {
                console.error(`[CONFIG_ERROR] Failed to load custom scraper module for ${key} from ${customScrapersMap[key]}:`, err.message);
            }
        }
        console.log('[CONFIG] Configuration loaded successfully from config.json');
    } else {
        console.warn('[CONFIG_WARN] config.json not found. Using default global strategy and no site overrides or custom scrapers.');
        globalStrategy = process.env.BACKEND_STRATEGY || 'custom';
    }
} catch (err) {
    console.error('[CONFIG_ERROR] Failed to load or parse config.json:', err);
    globalStrategy = process.env.BACKEND_STRATEGY || 'custom';
}

// --- Logging Configuration (Basic) ---
const log = {
    info: (message, ...args) => console.log(`[INFO] ${new Date().toISOString()}: ${message}`, ...args),
    error: (message, ...args) => console.error(`[ERROR] ${new Date().toISOString()}: ${message}`, ...args),
    warn: (message, ...args) => console.warn(`[WARN] ${new Date().toISOString()}: ${message}`, ...args),
    debug: (message, ...args) => {
        if (process.env.DEBUG === 'true') {
            console.log(`[DEBUG] ${new Date().toISOString()}: ${message}`, ...args);
        }
    }
};

log.info(`Initial Global Backend Strategy set to: ${globalStrategy}`);
log.info('Site-specific strategies:', siteStrategies);
log.info(`Loaded ${Object.keys(loadedCustomScrapers).length} custom scrapers: ${Object.keys(loadedCustomScrapers).join(', ')}`);

// --- Middleware ---
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public'))); // Serve static files from public/

// --- Handler Functions ---
async function handlePornsearchRequest(params) {
    log.info(`[Pornsearch Handler] Processing request for driver '${params.driver}' with query '${params.query}', type '${params.type}', page ${params.page}.`);
    try {
        const search = new Pornsearch(params.query, params.driver); // pornsearch library expects driver name directly
        let results;
        if (params.type === 'gifs') {
            if (typeof search.gifs !== 'function') {
                 throw { status: 501, message: `GIF search not supported by 'pornsearch' library for driver '${params.driver}'.` };
            }
            results = await search.gifs(params.page);
        } else {
            if (typeof search.videos !== 'function') {
                 throw { status: 501, message: `Video search not supported by 'pornsearch' library for driver '${params.driver}'.` };
            }
            results = await search.videos(params.page);
        }
        log.info(`[Pornsearch Handler] Found ${results ? results.length : 0} results for ${params.driver}.`);
        return {
            message: `'pornsearch' library results for ${params.query} on ${params.driver}`,
            data: results || []
        };
    } catch (error) {
        log.error(`[Pornsearch Handler] Error searching with pornsearch for driver '${params.driver}':`, error.message);
        throw { status: 502, message: `Error from pornsearch driver '${params.driver}': ${error.message}` };
    }
}

async function handleCustomScraperRequest(driver, params) {
    const driverKey = driver.toLowerCase();
    log.info(`[Custom Scraper Handler] Processing request for driver '${driverKey}' with query '${params.query}', type '${params.type}', page ${params.page}.`);
    const ScraperClass = loadedCustomScrapers[driverKey];

    if (!ScraperClass) {
        log.error(`[Custom Scraper Handler] Custom scraper for driver '${driverKey}' not found.`);
        throw { status: 404, message: `Custom scraper for driver '${driverKey}' not found or not loaded.` };
    }

    try {
        const scraperInstance = new ScraperClass({
            query: params.query,
            driverName: driverKey,
            page: params.page
        });

        let resultsData;
        if (params.type === 'gifs') {
            if (typeof scraperInstance.searchGifs !== 'function') {
                throw { status: 501, message: `GIF search (searchGifs method) not implemented by custom scraper for '${driverKey}'.` };
            }
            log.debug(`[Custom Scraper Handler] Calling searchGifs for ${driverKey}...`);
            resultsData = await scraperInstance.searchGifs(params.query, params.page);
        } else {
            if (typeof scraperInstance.searchVideos !== 'function') {
                throw { status: 501, message: `Video search (searchVideos method) not implemented by custom scraper for '${driverKey}'.` };
            }
            log.debug(`[Custom Scraper Handler] Calling searchVideos for ${driverKey}...`);
            resultsData = await scraperInstance.searchVideos(params.query, params.page);
        }

        log.info(`[Custom Scraper Handler] Custom scraper for ${driverKey} (type: ${params.type}) returned ${resultsData ? resultsData.length : 0} results.`);
        return {
            message: `Results from custom scraper '${driverKey}' for query '${params.query}' (type: ${params.type})`,
            data: resultsData || []
        };
    } catch (error) {
        log.error(`[Custom Scraper Handler] Error with custom scraper for driver '${driverKey}' (type: ${params.type}):`, error.message, error.stack);
        if (error.status) throw error;
        throw { status: 500, message: `Error processing custom scraper for '${driverKey}': ${error.message}` };
    }
}

// --- API Search Endpoint ---
app.get('/api/search', async (req, res) => {
    log.debug('[/api/search] Received request. Query params:', req.query);
    const { query, driver, type = 'videos', page = '1' } = req.query;

    if (!query) {
        log.warn('[/api/search] Bad Request: Missing query parameter.');
        return res.status(400).json({ error: 'Missing required parameter: query' });
    }
    if (!driver) {
        log.warn('[/api/search] Bad Request: Missing driver parameter.');
        return res.status(400).json({ error: 'Missing required parameter: driver (site/source)' });
    }

    let pageNumber;
    try {
        pageNumber = parseInt(page, 10);
        if (isNaN(pageNumber) || pageNumber < 0) { // Allow page 0 if scrapers handle it (e.g. xvideos)
             log.warn(`[/api/search] Bad Request: Invalid page number '${page}'. Using default page of scraper.`);
             pageNumber = undefined; // Let scraper use its default firstpage
        }
    } catch(e){
        log.warn(`[/api/search] Bad Request: Could not parse page number '${page}'. Using default page of scraper.`);
        pageNumber = undefined;
    }


    const searchParams = { query, driver: driver.toLowerCase(), type: type.toLowerCase(), page: pageNumber };
    const driverKey = searchParams.driver;
    const effectiveStrategy = siteStrategies[driverKey] || globalStrategy;
    log.info(`[/api/search] Effective strategy for driver '${driverKey}': ${effectiveStrategy}`);

    try {
        let responsePayload;
        if (effectiveStrategy === 'pornsearch') {
            responsePayload = await handlePornsearchRequest(searchParams);
        } else if (effectiveStrategy === 'custom') {
            responsePayload = await handleCustomScraperRequest(driverKey, searchParams);
        } else {
            log.error(`[/api/search] Unknown or unsupported strategy '${effectiveStrategy}' for driver '${driverKey}'.`);
            return res.status(501).json({ error: `Strategy '${effectiveStrategy}' not implemented for driver '${driverKey}'.` });
        }
        res.status(200).json(responsePayload);

    } catch (error) {
        log.error('[/api/search] Error during search processing:', error.message, error.status ? `Status: ${error.status}` : '', error.stack);
        const statusCode = error.status || 500;
        const responseMessage = error.message || 'An internal server error occurred.';
        res.status(statusCode).json({ error: responseMessage });
    }
});

// --- Root Route ---
app.get('/', (req, res) => {
    // Serve index.html from public directory
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// --- Start Server & Export ---
let serverInstance = null;

if (require.main === module) {
    // If this script is run directly, start the server.
    serverInstance = app.listen(PORT, '0.0.0.0', () => {
        log.info(`Hybrid backend server started on http://0.0.0.0:${PORT}`);
        log.info(`Current Global Backend Strategy: ${globalStrategy}`);
        log.info(`Access frontend at http://localhost:${PORT}`);
    });

    // Graceful shutdown for direct execution
    const gracefulShutdown = (signal) => {
        log.info(`${signal} signal received, closing server gracefully.`);
        if (serverInstance) {
            serverInstance.close(() => {
                log.info('Server closed.');
                process.exit(0);
            });
        } else {
            process.exit(0);
        }
    };
    process.on('SIGINT', () => gracefulShutdown('SIGINT'));
    process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
}

// Export the Express app instance for testing or programmatic use.
// Test files will be responsible for starting their own server with this app.
module.exports = app;
