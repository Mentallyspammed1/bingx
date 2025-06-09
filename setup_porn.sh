
#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e
# Treat unset variables as an error when substituting.
set -u
# The return value of a pipeline is the status of the last command to exit with a non-zero status,
# or zero if no command exited with a non-zero status.
set -o pipefail

PROJECT_NAME="searchxx_project"
FRONTEND_HTML_FILE="index.html" # Renamed from pornx.html for convention

# --- Helper Functions ---
info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

error_exit() {
    echo -e "\033[1;31m[ERROR]\033[0m $1" >&2
    exit 1
}

# --- Main Script ---
info "Starting setup for $PROJECT_NAME..."

# Check if project directory already exists
if [ -d "$PROJECT_NAME" ]; then
    warning "Directory '$PROJECT_NAME' already exists."
    read -r -p "Do you want to remove it and recreate? (y/N): " confirmation
    if [[ "$confirmation" =~ ^[Yy]$ ]]; then
        info "Removing existing directory '$PROJECT_NAME'..."
        rm -rf "$PROJECT_NAME"
    else
        info "Setup aborted by user."
        exit 0
    fi
fi

info "Creating project directory: $PROJECT_NAME"
mkdir -p "$PROJECT_NAME"
cd "$PROJECT_NAME" || error_exit "Failed to cd into $PROJECT_NAME"

info "Creating subdirectories: core, modules"
mkdir -p core modules

info "Initializing Node.js project..."
npm init -y > /dev/null # Suppress npm init output

info "Installing dependencies: express, pornsearch, cors, dotenv..."
npm install express pornsearch cors dotenv --silent > /dev/null # Suppress npm install output

# --- Create .env file ---
info "Creating .env file..."
cat << 'EOF' > .env
PORT=3001
# Add other environment variables here if needed
EOF

# --- Create .gitignore file ---
info "Creating .gitignore file..."
cat << 'EOF' > .gitignore
# Dependencies
node_modules/

# Environment variables
.env

# Logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
lerna-debug.log*

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
EOF

# --- Create server.cjs ---
info "Creating server.cjs..."
cat << 'EOF' > server.cjs
// server.cjs - Backend Server for Search Functionality

// --- Setup & Dependencies ---
require('dotenv').config(); // Load environment variables from .env file

const express = require('express');
const Pornsearch = require('pornsearch'); // Core search library
const cors = require('cors'); // Enable Cross-Origin Resource Sharing
const path = require('path'); // Utility for handling file paths

// --- Constants ---
const app = express();
const PORT = process.env.PORT || 3001; // Use 3001 as default to avoid common conflicts with frontend dev servers

// Define allowed search drivers and types
const ALLOWED_DRIVERS = Object.freeze(['pornhub', 'sex', 'redtube', 'xvideos']); // Use Object.freeze for immutability
const ALLOWED_TYPES = Object.freeze(['videos', 'gifs']);
const DEFAULT_TYPE = 'videos'; // Default search type

// --- Logging Configuration ---
// ANSI escape codes for styled console output
const LOG_STYLES = Object.freeze({
    RESET: '\u001b[0m',
    BOLD: '\u001b[1m',
    DIM: '\u001b[2m',
    RED: '\u001b[31m',
    GREEN: '\u001b[32m',
    YELLOW: '\u001b[33m',
    BLUE: '\u001b[34m',
    CYAN: '\u001b[36m',
    WHITE: '\u001b[37m',
});

// Define log prefixes with styles
const LOG_PREFIX = Object.freeze({
    API: `${LOG_STYLES.BLUE}API${LOG_STYLES.RESET}`,
    WARN: `${LOG_STYLES.BOLD}${LOG_STYLES.YELLOW}Warning${LOG_STYLES.RESET}`,
    NOTE: `${LOG_STYLES.DIM}${LOG_STYLES.WHITE}Note${LOG_STYLES.RESET}`,
    REQUEST: `${LOG_STYLES.BOLD}${LOG_STYLES.CYAN}Request${LOG_STYLES.RESET}`,
    SEARCH: `${LOG_STYLES.DIM}${LOG_STYLES.WHITE}--> Searching${LOG_STYLES.RESET}`,
    SUCCESS: `${LOG_STYLES.BOLD}${LOG_STYLES.GREEN}<-- Found${LOG_STYLES.RESET}`,
    ERROR: `${LOG_STYLES.BOLD}${LOG_STYLES.RED}!!! Error${LOG_STYLES.RESET}`,
    SERVER: `${LOG_STYLES.BOLD}${LOG_STYLES.GREEN}Server${LOG_STYLES.RESET}`,
    INFO: `${LOG_STYLES.BOLD}${LOG_STYLES.CYAN}Info${LOG_STYLES.RESET}`
});

/**
 * Helper function for consistent styled logging.
 * @param {keyof LOG_PREFIX} level - The log level (e.g., 'API', 'WARN').
 * @param {string} message - The main log message.
 * @param {any} [details] - Optional additional details to log.
 */
const log = (level, message, details) => {
    const timestamp = new Date().toLocaleTimeString();
    // Use the level key directly if it exists in LOG_PREFIX, otherwise use the level string itself
    const levelPrefix = LOG_PREFIX[level] || level;
    const logPrefix = `[${timestamp}] ${levelPrefix}:`;

    if (details !== undefined) {
        // Log details on a new line for better readability, especially for objects/errors
        console.log(`${logPrefix} ${message}`);
        console.log(details);
    } else {
        console.log(`${logPrefix} ${message}`);
    }
};

// --- Middleware ---
app.use(cors()); // Enable CORS for all origins (consider restricting in production)
app.use(express.json()); // Parse JSON request bodies
// Serve static files (like a frontend HTML page) from the project's root directory
// This will serve index.html when accessing the root URL if available.
app.use(express.static(path.resolve(__dirname)));

// --- Root Route ---
// This will be overridden by index.html if it exists in the root due to express.static
app.get('/', (req, res) => {
    // Provide a clear status message and basic instructions
    res.status(200).send(
        'Search Server Backend is running.\n' +
        `API Endpoint: /api/search?query=...&driver=...[&type=videos|gifs][&page=1]\n` +
        `Frontend: Should be served from root (e.g., /index.html)`
    );
});

// --- API Search Endpoint ---
app.get('/api/search', async (req, res) => {
    // Extract and sanitize query parameters
    const query = req.query.query ? String(req.query.query).trim() : '';
    const driver = req.query.driver ? String(req.query.driver).toLowerCase().trim() : '';
    const type = req.query.type ? String(req.query.type).toLowerCase().trim() : DEFAULT_TYPE;
    const page = req.query.page;

    // --- Input Validation ---

    // 1. Validate mandatory parameters
    if (!query || !driver) {
        const missingParams = [];
        if (!query) missingParams.push("'query'");
        if (!driver) missingParams.push("'driver'");
        const errorMessage = `Missing required query parameter(s): ${missingParams.join(' and ')}.`;
        log('WARN', errorMessage, req.query);
        return res.status(400).json({ error: errorMessage });
    }

    // 2. Validate driver
    if (!ALLOWED_DRIVERS.includes(driver)) {
        const errorMessage = `Invalid driver '${driver}'. Allowed drivers are: ${ALLOWED_DRIVERS.join(', ')}.`;
        log('WARN', errorMessage);
        return res.status(400).json({ error: errorMessage });
    }

    // 3. Validate and normalize search type
    let searchType = type;
    if (!ALLOWED_TYPES.includes(searchType)) {
        log('NOTE', `Invalid or missing 'type' parameter ('${type}'). Defaulting to '${DEFAULT_TYPE}'.`);
        searchType = DEFAULT_TYPE; // Default to videos if invalid or missing
    }

    // 4. Validate and parse page number
    let pageNumber = parseInt(page, 10);
    if (isNaN(pageNumber) || pageNumber < 1) {
        if (page !== undefined) { // Log only if page was provided but invalid
            log('NOTE', `Invalid or missing 'page' parameter ('${page}'). Defaulting to page 1.`);
        }
        pageNumber = 1; // Default to page 1
    }

    log('REQUEST', `Query="${query}", Driver=${driver}, Type=${searchType}, Page=${pageNumber}`);

    try {
        // --- Perform Search ---
        log('SEARCH', `${searchType === 'gifs' ? 'GIFs' : 'Videos'} on ${driver} (Page ${pageNumber})...`);
        const search = new Pornsearch(query, driver);
        let results;

        // Call the appropriate search method based on type
        if (searchType === 'gifs') {
            results = await search.gifs(pageNumber);
        } else { // Default to videos
            results = await search.videos(pageNumber);
        }

        // Ensure results is always an array, even if the library returns null/undefined
        const finalResults = Array.isArray(results) ? results : [];
        const resultCount = finalResults.length;
        log('SUCCESS', `${resultCount} ${searchType}(s) found for query="${query}", driver=${driver}, page=${pageNumber}.`);

        // Send results to the client
        res.status(200).json(finalResults);

    } catch (error) {
        // --- Error Handling ---
        log('ERROR', `Search failed [Type: ${searchType}, Driver: ${driver}, Page: ${pageNumber}, Query: "${query}"]`, error.message || error);
        // Avoid logging the full error object to console in production if it might contain sensitive info
        // console.error(error); // Uncomment for full stack trace during development/debugging

        let errorMessage = 'An unexpected error occurred while fetching search results.';
        let statusCode = 500; // Internal Server Error

        // Attempt to provide more specific feedback based on the error
        // Note: Relying on error message strings is fragile and might break if the library changes its error messages.
        const lowerCaseErrorMessage = error.message ? String(error.message).toLowerCase() : '';

        if (error.response?.status === 404 || lowerCaseErrorMessage.includes('not found') || lowerCaseErrorMessage.includes('no results')) {
            errorMessage = `Could not find results or page ${pageNumber} for ${searchType} on '${driver}'. The page may not exist, the query yielded no results, or the content type is unavailable.`;
            statusCode = 404; // Not Found
        } else if (lowerCaseErrorMessage.includes('driver') || lowerCaseErrorMessage.includes('support') || lowerCaseErrorMessage.includes('method') || lowerCaseErrorMessage.includes('not implemented')) {
            errorMessage = `The search provider '${driver}' may not support searching for ${searchType}, or an internal library error occurred.`;
            statusCode = 501; // Not Implemented (or 400 Bad Request if type is fundamentally unsupported)
        } else if (lowerCaseErrorMessage.includes('parse') || lowerCaseErrorMessage.includes('selector') || lowerCaseErrorMessage.includes('structure') || lowerCaseErrorMessage.includes('cannot read properties of undefined')) {
            // This often indicates the website structure changed, breaking the scraper
            errorMessage = `Failed to parse ${searchType} data from '${driver}'. The site's structure may have changed, temporarily breaking search for this provider.`;
            statusCode = 502; // Bad Gateway (issue with the upstream service/scraping)
        } else if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED' || error.code === 'ETIMEDOUT' || lowerCaseErrorMessage.includes('timeout')) {
            errorMessage = `Could not connect to '${driver}' or the connection timed out. The site might be down or unreachable.`;
            statusCode = 504; // Gateway Timeout
        } else if (error.response?.status === 429 || lowerCaseErrorMessage.includes('many requests')) {
            errorMessage = `Too many requests sent to '${driver}'. Please wait a moment before trying again.`;
            statusCode = 429; // Too Many Requests
        }
        // Add more specific error checks based on observed errors from the Pornsearch library if needed

        res.status(statusCode).json({
            error: errorMessage,
            // Optionally include details in non-production environments
            // details: process.env.NODE_ENV !== 'production' ? error.message : undefined
        });
    }
});

// --- Start Server ---
app.listen(PORT, () => {
    const host = `http://localhost:${PORT}`;
    log('SERVER', `Backend server listening on port ${LOG_STYLES.BOLD}${LOG_STYLES.YELLOW}${PORT}${LOG_STYLES.RESET}`);
    log('INFO', `Allowed Drivers: ${LOG_STYLES.BOLD}${LOG_STYLES.YELLOW}${ALLOWED_DRIVERS.join(', ')}${LOG_STYLES.RESET}`);
    log('INFO', `Allowed Types:   ${LOG_STYLES.BOLD}${LOG_STYLES.YELLOW}${ALLOWED_TYPES.join(', ')}${LOG_STYLES.RESET}`);
    log('INFO', `API Endpoint:    ${LOG_STYLES.BOLD}${LOG_STYLES.YELLOW}${host}/api/search${LOG_STYLES.RESET}`);
    log('INFO', `Server Status:   ${LOG_STYLES.BOLD}${LOG_STYLES.YELLOW}${host}/${LOG_STYLES.RESET}`);
    console.log(`(${LOG_STYLES.DIM}${LOG_STYLES.WHITE}Press Ctrl+C to stop the server${LOG_STYLES.RESET})`);
});

// --- Graceful Shutdown (Optional but Recommended) ---
process.on('SIGINT', () => {
    log('SERVER', 'Shutdown signal received, closing server gracefully.');
    // Perform cleanup here if needed (e.g., close database connections)
    process.exit(0);
});

process.on('SIGTERM', () => {
    log('SERVER', 'Termination signal received, closing server gracefully.');
    // Perform cleanup here if needed
    process.exit(0);
});
EOF

# --- Create core/OverwriteError.js ---
info "Creating core/OverwriteError.js..."
cat << 'EOF' > core/OverwriteError.js
// core/OverwriteError.js
'use strict';

class OverwriteError extends Error {
  constructor(message) {
    super(message);
    this.name = 'OverwriteError';
    // Maintains proper prototype chain for instanceof checks
    Object.setPrototypeOf(this, OverwriteError.prototype);
  }
}

module.exports = OverwriteError;
EOF

# --- Create core/abstractMethodFactory.js ---
info "Creating core/abstractMethodFactory.js..."
cat << 'EOF' > core/abstractMethodFactory.js
// core/abstractMethodFactory.js
'use strict';

const OverwriteError = require('./OverwriteError');

/**
 * @typedef {new (...args: any[]) => object} BaseClassConstructor - Represents a base class constructor.
 * @template TBase - The type of the base class instances.
 */

/**
 * Factory function that takes a base class constructor and a list of method names.
 * It returns a new class constructor that inherits from the base class and enforces that
 * the specified methods must be implemented by any concrete subclass.
 *
 * @param {BaseClassConstructor<TBase>} BaseClass - The constructor function of the base class to inherit from.
 * @param {string[]} abstractMethods - An array of method names that must be implemented by subclasses.
 * @returns {BaseClassConstructor<TBase>} A new class constructor extending BaseClass.
 * @template TBase - The instance type of the base class.
 * @throws {Error} If BaseClass is not a valid constructor or if abstractMethods is not a non-empty array of valid strings.
 */
module.exports = (BaseClass, abstractMethods) => {
  if (typeof BaseClass !== 'function') {
    throw new Error('The first argument "BaseClass" must be a constructor function.');
  }

  if (!Array.isArray(abstractMethods) || abstractMethods.length === 0) {
    throw new Error('The second argument "abstractMethods" must be a non-empty array of strings.');
  }

  const validAbstractMethods = abstractMethods.filter(methodName =>
    typeof methodName === 'string' && methodName.trim().length > 0
  );

  if (validAbstractMethods.length === 0) {
    throw new Error('After filtering invalid entries, the "abstractMethods" array is empty or contains only invalid method names.');
  }

  const AbstractMethodEnforcer = class extends BaseClass {
    constructor(...args) {
      super(...args);
    }
  };

  validAbstractMethods.forEach(methodName => {
    Object.defineProperty(AbstractMethodEnforcer.prototype, methodName, {
      get() {
        // This getter is invoked when the 'abstract' method is accessed.
        // It returns the function that will actually be called.
        return (...args) => {
          // 'this' here refers to the instance of the concrete subclass.
          const callingClassName = this.constructor.name || 'Subclass';
          // BaseClass.name might not be reliable if BaseClass is an anonymous class from prior mixin application.
          // It's more about the *concept* of the layer that introduced the abstract method.
          throw new OverwriteError(
            `Abstract method "${methodName}" must be implemented by concrete class "${callingClassName}".`
          );
        };
      },
      configurable: true, // Allows subclasses to override.
      enumerable: false,   // Keeps it off for...in loops on the prototype.
    });
  });

  return AbstractMethodEnforcer;
};
EOF

# --- Create core/AbstractModule.js ---
info "Creating core/AbstractModule.js..."
cat << 'EOF' > core/AbstractModule.js
// core/AbstractModule.js
'use strict';

class AbstractModule {
  /**
   * @param {string} query - The search query.
   */
  constructor(query) {
    if (typeof query !== 'string') { // Basic check, concrete classes might do more
      this.query = '';
    } else {
      this.query = query.trim();
    }
    // Other common initializations can go here (e.g., HTTP client instance)
  }

  /**
   * Getter for the module's name. Must be implemented by subclasses.
   * @abstract
   * @returns {string}
   */
  get name() {
    throw new Error(`Getter "name" must be implemented by subclass "${this.constructor.name}".`);
  }

  /**
   * Getter for the first page number (pagination).
   * Defaults to 0, can be overridden by subclasses.
   * @returns {number}
   */
  get firstpage() {
    return 0;
  }

  /**
   * Static method to apply mixins to a class.
   * @param {...Function} mixinFactories - Mixin factory functions (e.g., VideoMixin, GifMixin).
   * @returns {Function} A new class composed with the applied mixins.
   */
  static with(...mixinFactories) {
    // 'this' refers to the class calling 'with' (e.g., AbstractModule or a class already extended by mixins)
    return mixinFactories.reduce((c, mixinFactory) => mixinFactory(c), this);
  }

  // Example of a utility method subclasses might use (requires http client injection)
  // async _fetchPage(url) {
  //   if (!this.httpClient) throw new Error("HTTP client not available on this module.");
  //   const response = await this.httpClient.get(url);
  //   return response.data; // Or response.text()
  // }
}

module.exports = AbstractModule;
EOF

# --- Create core/VideoMixin.js ---
info "Creating core/VideoMixin.js..."
cat << 'EOF' > core/VideoMixin.js
// core/VideoMixin.js
'use strict';

const enforceAbstractMethods = require('./abstractMethodFactory');

const videoAbstractMethods = [
  'videoUrl',    // Expected to return a string (URL)
  'videoParser', // Expected to parse data (e.g., from HTML or JSON) and return an array of video objects
];

/**
 * VideoMixin - A factory function that creates a mixin to add video-related requirements.
 * @param {Function} BaseClass - The base class constructor to extend.
 * @returns {Function} A new class constructor with enforced abstract methods for videos.
 */
const VideoMixin = (BaseClass) => {
  return enforceAbstractMethods(BaseClass, videoAbstractMethods);
};

module.exports = VideoMixin;
EOF

# --- Create core/GifMixin.js ---
info "Creating core/GifMixin.js..."
cat << 'EOF' > core/GifMixin.js
// core/GifMixin.js
'use strict';

const enforceAbstractMethods = require('./abstractMethodFactory'); // Path based on file structure

const gifAbstractMethods = [
  'gifUrl',
  'gifParser'
];

/**
 * GifMixin - A factory function that creates a mixin to add GIF-related requirements.
 * @param {Function} BaseClass - The base class constructor to extend.
 * @returns {Function} A new class constructor with enforced abstract methods for GIFs.
 */
const GifMixin = (BaseClass) => {
  return enforceAbstractMethods(BaseClass, gifAbstractMethods);
};

module.exports = GifMixin;
EOF

# --- Create modules/Redtube.js ---
info "Creating modules/Redtube.js..."
cat << 'EOF' > modules/Redtube.js
// modules/Redtube.js
'use strict';

const AbstractModule = require('../core/AbstractModule');
const VideoMixin = require('../core/VideoMixin');

// Base class composed with VideoMixin requirements
const BaseScraper = AbstractModule.with(VideoMixin);

class Redtube extends BaseScraper {
  constructor(query) {
    super(query); // Passes query to AbstractModule constructor
    // No Redtube-specific constructor logic needed here for now
  }

  get name() {
    return 'Redtube';
  }

  get firstpage() {
    return 1; // Redtube API pagination typically starts at 1
  }

  /**
   * Generates the API URL for Redtube video search.
   * @param {number} [page] - The page number. Defaults to `this.firstpage`.
   * @returns {string} The API URL.
   */
  videoUrl(page) {
    const pageNum = (Number.isInteger(page) && page >= this.firstpage) ? page : this.firstpage;
    // Using HTTPS for API endpoint
    return `https://api.redtube.com/?data=redtube.Videos.searchVideos&output=json&search=${encodeURIComponent(this.query)}&thumbsize=big&page=${pageNum}`;
  }

  /**
   * Parses the JSON response from Redtube API.
   * @param {object} jsonData - The parsed JSON data from the API response.
   * @returns {Array<object>} An array of video objects.
   */
  videoParser(jsonData) {
    if (!jsonData || !Array.isArray(jsonData.videos)) {
      // console.warn(`[${this.name}] Invalid or empty JSON data received for video parsing.`);
      return [];
    }

    return jsonData.videos.map(({ video }) => {
      if (!video) return null; // Skip if video object is missing
      return {
        title: video.title,
        url: video.url,
        duration: video.duration,
        thumb: video.default_thumb, // API provides 'default_thumb'
        source: this.name,
      };
    }).filter(video => video !== null); // Remove any null entries
  }
}

module.exports = Redtube;
EOF

# --- Create modules/SexCom.js ---
info "Creating modules/SexCom.js..."
cat << 'EOF' > modules/SexCom.js
// modules/SexCom.js
'use strict';

const AbstractModule = require('../core/AbstractModule');
const VideoMixin = require('../core/VideoMixin');
const GifMixin = require('../core/GifMixin');
// const cheerio = require('cheerio'); // Would be required if loading HTML here

// Base class composed with both GifMixin and VideoMixin requirements
const BaseScraper = AbstractModule.with(GifMixin, VideoMixin);

class SexCom extends BaseScraper {
  constructor(query) {
    super(query);
    this.baseUrl = 'https://www.sex.com'; // Use HTTPS
  }

  get name() {
    return 'Sex.com'; // Display name
  }

  get firstpage() {
    return 1; // Sex.com pagination starts at 1
  }

  /**
   * @param {number} [page]
   * @returns {string}
   */
  videoUrl(page) {
    const pageNum = (Number.isInteger(page) && page >= this.firstpage) ? page : this.firstpage;
    return `${this.baseUrl}/search/videos?query=${encodeURIComponent(this.query)}&page=${pageNum}`;
  }

  /**
   * @param {number} [page]
   * @returns {string}
   */
  gifUrl(page) {
    const pageNum = (Number.isInteger(page) && page >= this.firstpage) ? page : this.firstpage;
    return `${this.baseUrl}/search/gifs?query=${encodeURIComponent(this.query)}&page=${pageNum}`;
  }

