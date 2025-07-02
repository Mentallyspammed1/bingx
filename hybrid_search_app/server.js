// server.js - Hybrid Backend Server

// --- Setup & Dependencies ---
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');

// Import the custom Pornsearch orchestrator
const PornsearchOrchestrator = require('./Pornsearch.js');
// Comment out or remove the npm package if not used to prevent MODULE_NOT_FOUND
// const PornsearchNpm = require('pornsearch');

// --- Constants ---
const app = express();
const PORT = process.env.PORT || 3000;

// --- Global Configuration & Strategy ---
let globalStrategy = 'custom';
let siteStrategies = {};

let appConfig = { defaultStrategy: 'custom', siteOverrides: {}, customScrapersMap: {} };
try {
    const configPath = path.resolve(__dirname, 'config.json');
    if (fs.existsSync(configPath)) {
        const rawConfig = fs.readFileSync(configPath);
        appConfig = JSON.parse(rawConfig);
        globalStrategy = process.env.BACKEND_STRATEGY || appConfig.defaultStrategy || 'custom';
        siteStrategies = appConfig.siteOverrides || {};
        console.log('[CONFIG] Configuration loaded successfully from config.json');
    } else {
        console.warn('[CONFIG_WARN] config.json not found. Using default global strategy.');
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
        if (process.env.DEBUG === 'true' || (appConfig.global && appConfig.global.logLevel === 'debug')) {
            console.log(`[DEBUG] ${new Date().toISOString()}: ${message}`, ...args);
        }
    }
};

log.info(`Initial Global Backend Strategy set to: ${globalStrategy}`);
log.info('Site-specific strategies:', siteStrategies);

// --- Middleware ---
app.use(cors());
app.use(express.json());

// Serve static files from public directory (assuming index.html is there)
app.use(express.static(path.join(__dirname, 'public')));


// --- Instantiate Pornsearch Orchestrator ---
const pornsearchOrchestrator = new PornsearchOrchestrator({ /* options if any */ });


// --- Handler Functions ---
// Commenting out handlePornsearchNpmRequest as the npm package is not being used for "custom"
/*
async function handlePornsearchNpmRequest(params) {
    log.info(`[PornsearchNPM Handler] Processing for driver '${params.driver}' query '${params.query}', type '${params.type}', page ${params.page}.`);
    // ... implementation ...
}
*/

async function handleCustomOrchestratorRequest(driverKey, params) {
    log.info(`[Orchestrator Handler] Processing for driver '${driverKey}' query '${params.query}', type '${params.type}', page ${params.page}.`);
    try {
        // Ensure useMockData is true for current testing phase
        const useMockData = true;
        log.info(`[Orchestrator Handler] Using mock data: ${useMockData}`);

        const resultsData = await pornsearchOrchestrator.search({
            query: params.query,
            platform: driverKey,
            type: params.type,
            page: params.page,
            useMockData: useMockData
        });

        log.info(`[Orchestrator Handler] Orchestrator for ${driverKey} (type: ${params.type}) returned ${resultsData ? resultsData.length : 0} results.`);
        return {
            message: `Results from orchestrator for '${driverKey}' query '${params.query}' (type: ${params.type}, mock: ${useMockData})`,
            data: resultsData || []
        };
    } catch (error) {
        log.error(`[Orchestrator Handler] Error with orchestrator for driver '${driverKey}' (type: ${params.type}):`, error.message, error.stack);
        if (error.status) throw error;
        throw { status: 500, message: `Error processing custom search for '${driverKey}': ${error.message}` };
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
        if (isNaN(pageNumber) || pageNumber <= 0) {
             log.warn(`[/api/search] Bad Request: Invalid page number '${page}'. Defaulting to 1.`);
             pageNumber = 1;
        }
    } catch(e){
        log.warn(`[/api/search] Bad Request: Could not parse page number '${page}'. Defaulting to 1.`);
        pageNumber = 1;
    }

    const searchParams = { query, driver: driver.toLowerCase(), type: type.toLowerCase(), page: pageNumber };
    const driverKey = searchParams.driver;
    const effectiveStrategy = siteStrategies[driverKey] || globalStrategy;
    log.info(`[/api/search] Effective strategy for driver '${driverKey}': ${effectiveStrategy}`);

    try {
        let responsePayload;
        // If 'pornsearch' (npm) strategy is ever re-enabled, ensure PornsearchNpm is required and handlePornsearchNpmRequest is uncommented.
        if (effectiveStrategy === 'pornsearch') {
            // responsePayload = await handlePornsearchNpmRequest(searchParams);
            log.warn('[/api/search] "pornsearch" (npm package) strategy selected but currently commented out.');
            throw { status: 501, message: "'pornsearch' (npm package) strategy is currently disabled." };
        } else if (effectiveStrategy === 'custom') {
            responsePayload = await handleCustomOrchestratorRequest(driverKey, searchParams);
        } else {
            log.error(`[/api/search] Unknown strategy '${effectiveStrategy}' for driver '${driverKey}'.`);
            return res.status(501).json({ error: `Strategy '${effectiveStrategy}' not implemented for '${driverKey}'.` });
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
     const indexPath = path.join(__dirname, 'public', 'index.html');
     if (fs.existsSync(indexPath)) {
        res.sendFile(indexPath);
     } else {
        log.error('[/] index.html not found in public directory.');
        res.status(404).send('Frontend not found. Ensure index.html is in the public directory.');
     }
});


// --- Start Server ---
// Check if the module is being run directly
if (require.main === module) {
    app.listen(PORT, '0.0.0.0', () => { // Listen on 0.0.0.0 to be accessible externally if needed
        log.info(`Hybrid backend server started on http://localhost:${PORT} (accessible also via http://<your-ip>:${PORT} if firewall allows)`);
        log.info(`Current Global Backend Strategy: ${globalStrategy}`);
        log.info(`Serving frontend from: ${path.join(__dirname, 'public')}`);
    });
}


// --- Graceful Shutdown ---
function gracefulShutdown() {
    log.info('Shutdown signal received, closing server gracefully.');
    process.exit(0);
}
process.on('SIGINT', gracefulShutdown);
process.on('SIGTERM', gracefulShutdown);

module.exports = app;
