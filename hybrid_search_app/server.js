// server.js - Hybrid Backend Server (Enhanced)
// Made by your favorite AI assistant , optimized for Termux and Python coders!
// Incorporating neon colorization and complete enhanced features.

// --- Setup & Dependencies ---
require('dotenv').config(); // Load environment variables from .env file
const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const helmet = require('helmet'); // For security headers
const rateLimit = require('express-rate-limit'); // For API rate limiting
const chalk = require('chalk'); // For neon-colored terminal output

// Import the custom Pornsearch orchestrator
const PornsearchOrchestrator = require('./Pornsearch.js');

// --- Custom Neon-Themed Logger ---
const log = {
    info: (...args) => console.log(chalk.cyan('[INFO]'), ...args),
    warn: (...args) => console.warn(chalk.yellow('[WARN]'), ...args),
    error: (...args) => console.error(chalk.red('[ERROR]'), ...args),
    debug: (...args) => process.env.NODE_ENV !== 'production' && console.debug(chalk.magenta('[DEBUG]'), ...args),
};
// Override the original log if core/log.js exists and is preferred, otherwise use this one.
// For simplicity, this enhanced version uses its own chalk-based logger.
// const log = require('./core/log.js'); // If you want to use an external log module, uncomment this and adjust above.


// --- Constants & Configurations ---
const app = express();
const PORT = process.env.PORT || 3003;
const CACHE_DURATION_MS = parseInt(process.env.CACHE_DURATION_MS || (5 * 60 * 1000), 10); // 5 minutes by default

// Cache object for search results (in-memory, simple)
const cache = {};

// Global configuration variables
let globalStrategy = 'custom';
let siteStrategies = {};
let appConfig = { defaultStrategy: 'custom', siteOverrides: {}, customScrapersMap: {} };

const CONFIG_FILE_PATH = path.resolve(__dirname, 'config.json');

/**
 * Loads the application configuration from config.json.
 * Sets globalStrategy and siteStrategies based on loaded config or environment variables.
 */
function loadConfig() {
    try {
        if (fs.existsSync(CONFIG_FILE_PATH)) {
            const rawConfig = fs.readFileSync(CONFIG_FILE_PATH, 'utf8');
            appConfig = JSON.parse(rawConfig);
            globalStrategy = process.env.BACKEND_STRATEGY || appConfig.defaultStrategy || 'custom';
            siteStrategies = appConfig.siteOverrides || {};
            log.info(chalk.green(`[CONFIG] Configuration loaded successfully from ${CONFIG_FILE_PATH}`));
        } else {
            log.warn(chalk.yellow(`[CONFIG_WARN] config.json not found at ${CONFIG_FILE_PATH}. Using default global strategy.`));
            globalStrategy = process.env.BACKEND_STRATEGY || 'custom';
        }
    } catch (err) {
        log.error(chalk.red(`[CONFIG_ERROR] Failed to load or parse config.json: ${err.message}`));
        globalStrategy = process.env.BACKEND_STRATEGY || 'custom'; // Fallback to default
    }
    log.info(`Initial/Current Global Backend Strategy set to: ${chalk.bold.yellow(globalStrategy)}`);
    log.info('Site-specific strategies:', JSON.stringify(siteStrategies, null, 2));
}

/**
 * Watches the config.json file for changes and reloads the configuration.
 */
function watchConfig() {
    fs.watch(CONFIG_FILE_PATH, (eventType, filename) => {
        if (filename && eventType === 'change') {
            log.info(chalk.blue(`[CONFIG_WATCH] config.json changed. Reloading configuration...`));
            loadConfig();
            // Re-initialize orchestrator if strategy or custom scrapers map might have changed
            // This assumes PornsearchOrchestrator.create can handle re-initialization or internal updates.
            // For a simple case, a full restart might be preferred or Orchestrator designed for dynamic updates.
            // For now, we just reload the config variables.
            // If the orchestrator *must* be recreated, you'd need more complex logic here (e.g., stopping old, starting new).
        }
    });
    log.info(chalk.blue(`[CONFIG_WATCH] Watching for changes in ${CONFIG_FILE_PATH}`));
}