  /**
   * Parses video data from Sex.com HTML.
   * @param {import('cheerio').CheerioAPI} $ - Cheerio instance loaded with page HTML.
   * @returns {Array<object>}
   */
  videoParser($) {
    if (typeof $ !== 'function') {
      // console.warn(`[${this.name}] Cheerio instance not provided to videoParser.`);
      return [];
    }
    const videos = [];
    $('#masonry_container .masonry_box').each((_, element) => {
      const cached = $(element);
      const link = cached.find('.title a').first();
      const title = link.text()?.trim();
      const duration = cached.find('.duration').text()?.trim();
      const thumb = cached.find('.image[data-src]').data('src')?.trim(); // data-src for lazy loaded images
      const path = link.attr('href');

      if (title && path && duration && thumb) {
        videos.push({
          title,
          url: path.startsWith('http') ? path : `${this.baseUrl}${path}`,
          duration,
          thumb: thumb.startsWith('http') ? thumb : (thumb.startsWith('//') ? `https:${thumb}` : thumb),
          source: this.name,
        });
      }
    });
    return videos;
  }

  /**
   * Parses GIF data from Sex.com HTML.
   * @param {import('cheerio').CheerioAPI} $ - Cheerio instance loaded with page HTML.
   * @returns {Array<object>}
   */
  gifParser($) {
    if (typeof $ !== 'function') {
      // console.warn(`[${this.name}] Cheerio instance not provided to gifParser.`);
      return [];
    }
    const gifs = [];
    $('#masonry_container .masonry_box').not('.ad_box').each((_, element) => {
      const data = $(element).find('a.image_wrapper').first();
      const title = data.attr('title')?.trim();
      // GIF URL is often directly in data-src of an img inside the anchor
      const url = data.find('img[data-src]').data('src')?.trim();
      // Sex.com doesn't typically provide a separate .webm for search results directly,
      // the 'url' is the direct GIF.
      if (title && url) {
        gifs.push({
          title,
          url: url.startsWith('http') ? url : (url.startsWith('//') ? `https:${url}` : url),
          // webm: typically not available directly in Sex.com GIF search listings, might be on detail page.
          source: this.name,
        });
      }
    });
    return gifs;
  }
}

module.exports = SexCom;
EOF

# --- Create modules/Pornhub.js ---
info "Creating modules/Pornhub.js..."
cat << 'EOF' > modules/Pornhub.js
'use strict';

// Core dependencies - these better be rock solid!
const AbstractModule = require('../core/AbstractModule');
const GifMixin = require('../core/GifMixin');
const VideoMixin = require('../core/VideoMixin');

// We're assuming Cheerio is ready to roll, but not directly calling it here.
// const cheerio = require('cheerio');

/**
 * @typedef {import('cheerio').CheerioAPI} CheerioAPI
 */

/**
 * @typedef {object} VideoResult - The goods: what we found for videos.
 * @property {string} title - What's it called?
 * @property {string} url - Where's it at? (Full URL)
 * @property {string} duration - How long is the... show?
 * @property {string} thumb - A little peek (thumbnail URL).
 * @property {string} source - Where'd this gem come from? (e.g., 'Pornhub')
 */

/**
 * @typedef {object} GifResult - Quick loops of fun.
 * @property {string} title - GIF's catchy name.
 * @property {string} url - Direct link to the .gif prize.
 * @property {string} webm - The smoother, better WEBM version.
 * @property {string} source - Source, again.
 */

/**
 * Pornhub.com Scraper - This is where the magic happens for PH.
 * Built on our awesome AbstractModule and spiced up with Gif & Video Mixins.
 *
 * @class Pornhub
 * @extends AbstractModule // More like AbstractModule + Mixins extravaganza!
 * @mixes GifMixin
 * @mixes VideoMixin
 */
class Pornhub extends AbstractModule.with(GifMixin, VideoMixin) {
  /**
   * Fires up the Pornhub engine.
   * @param {string} query - What are you searching for, champ?
   * @throws {Error} If you don't give me a proper query.
   */
  constructor(query) {
    super(query); // Let the base class and mixins handle the query first.

    if (!query || typeof query !== 'string' || query.trim() === '') {
      throw new Error('Pornhub driver needs a non-empty search query. No query, no party!');
    }
    // this.query is assumed to be set by super(query) from AbstractModule/Mixins.
    // If not, you'd explicitly set something like this.rawQuery = query.trim();

    this.baseUrl = 'https://www.pornhub.com'; // HTTPS all the way, baby!
    this.baseGifCdnUrl = 'https://dl.phncdn.com'; // CDN also gets the HTTPS treatment.
  }

  /**
   * My name is Pornhub, and I am awesome.
   * @returns {string} 'Pornhub'
   */
  get name() {
    return 'Pornhub';
  }

  /**
   * Pornhub likes to start its page count at 1, like a normal website.
   * @returns {number} 1
   */
  get firstpage() {
    return 1;
  }

  /**
   * Builds the Pornhub video search URL.
   * @param {number} [page] - Page number. If you're lazy, I'll use the first.
   * @returns {string} The URL to hit for videos.
   * @throws {Error} If you give me a bogus page number.
   */
  videoUrl(page) {
    const pageNumber = (page !== undefined && Number.isInteger(page) && page >= this.firstpage) ? page : this.firstpage;

    if (pageNumber < this.firstpage) { // Ensure it's not less than our defined first page
      throw new Error(`WTF? Page number for ${this.name} videos (${pageNumber}) can't be less than ${this.firstpage}.`);
    }
    // Assuming this.query is the raw query string.
    return `${this.baseUrl}/video/search?search=${encodeURIComponent(this.query)}&page=${pageNumber}`;
  }

  /**
   * Builds the Pornhub GIF search URL.
   * @param {number} [page] - Page number, same deal as videos.
   * @returns {string} The URL to hit for GIFs.
   * @throws {Error} Bogus page number? You know the drill.
   */
  gifUrl(page) {
    const pageNumber = (page !== undefined && Number.isInteger(page) && page >= this.firstpage) ? page : this.firstpage;

    if (pageNumber < this.firstpage) {
      throw new Error(`Seriously? Page number for ${this.name} GIFs (${pageNumber}) must be ${this.firstpage} or more.`);
    }
    return `${this.baseUrl}/gifs/search?search=${encodeURIComponent(this.query)}&page=${pageNumber}`;
  }

  /**
   * Rips through Pornhub's video search page HTML and extracts the gold.
   * @param {CheerioAPI} $ - Your trusty Cheerio instance, loaded with HTML.
   * @returns {VideoResult[]} Array of video treasures.
   */
  videoParser($) {
    if (typeof $ !== 'function' || typeof $.root !== 'function') { // Basic Cheerio check
      console.error(`[${this.name}] Video parser needs a valid Cheerio instance, genius! What did you pass me?`);
      return [];
    }
    const results = [];
    try {
      // Pornhub's video items usually have this class, but let's be a bit more specific.
      $('ul.videos.search-video-thumbs li.pcVideoListItem[data-id]').each((_, el) => {
        const element = $(el);
        const linkElement = element.find('a.linkVideoThumb').first(); // More specific link
        const thumbImgElement = element.find('img.thumb'); // More specific img
        const durationElement = element.find('.duration');
        const titleElement = element.find('span.title a').first(); // Title is often in its own span a

        const title = titleElement.attr('title')?.trim() || titleElement.text()?.trim() || linkElement.attr('title')?.trim();
        const href = linkElement.attr('href');
        const duration = durationElement.text()?.trim();
        // Try multiple attributes for thumbnails, PH changes stuff. data-src is common for lazy loading.
        let rawThumb = thumbImgElement.attr('data-mediumthumb') || thumbImgElement.attr('data-src') || thumbImgElement.attr('src');

        if (title && href && duration && rawThumb) {
          const cleanedThumb = rawThumb.replace(/\([^)]*\)/g, '').trim(); // Strip (123x456)
          if (cleanedThumb) { // Make sure it's not empty after cleaning
            results.push({
              title,
              url: href.startsWith('http') ? href : `${this.baseUrl}${href}`,
              duration,
              thumb: cleanedThumb.startsWith('//') ? `https:${cleanedThumb}` : (cleanedThumb.startsWith('http') ? cleanedThumb : `${this.baseUrl}${cleanedThumb}`), // Ensure full https URL
              source: this.name,
            });
          } else {
            // console.warn(`[${this.name}] Video skipped: Cleaned thumb was empty. Original: ${rawThumb}`);
          }
        } else {
          // console.warn(`[${this.name}] Video skipped: Missing data. T: ${title}, H: ${href}, D: ${duration}, Th: ${rawThumb}`);
        }
      });
    } catch (error) {
      console.error(`[${this.name}] Oh shit! Video parsing exploded:`, error.message);
    }
    return results;
  }

  /**
   * Shreds Pornhub's GIF page HTML for those sweet, sweet loops.
   * @param {CheerioAPI} $ - Cheerio, again. Don't forget it.
   * @returns {GifResult[]} Array of GIF delights.
   */
  gifParser($) {
    if (typeof $ !== 'function' || typeof $.root !== 'function') {
      console.error(`[${this.name}] GIF parser also needs a real Cheerio instance. Try again!`);
      return [];
    }
    const results = [];
    try {
      // GIF items often have a distinct class or data attribute.
      $('ul.gifs.gifLink li.gifVideoBlock[data-gif_id]').each((_, el) => {
        const element = $(el);
        const linkElement = element.find('a.linkVideoThumb').first(); // GIF links are similar

        if (!linkElement.length) return; // No link, no GIF.

        const gifIdPath = linkElement.attr('href'); // e.g., /view_video.php?viewkey=phGIFID or /gif/123456
        const webmSource = element.find('video[data-webm]').attr('data-webm'); // Direct attribute
        const title = element.find('span.title a').text()?.trim() || linkElement.attr('data-gif_title')?.trim() || "Untitled GIF"; // Robust title finding

        if (gifIdPath && webmSource && title) {
          // Constructing direct GIF URL - Pornhub's CDN URLs can be specific.
          // The original `http://dl.phncdn.com${gifIdPath}.gif` implies `gifIdPath` is exactly what's needed.
          // This can be tricky if `gifIdPath` is like `/view_video.php?viewkey=ID`.
          // A more robust way might involve extracting the actual ID if necessary.
          // For now, let's stick to the pattern that *if* `gifIdPath` is just the ID part it works.
          // If `gifIdPath` is like `/view_video.php?viewkey=ph123`, then `${this.baseGifCdnUrl}/ph123.gif` might be a pattern.
          // The simplest assumption based on original code:
          let directGifSegment = gifIdPath;
          if (gifIdPath.includes("viewkey=")) {
            const keyMatch = gifIdPath.match(/viewkey=([^&]+)/);
            if (keyMatch && keyMatch[1]) directGifSegment = `/${keyMatch[1]}`; // Prepend / if it's just the ID
          }
          // If gifIdPath is already like /ID.gif or /path/to/ID, it might work.
          // This is highly dependent on the exact format of href and what dl.phncdn.com expects.
          // The most reliable method for phncdn is usually based on the actual video key (phXXXXXXXXX).

          results.push({
            title,
            url: `${this.baseGifCdnUrl}${directGifSegment}.gif`, // This is an assumption based on common patterns
            webm: webmSource.startsWith('//') ? `https:${webmSource}` : (webmSource.startsWith('http') ? webmSource : `${this.baseUrl}${webmSource}`), // Ensure full HTTPS URL
            source: this.name,
          });
        } else {
          // console.warn(`[${this.name}] GIF skipped: Missing data. P: ${gifIdPath}, W: ${webmSource}, T: ${title}`);
        }
      });
    } catch (error) {
      console.error(`[${this.name}] Crap! GIF parsing went sideways:`, error.message);
    }
    return results;
  }
}

module.exports = Pornhub;
EOF

# --- Create frontend HTML file ---
info "Creating $FRONTEND_HTML_FILE..."
cat << 'EOF' > "$FRONTEND_HTML_FILE"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Neon Search - Search Interface</title> <!-- Consider making title more specific if possible -->
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            /* Color Palette */
            --neon-pink: #ff00ff;
            --neon-cyan: #00ffff;
            --dark-bg-start: #1a1a2e;
            --dark-bg-end: #16213e;
            --input-bg: #0f172a;
            --text-color: #e0e0e0;
            --card-bg: rgba(0, 0, 0, 0.6);
            --modal-bg: rgba(0, 0, 0, 0.9);
            --error-bg: rgba(255, 0, 0, 0.8);
            --error-border: #ff4d4d;
            --disabled-opacity: 0.6;
            --focus-outline-color: var(--neon-cyan); /* Added for consistency */
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: var(--input-bg); }
        ::-webkit-scrollbar-thumb { background: var(--neon-pink); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #ff77ff; }

        body {
            background: linear-gradient(135deg, var(--dark-bg-start) 0%, var(--dark-bg-end) 100%);
            color: var(--text-color);
            font-family: 'Roboto', sans-serif;
            margin: 0;
            padding: 0;
            overflow-x: hidden; /* Prevent horizontal scroll */
            scrollbar-color: var(--neon-pink) var(--input-bg); /* Firefox scrollbar */
            scrollbar-width: thin; /* Firefox scrollbar */
        }

        /* Search Container */
        .search-container {
            background: rgba(0, 0, 0, 0.7);
            border: 2px solid var(--neon-pink);
            box-shadow: 0 0 20px var(--neon-pink), 0 0 40px var(--neon-cyan), inset 0 0 10px rgba(255, 0, 255, 0.3);
            border-radius: 12px;
        }

        /* Inputs & Select */
        .input-neon, .select-neon {
            background: var(--input-bg);
            color: var(--text-color);
            transition: box-shadow 0.3s ease, border-color 0.3s ease, opacity 0.3s ease;
            appearance: none; /* Remove default styling */
            background-repeat: no-repeat;
            background-position: right 0.75rem center;
            background-size: 0.8em;
            padding-right: 2.5rem; /* Space for custom arrow */
            line-height: 1.5;
            border-radius: 0.5rem; /* Match Tailwind rounded-lg */
        }
        .input-neon {
            border: 2px solid var(--neon-cyan);
            box-shadow: 0 0 10px var(--neon-cyan);
        }
        .input-neon:focus {
            box-shadow: 0 0 20px var(--neon-cyan), 0 0 30px var(--neon-cyan);
            outline: 2px solid transparent; /* Remove default outline */
            outline-offset: 2px;
            border-color: #40e0d0; /* Lighter cyan on focus */
        }
        .select-neon {
            border: 2px solid var(--neon-pink);
            box-shadow: 0 0 10px var(--neon-pink);
            /* Custom arrow using SVG */
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%23ff00ff'%3E%3Cpath fill-rule='evenodd' d='M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z' clip-rule='evenodd'/%3E%3C/svg%3E");
        }
        .select-neon:focus {
            box-shadow: 0 0 20px var(--neon-pink), 0 0 30px var(--neon-pink);
            outline: 2px solid transparent; /* Remove default outline */
            outline-offset: 2px;
            border-color: #ff77ff; /* Lighter pink on focus */
        }
        .input-neon:disabled, .select-neon:disabled {
            cursor: not-allowed;
            opacity: var(--disabled-opacity);
            box-shadow: none;
        }

        /* Buttons */
        .btn-neon {
            background: linear-gradient(45deg, var(--neon-pink), var(--neon-cyan));
            border: none;
            color: #ffffff; /* Ensure contrast */
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
            box-shadow: 0 0 15px var(--neon-pink), 0 0 30px var(--neon-cyan);
            transition: transform 0.2s ease, box-shadow 0.3s ease, background 0.3s ease, opacity 0.3s ease;
            position: relative;
            overflow: hidden;
            border-radius: 0.5rem; /* Match Tailwind rounded-lg */
        }
        .btn-neon:hover:not(:disabled) {
            transform: scale(1.05);
            box-shadow: 0 0 25px var(--neon-pink), 0 0 50px var(--neon-cyan);
        }
        .btn-neon:active:not(:disabled) {
            transform: scale(0.98);
            box-shadow: 0 0 10px var(--neon-pink), 0 0 20px var(--neon-cyan);
        }
        .btn-neon:focus-visible { /* Enhanced focus style */
            outline: 2px solid var(--focus-outline-color);
            outline-offset: 2px;
            box-shadow: 0 0 25px var(--neon-pink), 0 0 50px var(--neon-cyan);
        }
        .btn-neon:disabled {
            cursor: not-allowed;
            opacity: var(--disabled-opacity);
            box-shadow: none;
            background: linear-gradient(45deg, #800080, #008080); /* Darker disabled state */
        }
        .btn-neon .spinner {
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: #fff;
            width: 16px;
            height: 16px;
            animation: spin 1s linear infinite;
            display: inline-block;
            vertical-align: middle;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* Result Cards */
        .card {
            background: var(--card-bg);
            border: 2px solid var(--neon-cyan);
            box-shadow: 0 0 15px var(--neon-cyan), 0 0 30px var(--neon-pink);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            overflow: hidden;
            cursor: pointer;
            height: 300px; /* Fixed height - ensures grid alignment but may clip content */
            display: flex;
            flex-direction: column;
            border-radius: 8px;
        }
        .card:hover, .card:focus-visible { /* Style focus like hover for accessibility */
            transform: translateY(-5px);
            box-shadow: 0 0 25px var(--neon-cyan), 0 0 50px var(--neon-pink);
            outline: 2px solid transparent; /* Use box-shadow for focus indication */
            outline-offset: 2px;
        }
        .card-media-container {
            height: 200px; /* Fixed height for media area */
            background-color: var(--input-bg); /* Placeholder bg */
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0; /* Prevent shrinking */
            position: relative; /* Needed for absolute positioning of children */
            overflow: hidden;
        }
        /* Common styles for img/video */
        .card-media-container img,
        .card-media-container video {
            width: 100%;
            height: 100%;
            object-fit: cover; /* Cover the container */
            display: block;
            background-color: #000; /* Background during load */
        }
        /* Specific styles for video preview */
        .card-media-container img.video-thumb, /* Classify video thumbs */
        .card-media-container video.preview-video {
            position: absolute; /* Position video and thumb to overlap */
            top: 0;
            left: 0;
            transition: opacity 0.3s ease-in-out; /* Smooth transition */
        }
        .card-media-container video.preview-video {
            opacity: 0;
            pointer-events: none; /* Prevent interaction when hidden */
            z-index: 5;
        }
        .card-media-container:hover video.preview-video,
        .card:focus-within .card-media-container video.preview-video { /* Play on focus as well */
            opacity: 1;
            pointer-events: auto;
        }
        .card-media-container img.video-thumb {
            opacity: 1;
            z-index: 1;
        }
        /* GIF images are not absolutely positioned */
        .card-media-container img.gif-image {
            position: static; /* Let it behave normally */
        }

        .card-info {
            height: 100px; /* Fixed height for info area */
            display: flex;
            flex-direction: column;
            justify-content: space-between; /* Push link down */
            padding: 0.75rem;
            flex-grow: 1; /* Allow growing if needed, though height is fixed */
            overflow: hidden;
        }
        .card-title {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap; /* Prevent wrapping */
            text-shadow: 0 0 5px var(--neon-cyan);
        }
        .card-link {
             color: var(--neon-cyan);
             text-shadow: 0 0 5px var(--neon-pink);
             font-size: 0.875rem;
             transition: color 0.2s ease;
             align-self: flex-start;
             margin-top: auto; /* Push to bottom */
             text-decoration: none;
        }
        .card-link:hover, .card-link:focus {
             color: #7fffd4; /* Lighter cyan */
             text-decoration: underline;
             outline: none; /* Handled by parent card focus */
        }
        .media-error-placeholder {
             color: #aaa;
             text-align: center;
             padding: 10px;
             font-size: 0.9em;
             width: 100%;
             height: 100%;
             display: flex;
             align-items: center;
             justify-content: center;
             position: relative; /* Ensure it's positioned correctly */
             z-index: 1;
        }
        .duration-overlay {
            position: absolute;
            bottom: 0.5rem;
            right: 0.5rem;
            background-color: rgba(0, 0, 0, 0.75);
            color: white;
            font-size: 0.75rem;
            padding: 0.125rem 0.5rem;
            border-radius: 4px;
            text-shadow: 1px 1px 1px rgba(0,0,0,0.5);
            pointer-events: none; /* Don't interfere with hover */
            z-index: 10; /* Above image and video */
        }

        /* Modal */
        .modal {
            position: fixed;
            inset: 0;
            background: var(--modal-bg);
            z-index: 1000;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            backdrop-filter: blur(5px);
            -webkit-backdrop-filter: blur(5px);
            /* Transition properties */
            visibility: hidden;
            opacity: 0;
            transition: visibility 0s linear 0.3s, opacity 0.3s ease;
        }
        .modal.is-open {
            visibility: visible;
            opacity: 1;
            transition: visibility 0s linear 0s, opacity 0.3s ease;
        }
        .modal-container {
            position: relative;
            background: var(--input-bg);
            border: 3px solid var(--neon-pink);
            box-shadow: 0 0 30px var(--neon-pink), 0 0 60px var(--neon-cyan);
            max-width: 90vw;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            overflow: hidden; /* Contain content */
            border-radius: 8px;
            transform: scale(0.95); /* Start slightly smaller */
            transition: transform 0.3s ease;
        }
        .modal.is-open .modal-container {
            transform: scale(1); /* Scale to full size when open */
        }
        .modal-content {
            flex-grow: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100%;
            max-height: calc(90vh - 80px); /* Adjust based on link container height */
            overflow: hidden; /* Prevent content overflow */
            padding: 1rem;
            position: relative; /* Needed for error placeholder */
        }
        .modal-content img {
            max-width: 100%;
            max-height: 100%;
            display: block;
            object-fit: contain; /* Ensure full image/gif is visible */
            border-radius: 4px;
        }
        .modal-link-container {
            padding: 10px 15px;
            text-align: center;
            background: rgba(0,0,0,0.5);
            width: 100%;
            flex-shrink: 0; /* Prevent shrinking */
            border-top: 1px solid var(--neon-pink);
            min-height: 40px; /* Ensure some space */
            display: flex; /* Center link vertically */
            align-items: center;
            justify-content: center;
        }
        .modal-link {
            color: var(--neon-cyan);
            font-weight: 600;
            text-decoration: none;
            transition: color 0.2s ease;
            word-break: break-all; /* Prevent long URLs from overflowing */
            display: block; /* Ensure it takes full width for centering */
        }
        .modal-link:hover, .modal-link:focus {
             color: #7fffd4; /* Lighter cyan */
             text-decoration: underline;
             outline: none; /* Use default browser focus or custom style */
        }
        .close-button {
            position: absolute;
            top: 8px;
            right: 12px;
            color: var(--neon-cyan);
            font-size: 2rem;
            font-weight: bold;
            text-shadow: 0 0 10px var(--neon-pink);
            cursor: pointer;
            transition: transform 0.2s ease, color 0.2s ease;
            z-index: 1010; /* Above content */
            line-height: 1;
            border: none;
            background: none;
            padding: 0;
        }
        .close-button:hover, .close-button:focus {
            transform: scale(1.2);
            color: var(--neon-pink);
            outline: none; /* Custom styling */
        }
        .close-button:focus-visible { /* Explicit focus style */
             outline: 2px solid var(--focus-outline-color);
             outline-offset: 1px;
        }

        /* Error Message */
        #errorMessage {
            background: var(--error-bg);
            border: 2px solid var(--error-border);
            box-shadow: 0 0 15px #ff0000;
            color: #ffffff;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            word-break: break-word; /* Prevent overflow */
            transition: opacity 0.3s ease, visibility 0.3s ease; /* Match modal transition timing */
            opacity: 0;
            visibility: hidden;
            border-radius: 0.5rem; /* Match inputs */
        }
        #errorMessage:not(.hidden) { /* Use :not(.hidden) to control visibility */
             opacity: 1;
             visibility: visible;
             transition: opacity 0.3s ease, visibility 0s linear 0s; /* Show immediately */
        }

        /* Skeleton Loaders */
        .skeleton-card {
            background: rgba(0, 0, 0, 0.5);
            border: 2px solid #333; /* Less prominent border */
            border-radius: 8px;
            overflow: hidden;
            height: 300px; /* Match card height */
            animation: pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
            display: flex;
            flex-direction: column;
            padding: 0; /* No padding on skeleton itself */
        }
        .skeleton-img {
            height: 200px; /* Match card media height */
            background-color: #2a2a3e; /* Use a color from the palette */
            flex-shrink: 0;
        }
        .skeleton-info {
            padding: 0.75rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            flex-grow: 1;
            height: 100px; /* Match card info height */
        }
        .skeleton-text {
            height: 1rem; /* Match card title approx height */
            background-color: #2a2a3e;
            width: 80%;
            border-radius: 4px;
            margin-bottom: 0.5rem;
        }
        .skeleton-link {
            height: 0.875rem; /* Match card link approx height */
            background-color: #2a2a3e;
            width: 50%;
            border-radius: 4px;
            margin-top: auto; /* Align bottom */
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: .5; }
        }

        /* Utility */
        .hidden { display: none !important; } /* Tailwind often uses !important */

        /* Responsive Design */
        @media (max-width: 640px) {
            h1 { font-size: 2rem; }
            .search-container { padding: 1rem; }

            /* Adjust flex layout for controls on small screens */
            .search-controls {
                flex-direction: column;
                align-items: stretch; /* Make items full width */
            }
            .search-controls > *:not(:last-child) {
                 margin-bottom: 1rem; /* Add space between stacked controls */
                 margin-right: 0; /* Remove horizontal space */
            }
             /* Ensure selects and button take full width */
             .search-controls > select,
             .search-controls > button {
                 width: 100%;
             }

            /* Adjust card sizes */
            .card, .skeleton-card { height: 280px; }
            .card-media-container, .skeleton-img { height: 150px; }
            .card-info, .skeleton-info { height: 130px; padding: 0.5rem; } /* Increased info height */
            .card-title { font-size: 0.9rem; }

            /* Stack pagination controls vertically */
            .pagination-controls {
                flex-direction: column;
                align-items: stretch; /* Full width buttons */
            }
            .pagination-controls button {
                width: 100%;
                margin-bottom: 0.5rem;
            }
            .pagination-controls button:last-of-type {
                 margin-bottom: 0; /* Remove margin from last button */
            }
            .pagination-controls span { /* Page indicator */
                margin-bottom: 0.5rem;
                text-align: center;
                width: 100%;
            }

            /* Adjust modal content/link for smaller screens */
            .modal-content { padding: 0.5rem; max-height: calc(90vh - 70px); }
            .modal-link-container { min-height: 30px; padding: 5px 10px; }
            .modal-link { font-size: 0.9rem; }
        }
    </style>
</head>
<body class="min-h-screen flex flex-col items-center py-6 px-2">

    <!-- Search Header -->
    <header class="w-full max-w-5xl search-container p-6 sm:p-8 mb-8" role="search" aria-labelledby="search-heading">
        <h1 id="search-heading" class="text-3xl sm:text-4xl font-bold text-center mb-6" style="text-shadow: 0 0 10px var(--neon-pink), 0 0 20px var(--neon-cyan);">
            Neon Search
            <span class="text-lg block font-normal">(Search Interface)</span>
        </h1>
        <!-- Search Controls Container -->
        <div class="search-controls flex flex-col sm:flex-row items-stretch sm:space-x-4 mb-6">
             <input id="searchInput" type="text" placeholder="Enter search query..." aria-label="Search Query" class="input-neon flex-1 p-3 text-base" autocomplete="off">
             <!-- Type Select -->
             <select id="typeSelect" aria-label="Select Search Type" class="select-neon p-3 text-base sm:w-auto">
                 <option value="videos" selected>Videos</option>
                 <option value="gifs">GIFs</option>
             </select>
             <!-- Driver Select -->
             <select id="driverSelect" aria-label="Select Search Provider" class="select-neon p-3 text-base sm:w-auto">
                <option value="pornhub">Pornhub</option>
                <option value="sex">Sex.com</option>
                <option value="redtube" selected>Redtube</option> <!-- Default can be changed -->
                <option value="xvideos">XVideos</option>
                <option value="mock">Mock (Test)</option> <!-- Mock Driver for testing -->
             </select>
            <button id="searchBtn" type="button" class="btn-neon px-6 py-3 font-semibold text-base flex items-center justify-center" aria-controls="results" aria-describedby="errorMessage">
                <span id="searchBtnText">Search</span> <!-- Button Text Span -->
                <span id="loadingIndicator" class="hidden ml-2" aria-hidden="true"><span class="spinner"></span></span>
            </button>
        </div>
        <!-- Error Message Area -->
        <p id="errorMessage" class="text-white text-center p-3 hidden" role="alert" aria-live="assertive"></p>
    </header>

    <!-- Main Content Area (Results) -->
    <main class="w-full max-w-5xl flex-grow">
        <div id="results" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 px-4" aria-live="polite">
            <!-- Initial message or results go here -->
            <p id="initialMessage" class="text-center text-xl col-span-full text-gray-400" style="text-shadow: 0 0 5px var(--neon-cyan);">Enter a query and select options to search...</p>
        </div>

        <!-- Pagination Controls -->
        <nav id="pagination" class="w-full max-w-5xl mt-8 flex justify-center items-center space-x-4 pagination-controls px-4 hidden" role="navigation" aria-label="Pagination">
             <button id="prevBtn" type="button" aria-label="Previous Page" class="btn-neon px-4 py-2 text-sm font-semibold" disabled>&lt; Previous</button>
             <span id="pageIndicator" class="font-semibold text-lg" style="text-shadow: 0 0 8px var(--neon-cyan);" aria-live="polite">Page 1</span>
             <button id="nextBtn" type="button" aria-label="Next Page" class="btn-neon px-4 py-2 text-sm font-semibold" disabled>Next &gt;</button>
        </nav>
    </main>

    <!-- Media Modal -->
    <div id="mediaModal" class="modal" role="dialog" aria-modal="true" aria-labelledby="modalLinkContainer" tabindex="-1">
         <div class="modal-container">
             <button type="button" class="close-button" title="Close" aria-label="Close Modal">×</button>
             <div id="modalContent" class="modal-content">
                 <!-- Modal Image/GIF/Placeholder will be loaded here -->
             </div>
             <div id="modalLinkContainer" class="modal-link-container">
                 <!-- Modal Link will be loaded here -->
             </div>
         </div>
    </div>

    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/axios@1.7.2/dist/axios.min.js" defer></script> <!-- Use defer to load after HTML parsing -->
    <script>
        'use strict';

        // --- Constants ---
        const API_BASE_URL = '/api/search'; // Centralized API endpoint
        const HOVER_PLAY_DELAY_MS = 150; // Delay before playing video on hover/focus
        const HOVER_LEAVE_DELAY_MS = 50; // Delay before pausing video on leave/blur
        const API_TIMEOUT_MS = 25000; // API request timeout in milliseconds
        const SKELETON_COUNT = 9; // Number of skeleton loaders to show

        // --- DOM Element References ---
        const searchInput = document.getElementById('searchInput');
        const typeSelect = document.getElementById('typeSelect');
        const driverSelect = document.getElementById('driverSelect');
        const searchBtn = document.getElementById('searchBtn');
        const searchBtnText = document.getElementById('searchBtnText');
        const loadingIndicator = document.getElementById('loadingIndicator');
        const resultsDiv = document.getElementById('results');
        const initialMessage = document.getElementById('initialMessage');
        const errorMessage = document.getElementById('errorMessage');
        const modal = document.getElementById('mediaModal');
        const modalContent = document.getElementById('modalContent');
        const modalLinkContainer = document.getElementById('modalLinkContainer');
        const closeModalBtn = modal.querySelector('.close-button');
        const paginationControls = document.getElementById('pagination');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const pageIndicator = document.getElementById('pageIndicator');

        // --- Application State ---
        const appState = {
            isLoading: false,
            currentPage: 1,
            currentQuery: '',
            currentDriver: driverSelect.value,
            currentType: typeSelect.value,
            resultsCache: [],
            lastFocusedElement: null, // Store element that opened the modal
            // Heuristic for enabling 'Next' button. Assumes API returns *at least* this many items if more pages exist.
            // This might enable 'Next' on the last page if it returns exactly this number.
            // Ideally, the API provides total results/pages. Updated dynamically based on results.
            maxResultsHeuristic: 18, // Initial default, updated based on API response or mock data size
            hoverPlayTimeout: null, // Timeout ID for delayed video play on hover
            hoverLeaveTimeout: null, // Timeout ID for delayed video pause on leave
        };

        // --- API Communication ---
        /**
         * Fetches search results from the backend API or mock data source.
         * @param {string} query - The search term.
         * @param {string} driver - The selected search provider/driver.
         * @param {string} type - The selected search type ('videos' or 'gifs').
         * @param {number} page - The requested page number.
         * @returns {Promise<{success: boolean, data?: Array<object>, error?: string}>} - Promise resolving to success/data or failure/error.
         */
        async function fetchResultsFromApi(query, driver, type, page) {
            // *** MOCK RESPONSE FOR TESTING ***
            if (driver === 'mock') {
                console.log(`%c[FE] Using Mock Data for ${type}`, 'color: orange');
                await new Promise(resolve => setTimeout(resolve, 500)); // Simulate network delay

                let mockData = [];
                const itemsPerPage = 6; // Define mock pagination size

                if (type === 'videos') {
                     mockData = [
                        { title: "Mock Video 1 (Preview)", url: "#vid1", thumbnail: "https://via.placeholder.com/640x360/ff00ff/fff?text=Vid+Thumb+1", image_hq: "https://via.placeholder.com/1280x720/ff00ff/fff?text=Vid+HQ+1", preview_video: "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4", duration: "0:10" },
                        { title: "Mock Video 2 (No Preview)", url: "#vid2", thumbnail: "https://via.placeholder.com/640x360/00ffff/000?text=Vid+Thumb+2", duration: "1:00" },
                        { title: "Mock Video 3 (Broken Thumb)", url: "#vid3", thumbnail: "https://invalid.url/thumb.jpg", preview_video: "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4", duration: "0:12" },
                        { title: "Mock Video 4 (No Media)", url: "#vid4", duration: "0:30" },
                        { title: "Mock Video 5 (Long Title That Might Wrap Or Get Cut Off Depending on Viewport)", url: "#vid5", thumbnail: "https://via.placeholder.com/640x360/ffaa00/fff?text=Vid+Thumb+5", duration: "5:00" },
                        { title: "Mock Video 6", url: "#vid6", thumbnail: "https://via.placeholder.com/640x360/00aaff/fff?text=Vid+Thumb+6", duration: "0:15" },
                        { title: "Mock Video 7 (Page 2)", url: "#vid7", thumbnail: "https://via.placeholder.com/640x360/aa00ff/fff?text=Vid+Thumb+7", duration: "2:30" },
                    ];
                } else if (type === 'gifs') {
                     mockData = [
                        { title: "Mock GIF 1", url: "https://media.tenor.com/gGQVLAlItnkAAAAC/cat-what.gif" }, // Direct GIF URL
                        { title: "Mock GIF 2", url: "https://media.tenor.com/g13_ym1KMWAAAAAC/cat-typing.gif" },
                        { title: "Mock GIF 3 (WebM Example - Note: Display not implemented)", url: "https://via.placeholder.com/300x200/00ff00/000?text=GIF+Thumb+3", webm: "https://sample-videos.com/video123/webm/720/big_buck_bunny_720p_1mb.webm" },
                        { title: "Mock GIF 4 (Broken URL)", url: "https://invalid.url/image.gif" },
                        { title: "Mock GIF 5", url: "https://media.tenor.com/vjZZE3bXhKcAAAAC/cats-animals.gif" },
                        { title: "Mock GIF 6", url: "https://media.tenor.com/h9c7u4dYm3QAAAAC/cat-computer.gif" },
                        { title: "Mock GIF 7 (Page 2)", url: "https://media.tenor.com/81f5t1LJp7UAAAAC/cat-working.gif" },
                    ];
                }

                // Simulate pagination
                const start = (page - 1) * itemsPerPage;
                const end = start + itemsPerPage;
                const paginatedData = mockData.slice(start, end);
                appState.maxResultsHeuristic = itemsPerPage; // Update heuristic based on mock page size
                return { success: true, data: paginatedData };
            }
            // *** END MOCK RESPONSE ***

            // --- Real API Call ---
            const params = { query, driver, type, page }; // Pass all necessary params
            console.log(`%c[FE] -> API Request: ${API_BASE_URL}`, 'color: cyan', params);

            try {
                const response = await axios.get(API_BASE_URL, { params, timeout: API_TIMEOUT_MS });
                // Ensure data is always an array, even if API returns null or something else on no results
                const data = Array.isArray(response.data) ? response.data : [];
                // Update heuristic based on actual results count, min of 10
                appState.maxResultsHeuristic = data.length > 0 ? Math.max(data.length, 10) : 10;
                console.log(`%c[FE] <- API Success (${response.status}): ${data.length} ${type} results received. Max heuristic: ${appState.maxResultsHeuristic}`, 'color: lightgreen');
                return { success: true, data: data };
            } catch (error) {
                console.error('[FE] <- API Error:', error);
                let message = 'An unexpected error occurred while fetching results.';
                if (error.code === 'ECONNABORTED' || (error.message && error.message.includes('timeout'))) {
                    message = `API request timed out after ${API_TIMEOUT_MS / 1000} seconds. The server might be busy or unavailable.`;
                } else if (error.response) {
                    // Try to get error message from backend response, fallback to status
                    const apiErrorMsg = error.response.data?.error || `Server responded with status ${error.response.status}`;
                    message = `API Error: ${apiErrorMsg}`;
                } else if (error.request) {
                    // Request was made but no response received
                    message = 'Network Error: Could not connect to the backend API. Is the server running?';
                } else {
                    // Setup error or other frontend issue
                    message = `Frontend Error: ${error.message}`;
                }
                return { success: false, error: message };
            }
        }

        // --- UI Manipulation ---

        /** Displays an error message to the user. */
        function showError(message) {
            errorMessage.textContent = message;
            errorMessage.classList.remove('hidden');
            errorMessage.setAttribute('aria-hidden', 'false');
            resultsDiv.innerHTML = ''; // Clear any existing results or skeletons
            initialMessage?.classList.add('hidden'); // Hide initial message
            paginationControls.classList.add('hidden'); // Hide pagination
            console.warn(`%c[FE] Displaying Error: ${message}`, 'color: orange');
        }

        /** Hides the error message area. */
        function hideError() {
            if (!errorMessage.classList.contains('hidden')) {
                errorMessage.classList.add('hidden');
                errorMessage.setAttribute('aria-hidden', 'true');
                errorMessage.textContent = ''; // Clear text for screen readers
            }
        }

        /** Displays skeleton loader cards while results are loading. */
        function showSkeletons(count = SKELETON_COUNT) {
            resultsDiv.innerHTML = ''; // Clear previous content
            initialMessage?.classList.add('hidden'); // Hide initial message
            resultsDiv.setAttribute('aria-busy', 'true'); // Indicate loading state
            console.log(`%c[FE] Displaying ${count} skeleton loaders...`, 'color: gray');
            const fragment = document.createDocumentFragment(); // Use fragment for performance
            for (let i = 0; i < count; i++) {
                const skeleton = document.createElement('div');
                skeleton.className = 'skeleton-card';
                skeleton.setAttribute('aria-hidden', 'true'); // Hide from screen readers
                skeleton.innerHTML = `
                    <div class="skeleton-img"></div>
                    <div class="skeleton-info">
                        <div class="skeleton-text"></div>
                        <div class="skeleton-link"></div>
                    </div>`;
                fragment.appendChild(skeleton);
            }
            resultsDiv.appendChild(fragment);
            paginationControls.classList.add('hidden'); // Hide pagination during load
        }

        /** Updates the UI state (disabling/enabling inputs, showing/hiding loader). */
        function setSearchState(loading) {
            appState.isLoading = loading;
            searchInput.disabled = loading;
            typeSelect.disabled = loading; // Disable type select during load
            driverSelect.disabled = loading;
            searchBtn.disabled = loading;
            resultsDiv.setAttribute('aria-busy', loading ? 'true' : 'false');

            // Always disable pagination buttons when loading starts
            prevBtn.disabled = true;
            nextBtn.disabled = true;

            if (loading) {
                searchBtnText.textContent = 'Searching...';
                loadingIndicator.classList.remove('hidden');
                loadingIndicator.setAttribute('aria-hidden', 'false');
                showSkeletons(); // Show skeletons when loading starts
            } else {
                searchBtnText.textContent = 'Search';
                loadingIndicator.classList.add('hidden');
                loadingIndicator.setAttribute('aria-hidden', 'true');
                // Re-enable inputs only if not loading
                searchInput.disabled = false;
                typeSelect.disabled = false;
                driverSelect.disabled = false;
                searchBtn.disabled = false;
                // Pagination buttons will be updated by updatePaginationButtons() after results
            }
        }

        /** Updates the visibility and state of pagination buttons based on current state. */
        function updatePaginationButtons() {
             // Hide pagination if loading or if an error is currently displayed
            if (appState.isLoading || !errorMessage.classList.contains('hidden')) {
                 paginationControls.classList.add('hidden');
                 return;
            }

            const hasResults = appState.resultsCache.length > 0;
            // Enable 'Next' if we received results equal to or more than the heuristic suggests a full page.
            // This is an *assumption* about the API behavior.
            const likelyMorePages = hasResults && appState.resultsCache.length >= appState.maxResultsHeuristic;
            // Show pagination if we have results OR if we are on a page > 1 (even if page > 1 has no results)
            const showPagination = hasResults || appState.currentPage > 1;

            paginationControls.classList.toggle('hidden', !showPagination);

            if (showPagination) {
                prevBtn.disabled = appState.currentPage <= 1;
                nextBtn.disabled = !likelyMorePages; // Disable if we likely don't have more pages
                pageIndicator.textContent = `Page ${appState.currentPage}`;
                pageIndicator.setAttribute('aria-label', `Current page, Page ${appState.currentPage}`);
            }
        }

        /** Renders a placeholder message within a media container (e.g., for broken images/videos). */
        function renderMediaErrorPlaceholder(container, text) {
             // Avoid adding multiple placeholders
             if (container.querySelector('.media-error-placeholder')) return;

             const errorPlaceholder = document.createElement('p');
             errorPlaceholder.className = 'media-error-placeholder';
             errorPlaceholder.textContent = text;
             container.innerHTML = ''; // Clear potentially broken elements first
             container.appendChild(errorPlaceholder);
        }

        /**
         * Creates the media container (image/video/placeholder) for a result card.
         * @param {object} item - The search result item.
         * @returns {HTMLDivElement} The configured media container element.
         */
        function createMediaContainer(item) {
            const mediaContainer = document.createElement('div');
            mediaContainer.className = 'card-media-container';
            const titleText = item.title || (appState.currentType === 'gifs' ? 'Untitled GIF' : 'Untitled Video');
            mediaContainer.setAttribute('role', 'figure'); // Semantically a figure
            mediaContainer.setAttribute('aria-label', `Preview for ${titleText}`);

            // --- Handle Videos ---
            if (appState.currentType === 'videos') {
                const thumbnailUrl = item.thumbnail || item.thumb; // Accept either key
                const previewVideoUrl = item.preview_video;
                let hasRenderedImage = false;
                let hasRenderedVideo = false;

                // Create image element (acts as poster and fallback)
                if (thumbnailUrl) {
                    const img = document.createElement('img');
                    img.src = thumbnailUrl;
                    img.alt = ''; // Decorative, alt text is on the figure/card
                    img.loading = 'lazy'; // Lazy load card images
                    img.width = 300; // Provide layout hints
                    img.height = 200;
                    img.className = 'video-thumb'; // Class for styling overlap
                    img.onerror = () => {
                        console.warn(`%c[FE] Video thumbnail load failed: ${thumbnailUrl}`, 'color: orange');
                        img.remove(); // Remove broken image
                        hasRenderedImage = false;
                        // If video also fails or doesn't exist, show placeholder
                        if (!hasRenderedVideo && !mediaContainer.querySelector('.media-error-placeholder')) {
                             renderMediaErrorPlaceholder(mediaContainer, 'Preview Unavailable');
                        }
                    };
                    mediaContainer.appendChild(img);
                    hasRenderedImage = true;
                }

                // Create video element if preview URL exists
                if (previewVideoUrl) {
                    const video = document.createElement('video');
                    video.src = previewVideoUrl;
                    // Use thumbnail as poster if available
                    if (hasRenderedImage && mediaContainer.querySelector('img.video-thumb')) {
                        video.poster = thumbnailUrl;
                    }
                    video.width = 300; video.height = 200; // Layout hints
                    video.muted = true; video.loop = true; // Standard preview attributes
                    video.playsInline = true; // Important for mobile
                    video.preload = 'metadata'; // Load enough to get dimensions/duration
                    video.className = 'preview-video';
                    video.onerror = (e) => {
                        console.warn(`%c[FE] Preview video load failed: ${previewVideoUrl}`, 'color: orange', e);
                        video.remove();
                        hasRenderedVideo = false;
                        // If image also failed or doesn't exist, show placeholder
                        if (!hasRenderedImage && !mediaContainer.querySelector('.media-error-placeholder')) {
                            renderMediaErrorPlaceholder(mediaContainer, 'Preview Unavailable');
                        }
                    };
                    // Insert video before image if image exists, otherwise just append
                    const firstChild = mediaContainer.firstChild;
                    if (firstChild) { mediaContainer.insertBefore(video, firstChild); }
                    else { mediaContainer.appendChild(video); }
                    hasRenderedVideo = true;
                }

                // If neither image nor video could be rendered, show placeholder
                if (!hasRenderedImage && !hasRenderedVideo && !mediaContainer.querySelector('.media-error-placeholder')) {
                     renderMediaErrorPlaceholder(mediaContainer, 'No Preview Available');
                }

                // Add duration overlay for videos only
                if (item.duration) {
                    const durationOverlay = document.createElement('span');
                    durationOverlay.className = 'duration-overlay';
                    durationOverlay.textContent = item.duration;
                    durationOverlay.setAttribute('aria-hidden', 'true'); // Decorative
                    mediaContainer.appendChild(durationOverlay);
                }
            }
            // --- Handle GIFs ---
            else if (appState.currentType === 'gifs') {
                const gifUrl = item.url; // GIF URL is expected in 'url' field
                if (gifUrl) {
                    const img = document.createElement('img');
                    img.src = gifUrl;
                    img.alt = ''; // Decorative, alt text is on the figure/card
                    img.loading = 'lazy';
                    img.width = 300; // Layout hints
                    img.height = 200;
                    img.className = 'gif-image'; // Classify for potential specific styling
                    img.onerror = () => {
                        console.warn(`%c[FE] GIF load failed: ${gifUrl}`, 'color: orange');
                        renderMediaErrorPlaceholder(mediaContainer, 'GIF Unavailable');
                    };
                    mediaContainer.appendChild(img);
                } else {
                    // No GIF URL provided
                    renderMediaErrorPlaceholder(mediaContainer, 'No GIF Available');
                }
                // No duration or video preview logic for GIFs
            }

            return mediaContainer;
        }

        /**
         * Displays search results in the grid or shows a 'no results' message.
         * @param {Array<object>} items - Array of result objects from the API.
         */
        function displayResults(items) {
            resultsDiv.innerHTML = ''; // Clear previous results/skeletons
            initialMessage?.classList.add('hidden'); // Ensure initial message is hidden
            resultsDiv.removeAttribute('aria-busy'); // Not busy anymore
            appState.resultsCache = items || []; // Store results, ensure it's an array

            console.log(`%c[FE] Displaying ${appState.resultsCache.length} ${appState.currentType} results.`, 'color: lightgreen');

            if (appState.resultsCache.length === 0) {
                const noResults = document.createElement('p');
                noResults.className = 'text-center text-lg col-span-full p-4';
                noResults.style.textShadow = '0 0 10px var(--neon-pink)';
                // More specific "No results" message
                noResults.textContent = `No ${appState.currentType} found for "${appState.currentQuery}" on page ${appState.currentPage} via ${appState.currentDriver}.`;
                resultsDiv.appendChild(noResults);
            } else {
                const fragment = document.createDocumentFragment(); // Use fragment for performance
                appState.resultsCache.forEach(item => {
                    const card = document.createElement('div');
                    card.className = 'card';

                    // Create media container (handles video/gif/errors internally)
                    const mediaContainer = createMediaContainer(item);

                    // Create info container
                    const infoContainer = document.createElement('div');
                    infoContainer.className = 'card-info';

                    const title = document.createElement('h3');
                    title.className = 'card-title';
                    const titleText = item.title || (appState.currentType === 'gifs' ? 'Untitled GIF' : 'Untitled Video');
                    title.textContent = titleText;
                    title.title = titleText; // Tooltip for potentially truncated titles
                    infoContainer.appendChild(title);

                    const link = document.createElement('a');
                    link.href = item.url || '#'; // For videos: source page; For GIFs: direct GIF URL
                    link.target = '_blank'; // Open in new tab
                    link.rel = 'noopener noreferrer'; // Security best practice
                    link.className = 'card-link';
                    // Adjust link text based on type
                    link.textContent = appState.currentType === 'gifs' ? 'View GIF' : 'View Source';
                    const arrowSpan = document.createElement('span');
                    arrowSpan.setAttribute('aria-hidden', 'true');
                    arrowSpan.innerHTML = ' &rarr;'; // Visual cue
                    link.appendChild(arrowSpan);
                    // Prevent card click when clicking the link itself
                    link.onclick = (e) => e.stopPropagation();
                    infoContainer.appendChild(link);

                    card.appendChild(mediaContainer);
                    card.appendChild(infoContainer);

                    // Make card focusable and interactive
                    card.setAttribute('tabindex', '0');
                    card.setAttribute('role', 'button');
                    card.setAttribute('aria-label', `View details for ${titleText}`);

                    // Event listeners for opening the modal
                    card.addEventListener('click', () => openModal(item, card));
                    card.addEventListener('keydown', (e) => {
                        if (e.key === 'Enter' || e.key === ' ') { // Space or Enter activates
                            e.preventDefault(); // Prevent page scroll on Space
                            openModal(item, card);
                        }
                    });

                    // --- Add Hover/Focus Listeners ONLY for Video Previews ---
                    if (appState.currentType === 'videos') {
                        const videoPreview = mediaContainer.querySelector('video.preview-video');
                        if (videoPreview) {
                            const playVideo = () => {
                                videoPreview.play().catch(e => {
                                    // Ignore AbortError which can happen if play is interrupted quickly
                                    if (e.name !== 'AbortError') {
                                        console.warn('[FE] Video play failed:', e.name, e.message);
                                    }
                                });
                            };
                            const pauseVideo = () => {
                                videoPreview.pause();
                                // Reset video to start only if it has loaded metadata
                                if (videoPreview.readyState > 0) videoPreview.currentTime = 0;
                            };

                            // Play on hover/focus (with delay)
                            const handleMouseEnterFocus = () => {
                                clearTimeout(appState.hoverLeaveTimeout); // Cancel any pending pause
                                // Debounce play action
                                appState.hoverPlayTimeout = setTimeout(playVideo, HOVER_PLAY_DELAY_MS);
                            };
                            // Pause on leave/blur (with delay)
                            const handleMouseLeaveBlur = () => {
                                clearTimeout(appState.hoverPlayTimeout); // Cancel any pending play
                                // Debounce pause action
                                appState.hoverLeaveTimeout = setTimeout(pauseVideo, HOVER_LEAVE_DELAY_MS);
                            };

                            mediaContainer.addEventListener('mouseenter', handleMouseEnterFocus);
                            card.addEventListener('focusin', handleMouseEnterFocus); // Use focusin to capture focus on card itself

                            mediaContainer.addEventListener('mouseleave', handleMouseLeaveBlur);
                            card.addEventListener('focusout', (e) => {
                                // Only pause if focus moves *outside* the card entirely
                                if (!card.contains(e.relatedTarget)) {
                                    handleMouseLeaveBlur();
                                }
                            });
                        }
                    } // --- End Video Hover/Focus Listeners ---

                    fragment.appendChild(card);
                });
                resultsDiv.appendChild(fragment);
            }
            updatePaginationButtons(); // Update pagination based on new results
        }

        // --- Modal Handling ---

        /** Opens the modal, adapting content for Videos or GIFs. */
        function openModal(item, triggerElement) {
            const itemType = appState.currentType; // Use current state type
            const titleText = item.title || (itemType === 'gifs' ? 'Untitled GIF' : 'Untitled Video');
            console.log(`%c[FE] Opening modal for ${itemType}: ${titleText}`, 'color: magenta');

            // Store the element that triggered the modal for focus return
            appState.lastFocusedElement = triggerElement || document.activeElement;

            modalContent.innerHTML = ''; // Clear previous modal content
            modalLinkContainer.innerHTML = ''; // Clear previous modal link

            // --- Modal Content (Image/GIF) ---
            let displayUrl = null;
            let isGif = itemType === 'gifs';

            if (isGif) {
                displayUrl = item.url; // Use direct GIF url
            } else { // It's a video
                // Prefer HQ image if available, fallback to thumbnail
                const thumbnailUrl = item.thumbnail || item.thumb;
                displayUrl = item.image_hq || thumbnailUrl;
            }

            if (displayUrl) {
                const modalImg = document.createElement('img');
                modalImg.src = displayUrl;
                modalImg.alt = `Preview for ${titleText}`; // Alt text for the image itself
                modalImg.loading = 'eager'; // Load modal content eagerly
                modalImg.onerror = () => {
                    console.warn(`%c[FE] Modal ${isGif ? 'GIF' : 'image'} load failed: ${displayUrl}`, 'color: orange');
                    // Simple fallback message inside the modal content area
                    renderMediaErrorPlaceholder(modalContent, `${isGif ? 'GIF' : 'Preview Image'} Failed to Load`);
                    // Make placeholder text more visible in modal
                    const placeholder = modalContent.querySelector('.media-error-placeholder');
                    if(placeholder) placeholder.style.color = 'white';
                };
                modalContent.appendChild(modalImg);
            } else {
                // Render placeholder if no display URL is available at all
                renderMediaErrorPlaceholder(modalContent, `${isGif ? 'GIF' : 'Preview Image'} Not Available`);
                const placeholder = modalContent.querySelector('.media-error-placeholder');
                if(placeholder) placeholder.style.color = 'white';
            }

            // --- Modal Link ---
            const modalLink = document.createElement('a');
            modalLink.href = item.url || '#'; // Video source page or GIF URL
            modalLink.target = '_blank';
            modalLink.rel = 'noopener noreferrer'; // Security best practice
            modalLink.className = 'modal-link';
            // Adjust link text and make it descriptive
            modalLink.textContent = isGif ? `View GIF Source: "${titleText}"` : `View Video Source: "${titleText}"`;
            modalLinkContainer.appendChild(modalLink);

            // Set aria-labelledby to the container holding the descriptive link
            modal.setAttribute('aria-labelledby', 'modalLinkContainer');

            // Show modal and manage focus
            modal.classList.add('is-open');
            // Move focus to the close button after the modal transition likely finishes
            requestAnimationFrame(() => {
                setTimeout(() => closeModalBtn.focus(), 50); // Small delay might help ensure focus works
            });
        }

        /** Closes the media modal and returns focus to the triggering element. */
        function closeModal() {
            if (!modal.classList.contains('is-open')) return; // Prevent closing if already closed

            console.log('%c[FE] Closing modal.', 'color: magenta');
            modal.classList.remove('is-open');

            // Delay clearing content until after fade-out transition (300ms)
            setTimeout(() => {
                // Double check it wasn't immediately reopened
                if (!modal.classList.contains('is-open')) {
                    modalContent.innerHTML = '';
                    modalLinkContainer.innerHTML = '';
                    modal.removeAttribute('aria-labelledby'); // Clean up ARIA attribute
                }
            }, 300);

            // Return focus to the element that opened the modal, or fallback
            if (appState.lastFocusedElement && typeof appState.lastFocusedElement.focus === 'function') {
                // Use requestAnimationFrame to ensure focus happens after potential DOM updates
                // and the element is focusable again (e.g., not hidden by loading state).
                 requestAnimationFrame(() => {
                    try {
                        appState.lastFocusedElement.focus({ preventScroll: true }); // Prevent scrolling jump
                    } catch (e) {
                         console.warn("[FE] Failed to return focus to last element.", e);
                         searchInput.focus(); // Fallback focus
                    }
                 });
            } else {
                searchInput.focus(); // Fallback focus if last element is gone or invalid
            }
            appState.lastFocusedElement = null; // Clear the stored element
        }

        // --- Main Search Orchestration ---

        /** Initiates a search request based on current form values and page number. */
        async function performSearch(page = 1) {
            if (appState.isLoading) {
                console.log('%c[FE] Search ignored, already processing.', 'color: gray');
                return; // Prevent concurrent searches
            }

            const query = searchInput.value.trim();
            const driver = driverSelect.value;
            const type = typeSelect.value; // Get selected type

            if (!query) {
                showError('Please enter a search query.');
                searchInput.focus(); // Focus input if query is missing
                return;
            }

            // Determine if this is a new search (query/driver/type changed) or just pagination
            const isNewSearch = query !== appState.currentQuery || driver !== appState.currentDriver || type !== appState.currentType;
            // If it's a new search, always go to page 1, otherwise use the requested page (ensuring >= 1)
            const targetPage = isNewSearch ? 1 : Math.max(1, page);

            // Update state *before* making the async API call
            appState.currentQuery = query;
            appState.currentDriver = driver;
            appState.currentType = type;
            appState.currentPage = targetPage;

            console.log(`%c[FE] ${isNewSearch ? 'New Search' : 'Paginating'} | Query: "${query}", Driver: ${driver}, Type: ${type}, Page: ${appState.currentPage}`, 'color: yellow');

            hideError(); // Clear any previous errors
            setSearchState(true); // Enter loading state (disables inputs, shows skeletons)

            // Fetch results using the updated state
            const result = await fetchResultsFromApi(appState.currentQuery, appState.currentDriver, appState.currentType, appState.currentPage);

            // --- State Check After Await ---
            // Crucial check: Only process the result if the current state *still* matches the state
            // when this specific request was initiated. Prevents race conditions where a faster,
            // later request finishes before a slower, earlier one.
            if (query === appState.currentQuery && driver === appState.currentDriver && type === appState.currentType && targetPage === appState.currentPage) {
                setSearchState(false); // Exit loading state

                if (result.success) {
                    displayResults(result.data); // Display results if successful
                } else {
                    showError(result.error || 'Failed to fetch results.'); // Display error message
                    appState.resultsCache = []; // Clear cache on error
                    updatePaginationButtons(); // Update pagination (will hide it due to error)
                }
            } else {
                // If state changed while waiting, discard this result
                console.log(`%c[FE] Search result ignored, state changed during request. (Current: ${appState.currentQuery}/${appState.currentDriver}/${appState.currentType}/p${appState.currentPage})`, 'color: gray');
                // Do not call setSearchState(false) here, as another request is likely in progress which will handle it.
            }
        }

        // --- Event Listeners ---

        // Search button click
        searchBtn.addEventListener('click', () => performSearch(1)); // Always start search from page 1

        // Enter key in search input
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault(); // Prevent potential form submission if wrapped in form
                searchBtn.click(); // Trigger search button click
            }
        });

        // Pagination buttons
        prevBtn.addEventListener('click', () => {
            if (!prevBtn.disabled) performSearch(appState.currentPage - 1);
        });
        nextBtn.addEventListener('click', () => {
            if (!nextBtn.disabled) performSearch(appState.currentPage + 1);
        });

        // Modal close button
        closeModalBtn.addEventListener('click', closeModal);

        // Click outside modal content to close
        modal.addEventListener('click', (e) => {
            // Close only if the click is directly on the modal backdrop itself
            if (e.target === modal) {
                closeModal();
            }
        });

        // Escape key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('is-open')) {
                closeModal();
            }
        });

        // Focus Trapping within Modal
        modal.addEventListener('keydown', (e) => {
            if (e.key === 'Tab' && modal.classList.contains('is-open')) {
                // Find all focusable elements within the modal
                const focusableElements = Array.from(
                    modal.querySelectorAll('button, [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')
                ).filter(el => el.offsetParent !== null); // Ensure element is visible and focusable

                if (!focusableElements.length) {
                    e.preventDefault(); // No focusable elements, prevent tabbing away
                    return;
                }

                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];

                if (e.shiftKey) { // Shift + Tab
                    if (document.activeElement === firstElement) {
                        lastElement.focus(); // Wrap to last element
                        e.preventDefault();
                    }
                } else { // Tab
                    if (document.activeElement === lastElement) {
                        firstElement.focus(); // Wrap to first element
                        e.preventDefault();
                    }
                }
                // Allow natural tab order within the modal otherwise
            }
        });

        // --- Initial Setup on Load ---
        window.addEventListener('load', () => {
            console.log('%c[FE] Neon Search Interface Initialized.', 'color: lightgreen');
            // Ensure initial state is clean
            modal.classList.remove('is-open');
            paginationControls.classList.add('hidden');
            errorMessage.classList.add('hidden');
            errorMessage.setAttribute('aria-hidden', 'true'); // Ensure hidden from AT initially

            // Sync initial state from dropdowns (in case HTML defaults change)
            appState.currentDriver = driverSelect.value;
            appState.currentType = typeSelect.value;

            // Set initial focus for usability
            searchInput.focus();
        });

    </script>