// Load initial config
loadConfig();


// --- Middleware ---
app.use(helmet()); // Add security headers
app.use(cors()); // Enable CORS for all origins (consider restricting in production)
app.use(express.json()); // Parse JSON request bodies

// Rate limiting for API requests
const limiter = rateLimit({
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || 60 * 1000, 10), // 1 minute
    max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || 100, 10), // Max 100 requests per minute per IP
    message: chalk.red("Too many requests from this IP, please try again after some time."),
    standardHeaders: true, // Return rate limit info in the `RateLimit-*` headers
    legacyHeaders: false, // Disable the `X-RateLimit-*` headers
});
app.use('/api/', limiter); // Apply rate limiting to all /api/ routes

// Serve static files from public directory (assuming index.html is there)
app.use(express.static(path.join(__dirname, 'public')));


// --- Instantiate Pornsearch Orchestrator ---
let pornsearchOrchestrator;

/**
 * Initializes the Pornsearch Orchestrator.
 * It loads custom scrapers based on appConfig.customScrapersMap.
 */
async function initializeOrchestrator() {
    try {
        // Placeholder for a more dynamic scraper loading mechanism
        // For example, reading from appConfig.customScrapersMap and registering them
        const dynamicScrapers = {};
        if (appConfig.customScrapersMap) {
            for (const [platformKey, scraperPath] of Object.entries(appConfig.customScrapersMap)) {
                try {
                    const absoluteScraperPath = path.resolve(__dirname, scraperPath);
                    // Clear require cache to ensure fresh module load on config reload if needed
                    // delete require.cache[require.resolve(absoluteScraperPath)];
                    dynamicScrapers[platformKey] = require(absoluteScraperPath);
                    log.info(chalk.green(`[ORCHESTRATOR] Loaded custom scraper for '${platformKey}' from ${absoluteScraperPath}`));
                } catch (loadError) {
                    log.error(chalk.red(`[ORCHESTRATOR_ERROR] Failed to load custom scraper for '${platformKey}' from ${scraperPath}: ${loadError.message}`));
                }
            }
        }

        // Pass dynamicScrapers to the orchestrator for registration
        pornsearchOrchestrator = await PornsearchOrchestrator.create({
            customScrapers: dynamicScrapers
            // You can pass other configuration to the orchestrator here
        });
        log.info(chalk.green('PornsearchOrchestrator created and drivers registered successfully.'));
        log.info(chalk.green('Available Platforms/Drivers:', chalk.yellow(pornsearchOrchestrator.getAvailablePlatforms().map(d => d.name).join(', '))));

    } catch (err) {
        log.error(chalk.red('Failed to create PornsearchOrchestrator:', err.message), err.stack);
        // It's critical, so we should exit or handle gracefully
        process.exit(1); // Exit if orchestrator fails to initialize
    }
}


// --- Handler Functions ---
async function handleCustomOrchestratorRequest(driverKey, params) {
    log.debug(chalk.gray(`[Orchestrator Handler] Processing for driver '${driverKey}' query '${params.query}', type '${params.type}', page ${params.page}.`));
    try {
        const useMockData = process.env.USE_MOCK_DATA === 'true';
        log.debug(chalk.gray(`[Orchestrator Handler] Using mock data: ${useMockData}`));

        // Validate driver key before passing to orchestrator to prevent unexpected errors
        const availablePlatforms = pornsearchOrchestrator.getAvailablePlatforms().map(d => d.name.toLowerCase());
        if (!availablePlatforms.includes(driverKey.toLowerCase())) {
             throw { status: 400, message: `Invalid or unsupported driver: '${driverKey}'. Available drivers: ${availablePlatforms.join(', ')}` };
        }

        const resultsData = await pornsearchOrchestrator.search({
            query: params.query,
            platform: driverKey,
            type: params.type,
            page: params.page,
            useMockData: useMockData
        });

        log.info(chalk.cyan(`[Orchestrator Handler] Orchestrator for ${chalk.yellow(driverKey)} (type: ${params.type}) returned ${chalk.green(resultsData ? resultsData.length : 0)} results.`));
        return {
            message: `Results from orchestrator for '${driverKey}' query '${params.query}' (type: ${params.type}, mock: ${useMockData})`,
            data: resultsData || []
        };
    } catch (error) {
        log.error(chalk.red(`[Orchestrator Handler] Error with orchestrator for driver '${driverKey}' (type: ${params.type}): ${error.message}`));
        if (error.status) throw error; // Re-throw custom errors with status
        throw { status: 500, message: `Error processing custom search for '${driverKey}': ${error.message}` };
    }
}

// --- API Endpoints ---
app.get('/api/search', async (req, res, next) => {
    log.debug(chalk.gray('[/api/search] Received request. Query params:', req.query));
    const { query, driver, type = 'videos', page = '1' } = req.query;

    if (!query) {
        log.warn(chalk.yellow('[/api/search] Bad Request: Missing query parameter.'));
        return res.status(400).json({ error: 'Missing required parameter: query' });
    }

    let pageNumber;
    try {
        pageNumber = parseInt(page, 10);
        if (isNaN(pageNumber) || pageNumber <= 0) {
            log.warn(chalk.yellow(`[/api/search] Invalid page number '${page}'. Defaulting to 1.`));
            pageNumber = 1;
        }
    } catch (e) {
        log.warn(chalk.yellow(`[/api/search] Could not parse page number '${page}'. Defaulting to 1.`));
        pageNumber = 1;
    }

    // Determine the effective driver, defaulting to a common one or a preferred one if 'driver' is not provided.
    // This assumes your Pornsearch.js has a default or can infer one.
    // For robust setup, it's better to explicitly check if 'driver' is valid.
    const effectiveDriver = (driver || appConfig.defaultStrategy || 'custom').toLowerCase();
    const searchParams = { query, type: type.toLowerCase(), page: pageNumber };

    const driverKey = effectiveDriver;
    const effectiveStrategy = siteStrategies[driverKey] || globalStrategy;
    log.info(`[/api/search] Effective strategy for driver '${chalk.blue(driverKey)}': ${chalk.green(effectiveStrategy)}`);

    const cacheKey = `${driverKey}-${searchParams.type}-${searchParams.query}-${searchParams.page}`;
    const cachedResult = cache[cacheKey];

    if (cachedResult && (Date.now() - cachedResult.timestamp < CACHE_DURATION_MS)) {
        log.info(chalk.green(`[/api/search] Returning cached results for key: ${chalk.white(cacheKey)}`));
        return res.status(200).json(cachedResult.data);
    }

    try {
        let responsePayload;
        // The 'pornsearch' (npm) package strategy is commented out as per your original code.
        // If re-enabled, ensure 'pornsearch' npm package is installed and its handler is implemented.
        if (effectiveStrategy === 'pornsearch') {
            log.warn(chalk.yellow('[/api/search] "pornsearch" (npm package) strategy selected but currently disabled.'));
            throw { status: 501, message: "'pornsearch' (npm package) strategy is currently disabled." };
        } else if (effectiveStrategy === 'custom') {
            responsePayload = await handleCustomOrchestratorRequest(driverKey, searchParams);
        } else {
            log.error(chalk.red(`[/api/search] Unknown or unsupported strategy '${effectiveStrategy}' for driver '${driverKey}'.`));
            throw { status: 501, message: `Strategy '${effectiveStrategy}' not implemented or supported for '${driverKey}'.` };
        }

        cache[cacheKey] = {
            timestamp: Date.now(),
            data: responsePayload,
        };

        res.status(200).json(responsePayload);

    } catch (error) {
        // Pass error to the centralized error handler
        next(error);
    }
});