</body>
</html>
EOF

# --- Final Instructions ---
echo ""
success "Project '$PROJECT_NAME' setup complete!"
echo ""
info "To run the application:"
info "1. Navigate to the project directory: cd $PROJECT_NAME"
info "2. Start the backend server: node server.cjs"
info "3. Open your web browser and go to: http://localhost:3001 (or the port specified in .env)"
echo ""
info "The script '$0' has finished."


#!/bin/bash

# Exit on any error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${CYAN}🚀 Starting enhanced setup for Neon Video Search App in Termux...${NC}"
echo -e "${CYAN}This script will set up the custom frontend and backend drivers.${NC}"
echo "----------------------------------------------------------------------"

# --- Preliminary Checks ---
echo -e "${CYAN}🔍 Checking for prerequisites (Node.js, npm, git)...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js is not installed. Please install it first.${NC}"
    echo -e "${YELLOW}In Termux, you can try: pkg install nodejs${NC}"
    exit 1
fi
if ! command -v npm &> /dev/null; then
    echo -e "${RED}npm is not installed. Please install it first (usually comes with Node.js).${NC}"
    exit 1
fi
if ! command -v git &> /dev/null; then
    echo -e "${YELLOW}Git is not installed. Installing git...${NC}"
    pkg install git -y
fi
echo -e "${GREEN}Prerequisites check passed.${NC}"
echo "----------------------------------------------------------------------"


# Step 1: Update Termux and install prerequisites
echo -e "${CYAN}🔄 Updating Termux and ensuring Node.js, git, and required packages are present...${NC}"
pkg update -y && pkg upgrade -y
# Node.js and git checks are now above.
# Install termux-api for termux-open if not already installed
pkg install termux-api -y || echo -e "${YELLOW}Termux-api already installed or failed to install. Continuing.${NC}"

# Step 2: Set up Termux storage
echo -e "${CYAN}📂 Setting up Termux storage access (grant permission if prompted)...${NC}"
termux-setup-storage

# Step 3: Create project directory
PROJECT_DIR="$HOME/neon-video-search"
echo -e "${CYAN}📁 Creating project directory at $PROJECT_DIR...${NC}"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Step 4: Initialize npm project and install dependencies for custom drivers
echo -e "${CYAN}📦 Initializing npm project and installing dependencies...${NC}"
npm init -y
echo -e "${CYAN}📦 Installing runtime dependencies (express, axios, cheerio, cors, babel-runtime)...${NC}"
npm install express axios cheerio cors babel-runtime@6.26.0 --save
echo -e "${CYAN}📦 Installing development/optional dependencies (http-server)...${NC}"
npm install http-server --save-dev # http-server is optional if only using Express to serve

# Create core and modules directories
mkdir -p core
mkdir -p modules

# Step 5: Create core JavaScript files
echo -e "${CYAN}⚙️ Creating core JavaScript files (AbstractModule.js, VideoMixin.js, GifMixin.js, OverwriteError.js)...${NC}"

cat > core/OverwriteError.js << 'EOF'
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

/**
 * @class OverwriteError
 * @extends Error
 * @classdesc Custom error class for indicating that an abstract method or property
 * must be overridden by a subclass.
 */
var OverwriteError = function (_Error) {
  _inherits(OverwriteError, _Error);

  /**
   * Creates an instance of OverwriteError.
   * @param {string} methodName - The name of the method or property that needs to be overridden.
   */
  function OverwriteError(methodName) {
    _classCallCheck(this, OverwriteError);

    var _this = _possibleConstructorReturn(this, (OverwriteError.__proto__ || Object.getPrototypeOf(OverwriteError)).call(this, `Method or property "${methodName}" must be overridden by subclass.`));

    _this.name = 'OverwriteError';
    return _this;
  }

  return OverwriteError;
}(Error);

exports.default = OverwriteError;
module.exports = exports['default'];
EOF

cat > core/AbstractModule.js << 'EOF'
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

var _classCallCheck2 = require('babel-runtime/helpers/classCallCheck');
var _classCallCheck3 = _interopRequireDefault(_classCallCheck2);
var _createClass2 = require('babel-runtime/helpers/createClass');
var _createClass3 = _interopRequireDefault(_createClass2);

var _OverwriteError = require('./OverwriteError');
var _OverwriteError2 = _interopRequireDefault(_OverwriteError);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * @class AbstractModule
 * @classdesc Base class for all content source drivers.
 * It handles common functionalities like storing the search query and provides a mixin mechanism.
 * Concrete drivers must implement `name` and `firstpage` getters, and URL/parser methods.
 */
var AbstractModule = function () {
  /**
   * Constructor for AbstractModule.
   * @param {object} [options={}] - Configuration options for the driver.
   * @param {string} [options.query=''] - The search query term.
   */
  function AbstractModule() {
    var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    (0, _classCallCheck3.default)(this, AbstractModule);

    if (typeof options === 'object' && options !== null) {
      this.query = options.query ? options.query.trim() : '';
    } else {
      this.query = '';
    }
    this.page = 1; // Default page number

    // Abstract properties that must be implemented by concrete classes
    if (this.name === undefined) {
      throw new _OverwriteError2.default('name getter');
    }
    if (this.firstpage === undefined) {
      throw new _OverwriteError2.default('firstpage getter');
    }
  }

  (0, _createClass3.default)(AbstractModule, [{
    key: 'setQuery',
    /**
     * Optional method to update the query after instantiation.
     * @param {string} newQuery
     */
    value: function setQuery(newQuery) {
        if (typeof newQuery === 'string') {
            this.query = newQuery.trim();
        } else {
            this.query = '';
        }
    }
  }, {
    key: 'name',
    /**
     * Abstract getter for the name of the driver.
     * Must be implemented by subclasses.
     * @abstract
     * @type {string}
     */
    get: function get() {
      throw new _OverwriteError2.default('name getter');
    }
  }, {
    key: 'firstpage',
    /**
     * Abstract getter for the default starting page number.
     * Must be implemented by subclasses.
     * @abstract
     * @type {number}
     */
    get: function get() {
      throw new _OverwriteError2.default('firstpage getter');
    }
  }], [{
    key: 'with',
    /**
     * Static helper method to apply mixins to a class.
     * @param  {...Function} mixins - Mixin functions to apply.
     * @returns {Function} The class with mixins applied.
     */
    value: function _with() {
      var baseClass = this;
      for (var _len = arguments.length, mixins = Array(_len), _key = 0; _key < _len; _key++) {
        mixins[_key] = arguments[_key];
      }

      return mixins.reduce(function (extendedClass, mixin) {
        if (typeof mixin === 'function') {
          return mixin(extendedClass);
        }
        console.warn('[AbstractModule.with] Encountered a non-function in mixins array:', mixin);
        return extendedClass;
      }, baseClass);
    }
  }]);

  return AbstractModule;
}();

exports.default = AbstractModule;
module.exports = exports['default'];
EOF

cat > core/VideoMixin.js << 'EOF'
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

var _getPrototypeOf = require('babel-runtime/core-js/object/get-prototype-of');
var _getPrototypeOf2 = _interopRequireDefault(_getPrototypeOf);
var _classCallCheck2 = require('babel-runtime/helpers/classCallCheck');
var _classCallCheck3 = _interopRequireDefault(_classCallCheck2);
var _createClass2 = require('babel-runtime/helpers/createClass');
var _createClass3 = _interopRequireDefault(_createClass2);
var _possibleConstructorReturn2 = require('babel-runtime/helpers/possibleConstructorReturn');
var _possibleConstructorReturn3 = _interopRequireDefault(_possibleConstructorReturn2);
var _inherits2 = require('babel-runtime/helpers/inherits');
var _inherits3 = _interopRequireDefault(_inherits2);

var _OverwriteError = require('./OverwriteError');
var _OverwriteError2 = _interopRequireDefault(_OverwriteError);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * @file VideoMixin.js
 * A mixin factory that enhances a base class with abstract video-related methods.
 * Classes that have this mixin applied are contractually obligated to implement
 * `videoUrl()` and `videoParser()` methods for video searching capabilities.
 */

/**
 * A higher-order function (mixin factory) that takes a BaseClass and returns a new class
 * that extends BaseClass and includes video search functionalities.
 * @param {Class} BaseClass - The class to extend.
 * @returns {Class} A new class with video search capabilities.
 */
var WithVideoFeatures = exports.default = function (BaseClass) {
  function WithVideoFeatures() {
    (0, _classCallCheck3.default)(this, WithVideoFeatures);
    return (0, _possibleConstructorReturn3.default)(this, (WithVideoFeatures.__proto__ || Object.getPrototypeOf(WithVideoFeatures)).apply(this, arguments));
  }

  (0, _createClass3.default)(WithVideoFeatures, [{
    key: 'videoUrl',
    /**
     * Abstract method to retrieve the URL for video search.
     * This method MUST be overridden by any class that uses this mixin.
     *
     * @abstract
     * @param {string} query - The search query.
     * @param {number} page - The page number for the search results.
     * @returns {string} The fully qualified URL for video search.
     * @throws {OverwriteError} If this method is not implemented by the consuming class.
     */
    value: function videoUrl(query, page) {
      throw new _OverwriteError2.default('videoUrl');
    }
  }, {
    key: 'videoParser',
    /**
     * Abstract method to parse the raw response (HTML or JSON) from a video search.
     * This method MUST be overridden by any class that uses this mixin.
     *
     * @abstract
     * @param {CheerioAPI | null} cheerioInstance - A CheerioAPI instance loaded with HTML, or null if the response is JSON.
     * @param {string | object} rawBody - The raw string response body (e.g., HTML) or a pre-parsed JSON object.
     * @returns {Array<object>} An array of `MediaResult` objects.
     * @throws {OverwriteError} If this method is not implemented by the consuming class.
     */
    value: function videoParser(cheerioInstance, rawBody) {
      throw new _OverwriteError2.default('videoParser');
    }
  }]);
  return WithVideoFeatures;
}(BaseClass);

module.exports = exports['default'];
EOF

cat > core/GifMixin.js << 'EOF'
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

var _getPrototypeOf = require('babel-runtime/core-js/object/get-prototype-of');
var _getPrototypeOf2 = _interopRequireDefault(_getPrototypeOf);
var _classCallCheck2 = require('babel-runtime/helpers/classCallCheck');
var _classCallCheck3 = _interopRequireDefault(_classCallCheck2);
var _createClass2 = require('babel-runtime/helpers/createClass');
var _createClass3 = _interopRequireDefault(_createClass2);
var _possibleConstructorReturn2 = require('babel-runtime/helpers/possibleConstructorReturn');
var _possibleConstructorReturn3 = _interopRequireDefault(_possibleConstructorReturn2);
var _inherits2 = require('babel-runtime/helpers/inherits');
var _inherits3 = _interopRequireDefault(_inherits2);

var _OverwriteError = require('./OverwriteError');
var _OverwriteError2 = _interopRequireDefault(_OverwriteError);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * @file GifMixin.js
 * A mixin factory that enhances a base class with abstract GIF-related methods.
 * Classes applying this mixin are contractually obligated to implement `gifUrl()`
 * and `gifParser()` methods for GIF searching capabilities.
 */

/**
 * A higher-order function (mixin factory) that takes a BaseClass and returns a new class
 * that extends BaseClass and includes GIF search functionalities.
 * @param {Class} BaseClass - The class to extend.
 * @returns {Class} A new class with GIF search capabilities.
 */
var GifFeatureMixin = exports.default = function (BaseClass) {
  function GifFeatureMixin() {
    (0, _classCallCheck3.default)(this, GifFeatureMixin);
    return (0, _possibleConstructorReturn3.default)(this, (GifFeatureMixin.__proto__ || Object.getPrototypeOf(GifFeatureMixin)).apply(this, arguments));
  }

  (0, _createClass3.default)(GifFeatureMixin, [{
    key: 'gifUrl',
    /**
     * Abstract method to retrieve the URL of the GIF search.
     * This method MUST be overridden by any class that uses this mixin.
     *
     * @abstract
     * @param {string} query - The search query.
     * @param {number} page - The page number for the search results.
     * @returns {string} The fully qualified URL of the GIF search.
     * @throws {OverwriteError} If this method is not implemented by the consuming class.
     */
    value: function gifUrl(query, page) {
      throw new _OverwriteError2.default('gifUrl');
    }
  }, {
    key: 'gifParser',
    /**
     * Abstract method to parse raw GIF data or HTML/JSON response from a GIF search.
     * This method MUST be overridden by any class that uses this mixin.
     *
     * @abstract
     * @param {CheerioAPI | null} cheerioInstance - A CheerioAPI instance loaded with HTML, or null if the response is JSON.
     * @param {string | object} rawData - The raw data stream or buffer of the GIF to be parsed, or raw HTML/JSON.
     * @returns {Array<object>} An array of `MediaResult` objects.
     * @throws {OverwriteError} If this method is not implemented by the consuming class.
     */
    value: function gifParser(cheerioInstance, rawData) {
      throw new _OverwriteError2.default('gifParser');
    }
  }]);
  return GifFeatureMixin;
}(BaseClass);

module.exports = exports['default'];
EOF

# Step 6: Create module-specific JavaScript files
echo -e "${CYAN}⚙️ Creating module-specific JavaScript files (Pornhub.js, Xvideos.js, Redtube.js, Xhamster.js, Youporn.js)...${NC}"

cat > modules/Pornhub.js << 'EOF'
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

var _getPrototypeOf = require('babel-runtime/core-js/object/get-prototype-of');
var _getPrototypeOf2 = _interopRequireDefault(_getPrototypeOf);
var _classCallCheck2 = require('babel-runtime/helpers/classCallCheck');
var _classCallCheck3 = _interopRequireDefault(_classCallCheck2);
var _createClass2 = require('babel-runtime/helpers/createClass');
var _createClass3 = _interopRequireDefault(_createClass2);
var _possibleConstructorReturn2 = require('babel-runtime/helpers/possibleConstructorReturn');
var _possibleConstructorReturn3 = _interopRequireDefault(_possibleConstructorReturn2);
var _inherits2 = require('babel-runtime/helpers/inherits');
var _inherits3 = _interopRequireDefault(_inherits2);

var _GifMixin = require('../core/GifMixin');
var _GifMixin2 = _interopRequireDefault(_GifMixin);
var _VideoMixin = require('../core/VideoMixin');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _AbstractModule = require('../core/AbstractModule');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

const BASE_URL = 'https://www.pornhub.com';
const PLACEHOLDER_GIF_DATA_URI = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';

/**
 * @typedef {object} MediaResult
 * @property {string} id - Unique identifier for the media item.
 * @property {string} title - The title of the media.
 * @property {string} url - The direct URL to the media page.
 * @property {string} [duration] - Duration of the video (e.g., "05:30"). Only for videos.
 * @property {string} thumbnail - URL to the static thumbnail image.
 * @property {string} [preview_video] - URL to an animated video preview (WebM/MP4).
 * @property {string} source - The name of the source (e.g., "Pornhub").
 */

/**
 * @class Pornhub
 * @classdesc Driver for scraping video and GIF content from Pornhub.com.
 * This driver uses Cheerio for parsing HTML.
 */