app.get('/api/health', (req, res) => {
    if (pornsearchOrchestrator) {
        res.status(200).json({ status: 'ok', message: 'Scraper orchestrator is initialized.' });
    } else {
        res.status(503).json({ status: 'error', message: 'Scraper orchestrator not yet available.' });
    }
});

// New endpoint for listing available drivers/platforms
app.get('/api/drivers', (req, res) => {
    if (pornsearchOrchestrator) {
        const driverNames = pornsearchOrchestrator.getAvailablePlatforms().map(d => d.name);
        res.status(200).json({ drivers: driverNames });
    } else {
        res.status(503).json({ error: 'Scraper orchestrator not yet available.' });
    }
});

// Alias for /api/drivers for backward compatibility
app.get('/api/scrapers', (req, res) => {
    log.warn(chalk.yellow('[/api/scrapers] This endpoint is deprecated. Please use /api/drivers instead.'));
    if (pornsearchOrchestrator) {
        const driverNames = pornsearchOrchestrator.getAvailablePlatforms().map(d => d.name);
        res.status(200).json({ scrapers: driverNames });
    } else {
        res.status(503).json({ error: 'Scraper orchestrator not yet available.' });
    }
});

// New endpoint to check current backend configuration
app.get('/api/config', (req, res) => {
    res.status(200).json({
        globalStrategy: globalStrategy,
        siteStrategies: siteStrategies,
        cacheDurationMs: CACHE_DURATION_MS,
        useMockData: process.env.USE_MOCK_DATA === 'true',
        rateLimit: {
            windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || 60 * 1000, 10),
            maxRequests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || 100, 10)
        }
    });
});

// --- Root Route ---
app.get('/', (req, res) => {
    // Serve index.html from public directory
    const indexPath = path.join(__dirname, 'public', 'index.html');
    if (fs.existsSync(indexPath)) {
        res.sendFile(indexPath);
    } else {
        log.error(chalk.red('[/] index.html not found in public directory.'));
        res.status(404).send('Frontend not found. Ensure index.html is in the public directory.');
    }
});


// --- Centralized Error Handling Middleware ---
app.use((err, req, res, next) => {
    log.error(chalk.red(`[GLOBAL_ERROR] Unhandled error: ${err.message}`), err.stack);

    const statusCode = err.status || 500;
    const responseMessage = err.message || 'An unexpected internal server error occurred.';

    res.status(statusCode).json({
        error: responseMessage,
        details: process.env.NODE_ENV === 'development' ? err.stack : undefined // Provide stack trace only in dev
    });
});


// --- Start Server ---
// Check if the module is being run directly (not imported)
if (require.main === module) {
    initializeOrchestrator().then(() => {
        // Start watching config file *after* initial config load and orchestrator initialization
        watchConfig();

        app.listen(PORT, '0.0.0.0', () => { // Listen on 0.0.0.0 to be accessible externally (e.g., from Termux over network)
            log.info(chalk.green(`Hybrid backend server started on ${chalk.blue(`http://localhost:${PORT}`)}`));
            log.info(chalk.green(`(Accessible also via ${chalk.blue(`http://your-ip:${PORT}`)} if firewall allows, for Termux users)`));
            log.info(`Current Global Backend Strategy: ${chalk.bold.yellow(globalStrategy)}`);
            log.info(`Serving frontend from: ${chalk.blue(path.join(__dirname, 'public'))}`);
        });
    }).catch(err => {
        log.error(chalk.red('Failed to start server due to orchestrator initialization error. Exiting.'));
        process.exit(1);
    });
}


// --- Graceful Shutdown ---
function gracefulShutdown() {
    log.info(chalk.cyan('Shutdown signal received, closing server gracefully.'));
    // Here you can add cleanup logic if needed, e.g., closing database connections,
    // closing open file handles, etc.
    process.exit(0);
}
process.on('SIGINT', gracefulShutdown);  // Ctrl+C
process.on('SIGTERM', gracefulShutdown); // kill command

module.exports = app;