var Pornhub = function (_AbstractModule$with) {
  (0, _inherits3.default)(Pornhub, _AbstractModule$with);

  function Pornhub() {
    (0, _classCallCheck3.default)(this, Pornhub);
    return (0, _possibleConstructorReturn3.default)(this, (Pornhub.__proto__ || Object.getPrototypeOf(Pornhub)).apply(this, arguments));
  }

  (0, _createClass3.default)(Pornhub, [{
    key: 'videoUrl',
    /**
     * Constructs the URL for video search on Pornhub.
     * @param {string} query - The search query.
     * @param {number} page - The page number.
     * @returns {string} The full URL for the video search results page.
     */
    value: function videoUrl(query, page) {
      return `${BASE_URL}/video/search?search=${encodeURIComponent(query)}&page=${page}`;
    }
  }, {
    key: 'videoParser',
    /**
     * Parses the raw HTML response from a Pornhub video search page.
     * @param {CheerioAPI} $ - A CheerioAPI instance loaded with the HTML.
     * @param {string} rawBody - The raw HTML string.
     * @returns {Array<MediaResult>} An array of parsed video results.
     */
    value: function videoParser($, rawBody) {
      const results = [];
      $('li.pcVideoListItem').each((i, el) => {
        const $el = $(el);
        const titleText = $el.find('.title a').attr('title');
        const relativeUrlToPage = $el.find('.title a').attr('href');
        const videoIdMatch = relativeUrlToPage ? relativeUrlToPage.match(/\/viewkey=(\w+)/) : null;
        const videoId = videoIdMatch ? videoIdMatch[1] : null;

        const durationText = $el.find('.duration').text().trim();
        const staticThumbnailUrl = $el.find('.thumb img').attr('data-thumb_url') || $el.find('.thumb img').attr('src');
        const animatedPreviewUrl = $el.find('a.fade').attr('data-video-overlay-url') || $el.find('video').attr('data-url');

        if (titleText && relativeUrlToPage && videoId) {
          results.push({
            id: videoId,
            title: titleText,
            url: this._makeAbsolute(relativeUrlToPage, BASE_URL),
            duration: durationText,
            thumbnail: staticThumbnailUrl || PLACEHOLDER_GIF_DATA_URI,
            preview_video: animatedPreviewUrl,
            source: this.name
          });
        }
      });
      console.log(`[Pornhub Video Parser] Parsed ${results.length} video items.`);
      return results;
    }
  }, {
    key: 'gifUrl',
    /**
     * Constructs the URL for GIF search on Pornhub.
     * @param {string} query - The search query.
     * @param {number} page - The page number.
     * @returns {string} The full URL for the GIF search results page.
     */
    value: function gifUrl(query, page) {
      return `${BASE_URL}/gifs/search?search=${encodeURIComponent(query)}&page=${page}`;
    }
  }, {
    key: 'gifParser',
    /**
     * Parses the raw HTML response from a Pornhub GIF search page.
     * @param {CheerioAPI} $ - A CheerioAPI instance loaded with the HTML.
     * @param {string} rawBody - The raw HTML string.
     * @returns {Array<MediaResult>} An array of parsed GIF results.
     */
    value: function gifParser($, rawBody) {
      const results = [];
      $('li.gifLink').each((i, el) => {
        const $el = $(el);
        const titleText = $el.find('.gifTitle').text().trim();
        const relativeUrlToPage = $el.find('a').attr('href');
        const gifIdMatch = relativeUrlToPage ? relativeUrlToPage.match(/\/gif(\d+)/) : null;
        const gifId = gifIdMatch ? gifIdMatch[1] : null;

        const staticThumbnailUrl = $el.find('img').attr('data-src') || $el.find('img').attr('src');
        const animatedPreviewUrl = $el.find('video').attr('data-src') || $el.find('img').attr('data-webm');

        if (titleText && relativeUrlToPage && gifId) {
          results.push({
            id: gifId,
            title: titleText,
            url: this._makeAbsolute(relativeUrlToPage, BASE_URL),
            preview_video: animatedPreviewUrl || staticThumbnailUrl,
            thumbnail: staticThumbnailUrl || PLACEHOLDER_GIF_DATA_URI,
            duration: undefined,
            source: this.name
          });
        }
      });
      console.log(`[Pornhub GIF Parser] Parsed ${results.length} GIF items.`);
      return results;
    }
  }, {
    key: '_makeAbsolute',
    value: function _makeAbsolute(urlString, baseUrl) {
      if (!urlString || typeof urlString !== 'string') return undefined;
      if (urlString.startsWith('data:image/')) return urlString;
      if (urlString.startsWith('//')) return `https:${urlString}`;
      if (urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString;
      try {
        return new URL(urlString, baseUrl).href;
      } catch (e) {
        console.warn(`[Pornhub Driver _makeAbsolute] Failed to resolve URL: "${urlString}" with base "${baseUrl}"`, e.message);
        return undefined;
      }
    }
  }, {
    key: 'name',
    get: function get() {
      return 'Pornhub';
    }
  }, {
    key: 'firstpage',
    get: function get() {
      return 1;
    }
  }]);

  return Pornhub;
}(_AbstractModule2.default.with(_GifMixin2.default, _VideoMixin2.default));

module.exports = exports['default'];
EOF

cat > modules/Xvideos.js << 'EOF'
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

var _getPrototypeOf = require('babel-runtime/core-js/object/get-prototype-of');
var _getPrototypeOf2 = _interopRequireDefault(_getPrototypeOf);
var _classCallCheck2 = require('babel-runtime/helpers/classCallCheck');
var _classCallCheck3 = _interopRequireDefault(_classCallCheck2);
var _createClass2 = require('babel-runtime/helpers/createClass');
var _createClass3 = _interopRequireDefault(_createClass2);
var _possibleConstructorReturn2 = require('babel-runtime/helpers/possibleConstructorReturn');
var _possibleConstructorReturn3 = _interopRequireDefault(_possibleConstructorReturn2);
var _inherits2 = require('babel-runtime/helpers/inherits');
var _inherits3 = _interopRequireDefault(_inherits2);

var _VideoMixin = require('../core/VideoMixin');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _AbstractModule = require('../core/AbstractModule');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

const BASE_URL = 'https://www.xvideos.com';

/**
 * @typedef {object} MediaResult
 * @property {string} id - Unique identifier for the media item.
 * @property {string} title - The title of the media.
 * @property {string} url - The direct URL to the media page.
 * @property {string} [duration] - Duration of the video (e.g., "05:30"). Only for videos.
 * @property {string} thumbnail - URL to the static thumbnail image.
 * @property {string} [preview_video] - URL to an animated video preview (WebM/MP4).
 * @property {string} source - The name of the source (e.g., "XVideos").
 */

/**
 * @class Xvideos
 * @classdesc Driver for scraping video content from Xvideos.com.
 * This driver currently focuses on videos.
 */
var Xvideos = function (_AbstractModule$with) {
  (0, _inherits3.default)(Xvideos, _AbstractModule$with);

  function Xvideos() {
    (0, _classCallCheck3.default)(this, Xvideos);
    return (0, _possibleConstructorReturn3.default)(this, (Xvideos.__proto__ || Object.getPrototypeOf(Xvideos)).apply(this, arguments));
  }

  (0, _createClass3.default)(Xvideos, [{
    key: 'videoUrl',
    /**
     * Constructs the URL for video search on Xvideos.
     * @param {string} query - The search query.
     * @param {number} page - The page number.
     * @returns {string} The full URL for the video search results page.
     */
    value: function videoUrl(query, page) {
      return `${BASE_URL}/?k=${encodeURIComponent(query)}&p=${page}`;
    }
  }, {
    key: 'videoParser',
    /**
     * Parses the raw HTML response from an Xvideos video search page.
     * @param {CheerioAPI} $ - A CheerioAPI instance loaded with the HTML.
     * @param {string} rawBody - The raw HTML string.
     * @returns {Array<MediaResult>} An array of parsed video results.
     */
    value: function videoParser($, rawBody) {
      const results = [];
      $('div.thumb-block').each((i, el) => {
        const $el = $(el);
        const titleText = $el.find('.thumb-under a').attr('title');
        const relativeUrl = $el.find('.thumb-under a').attr('href');
        const videoIdMatch = relativeUrl ? relativeUrl.match(/\/video(\d+)\//) : null;
        const videoId = videoIdMatch ? videoIdMatch[1] : null;

        const durationText = $el.find('.duration').text().trim();
        const staticThumbnailUrl = $el.find('img').attr('data-src') || $el.find('img').attr('src');
        const animatedPreviewUrl = $el.find('video').attr('data-src');

        if (titleText && relativeUrl && videoId) {
          results.push({
            id: videoId,
            title: titleText,
            url: this._makeAbsolute(relativeUrl, BASE_URL),
            duration: durationText,
            thumbnail: staticThumbnailUrl,
            preview_video: animatedPreviewUrl,
            source: this.name
          });
        }
      });
      console.log(`[Xvideos Video Parser] Parsed ${results.length} video items.`);
      return results;
    }
  }, {
    key: '_makeAbsolute',
    value: function _makeAbsolute(urlString, baseUrl) {
      if (!urlString || typeof urlString !== 'string') return undefined;
      if (urlString.startsWith('data:image/')) return urlString;
      if (urlString.startsWith('//')) return `https:${urlString}`;
      if (urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString;
      try {
        return new URL(urlString, baseUrl).href;
      } catch (e) {
        console.warn(`[Xvideos Driver _makeAbsolute] Failed to resolve URL: "${urlString}" with base "${baseUrl}"`, e.message);
        return undefined;
      }
    }
  }, {
    key: 'name',
    get: function get() {
      return 'Xvideos';
    }
  }, {
    key: 'firstpage',
    get: function get() {
      return 0;
    }
  }]);

  return Xvideos;
}(_AbstractModule2.default.with(_VideoMixin2.default));

module.exports = exports['default'];
EOF

cat > modules/Redtube.js << 'EOF'
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

var _getPrototypeOf = require('babel-runtime/core-js/object/get-prototype-of');
var _getPrototypeOf2 = _interopRequireDefault(_getPrototypeOf);
var _classCallCheck2 = require('babel-runtime/helpers/classCallCheck');
var _classCallCheck3 = _interopRequireDefault(_classCallCheck2);
var _createClass2 = require('babel-runtime/helpers/createClass');
var _createClass3 = _interopRequireDefault(_createClass2);
var _possibleConstructorReturn2 = require('babel-runtime/helpers/possibleConstructorReturn');
var _possibleConstructorReturn3 = _interopRequireDefault(_possibleConstructorReturn2);
var _inherits2 = require('babel-runtime/helpers/inherits');
var _inherits3 = _interopRequireDefault(_inherits2);

var _VideoMixin = require('../core/VideoMixin');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);

var _AbstractModule = require('../core/AbstractModule');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

const REDTUBE_API_BASE_URL = 'https://api.redtube.com/';
const REDTUBE_API_TOKEN = 'YOUR_REDTUBE_API_TOKEN'; // IMPORTANT: Replace with your actual Redtube API token

/**
 * @typedef {object} MediaResult
 * @property {string} id - Unique identifier for the media item.
 * @property {string} title - The title of the media.
 * @property {string} url - The direct URL to the media page.
 * @property {string} [duration] - Duration of the video (e.g., "05:30"). Only for videos.
 * @property {string} thumbnail - URL to the static thumbnail image.
 * @property {string} [preview_video] - URL to an animated video preview (WebM/MP4).
 * @property {string} source - The name of the source (e.g., "Redtube").
 */

/**
 * @class Redtube
 * @classdesc Driver for fetching video content from Redtube using their official API.
 * Requires an API token.
 */
var Redtube = function (_AbstractModule$with) {
  (0, _inherits3.default)(Redtube, _AbstractModule$with);

  function Redtube() {
    (0, _classCallCheck3.default)(this, Redtube);
    return (0, _possibleConstructorReturn3.default)(this, (Redtube.__proto__ || Object.getPrototypeOf(Redtube)).apply(this, arguments));
  }

  (0, _createClass3.default)(Redtube, [{
    key: 'videoUrl',
    /**
     * Constructs the API URL for video search on Redtube.
     * @param {string} query - The search query.
     * @param {number} page - The page number.
     * @returns {string} The full API URL for the video search.
     */
    value: function videoUrl(query, page) {
      const params = {
        search: query,
        page: page,
        thumbsize: "all"
      };
      // Note: Redtube API documentation might be outdated or behavior might vary.
      // The original example had `&${REDTUBE_API_TOKEN ? `token=${REDTUBE_API_TOKEN}` : ''}` which would just append the token if present,
      // but usually API tokens are part of the `params` object or a header.
      // For now, keeping it as query parameter if it's not empty.
      let url = `${REDTUBE_API_BASE_URL}api/v1.0/Redtube.Videos.search?data=${encodeURIComponent(JSON.stringify(params))}&output=json`;
      if (REDTUBE_API_TOKEN && REDTUBE_API_TOKEN !== 'YOUR_REDTUBE_API_TOKEN') {
          url += `&token=${REDTUBE_API_TOKEN}`;
      }
      return url;
    }
  }, {
    key: 'videoParser',
    /**
     * Parses the raw JSON response from the Redtube API.
     * @param {null} cheerioInstance - Not used for API parsing.
     * @param {string} rawBody - The raw JSON string response body.
     * @returns {Array<MediaResult>} An array of parsed video results.
     */
    value: function videoParser(cheerioInstance, rawBody) {
      const results = [];
      try {
        const apiResponse = JSON.parse(rawBody);
        if (apiResponse && apiResponse.videos && Array.isArray(apiResponse.videos)) {
          apiResponse.videos.forEach(videoWrapper => {
            const apiVideoData = videoWrapper.video;
            if (apiVideoData && apiVideoData.video_id && apiVideoData.title && apiVideoData.url) {
              const thumbnail = apiVideoData.default_thumb || apiVideoData.thumb;
              // Prefer larger GIF previews if available
              const previewVideo = apiVideoData.thumb_600x450_gif || 
                                   apiVideoData.thumb_400x300_gif || 
                                   apiVideoData.thumb_220x165_gif || 
                                   apiVideoData.thumb_120x90_gif;

              results.push({
                id: apiVideoData.video_id,
                title: apiVideoData.title,
                url: apiVideoData.url,
                duration: apiVideoData.duration || 'N/A',
                thumbnail: thumbnail,
                preview_video: previewVideo,
                source: this.name
              });
            }
          });
        } else {
          console.warn('[Redtube Video Parser] Unexpected API response structure:', apiResponse);
        }
      } catch (e) {
        console.error('[Redtube Video Parser] Error parsing JSON response:', e);
      }
      console.log(`[Redtube Video Parser] Parsed ${results.length} video items.`);
      return results;
    }
  }, {
    key: 'name',
    get: function get() {
      return 'Redtube';
    }
  }, {
    key: 'firstpage',
    get: function get() {
      return 1;
    }
  }]);

  return Redtube;
}(_AbstractModule2.default.with(_VideoMixin2.default));

module.exports = exports['default'];
EOF

cat > modules/Xhamster.js << 'EOF'
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

var _getPrototypeOf = require('babel-runtime/core-js/object/get-prototype-of');
var _getPrototypeOf2 = _interopRequireDefault(_getPrototypeOf);
var _classCallCheck2 = require('babel-runtime/helpers/classCallCheck');
var _classCallCheck3 = _interopRequireDefault(_classCallCheck2);
var _createClass2 = require('babel-runtime/helpers/createClass');
var _createClass3 = _interopRequireDefault(_createClass2);
var _possibleConstructorReturn2 = require('babel-runtime/helpers/possibleConstructorReturn');
var _possibleConstructorReturn3 = _interopRequireDefault(_possibleConstructorReturn2);
var _inherits2 = require('babel-runtime/helpers/inherits');
var _inherits3 = _interopRequireDefault(_inherits2);

var _GifMixin = require('../core/GifMixin');
var _GifMixin2 = _interopRequireDefault(_GifMixin);
var _VideoMixin = require('../core/VideoMixin');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _AbstractModule = require('../core/AbstractModule');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

const BASE_URL = 'https://xhamster.com';

/**
 * @typedef {object} MediaResult
 * @property {string} id - Unique identifier for the media item.
 * @property {string} title - The title of the media.
 * @property {string} url - The direct URL to the media page.
 * @property {string} [duration] - Duration of the video (e.g., "05:30"). Only for videos.
 * @property {string} thumbnail - URL to the static thumbnail image.
 * @property {string} [preview_video] - URL to an animated video preview (WebM/MP4).
 * @property {string} source - The name of the source (e.g., "Xhamster").
 */

/**
 * @class Xhamster
 * @classdesc Driver for scraping video and GIF content from Xhamster.com.
 */
var Xhamster = function (_AbstractModule$with) {
  (0, _inherits3.default)(Xhamster, _AbstractModule$with);

  function Xhamster() {
    (0, _classCallCheck3.default)(this, Xhamster);
    return (0, _possibleConstructorReturn3.default)(this, (Xhamster.__proto__ || Object.getPrototypeOf(Xhamster)).apply(this, arguments));
  }

  (0, _createClass3.default)(Xhamster, [{
    key: 'videoUrl',
    /**
     * Constructs the URL for video search on Xhamster.
     * @param {string} query - The search query.
     * @param {number} page - The page number.
     * @returns {string} The full URL for the video search results page.
     */
    value: function videoUrl(query, page) {
      return `${BASE_URL}/search/${encodeURIComponent(query)}?page=${page}`; // Xhamster uses page query param for videos
    }
  }, {
    key: 'videoParser',
    /**
     * Parses the raw HTML response from an Xhamster video search page.
     * @param {CheerioAPI} $ - A CheerioAPI instance loaded with the HTML.
     * @param {string} rawBody - The raw HTML string.
     * @returns {Array<MediaResult>} An array of parsed video results.
     */
    value: function videoParser($, rawBody) {
      const results = [];
      // Selector might need update if Xhamster changes layout
      $('div.video-thumb-info__name a.video-thumb-info__name').each((i, el) => {
        const $el = $(el);
        const titleText = $el.text().trim();
        const relativeUrl = $el.attr('href');
        const videoIdMatch = relativeUrl ? relativeUrl.match(/\/videos\/[^\/]+-(\d+)/) : null;
        const videoId = videoIdMatch ? videoIdMatch[1] : null;
        
        const $videoThumb = $el.closest('div.video-thumb');
        const durationText = $videoThumb.find('.video-thumb-duration').text().trim();
        const staticThumbnailUrl = $videoThumb.find('img.video-thumb__image').attr('src');
        const animatedPreviewUrl = $videoThumb.find('video.video-thumb__preview-video').attr('src');

        if (titleText && relativeUrl && videoId) {
          results.push({
            id: videoId,
            title: titleText,
            url: this._makeAbsolute(relativeUrl, BASE_URL),
            duration: durationText,
            thumbnail: staticThumbnailUrl,
            preview_video: animatedPreviewUrl,
            source: this.name
          });
        }
      });
      // Fallback for a slightly different structure sometimes observed
      if (results.length === 0) {
          $('a.video-thumb-info__name').each((i, el) => {
            const $el = $(el);
            const titleText = $el.text().trim();
            const relativeUrl = $el.attr('href');
            const videoIdMatch = relativeUrl ? relativeUrl.match(/\/videos\/[^\/]+-(\d+)/) : null;
            const videoId = videoIdMatch ? videoIdMatch[1] : null;

            const $videoThumbContainer = $el.closest('.video-thumb__container');
            const durationText = $videoThumbContainer.find('.video-thumb-duration').text().trim();
            const staticThumbnailUrl = $videoThumbContainer.find('img.video-thumb__image').attr('src');
            // Note: Xhamster might use JS to load previews, direct video tag src might not always be there
            const animatedPreviewUrl = $videoThumbContainer.find('video').attr('src') || $videoThumbContainer.find('img.video-thumb__image').attr('data-preview');


            if (titleText && relativeUrl && videoId) {
              results.push({
                id: videoId,
                title: titleText,
                url: this._makeAbsolute(relativeUrl, BASE_URL),
                duration: durationText,
                thumbnail: staticThumbnailUrl,
                preview_video: animatedPreviewUrl,
                source: this.name
              });
            }
          });
      }
      console.log(`[Xhamster Video Parser] Parsed ${results.length} video items.`);
      return results;
    }
  }, {
    key: 'gifUrl',
    /**
     * Constructs the URL for GIF search on Xhamster.
     * @param {string} query - The search query.
     * @param {number} page - The page number.
     * @returns {string} The full URL for the GIF search results page.
     */
    value: function gifUrl(query, page) {
      return `${BASE_URL}/gifs/search/${encodeURIComponent(query)}/${page}`; // GIFs seem to use path-based pagination
    }
  }, {
    key: 'gifParser',
    /**
     * Parses the raw HTML response from an Xhamster GIF search page.
     * @param {CheerioAPI} $ - A CheerioAPI instance loaded with the HTML.
     * @param {string} rawBody - The raw HTML string.
     * @returns {Array<MediaResult>} An array of parsed GIF results.
     */
    value: function gifParser($, rawBody) {
      const results = [];
      // Selector might need update if Xhamster changes layout for GIFs
      $('div.gif-thumb__name a').each((i, el) => {
        const $el = $(el);
        const titleText = $el.text().trim();
        const relativeUrl = $el.attr('href');
        const gifIdMatch = relativeUrl ? relativeUrl.match(/\/gifs\/[^\/]+-(\d+)/) : null;
        const gifId = gifIdMatch ? gifIdMatch[1] : null;

        const $gifThumb = $el.closest('div.gif-thumb');
        const staticPosterUrl = $gifThumb.find('img.gif-thumb__image').attr('src');
        const animatedGifUrl = $gifThumb.find('video.gif-thumb__preview-video').attr('src') || staticPosterUrl; // Fallback to poster

        if (titleText && relativeUrl && gifId) {
          results.push({
            id: gifId,
            title: titleText,
            url: this._makeAbsolute(relativeUrl, BASE_URL),
            preview_video: animatedGifUrl,
            thumbnail: staticPosterUrl,
            duration: undefined,
            source: this.name
          });
        }
      });
      console.log(`[Xhamster GIF Parser] Parsed ${results.length} GIF items.`);
      return results;
    }
  }, {
    key: '_makeAbsolute',
    value: function _makeAbsolute(urlString, baseUrl) {
      if (!urlString || typeof urlString !== 'string') return undefined;
      if (urlString.startsWith('data:image/')) return urlString;
      if (urlString.startsWith('//')) return `https:${urlString}`;
      if (urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString;
      try {
        return new URL(urlString, baseUrl).href;
      } catch (e) {
        console.warn(`[Xhamster Driver _makeAbsolute] Failed to resolve URL: "${urlString}" with base "${baseUrl}"`, e.message);
        return undefined;
      }
    }
  }, {
    key: 'name',
    get: function get() {
      return 'Xhamster';
    }
  }, {
    key: 'firstpage',
    get: function get() {
      return 1;
    }
  }]);

  return Xhamster;
}(_AbstractModule2.default.with(_GifMixin2.default, _VideoMixin2.default));

module.exports = exports['default'];
EOF

cat > modules/Youporn.js << 'EOF'
'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

var _getPrototypeOf = require('babel-runtime/core-js/object/get-prototype-of');
var _getPrototypeOf2 = _interopRequireDefault(_getPrototypeOf);
var _classCallCheck2 = require('babel-runtime/helpers/classCallCheck');
var _classCallCheck3 = _interopRequireDefault(_classCallCheck2);
var _createClass2 = require('babel-runtime/helpers/createClass');
var _createClass3 = _interopRequireDefault(_createClass2);
var _possibleConstructorReturn2 = require('babel-runtime/helpers/possibleConstructorReturn');
var _possibleConstructorReturn3 = _interopRequireDefault(_possibleConstructorReturn2);
var _inherits2 = require('babel-runtime/helpers/inherits');
var _inherits3 = _interopRequireDefault(_inherits2);

var _VideoMixin = require('../core/VideoMixin');
var _VideoMixin2 = _interopRequireDefault(_VideoMixin);
var _AbstractModule = require('../core/AbstractModule');
var _AbstractModule2 = _interopRequireDefault(_AbstractModule);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

const BASE_URL = 'https://www.youporn.com';

/**
 * @typedef {object} MediaResult
 * @property {string} id - Unique identifier for the media item.
 * @property {string} title - The title of the media.
 * @property {string} url - The direct URL to the media page.
 * @property {string} [duration] - Duration of the video (e.g., "05:30"). Only for videos.
 * @property {string} thumbnail - URL to the static thumbnail image.
 * @property {string} [preview_video] - URL to an animated video preview (WebM/MP4).
 * @property {string} source - The name of the source (e.g., "Youporn").
 */

/**
 * @class Youporn
 * @classdesc Driver for scraping video content from Youporn.com.
 * NOTE: Youporn.com's HTML structure and selectors might change.
 * These selectors are based on inspection at a point in time.
 */
var Youporn = function (_AbstractModule$with) {
  (0, _inherits3.default)(Youporn, _AbstractModule$with);

  function Youporn() {
    (0, _classCallCheck3.default)(this, Youporn);
    return (0, _possibleConstructorReturn3.default)(this, (Youporn.__proto__ || Object.getPrototypeOf(Youporn)).apply(this, arguments));
  }

  (0, _createClass3.default)(Youporn, [{
    key: 'videoUrl',
    /**
     * Constructs the URL for video search on Youporn.
     * @param {string} query - The search query.
     * @param {number} page - The page number.
     * @returns {string} The full URL for the video search results page.
     */
    value: function videoUrl(query, page) {
      return `${BASE_URL}/search/?query=${encodeURIComponent(query)}&page=${page}`;
    }
  }, {
    key: 'videoParser',
    /**
     * Parses the raw HTML response from a Youporn video search page.
     * @param {CheerioAPI} $ - A CheerioAPI instance loaded with the HTML.
     * @param {string} rawBody - The raw HTML string.
     * @returns {Array<MediaResult>} An array of parsed video results.
     */
    value: function videoParser($, rawBody) {
      const results = [];
      // Selector for video items. This is highly subject to change.
      // As of late 2023/early 2024, YouPorn uses client-side rendering heavily.
      // Direct scraping of simple HTML might be insufficient or yield few results.
      // This parser attempts a basic structure often found in such sites.
      $('div.video-list-item, div.video-item, li.video-thumb-item').each((i, el) => {
        const $el = $(el);
        // Try to find title and link from common patterns
        const $linkElement = $el.find('a[href*="/watch/"]');
        const titleText = $linkElement.attr('title') || $linkElement.find('.video-title, .title').text().trim();
        const relativeUrl = $linkElement.attr('href');
        
        const videoIdMatch = relativeUrl ? relativeUrl.match(/\/watch\/(\d+)\//) : null;
        const videoId = videoIdMatch ? videoIdMatch[1] : null;

        const durationText = $el.find('.duration, .video-duration').text().trim();
        // Thumbnails can be in img tags, data attributes, or style attributes
        let staticThumbnailUrl = $el.find('img').attr('data-src') || $el.find('img').attr('src');
        if (!staticThumbnailUrl) {
            const styleThumb = $el.find('[style*="background-image"]').css('background-image');
            if (styleThumb && styleThumb.includes('url(')) {
                staticThumbnailUrl = styleThumb.replace(/^url\(["']?/, '').replace(/["']?\)$/, '');
            }
        }

        // Animated previews are often in video tags or data attributes on images
        const animatedPreviewUrl = $el.find('video[data-preview_url], video[data-src]').attr('data-preview_url') || 
                                   $el.find('video[data-preview_url], video[data-src]').attr('data-src') ||
                                   $el.find('img[data-gif_url], img[data-preview]').attr('data-gif_url') ||
                                   $el.find('img[data-gif_url], img[data-preview]').attr('data-preview');


        if (titleText && relativeUrl && videoId) {
          results.push({
            id: videoId,
            title: titleText,
            url: this._makeAbsolute(relativeUrl, BASE_URL),
            duration: durationText || 'N/A',
            thumbnail: staticThumbnailUrl,
            preview_video: animatedPreviewUrl,
            source: this.name
          });
        }
      });
      
      if (results.length === 0) {
          console.warn("[Youporn Video Parser] No items found with primary selectors. YouPorn might have changed its layout or uses heavy client-side rendering not capturable by simple Cheerio parsing.");
      }
      console.log(`[Youporn Video Parser] Parsed ${results.length} video items.`);
      return results;
    }
  }, {
    key: '_makeAbsolute',
    value: function _makeAbsolute(urlString, baseUrl) {
      if (!urlString || typeof urlString !== 'string') return undefined;
      if (urlString.startsWith('data:image/')) return urlString;
      if (urlString.startsWith('//')) return `https:${urlString}`;
      if (urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString;
      try {
        return new URL(urlString, baseUrl).href;
      } catch (e) {
        console.warn(`[Youporn Driver _makeAbsolute] Failed to resolve URL: "${urlString}" with base "${baseUrl}"`, e.message);
        return undefined;
      }
    }
  }, {
    key: 'name',
    get: function get() {
      return 'Youporn';
    }
  }, {
    key: 'firstpage',
    get: function get() {
      return 1;
    }
  }]);

  return Youporn;
}(_AbstractModule2.default.with(_VideoMixin2.default));

module.exports = exports['default'];
EOF

# Step 7: Create the backend server file (server.js)
echo -e "${CYAN}⚙️ Creating backend server file (server.js) to serve API requests and frontend...${NC}"
cat > server.js << 'EOF'
#!/usr/bin/env node

const express = require('express');
const cors = require('cors'); // Import cors
const app = express();
const path = require('path');
const axios = require('axios');
const cheerio = require('cheerio');
const { URL } = require('url');

// Import core modules and mixins
const AbstractModule = require('./core/AbstractModule');
const VideoMixin = require('./core/VideoMixin');
const GifMixin = require('./core/GifMixin');

// Import all specific drivers
const Redtube = require('./modules/Redtube');
const Pornhub = require('./modules/Pornhub');
const Xvideos = require('./modules/Xvideos');
const Xhamster = require('./modules/Xhamster');
const Youporn = require('./modules/Youporn');

// Map driver names to their classes
const drivers = {
    'redtube': Redtube,
    'pornhub': Pornhub,
    'xvideos': Xvideos,
    'xhamster': Xhamster,
    'youporn': Youporn,
    // Add a mock driver for testing
    'mock': class MockDriver extends AbstractModule.with(VideoMixin, GifMixin) {
        constructor(options) { super(options); }
        get name() { return 'Mock'; }
        get firstpage() { return 1; }
        videoUrl(query, page) { return `http://mock.com/videos?q=${query}&page=${page}`; }
        videoParser(cheerioInstance, rawBody) {
            console.log('Mock Video Parser called.');
            const results = [];
            for (let i = 0; i < 5; i++) {
                results.push({
                    id: `mock-video-${i}-${Date.now()}`,
                    title: `Mock Video ${this.query} - Page ${this.page} - Item ${i + 1}`,
                    url: `http://mock.com/video/${i}`,
                    duration: '0:30',
                    thumbnail: `https://placehold.co/320x180/00e5ff/000000?text=Mock+Video+${i+1}`,
                    preview_video: `https://www.w3schools.com/html/mov_bbb.mp4`, // A common test video
                    source: 'Mock.com'
                });
            }
            return results;
        }
        gifUrl(query, page) { return `http://mock.com/gifs?q=${query}&page=${page}`; }
        gifParser(cheerioInstance, rawData) { // Ensure gifParser also accepts cheerioInstance
            console.log('Mock GIF Parser called.');
            const results = [];
            for (let i = 0; i < 5; i++) {
                results.push({
                    id: `mock-gif-${i}-${Date.now()}`,
                    title: `Mock GIF ${this.query} - Page ${this.page} - Item ${i + 1}`,
                    url: `http://mock.com/gif/${i}`,
                    thumbnail: `https://placehold.co/320x180/ff00aa/000000?text=Mock+GIF+${i+1}`,
                    preview_video: `https://i.giphy.com/media/VbnUQpnihPSIgIXuZv/giphy.gif`, // A sample GIF
                    source: 'Mock.com'
                });
            }
            return results;
        }
    }
};

// Middleware
app.use(cors()); // Enable CORS for all routes
app.use(express.static(__dirname)); // Serve static files from the current directory (for index.html)

// API endpoint for search
app.get('/api/search', async (req, res) => {
    const { query, driver: driverName, type, page } = req.query;

    if (!query || !driverName || !type) {
        return res.status(400).json({ error: 'Missing query, driver, or type parameters.' });
    }

    const DriverClass = drivers[driverName.toLowerCase()];
    if (!DriverClass) {
        return res.status(400).json({ error: `Unsupported driver: ${driverName}.` });
    }

    try {
        const driverInstance = new DriverClass({ query });
        driverInstance.setQuery(query);
        driverInstance.page = parseInt(page, 10) || driverInstance.firstpage;

        let results = [];
        let url = '';
        let rawContent;

        // Axios request configuration
        const axiosConfig = {
            timeout: 30000, // 30 seconds timeout
            headers: {
                // Some sites might require a common User-Agent
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        };

        if (type === 'videos' && typeof driverInstance.videoUrl === 'function' && typeof driverInstance.videoParser === 'function') {
            url = driverInstance.videoUrl(query, driverInstance.page);
            console.log(`[Backend] Fetching video from ${driverName}: ${url}`);
            const response = await axios.get(url, axiosConfig);
            rawContent = response.data;

            // Cheerio is passed for drivers that parse HTML, null otherwise (e.g., API-based drivers)
            // The list-based check is a bit fragile; a driver property would be better for future.
            if (['pornhub', 'xvideos', 'xhamster', 'youporn'].includes(driverName.toLowerCase())) {
                const $ = cheerio.load(rawContent);
                results = await driverInstance.videoParser($, rawContent);
            } else {
                results = await driverInstance.videoParser(null, rawContent); // e.g., Redtube (JSON API), Mock
            }
        } else if (type === 'gifs' && typeof driverInstance.gifUrl === 'function' && typeof driverInstance.gifParser === 'function') {
            url = driverInstance.gifUrl(query, driverInstance.page);
            console.log(`[Backend] Fetching GIF from ${driverName}: ${url}`);
            const response = await axios.get(url, axiosConfig);
            rawContent = response.data;

            if (['pornhub', 'xhamster'].includes(driverName.toLowerCase())) { // Mock also uses null for cheerio
                const $ = cheerio.load(rawContent);
                results = await driverInstance.gifParser($, rawContent);
            } else {
                results = await driverInstance.gifParser(null, rawContent); // Pass null for cheerioInstance if not HTML scraping
            }
        } else {
            return res.status(400).json({ error: `Unsupported search type '${type}' for driver '${driverName}'.` });
        }

        results = results.map(item => ({
            ...item,
            source: driverInstance.name // Ensure source is set from driver
        }));

        res.json(results);

    } catch (error) {
        console.error(`[Backend] Error during search for ${driverName} (${type}):`, error.message);
        if (error.response) {
            console.error(`[Backend] Response status: ${error.response.status}, data:`, error.response.data);
            res.status(error.response.status).json({ error: `Failed to fetch results from ${driverName}. Server responded with ${error.response.status}. ${error.response.data.error || ''}` });
        } else if (error.request) {
             console.error(`[Backend] No response received for request to ${driverName}.`);
             res.status(504).json({ error: `Failed to fetch results from ${driverName}. No response from upstream server.` });
        } else {
            res.status(500).json({ error: `Failed to fetch results from ${driverName}. ${error.message}` });
        }
    }
});

// Serve index.html for the root path
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});


const PORT = process.env.PORT || 3000;
app.listen(PORT, '0.0.0.0', () => { // Listen on 0.0.0.0 to be accessible on network
    console.log(`Neon Video Search App backend API server running on http://0.0.0.0:${PORT}`);
    console.log(`Frontend should be accessible at http://localhost:${PORT} or http://<your-device-ip>:${PORT}`);
});
EOF
chmod +x server.js

# Step 8: Create the enhanced frontend HTML file (index.html)
echo -e "${CYAN}🎨 Creating the enhanced frontend HTML file (index.html)...${NC}"
cat > index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Neon Search | Find Videos & GIFs</title>
    <meta name="description" content="Search for videos and GIFs with a vibrant neon-themed interface. Features history and local favorites.">
    <meta name="keywords" content="video search, gif search, neon theme, online media, adult entertainment search, favorites, history">
    <meta name="author" content="Neon Search Project">
    <!-- Using a cool neon light bulb emoji as the favicon -->
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>💡</text></svg>">

    <!-- Link to Tailwind CSS for utility classes -->
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <!-- Link to Google Fonts (Roboto) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">

    <style>
        /* --- CSS Variables for Enhanced Neon Theme --- */
        :root {
            --neon-pink: #ff00aa;
            --neon-cyan: #00e5ff;
            --neon-green: #39ff14;
            --neon-purple: #9d00ff;
            --dark-bg-start: #0d0c1d;
            --dark-bg-end: #101026;
            --input-bg: #0a0a1a;
            --text-color: #f0f0f0;
            --card-bg: rgba(10, 10, 26, 0.8);
            --modal-bg: rgba(5, 5, 15, 0.96);
            --error-bg: rgba(255, 20, 100, 0.88);
            --error-border: var(--neon-pink);
            --disabled-opacity: 0.4;
            --focus-outline-color: var(--neon-green);
            --link-color: var(--neon-cyan);
            --link-hover-color: var(--neon-green);
            --favorite-btn-color: #aaa;
            --favorite-btn-active-color: var(--neon-pink);
        }

        /* --- Base Styles & Scrollbar --- */
        html { scroll-behavior: smooth; }
        body {
            background: linear-gradient(145deg, var(--dark-bg-start) 0%, var(--dark-bg-end) 100%);
            color: var(--text-color);
            font-family: 'Roboto', sans-serif;
            margin: 0; padding: 0; overflow-x: hidden; min-height: 100vh;
            scrollbar-color: var(--neon-pink) var(--input-bg); scrollbar-width: thin;
        }
        ::-webkit-scrollbar { width: 10px; }
        ::-webkit-scrollbar-track { background: var(--input-bg); border-radius: 5px; }
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(var(--neon-pink), var(--neon-purple));
            border-radius: 5px; border: 1px solid var(--dark-bg-end);
        }
        ::-webkit-scrollbar-thumb:hover { background: linear-gradient(var(--neon-purple), var(--neon-pink)); }

        /* --- Layout & Main Title --- */
        .search-container {
            background: rgba(10, 10, 25, 0.9); border: 2px solid var(--neon-pink);
            box-shadow: 0 0 20px var(--neon-pink), 0 0 40px var(--neon-cyan), 0 0 60px var(--neon-purple), inset 0 0 15px rgba(255, 0, 170, 0.5);
            border-radius: 16px;
            animation: searchContainerGlow 6s infinite alternate ease-in-out;
        }
        @keyframes searchContainerGlow {
            0% { box-shadow: 0 0 20px var(--neon-pink), 0 0 40px var(--neon-cyan), 0 0 60px var(--neon-purple), inset 0 0 15px rgba(255, 0, 170, 0.5); border-color: var(--neon-pink); }
            50% { box-shadow: 0 0 30px var(--neon-cyan), 0 0 50px var(--neon-purple), 0 0 70px var(--neon-pink), inset 0 0 20px rgba(0, 229, 255, 0.5); border-color: var(--neon-cyan); }
            100% { box-shadow: 0 0 20px var(--neon-purple), 0 0 40px var(--neon-pink), 0 0 60px var(--neon-cyan), inset 0 0 15px rgba(157, 0, 255, 0.5); border-color: var(--neon-purple); }
        }
        .title-main { text-shadow: 0 0 10px var(--neon-pink), 0 0 20px var(--neon-cyan), 0 0 30px var(--neon-purple), 0 0 40px #fff; }
        .title-sub { text-shadow: 0 0 5px var(--neon-cyan); }

        /* --- Form Elements (Enhanced Neon) --- */
        .input-wrapper { position: relative; display: flex; align-items: center; flex: 1; }
        .input-neon {
            background: var(--input-bg); color: var(--text-color); border: 2px solid var(--neon-cyan);
            box-shadow: 0 0 10px var(--neon-cyan), inset 0 0 8px rgba(0, 229, 255, 0.25);
            transition: all 0.3s ease; padding: 0.75rem 1rem; padding-right: 2.8rem;
            font-size: 1rem; line-height: 1.5; border-radius: 0.6rem; width: 100%;
        }
        .input-neon::placeholder { color: var(--text-color); opacity: 0.6; }
        .input-neon:focus {
            border-color: var(--neon-green);
            box-shadow: 0 0 18px var(--neon-green), 0 0 30px var(--neon-cyan), inset 0 0 10px rgba(57, 255, 20, 0.4);
            outline: none; animation: focusPulseNeon 1.2s infinite alternate;
        }
        .clear-input-btn {
            position: absolute; right: 0.5rem; top: 50%; transform: translateY(-50%);
            background: transparent; border: none; color: var(--neon-pink);
            font-size: 1.8rem; line-height: 1; cursor: pointer; display: none;
            padding: 0.25rem; transition: color 0.2s ease, transform 0.2s ease; z-index: 10;
        }
        .input-wrapper input:not(:placeholder-shown)+.clear-input-btn { display: block; }
        .clear-input-btn:hover { color: var(--neon-green); transform: translateY(-50%) scale(1.15) rotate(90deg); }
        .select-neon {
            background: var(--input-bg); color: var(--text-color); border: 2px solid var(--neon-pink);
            box-shadow: 0 0 10px var(--neon-pink), inset 0 0 8px rgba(255, 0, 170, 0.25);
            transition: all 0.3s ease; padding: 0.75rem 1rem; font-size: 1rem; line-height: 1.5; border-radius: 0.6rem;
            -webkit-appearance: none; -moz-appearance: none; appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%23ff00aa'%3E%3Cpath fill-rule='evenodd' d='M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z' clip-rule='evenodd'/%3E%3C/svg%3E");
            background-repeat: no-repeat; background-position: right 0.75rem center; background-size: 0.9em auto; padding-right: 2.8rem;
        }
        .select-neon:focus {
            border-color: var(--neon-green);
            box-shadow: 0 0 18px var(--neon-green), 0 0 30px var(--neon-pink), inset 0 0 10px rgba(57, 255, 20, 0.4);
            outline: none; animation: focusPulseNeon 1.2s infinite alternate;
        }
        @keyframes focusPulseNeon {
            0% { box-shadow: 0 0 18px var(--neon-green), 0 0 30px var(--neon-cyan), inset 0 0 10px rgba(57, 255, 20, 0.4); }
            50% { box-shadow: 0 0 25px var(--neon-green), 0 0 40px var(--neon-cyan), inset 0 0 15px rgba(57, 255, 20, 0.6); }
            100% { box-shadow: 0 0 18px var(--neon-green), 0 0 30px var(--neon-cyan), inset 0 0 10px rgba(57, 255, 20, 0.4); }
        }
        .input-neon:disabled, .select-neon:disabled {
            cursor: not-allowed; opacity: var(--disabled-opacity); box-shadow: none;
            border-color: #444; animation: none;
        }
        .btn-neon {
            background: linear-gradient(55deg, var(--neon-pink), var(--neon-purple), var(--neon-cyan));
            background-size: 200% 200%; border: 2px solid transparent; color: #ffffff;
            text-shadow: 0 0 6px #fff, 0 0 12px var(--neon-pink), 0 0 18px var(--neon-cyan);
            box-shadow: 0 0 12px var(--neon-pink), 0 0 24px var(--neon-cyan), 0 0 36px var(--neon-purple), inset 0 0 10px rgba(255, 255, 255, 0.3);
            transition: all 0.35s cubic-bezier(0.25, 0.1, 0.25, 1); position: relative; overflow: hidden;
            border-radius: 0.6rem; cursor: pointer; animation: idleButtonGlow 3s infinite alternate;
        }
        @keyframes idleButtonGlow {
            0% { background-position: 0% 50%; box-shadow: 0 0 12px var(--neon-pink), 0 0 24px var(--neon-cyan), 0 0 36px var(--neon-purple), inset 0 0 10px rgba(255, 255, 255, 0.3); }
            50% { background-position: 100% 50%; box-shadow: 0 0 15px var(--neon-cyan), 0 0 30px var(--neon-purple), 0 0 45px var(--neon-pink), inset 0 0 12px rgba(255, 255, 255, 0.4); }
            100% { box-shadow: 0 0 20px var(--neon-purple), 0 0 40px var(--neon-pink), 0 0 60px var(--neon-cyan), inset 0 0 15px rgba(157, 0, 255, 0.5); }
        }
        .btn-neon:hover:not(:disabled) {
            transform: scale(1.04) translateY(-3px);
            box-shadow: 0 0 18px var(--neon-green), 0 0 36px var(--neon-cyan), 0 0 54px var(--neon-pink), inset 0 0 15px rgba(255, 255, 255, 0.6);
            border-color: var(--neon-green);
            text-shadow: 0 0 8px #fff, 0 0 18px var(--neon-green), 0 0 24px var(--neon-cyan);
            animation-play-state: paused;
        }
        .btn-neon:active:not(:disabled) {
            transform: scale(0.97);
            box-shadow: 0 0 8px var(--neon-pink), 0 0 15px var(--neon-cyan), inset 0 0 5px rgba(0, 0, 0, 0.2);
        }
        .btn-neon:focus-visible { outline: 3px solid var(--focus-outline-color); outline-offset: 3px; animation-play-state: paused; }
        .btn-neon:disabled {
            cursor: not-allowed; opacity: var(--disabled-opacity); box-shadow: none;
            border-color: #444; text-shadow: none; background: #222; animation: none;
        }
        .btn-neon .spinner {
            border: 3px solid rgba(255, 255, 255, 0.2); border-radius: 50%;
            border-top-color: var(--neon-pink); border-right-color: var(--neon-cyan);
            width: 1.1rem; height: 1.1rem; animation: spin 0.8s linear infinite;
            display: inline-block; vertical-align: middle;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* --- Results Grid (Cards) --- */
        .card {
            background: var(--card-bg); border: 2px solid var(--neon-cyan);
            box-shadow: 0 0 12px var(--neon-cyan), 0 0 24px var(--neon-pink), inset 0 0 10px rgba(10, 10, 26, 0.6);
            transition: transform 0.35s cubic-bezier(0.25, 0.1, 0.25, 1), box-shadow 0.4s ease, border-color 0.3s ease;
            overflow: hidden; cursor: pointer; height: 300px; display: flex; flex-direction: column;
            border-radius: 10px; color: inherit; position: relative;
        }
        .card:hover, .card:focus-visible {
            transform: translateY(-8px) scale(1.03); border-color: var(--neon-green);
            box-shadow: 0 0 22px var(--neon-green), 0 0 40px var(--neon-cyan), 0 0 60px var(--neon-pink), inset 0 0 15px rgba(10, 10, 26, 0.4);
            outline: none;
        }
        .favorite-btn {
            position: absolute; top: 0.5rem; right: 0.5rem; background: rgba(0, 0, 0, 0.5);
            border: none; color: var(--favorite-btn-color); font-size: 1.5rem; line-height: 1;
            cursor: pointer; z-index: 60; display: flex; justify-content: center; align-items: center;
            width: 30px; height: 30px; border-radius: 50%;
            transition: color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
            box-shadow: 0 0 8px rgba(0, 0, 0, 0.3);
        }
        .favorite-btn:hover { color: var(--favorite-btn-active-color); transform: scale(1.2); box-shadow: 0 0 12px var(--favorite-btn-active-color); }
        .favorite-btn.is-favorite {
            color: var(--favorite-btn-active-color); text-shadow: 0 0 8px var(--favorite-btn-active-color);
            animation: favoritePulse 1.5s infinite alternate;
        }
        @keyframes favoritePulse {
            0% { text-shadow: 0 0 8px var(--favorite-btn-active-color); box-shadow: 0 0 12px var(--favorite-btn-active-color); }
            100% { text-shadow: 0 0 15px var(--favorite-btn-active-color), 0 0 25px var(--favorite-btn-active-color); box-shadow: 0 0 18px var(--favorite-btn-active-color), 0 0 30px var(--favorite-btn-active-color); }
        }
        .card-media-container {
            height: 200px; background-color: var(--input-bg); display: flex; align-items: center; justify-content: center;
            flex-shrink: 0; position: relative; overflow: hidden; border-radius: 6px 6px 0 0;
        }
        .card-media-container>img, .card-media-container>video {
            width: 100%; height: 100%; object-fit: cover; display: block; background-color: #05080f;
        }
        .card-media-container img.static-thumb {
            position: absolute; top: 0; left: 0; opacity: 1; z-index: 1; transition: opacity 0.3s ease-in-out;
        }
        .card-media-container video.preview-video, .card-media-container img.preview-gif-image {
            position: absolute; top: 0; left: 0; opacity: 0; pointer-events: none; z-index: 5; transition: opacity 0.3s ease-in-out;
        }
        .card-media-container:hover .preview-video, .card:focus-within .card-media-container .preview-video,
        .card-media-container:hover .preview-gif-image, .card:focus-within .card-media-container .preview-gif-image {
            opacity: 1; pointer-events: auto;
        }
        .card-media-container:hover img.static-thumb, .card:focus-within .card-media-container img.static-thumb { opacity: 0.1; }
        .card-info {
            height: 100px; display: flex; flex-direction: column; justify-content: space-between;
            padding: 0.75rem; flex-grow: 1; overflow: hidden;
        }
        .card-title {
            font-size: 1rem; font-weight: 600; margin-bottom: 0.25rem;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
            text-shadow: 0 0 6px var(--neon-cyan), 0 0 10px var(--neon-pink);
        }
        .card-link {
            color: var(--link-color); text-shadow: 0 0 4px var(--neon-pink); font-size: 0.875rem;
            transition: color 0.25s ease, text-shadow 0.25s ease;
            align-self: flex-start; margin-top: auto; text-decoration: none;
        }
        .card-link:hover, .card-link:focus {
            color: var(--link-hover-color);
            text-shadow: 0 0 6px var(--neon-green), 0 0 8px var(--neon-cyan);
            text-decoration: underline; outline: none;
        }
        .media-error-placeholder {
            width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
            background-color: rgba(255, 0, 79, 0.2); color: var(--error-border);
            font-weight: bold; text-align: center; padding: 1rem; font-size: 0.9rem;
        }
        .duration-overlay {
            position: absolute; bottom: 0.5rem; right: 0.5rem; background: rgba(0, 0, 0, 0.6);
            color: white; font-size: 0.75rem; padding: 0.2rem 0.4rem; border-radius: 4px; z-index: 10;
        }

        /* --- Modal Styles --- */
        .modal {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: var(--modal-bg);
            display: flex; justify-content: center; align-items: center; z-index: 100;
            opacity: 0; visibility: hidden; transition: opacity 0.3s ease, visibility 0.3s ease;
        }
        .modal.is-open { opacity: 1; visibility: visible; }
        .modal-container {
            position: relative; background: var(--input-bg); border: 3px solid var(--neon-pink);
            box-shadow: 0 0 30px var(--neon-pink), 0 0 60px var(--neon-cyan), 0 0 90px var(--neon-purple), inset 0 0 20px rgba(5, 5, 15, 0.6);
            max-width: 95vw; max-height: 95vh; display: flex; flex-direction: column; align-items: center;
            overflow: hidden; border-radius: 12px; transform: scale(0.95);
            transition: transform 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        .modal.is-open .modal-container { transform: scale(1); }
        .modal-content {
            flex-grow: 1; display: flex; justify-content: center; align-items: center; width: 100%;
            max-height: calc(95vh - 80px); overflow: auto; padding: 1.5rem; position: relative;
        }
        .modal-content img, .modal-content video {
            display: block; max-width: 100%; max-height: 100%; width: auto; height: auto;
            object-fit: contain; border-radius: 6px; box-shadow: 0 0 15px rgba(0, 229, 255, 0.3);
        }
        .modal-link-container {
            width: 100%; padding: 1rem 1.5rem; border-top: 2px solid rgba(255, 255, 255, 0.1);
            text-align: center; box-shadow: inset 0 10px 15px rgba(0, 0, 0, 0.2);
        }
        .modal-link {
            color: var(--link-color); font-weight: 600; text-decoration: none;
            transition: color 0.2s ease, text-shadow 0.2s ease; display: block;
            text-shadow: 0 0 5px var(--neon-pink);
        }
        .modal-link:hover, .modal-link:focus {
            color: var(--link-hover-color); text-decoration: underline;
            text-shadow: 0 0 8px var(--neon-green); outline: none;
        }
        .close-button {
            position: absolute; top: 10px; right: 10px; background: rgba(0, 0, 0, 0.6); color: white;
            border: none; border-radius: 50%; width: 34px; height: 34px; font-size: 1.9rem;
            line-height: 1; cursor: pointer; z-index: 110; display: flex; justify-content: center; align-items: center;
            transition: background 0.2s ease, transform 0.2s ease; box-shadow: 0 0 8px rgba(0, 0, 0, 0.3);
        }
        .close-button:hover { background: rgba(255, 20, 100, 0.8); transform: rotate(90deg) scale(1.1); }

        /* --- Error Message Area --- */
        #errorMessage {
            background: var(--error-bg); border: 2px solid var(--error-border);
            box-shadow: 0 0 18px var(--error-border), 0 0 30px var(--neon-pink), inset 0 0 10px var(--neon-pink);
            color: #ffffff; text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.8);
            border-radius: 8px; padding: 1rem; margin-bottom: 1rem; font-weight: bold; word-break: break-word;
        }
        #errorMessage:not(.hidden) { display: block; }

        /* --- Skeleton Loaders --- */
        .skeleton-card {
            background: var(--card-bg); border: 2px solid #333959; border-radius: 10px;
            height: 300px; display: flex; flex-direction: column; overflow: hidden;
            animation: pulse 1.5s infinite ease-in-out;
        }
        .skeleton-img { height: 200px; background-color: #1f253d; }
        .skeleton-info { flex-grow: 1; padding: 0.75rem; display: flex; flex-direction: column; justify-content: space-between; }
        .skeleton-text { height: 1em; background-color: #1f253d; border-radius: 4px; margin-bottom: 0.5rem; width: 90%; }
        .skeleton-link { height: 0.8em; background-color: #1f253d; border-radius: 4px; width: 40%; margin-top: auto; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .5; } }

        /* --- Utility & Responsive --- */
        .hidden { display: none !important; }
        @media (max-width: 640px) {
            body { padding-left: 1rem; padding-right: 1rem; }
            .search-container, #resultsDiv, #paginationControls, #favoritesView { padding-left: 0.5rem; padding-right: 0.5rem; }
            .modal-content { padding: 1rem; }
            .modal-link-container { padding: 0.75rem 1rem; }
        }
    </style>
</head>

<body class="min-h-screen flex flex-col items-center py-6 px-2 sm:px-4">

    <header class="w-full max-w-5xl search-container p-4 sm:p-6 md:p-8 mb-8" role="search" aria-labelledby="search-heading">
        <h1 id="search-heading" class="title-main text-3xl sm:text-4xl font-bold text-center mb-2">
            Neon Search
            <span class="title-sub text-lg block font-normal opacity-80">(Find Videos & GIFs)</span>
        </h1>
        <div class="text-center mb-4">
            <button id="toggleFavoritesBtn" class="btn-neon px-4 py-2 text-sm">View Favorites (<span id="favoritesCountDisplay">0</span>)</button>
        </div>

        <div class="search-controls flex flex-col sm:flex-row items-stretch sm:space-y-4 sm:space-y-0 sm:space-x-3 md:space-x-4 mb-6">
            <div class="input-wrapper mb-4 sm:mb-0">
                <label for="searchInput" class="sr-only">Search Query</label>
                <input id="searchInput" type="text" placeholder="Enter search query..." class="input-neon" autocomplete="off">
                <button type="button" id="clearSearchBtn" class="clear-input-btn" aria-label="Clear search query" title="Clear search">×</button>
            </div>
            <div class="relative mb-4 sm:mb-0">
                <label for="typeSelect" class="sr-only">Search Type</label>
                <select id="typeSelect" aria-label="Select Search Type" class="select-neon w-full sm:w-auto">
                    <option value="videos" selected>Videos</option>
                    <option value="gifs">GIFs</option>
                </select>
            </div>
            <div class="relative mb-4 sm:mb-0">
                <label for="driverSelect" class="sr-only">Search Provider</label>
                <select id="driverSelect" aria-label="Select Search Provider" class="select-neon w-full sm:w-auto">
                    <option value="pornhub">Pornhub</option>
                    <option value="redtube" selected>Redtube</option>
                    <option value="xvideos">XVideos</option>
                    <option value="xhamster">Xhamster</option>
                    <option value="youporn">Youporn</option>
                    <option value="mock">Mock (Test)</option>
                </select>
            </div>
            <button id="searchBtn" type="button" class="btn-neon px-6 py-3 font-semibold text-base flex items-center justify-center w-full sm:w-auto" aria-controls="resultsDiv" aria-describedby="errorMessage">
                <span id="searchBtnText">Search</span> <span id="loadingIndicator" class="hidden ml-2" aria-hidden="true"><span class="spinner"></span></span>
            </button>
        </div>
        <p id="errorMessage" class="text-white text-center p-3 hidden" role="alert" aria-live="assertive" aria-hidden="true"></p>
    </header>

    <main class="w-full max-w-5xl flex-grow">
        <div id="resultsDiv" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 px-2 sm:px-4" aria-live="polite" aria-busy="false">
            <p id="initialMessage" class="text-center text-xl col-span-full text-gray-400 py-10" style="text-shadow: 0 0 5px var(--neon-cyan);">Enter a query and select options to search...</p>
        </div>

        <div id="favoritesView" class="w-full max-w-5xl hidden mt-8">
             <h2 class="text-2xl font-bold text-center mb-6" style="text-shadow: 0 0 8px var(--neon-pink);">My Favorites <span id="favoritesViewCountDisplay">(0)</span></h2>
             <div id="favoritesGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 px-2 sm:px-4" aria-live="polite" aria-busy="false">
                 <p id="noFavoritesMessage" class="text-center text-xl col-span-full text-gray-400 py-10">No favorites added yet. Click the ♡ on a card to add it!</p>
             </div>
        </div>

        <nav id="paginationControls" class="w-full max-w-5xl mt-8 flex flex-col sm:flex-row justify-center items-center sm:space-x-4 pagination-controls px-2 sm:px-4 hidden" role="navigation" aria-label="Pagination">
            <button id="prevBtn" type="button" aria-label="Previous Page" class="btn-neon px-4 py-2 text-sm font-semibold w-full sm:w-auto mb-2 sm:mb-0" disabled>< Prev</button>
            <span id="pageIndicator" class="font-semibold text-lg mx-2 sm:mx-4 my-2 sm:my-0" style="text-shadow: 0 0 8px var(--neon-cyan);" aria-live="polite">Page 1</span>
            <button id="nextBtn" type="button" aria-label="Next Page" class="btn-neon px-4 py-2 text-sm font-semibold w-full sm:w-auto" disabled>Next ></button>
        </nav>
    </main>

    <div id="mediaModal" class="modal" role="dialog" aria-modal="true" aria-hidden="true" tabindex="-1">
        <div class="modal-container">
            <button type="button" id="closeModalBtn" class="close-button" title="Close" aria-label="Close Modal">×</button>
            <div id="modalContent" class="modal-content"></div>
            <div id="modalLinkContainer" class="modal-link-container"></div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/axios@1.7.2/dist/axios.min.js"></script>
    <script>
        'use strict';

        const API_BASE_URL = '/api/search';
        const HOVER_PLAY_DELAY_MS = 200;
        const HOVER_PAUSE_DELAY_MS = 100;
        const API_TIMEOUT_MS = 30000;
        const SKELETON_COUNT = 6;
        const RESULTS_PER_PAGE_HEURISTIC = 10;
        const PLACEHOLDER_GIF_DATA_URI = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
        const FAVORITES_STORAGE_KEY = 'neonSearchFavorites';

        const searchInput = document.getElementById('searchInput');
        const clearSearchBtn = document.getElementById('clearSearchBtn');
        const typeSelect = document.getElementById('typeSelect');
        const driverSelect = document.getElementById('driverSelect');
        const searchBtn = document.getElementById('searchBtn');
        const searchBtnText = document.getElementById('searchBtnText');
        const loadingIndicator = document.getElementById('loadingIndicator');
        const resultsDiv = document.getElementById('resultsDiv');
        const initialMessage = document.getElementById('initialMessage');
        const errorMessage = document.getElementById('errorMessage');
        const mediaModal = document.getElementById('mediaModal');
        const modalContent = document.getElementById('modalContent');
        const modalLinkContainer = document.getElementById('modalLinkContainer');
        const closeModalBtn = document.getElementById('closeModalBtn');
        const paginationControls = document.getElementById('paginationControls');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const pageIndicator = document.getElementById('pageIndicator');

        const toggleFavoritesBtn = document.getElementById('toggleFavoritesBtn');
        const favoritesCountDisplay = document.getElementById('favoritesCountDisplay'); // For button
        const favoritesViewCountDisplay = document.getElementById('favoritesViewCountDisplay'); // For view title
        const favoritesView = document.getElementById('favoritesView');
        const favoritesGrid = document.getElementById('favoritesGrid');
        const noFavoritesMessage = document.getElementById('noFavoritesMessage');

        const appState = {
            isLoading: false, currentPage: 1, currentQuery: '', currentDriver: '', currentType: '',
            resultsCache: [], lastFocusedElement: null, maxResultsHeuristic: RESULTS_PER_PAGE_HEURISTIC,
            hoverPlayTimeout: null, hoverPauseTimeout: null, currentAbortController: null,
            favorites: [], showingFavorites: false,
        };

        const log = {
            info: (message, ...args) => console.info(`%c[FE INFO] ${message}`, 'color: #00ffff; font-weight: bold;', ...args),
            warn: (message, ...args) => console.warn(`%c[FE WARN] ${message}`, 'color: #ff8800; font-weight: bold;', ...args),
            error: (message, ...args) => console.error(`%c[FE ERROR] ${message}`, 'color: #ff00ff; font-weight: bold;', ...args),
            api: (message, ...args) => console.log(`%c[API REQ] ${message}`, 'color: #39ff14;', ...args),
            apiSuccess: (message, ...args) => console.log(`%c[API OK] ${message}`, 'color: #39ff14; font-weight: bold;', ...args),
            apiError: (message, ...args) => console.error(`%c[API FAIL] ${message}`, 'color: #ff3333; font-weight: bold;', ...args),
            modal: (message, ...args) => console.log(`%c[MODAL] ${message}`, 'color: #9d00ff;', ...args),
            favorites: (message, ...args) => console.log(`%c[FAV] ${message}`, 'color: #ff00aa;', ...args),
        };

        function loadFavorites() {
            try {
                const storedFavorites = localStorage.getItem(FAVORITES_STORAGE_KEY);
                appState.favorites = storedFavorites ? JSON.parse(storedFavorites) : [];
                log.favorites(`Loaded ${appState.favorites.length} favorites.`);
                updateFavoritesCountDisplay();
            } catch (e) {
                log.error('Failed to load favorites:', e);
                appState.favorites = [];
            }
        }

        function saveFavorites() {
            try {
                localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(appState.favorites));
                log.favorites(`Saved ${appState.favorites.length} favorites.`);
                updateFavoritesCountDisplay();
            } catch (e) {
                log.error('Failed to save favorites:', e);
            }
        }
        
        function updateFavoritesCountDisplay() {
            const count = appState.favorites.length;
            if (favoritesCountDisplay) favoritesCountDisplay.textContent = count;
            if (favoritesViewCountDisplay) favoritesViewCountDisplay.textContent = `(${count})`;
            if (noFavoritesMessage) noFavoritesMessage.classList.toggle('hidden', count > 0);
        }

        function isFavorite(item) {
            return appState.favorites.some(fav => fav.url === item.url && fav.source === item.source);
        }

        function toggleFavorite(item) {
            const itemIdentifier = { url: item.url, source: item.source }; // Use URL and source for uniqueness
            const existingFavIndex = appState.favorites.findIndex(fav => fav.url === itemIdentifier.url && fav.source === itemIdentifier.source);

            if (existingFavIndex > -1) {
                appState.favorites.splice(existingFavIndex, 1);
                log.favorites('Removed from favorites:', item.title);
            } else {
                const itemCopy = { ...item }; // Create a shallow copy
                appState.favorites.push(itemCopy);
                log.favorites('Added to favorites:', item.title);
            }
            saveFavorites();

            const cardElement = document.querySelector(`.card[data-url="${CSS.escape(item.url)}"][data-source="${CSS.escape(item.source)}"]`);
            if (cardElement) {
                const favBtn = cardElement.querySelector('.favorite-btn');
                if (favBtn) favBtn.classList.toggle('is-favorite', isFavorite(item));
            }
            
            if (appState.showingFavorites) { // If currently viewing favorites, refresh the view
                displayFavoritesView();
            }
        }

        function displayFavoritesView() {
            if (appState.isLoading) { log.favorites('Cannot display favorites while loading.'); return; }
            appState.showingFavorites = true;
            resultsDiv.classList.add('hidden');
            paginationControls.classList.add('hidden');
            initialMessage?.classList.add('hidden');
            favoritesView.classList.remove('hidden');
            
            favoritesGrid.innerHTML = ''; // Clear previous favorites
            if (appState.favorites.length === 0) {
                noFavoritesMessage?.classList.remove('hidden');
            } else {
                noFavoritesMessage?.classList.add('hidden');
                // Pass 'appState.favorites' to renderItems, target favoritesGrid, and use item's own type
                renderItems(appState.favorites, favoritesGrid); 
            }
            updateFavoritesCountDisplay();
            log.favorites('Displaying favorites view.');
            if (toggleFavoritesBtn) toggleFavoritesBtn.textContent = 'Back to Search';
        }

        function hideFavoritesView() {
            appState.showingFavorites = false;
            favoritesView.classList.add('hidden');
            resultsDiv.classList.remove('hidden');
            // paginationControls.classList.remove('hidden'); // Will be shown by displaySearchResults if needed

            if (appState.resultsCache.length > 0) {
                displaySearchResults(appState.resultsCache);
            } else {
                resultsDiv.innerHTML = '';
                initialMessage?.classList.remove('hidden');
                paginationControls.classList.add('hidden');
            }
            log.favorites('Hiding favorites, returning to search results.');
            if (toggleFavoritesBtn) toggleFavoritesBtn.textContent = `View Favorites (${appState.favorites.length})`;
        }


        async function fetchResultsFromApi(query, driver, type, page) {
            if (appState.currentAbortController) {
                appState.currentAbortController.abort();
                log.api('Previous API request aborted.');
            }
            appState.currentAbortController = new AbortController();
            const params = { query, driver, type, page };
            log.api(`-> Fetching: ${API_BASE_URL}`, params);

            try {
                const response = await axios.get(API_BASE_URL, {
                    params, timeout: API_TIMEOUT_MS, signal: appState.currentAbortController.signal,
                });
                const data = Array.isArray(response.data) ? response.data : [];
                appState.maxResultsHeuristic = data.length > 0 ? data.length : RESULTS_PER_PAGE_HEURISTIC;
                log.apiSuccess(`<- Success (${response.status}): ${data.length} results. Heuristic: ${appState.maxResultsHeuristic}`);
                return { success: true, data };
            } catch (error) {
                if (axios.isCancel(error)) {
                    log.apiError('Request canceled.');
                    return { success: false, error: 'Search canceled.', isAbort: true };
                }
                log.apiError('<- API Error:', error.message, error.response || error.request || error);
                let userMessage = 'Unexpected API error.';
                if (error.code === 'ECONNABORTED' || error.message.toLowerCase().includes('timeout')) {
                    userMessage = 'API request timed out.';
                } else if (error.response) {
                    userMessage = `API Error: ${error.response.data?.error || `Status ${error.response.status}`}.`;
                } else if (error.request) {
                    userMessage = 'Network Error: Cannot connect to API.';
                }
                return { success: false, error: userMessage };
            } finally {
                appState.currentAbortController = null;
                setSearchState(false); // This will be called again by performSearch, but good for safety
            }
        }

        function showError(message) {
            errorMessage.textContent = message;
            errorMessage.classList.remove('hidden');
            errorMessage.setAttribute('aria-hidden', 'false');
            log.error('Error Displayed:', message);
            initialMessage?.classList.add('hidden');
        }

        function hideError() {
            if (!errorMessage.classList.contains('hidden')) {
                errorMessage.classList.add('hidden');
                errorMessage.setAttribute('aria-hidden', 'true');
                errorMessage.textContent = '';
            }
        }
        
        function renderMediaErrorPlaceholder(container, message) {
            container.innerHTML = '';
            const errorDiv = document.createElement('div');
            errorDiv.className = 'media-error-placeholder absolute inset-0';
            errorDiv.textContent = message;
            container.appendChild(errorDiv);
            log.warn('Media placeholder shown:', message);
        }

        function showSkeletons(count = SKELETON_COUNT, targetGrid = resultsDiv) {
            targetGrid.innerHTML = '';
            if (targetGrid === resultsDiv) initialMessage?.classList.add('hidden');
            
            targetGrid.setAttribute('aria-busy', 'true');
            targetGrid.removeAttribute('aria-live');

            setTimeout(() => {
                if (appState.isLoading) {
                    const fragment = document.createDocumentFragment();
                    for (let i = 0; i < count; i++) {
                        const skeleton = document.createElement('div');
                        skeleton.className = 'skeleton-card';
                        skeleton.setAttribute('aria-hidden', 'true');
                        skeleton.innerHTML = `<div class="skeleton-img"></div><div class="skeleton-info"><div class="skeleton-text"></div><div class="skeleton-link"></div></div>`;
                        fragment.appendChild(skeleton);
                    }
                    targetGrid.appendChild(fragment);
                }
            }, 100); // Small delay
        }

        function setSearchState(isLoading) {
            appState.isLoading = isLoading;
            searchInput.disabled = isLoading;
            typeSelect.disabled = isLoading;
            driverSelect.disabled = isLoading;
            searchBtn.disabled = isLoading;
            if (toggleFavoritesBtn) toggleFavoritesBtn.disabled = isLoading;

            if (isLoading) {
                searchBtnText.classList.add('hidden');
                loadingIndicator.classList.remove('hidden');
                if (!appState.showingFavorites) { // Only show skeletons for search, not when toggling favorites view
                    showSkeletons(SKELETON_COUNT, resultsDiv);
                }
                resultsDiv.setAttribute('aria-busy', 'true');
            } else {
                searchBtnText.classList.remove('hidden');
                loadingIndicator.classList.add('hidden');
                resultsDiv.setAttribute('aria-busy', 'false');
                resultsDiv.setAttribute('aria-live', 'polite');
            }
        }
        
        function createCard(itemData, itemType) {
            const card = document.createElement('a'); // Make card an anchor for better semantics if it links somewhere
            card.className = 'card relative group';
            card.href = itemData.url; // Link to the source page
            card.target = '_blank'; // Open in new tab
            card.rel = 'noopener noreferrer';
            card.setAttribute('data-url', itemData.url); // For favorite lookup
            card.setAttribute('data-source', itemData.source); // For favorite lookup
            card.setAttribute('aria-label', `View ${itemData.title} from ${itemData.source}`);

            // Prevent default navigation, open modal instead
            card.addEventListener('click', (e) => {
                e.preventDefault();
                openModal(itemData, itemType);
            });
            
            // Favorite Button
            const favBtn = document.createElement('button');
            favBtn.type = 'button';
            favBtn.className = 'favorite-btn';
            favBtn.innerHTML = '♡'; // Heart outline
            favBtn.setAttribute('aria-label', isFavorite(itemData) ? 'Remove from favorites' : 'Add to favorites');
            favBtn.title = isFavorite(itemData) ? 'Remove from favorites' : 'Add to favorites';
            if (isFavorite(itemData)) favBtn.classList.add('is-favorite');
            
            favBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent card click (modal opening)
                e.preventDefault(); // Prevent link navigation if any
                toggleFavorite(itemData);
                favBtn.classList.toggle('is-favorite', isFavorite(itemData));
                favBtn.setAttribute('aria-label', isFavorite(itemData) ? 'Remove from favorites' : 'Add to favorites');
                favBtn.title = isFavorite(itemData) ? 'Remove from favorites' : 'Add to favorites';
            });
            card.appendChild(favBtn);

            const mediaContainer = document.createElement('div');
            mediaContainer.className = 'card-media-container';

            const staticThumb = document.createElement('img');
            staticThumb.className = 'static-thumb';
            staticThumb.src = itemData.thumbnail || PLACEHOLDER_GIF_DATA_URI;
            staticThumb.alt = `Thumbnail for ${itemData.title}`;
            staticThumb.loading = 'lazy';
            staticThumb.onerror = () => renderMediaErrorPlaceholder(mediaContainer, 'Thumb load error');
            mediaContainer.appendChild(staticThumb);

            if (itemData.preview_video) {
                if (itemData.preview_video.endsWith('.gif')) {
                    const previewGifImg = document.createElement('img');
                    previewGifImg.className = 'preview-gif-image'; // Ensure this class is styled for opacity transition
                    previewGifImg.src = itemData.preview_video;
                    previewGifImg.alt = `Animated preview for ${itemData.title}`;
                    previewGifImg.loading = 'lazy'; // GIFs can also be lazy-loaded
                    mediaContainer.appendChild(previewGifImg);
                } else {
                    const previewVideo = document.createElement('video');
                    previewVideo.className = 'preview-video';
                    previewVideo.src = itemData.preview_video;
                    previewVideo.loop = true;
                    previewVideo.muted = true;
                    previewVideo.playsInline = true;
                    previewVideo.preload = 'metadata'; // Only load metadata initially
                    // Add poster to video for a smoother transition if thumb is hidden fast
                    previewVideo.poster = itemData.thumbnail || PLACEHOLDER_GIF_DATA_URI;


                    card.addEventListener('mouseenter', () => {
                        clearTimeout(appState.hoverPauseTimeout);
                        appState.hoverPlayTimeout = setTimeout(() => previewVideo.play().catch(log.warn), HOVER_PLAY_DELAY_MS);
                    });
                    card.addEventListener('mouseleave', () => {
                        clearTimeout(appState.hoverPlayTimeout);
                        appState.hoverPauseTimeout = setTimeout(() => previewVideo.pause(), HOVER_PAUSE_DELAY_MS);
                    });
                    card.addEventListener('focus', () => previewVideo.play().catch(log.warn)); // Play on focus for accessibility
                    card.addEventListener('blur', () => previewVideo.pause()); // Pause on blur

                    mediaContainer.appendChild(previewVideo);
                }
            }
            
            if (itemData.duration && itemType === 'videos') {
                const durationOverlay = document.createElement('span');
                durationOverlay.className = 'duration-overlay';
                durationOverlay.textContent = itemData.duration;
                mediaContainer.appendChild(durationOverlay);
            }

            card.appendChild(mediaContainer);

            const infoDiv = document.createElement('div');
            infoDiv.className = 'card-info';
            const title = document.createElement('h3');
            title.className = 'card-title';
            title.textContent = itemData.title;
            infoDiv.appendChild(title);

            const sourceLink = document.createElement('p'); // Changed to p for non-interactive text
            sourceLink.className = 'card-link'; // Re-use styling, but it's not a link anymore
            sourceLink.textContent = `Source: ${itemData.source}`;
            infoDiv.appendChild(sourceLink);
            card.appendChild(infoDiv);
            return card;
        }

        // Generic function to render items (results or favorites) to a target grid
        function renderItems(items, targetGridElement) {
            targetGridElement.innerHTML = ''; // Clear previous items
            targetGridElement.setAttribute('aria-busy', 'false');
            targetGridElement.setAttribute('aria-live', 'polite');

            if (!items || items.length === 0) {
                if (targetGridElement === resultsDiv) {
                    targetGridElement.innerHTML = `<p class="text-center text-xl col-span-full text-gray-400 py-10">No results found for "${appState.currentQuery}".</p>`;
                } else if (targetGridElement === favoritesGrid) {
                    // noFavoritesMessage is handled by displayFavoritesView
                }
                return;
            }
            
            const fragment = document.createDocumentFragment();
            items.forEach(item => {
                // Use item.type if present (especially for favorites), otherwise use current search type
                const itemActualType = item.type || (appState.showingFavorites ? 'videos' : appState.currentType);
                const card = createCard(item, itemActualType);
                fragment.appendChild(card);
            });
            targetGridElement.appendChild(fragment);
        }

        function displaySearchResults(results) {
            appState.resultsCache = results; // Cache for potential re-renders or history
            renderItems(results, resultsDiv); // Use the generic renderItems
            updatePaginationButtons(results.length);
            hideError();
            initialMessage?.classList.add('hidden');
            favoritesView.classList.add('hidden'); // Ensure favorites view is hidden
            resultsDiv.classList.remove('hidden');
        }


        function openModal(itemData, itemType) {
            appState.lastFocusedElement = document.activeElement;
            modalContent.innerHTML = ''; // Clear previous content
            modalLinkContainer.innerHTML = ''; // Clear previous link

            let mediaElement;
            let effectiveUrl = itemData.url; // This is the page URL typically
            let mediaSourceUrl = itemData.preview_video || itemData.thumbnail; // Fallback chain for actual media
            
            // Determine if the item is a video or GIF for modal display
            // itemType is crucial here. It comes from appState.currentType or favorite item's stored type.
            const displayType = itemType === 'gifs' ? 'gif' : 'video';

            if (displayType === 'video' && itemData.preview_video && !itemData.preview_video.endsWith('.gif')) {
                // If it's a video type and has a video preview, prefer that for modal if it's a proper video URL
                mediaSourceUrl = itemData.preview_video; 
            } else if (displayType === 'gif' && itemData.preview_video && itemData.preview_video.endsWith('.gif')) {
                // If it's a GIF type and has a GIF preview, use that
                mediaSourceUrl = itemData.preview_video;
            }
            // If preview_video is not suitable or not present, use thumbnail as a static image.
            // For videos, ideally, we'd fetch the actual video embed, but for simplicity, we use preview or thumb.


            if (displayType === 'video' && mediaSourceUrl && (mediaSourceUrl.endsWith('.mp4') || mediaSourceUrl.endsWith('.webm'))) {
                mediaElement = document.createElement('video');
                mediaElement.src = mediaSourceUrl;
                mediaElement.controls = true;
                mediaElement.autoplay = true;
                mediaElement.loop = false; // No loop for main modal view typically
                mediaElement.style.maxHeight = 'calc(95vh - 100px)'; // Adjust max height
                mediaElement.style.maxWidth = '100%';
            } else { // Fallback to image (for GIFs or if video preview is image-like or unavailable)
                mediaElement = document.createElement('img');
                mediaElement.src = mediaSourceUrl; // This could be itemData.preview_video (if it's a .gif) or itemData.thumbnail
                mediaElement.alt = itemData.title;
                mediaElement.style.maxHeight = 'calc(95vh - 100px)';
                mediaElement.style.maxWidth = '100%';
            }
            
            mediaElement.onerror = () => {
                 renderMediaErrorPlaceholder(modalContent, 'Error loading media in modal.');
                 log.error('Modal media load error for:', mediaSourceUrl);
            };
            modalContent.appendChild(mediaElement);
            
            const sourceLink = document.createElement('a');
            sourceLink.href = itemData.url; // Link to the original page
            sourceLink.target = '_blank';
            sourceLink.rel = 'noopener noreferrer';
            sourceLink.className = 'modal-link';
            sourceLink.textContent = `View on ${itemData.source}`;
            modalLinkContainer.appendChild(sourceLink);

            mediaModal.classList.add('is-open');
            mediaModal.setAttribute('aria-hidden', 'false');
            closeModalBtn.focus(); // Focus the close button for accessibility
            log.modal('Modal opened for:', itemData.title);
        }

        function closeModal() {
            mediaModal.classList.remove('is-open');
            mediaModal.setAttribute('aria-hidden', 'true');
            modalContent.innerHTML = ''; // Clear content to stop video/gif
            if (appState.lastFocusedElement) {
                appState.lastFocusedElement.focus();
            }
            log.modal('Modal closed.');
        }

        function updatePaginationButtons(numResultsThisPage) {
            prevBtn.disabled = appState.currentPage <= 1;
            // Enable next button if we received a full page of results (heuristic)
            // Or if the driver has a known fixed results per page that we could use
            nextBtn.disabled = numResultsThisPage < appState.maxResultsHeuristic; 

            pageIndicator.textContent = `Page ${appState.currentPage}`;
            paginationControls.classList.toggle('hidden', numResultsThisPage === 0 && appState.currentPage === 1);
        }

        async function performSearch(pageNumber = 1) {
            const query = searchInput.value.trim();
            const driver = driverSelect.value;
            const type = typeSelect.value;

            if (!query) {
                showError('Please enter a search query.');
                return;
            }
            hideError();
            if (appState.showingFavorites) hideFavoritesView(); // Switch back to search results

            appState.currentPage = pageNumber;
            appState.currentQuery = query;
            appState.currentDriver = driver;
            appState.currentType = type;

            setSearchState(true);
            log.info(`Performing search: Q='${query}', D='${driver}', T='${type}', P=${pageNumber}`);

            const apiResponse = await fetchResultsFromApi(query, driver, type, pageNumber);
            
            setSearchState(false); // Ensure loading state is reset regardless of outcome

            if (apiResponse.isAbort) {
                 log.info("Search was aborted, UI not updated further.");
                 return; // Don't update UI if aborted by a new search
            }

            if (apiResponse.success) {
                displaySearchResults(apiResponse.data);
            } else {
                showError(apiResponse.error || 'Failed to fetch results.');
                resultsDiv.innerHTML = ''; // Clear any skeletons
                updatePaginationButtons(0); // Hide pagination on error
            }
        }

        // --- Event Listeners ---
        searchBtn.addEventListener('click', () => performSearch(1));
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch(1);
        });
        clearSearchBtn.addEventListener('click', () => {
            searchInput.value = '';
            clearSearchBtn.style.display = 'none'; // Hide button
            searchInput.focus();
        });
        searchInput.addEventListener('input', () => { // Show/hide clear button
            clearSearchBtn.style.display = searchInput.value.length > 0 ? 'block' : 'none';
        });

        prevBtn.addEventListener('click', () => {
            if (appState.currentPage > 1) performSearch(appState.currentPage - 1);
        });
        nextBtn.addEventListener('click', () => {
            performSearch(appState.currentPage + 1);
        });

        closeModalBtn.addEventListener('click', closeModal);
        mediaModal.addEventListener('click', (e) => { // Close on overlay click
            if (e.target === mediaModal) closeModal();
        });
        document.addEventListener('keydown', (e) => { // Close on Escape key
            if (e.key === 'Escape' && mediaModal.classList.contains('is-open')) closeModal();
        });

        if (toggleFavoritesBtn) {
            toggleFavoritesBtn.addEventListener('click', () => {
                if (appState.isLoading) return; // Don't toggle if a search is loading
                if (appState.showingFavorites) {
                    hideFavoritesView();
                } else {
                    displayFavoritesView();
                }
            });
        }

        // --- Initialization ---
        document.addEventListener('DOMContentLoaded', () => {
            log.info('DOM fully loaded and parsed.');
            loadFavorites(); // Load favorites from localStorage on startup
            // Initial state for clear button if input has pre-filled value (e.g. browser cache)
            clearSearchBtn.style.display = searchInput.value.length > 0 ? 'block' : 'none';
        });

    </script>
</body>
</html>
EOF

# Step 9: Final instructions
echo "----------------------------------------------------------------------"
echo -e "${GREEN}✅ Enhanced setup complete!${NC}"
echo "----------------------------------------------------------------------"
echo -e "${YELLOW}📢 IMPORTANT: For the 'Redtube' driver to work, you MUST replace 'YOUR_REDTUBE_API_TOKEN' with a valid API token in the file:${NC}"
echo -e "${CYAN}$PROJECT_DIR/modules/Redtube.js${NC}"
echo "----------------------------------------------------------------------"
echo -e "${CYAN}To start the application:${NC}"
echo "1. Navigate to the project directory:"
echo -e "   ${GREEN}cd $PROJECT_DIR${NC}"
echo "2. Run the backend server (which also serves the frontend):"
echo -e "   ${GREEN}node server.js${NC}"
echo -e "   Alternatively, since it has a shebang and is executable:"
echo -e "   ${GREEN}./server.js${NC}"
echo "3. Open your web browser and go to:"
echo -e "   ${YELLOW}http://localhost:3000${NC}"
echo -e "   (If on Termux, you might need to use your device's local IP address if accessing from another device on the same network, or use 'termux-open http://localhost:3000' to open on device)"
echo "----------------------------------------------------------------------"
echo -e "${CYAN}Happy searching! 💡${NC}"


