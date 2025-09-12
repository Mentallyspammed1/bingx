```bash
#!/bin/bash

# ==============================================================================
# SETUP SCRIPT FOR HYBRID SEARCH APPLICATION
# ==============================================================================
# This script generates a Node.js application with a hybrid backend that can
# use either the 'pornsearch' npm library or custom-written scrapers to fetch
# content from various sites.
#
# Generated Structure:
# --------------------
# hybrid_search_app/
# |-- core/
# |   |-- AbstractModule.js
# |   |-- GifMixin.js
# |   |-- OverwriteError.js
# |   |-- VideoMixin.js
# |   `-- abstractMethodFactory.js
# |-- modules/
# |   `-- custom_scrapers/
# |       |-- pornhubScraper.js
# |       |-- xvideosScraper.js
# |       |-- (other scraper stubs)
# |-- public/
# |   |-- css/ (placeholder, not used by current index.html)
# |   `-- index.html
# |-- utils/ (placeholder, not used yet)
# |-- .env
# |-- .gitignore
# |-- config.json
# |-- package.json
# `-- server.js
#
# ==============================================================================

# --- Configuration & Helpers ---
PROJECT_DIR="hybrid_search_app"

# Colors for output
BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m' # No Color

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}
success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}
warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}
error_exit() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
    exit 1
}

# Exit on any error, treat unset variables as an error, and ensure pipeline errors are caught.
set -e
set -u
set -o pipefail

info "Starting setup for the Hybrid Search Application..."

# --- Directory Creation ---
info "Creating project directory structure: $PROJECT_DIR"
mkdir -p "$PROJECT_DIR/core" \
         "$PROJECT_DIR/modules/custom_scrapers" \
         "$PROJECT_DIR/public/css" \
         "$PROJECT_DIR/utils"

cd "$PROJECT_DIR" || error_exit "Failed to change directory to $PROJECT_DIR"

# --- NPM Initialization and Dependency Installation ---
info "Initializing npm project and installing dependencies..."
npm init -y > /dev/null # Suppress verbose output
info "Installing runtime dependencies: express, cors, dotenv, axios, cheerio, pornsearch..."
# Note: babel-runtime was in neon_search_app.sh's dependencies, but the core modules here don't use its specific helpers like _classCallCheck3
# The core modules generated in step 8 use standard ES6 class syntax.
npm install express cors dotenv axios cheerio pornsearch --silent > /dev/null

info "Adding start script to package.json..."
npm pkg set scripts.start="node server.js" > /dev/null

success "NPM setup complete."

# --- Generate .env File ---
info "Generating .env file..."
cat << 'EOF' > .env
PORT=3000
# Options for BACKEND_STRATEGY:
# "custom"      - Primarily uses custom scrapers defined in modules/custom_scrapers/.
# "pornsearch"  - Primarily uses the 'pornsearch' npm library.
# Site-specific overrides can be defined in config.json.
BACKEND_STRATEGY=custom

# Optional: Enable more verbose logging in some modules
# DEBUG=true
EOF
success ".env file created."

# --- Generate config.json File ---
info "Generating config.json template..."
cat << 'EOF' > config.json
{
  "defaultStrategy": "custom",
  "siteOverrides": {
    "Redtube": "pornsearch"
  },
  "customScrapersMap": {
    "Pornhub": "./modules/custom_scrapers/pornhubScraper.js",
    "Xvideos": "./modules/custom_scrapers/xvideosScraper.js",
    "SexCom": "./modules/custom_scrapers/sexComScraper.js",
    "Youporn": "./modules/custom_scrapers/youpornScraper.js",
    "Xhamster": "./modules/custom_scrapers/xhamsterScraper.js",
    "Motherless": "./modules/custom_scrapers/motherlessScraper.js",
    "Redtube": "./modules/custom_scrapers/redtubeScraper.js",
    "Mock": "./modules/custom_scrapers/mockScraper.cjs"
  }
}
EOF
success "config.json created."

# --- Generate .gitignore File ---
info "Generating .gitignore file..."
cat << 'EOF' > .gitignore
# Dependencies
node_modules/

# Environment specific files
.env
*.env
.env.*
!/.env.example

# Logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
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
success ".gitignore file created."

# --- Generate Core Helper Files ---
info "Generating core JavaScript modules..."

info "Creating core/OverwriteError.js..."
cat << 'EOF' > core/OverwriteError.js
// core/OverwriteError.js
'use strict';

class OverwriteError extends Error {
  constructor(message) {
    super(message);
    this.name = 'OverwriteError';
    // Maintains proper prototype chain for instanceof checks
    // and captures stack trace in V8 environments (Node.js, Chrome)
    if (typeof Error.captureStackTrace === 'function') {
      Error.captureStackTrace(this, this.constructor);
    } else {
      this.stack = (new Error(message)).stack;
    }
  }
}

module.exports = OverwriteError;
EOF

info "Creating core/abstractMethodFactory.js..."
cat << 'EOF' > core/abstractMethodFactory.js
// core/abstractMethodFactory.js
'use strict';
const OverwriteError = require('./OverwriteError'); // Correct path

module.exports = (BaseClass, abstractMethods) => {
  if (typeof BaseClass !== 'function') {
    throw new Error('BaseClass must be a constructor function.');
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
        return (...args) => { // eslint-disable-line no-unused-vars
          // 'this' here refers to the instance of the concrete subclass.
          const callingClassName = this.constructor.name || 'Subclass';
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

info "Creating core/AbstractModule.js..."
cat << 'EOF' > core/AbstractModule.js
// core/AbstractModule.js
'use strict';
const OverwriteError = require('./OverwriteError');
const axios = require('axios');

class AbstractModule {
  constructor(options = {}) {
    this.query = (options.query || '').trim();
    this.driverName = options.driverName || this.name;
    this.page = parseInt(options.page, 10) || this.firstpage;

    this.httpClient = axios.create({
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'
      },
      timeout: 20000, // 20 seconds timeout
    });
    // console.log(`[AbstractModule] Initialized for driver: ${this.driverName}, Query: "${this.query}", Page: ${this.page}`);
  }

  get name() {
    throw new OverwriteError('Getter "name" must be implemented by the concrete scraper class.');
  }

  get firstpage() {
    return 1; // Default first page for most sites (1-indexed)
  }

  async _fetchHtml(url) {
    try {
      console.log(`[AbstractModule _fetchHtml] Fetching URL: ${url} for driver ${this.name}`);
      const response = await this.httpClient.get(url);
      return response.data;
    } catch (error) {
      console.error(`[${this.name || 'AbstractModule'} _fetchHtml] Error fetching URL ${url}:`, error.message);
      if (error.response) {
        console.error(`[${this.name || 'AbstractModule'} _fetchHtml] Status: ${error.response.status}, Headers: ${JSON.stringify(error.response.headers)}`);
      } else if (error.request) {
        console.error(`[${this.name || 'AbstractModule'} _fetchHtml] No response received for request:`, error.request);
      }
      throw new Error(`Failed to fetch HTML from ${url} for driver ${this.name}. Original error: ${error.message}`);
    }
  }

  _makeAbsolute(urlString, baseUrl) {
    if (!urlString || typeof urlString !== 'string') {
        return undefined;
    }
    if (urlString.startsWith('data:') || urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString;
    if (urlString.startsWith('//')) return `https:${urlString}`;

    try {
      const effectiveBase = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
      return new URL(urlString, effectiveBase).href;
    } catch (e) {
      console.warn(`[${this.name || 'AbstractModule'}] _makeAbsolute: Failed to resolve URL "${urlString}" with base "${baseUrl}". Error: ${e.message}`);
      return undefined;
    }
  }

  static with(...mixinFactories) {
    return mixinFactories.reduce((c, mixinFactory) => {
        if (typeof mixinFactory !== 'function') {
            console.warn('[AbstractModule.with] Encountered a non-function in mixinFactories array:', mixinFactory);
            return c;
        }
        return mixinFactory(c);
    }, this);
  }
}

module.exports = AbstractModule;
EOF

info "Creating core/VideoMixin.js..."
cat << 'EOF' > core/VideoMixin.js
// core/VideoMixin.js
'use strict';
const enforceAbstractMethods = require('./abstractMethodFactory');

const videoAbstractMethods = [
  'videoUrl',    // Expected to return a string (URL). Params: (query, page)
  'videoParser', // Expected to parse data and return an array. Params: (cheerioInstance, rawHtmlOrJsonData)
];

module.exports = (BaseClass) => enforceAbstractMethods(BaseClass, videoAbstractMethods);
EOF

info "Creating core/GifMixin.js..."
cat << 'EOF' > core/GifMixin.js
// core/GifMixin.js
'use strict';
const enforceAbstractMethods = require('./abstractMethodFactory');

const gifAbstractMethods = [
  'gifUrl',    // Expected to return a string (URL). Params: (query, page)
  'gifParser', // Expected to parse data and return an array. Params: (cheerioInstance, rawHtmlOrJsonData)
];

module.exports = (BaseClass) => enforceAbstractMethods(BaseClass, gifAbstractMethods);
EOF

info "Creating core/log.js..."
cat << 'EOF' > core/log.js
// Basic console logger utility
const log = {
    debug: (message, ...args) => { if (process.env.NODE_ENV === 'development') console.log(`[DEBUG] ${new Date().toISOString()}: `, message, ...args); },
    info: (message, ...args) => console.log(`[INFO] ${new Date().toISOString()}: `, message, ...args),
    warn: (message, ...args) => console.warn(`[WARN] ${new Date().toISOString()}: `, message, ...args),
    error: (message, ...args) => console.error(`[ERROR] ${new Date().toISOString()}: `, message, ...args),
    child: function(bindings) { // Added basic child-like behavior
        return {
            debug: (message, ...args) => this.debug(`[${bindings.module || 'child'}] `, message, ...args),
            info: (message, ...args) => this.info(`[${bindings.module || 'child'}] `, message, ...args),
            warn: (message, ...args) => this.warn(`[${bindings.module || 'child'}] `, message, ...args),
            error: (message, ...args) => this.error(`[${bindings.module || 'child'}] `, message, ...args),
        };
    }
};
module.exports = log;
EOF
success "Core modules created."

# --- Generate Custom Scraper Modules ---
info "Generating custom scraper modules..."

info "Creating modules/custom_scrapers/pornhubScraper.js..."
cat << 'EOF' > modules/custom_scrapers/pornhubScraper.js
// modules/custom_scrapers/pornhubScraper.js
'use strict';

const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const cheerio = require('cheerio');

const log = {
    debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[PornhubScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args);},
    info: (message, ...args) => console.log(`[PornhubScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
    warn: (message, ...args) => console.warn(`[PornhubScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
};

class PornhubScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.pornhub.com';
        log.debug(`PornhubScraper instantiated. Query: "${this.query}", Page: ${this.page}`);
    }

    get name() { return 'Pornhub'; }
    get firstpage() { return 1; }

    videoUrl(query, page) {
        const searchPage = page || this.firstpage;
        const url = `${this.baseUrl}/video/search?search=${encodeURIComponent(query)}&page=${searchPage}`;
        log.debug(`Constructed video URL: ${url}`);
        return url;
    }

    async searchVideos(query, page) {
        const url = this.videoUrl(query, page);
        log.info(`Fetching HTML for Pornhub videos from: ${url}`);
        try {
            const html = await this._fetchHtml(url);
            const $ = cheerio.load(html);
            return this.videoParser($, html);
        } catch (error) {
            log.error(`Error in searchVideos for query "${query}" on page ${page}: ${error.message}`);
            return [];
        }
    }

    videoParser($, rawData) {
        log.info(`Parsing Pornhub video data...`);
        const videos = [];
        $('ul.videos.search-video-thumbs li.pcVideoListItem').each((i, elem) => {
            const $elem = $(elem);
            const title = $elem.find('span.title a').attr('title')?.trim();
            const videoPageUrl = $elem.find('span.title a').attr('href');
            const duration = $elem.find('var.duration').text()?.trim();
            // Corrected thumbnail logic
            let thumbnail = $elem.find('img').attr('data-mediumthumb');
            if (!thumbnail) thumbnail = $elem.find('img').attr('data-src');
            if (!thumbnail) thumbnail = $elem.find('img').attr('src');

            // Corrected preview video logic
            let previewVideo = $elem.find('a.linkVideoThumb').attr('data-mediabook');
            if (!previewVideo) previewVideo = $elem.find('img').attr('data-mediabook');
            if (!previewVideo) previewVideo = $elem.find('img').attr('data-previewvideo');

            if (title && videoPageUrl) {
                videos.push({
                    title,
                    url: this._makeAbsolute(videoPageUrl, this.baseUrl),
                    thumbnail: this._makeAbsolute(thumbnail, this.baseUrl),
                    duration: duration || 'N/A',
                    preview_video: this._makeAbsolute(previewVideo, this.baseUrl),
                    source: this.name,
                });
            } else {
                log.warn('Skipped a Pornhub video item due to missing title or URL.');
            }
        });
        log.info(`Parsed ${videos.length} video items from Pornhub.`);
        return videos;
    }

    gifUrl(query, page) {
        const searchPage = page || this.firstpage;
        const url = `${this.baseUrl}/gifs/search?search=${encodeURIComponent(query)}&page=${searchPage}`;
        log.debug(`Constructed GIF URL: ${url}`);
        return url;
    }

    async searchGifs(query, page) {
        const url = this.gifUrl(query, page);
        log.info(`Fetching HTML for Pornhub GIFs from: ${url}`);
        try {
            const html = await this._fetchHtml(url);
            const $ = cheerio.load(html);
            return this.gifParser($, html);
        } catch (error) {
            log.error(`Error in searchGifs for query "${query}" on page ${page}: ${error.message}`);
            return [];
        }
    }

    gifParser($, rawData) {
        log.info(`Parsing Pornhub GIF data...`);
        const gifs = [];
        $('ul.gifs.gifLink li.gifVideoBlock').each((i, elem) => {
            const $elem = $(elem);
            const title = $elem.find('a').attr('title')?.trim() || $elem.find('.title').text()?.trim();
            const gifPageUrl = $elem.find('a').attr('href');
            // Corrected GIF thumbnail logic
            let thumbnail = $elem.find('video').attr('data-poster');
            if (!thumbnail) thumbnail = $elem.find('img.thumb').attr('data-src');
            if (!thumbnail) thumbnail = $elem.find('img.thumb').attr('src');

            // Corrected GIF preview video logic
            let previewVideo = $elem.find('video').attr('data-webm');
            if (!previewVideo) previewVideo = $elem.find('video source[type="video/webm"]').attr('src');

            if (title && gifPageUrl) {
                gifs.push({
                    title,
                    url: this._makeAbsolute(gifPageUrl, this.baseUrl),
                    thumbnail: this._makeAbsolute(thumbnail, this.baseUrl),
                    preview_video: this._makeAbsolute(previewVideo, this.baseUrl),
                    source: this.name,
                });
            } else {
                log.warn('Skipped a Pornhub GIF item due to missing title or URL.');
            }
        });
        log.info(`Parsed ${gifs.length} GIF items from Pornhub.`);
        return gifs;
    }
}

module.exports = PornhubScraper;
EOF

info "Creating modules/custom_scrapers/xvideosScraper.js..."
cat << 'EOF' > modules/custom_scrapers/xvideosScraper.js
// modules/custom_scrapers/xvideosScraper.js
'use strict';

const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const cheerio = require('cheerio');

const log = {
    debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[XvideosScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args);},
    info: (message, ...args) => console.log(`[XvideosScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
    warn: (message, ...args) => console.warn(`[XvideosScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
};

class XvideosScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.xvideos.com';
        log.debug(`XvideosScraper instantiated. Query: "${this.query}", Page: ${this.page}`);
    }

    get name() { return 'Xvideos'; }
    get firstpage() { return 0; } // Xvideos 'p' param is 0-indexed

    videoUrl(query, page) {
        const xvideosPage = Math.max(0, (parseInt(page, 10) || 1) - 1 + this.firstpage); // Adjust for 0-indexed
        const url = `${this.baseUrl}/?k=${encodeURIComponent(query)}&p=${xvideosPage}`;
        log.debug(`Constructed Xvideos video URL: ${url}`);
        return url;
    }

    async searchVideos(query, page) {
        const url = this.videoUrl(query, page);
        log.info(`Fetching HTML for Xvideos videos from: ${url}`);
        try {
            const html = await this._fetchHtml(url);
            const $ = cheerio.load(html);
            return this.videoParser($, html);
        } catch (error) {
            log.error(`Error in Xvideos searchVideos for query "${query}" on page ${page}: ${error.message}`);
            return [];
        }
    }

    videoParser($, rawData) {
        log.info(`Parsing Xvideos video data...`);
        const videos = [];
        $('div.thumb-block').each((i, elem) => {
            const $elem = $(elem);
            const $titleLink = $elem.find('p.title a');
            const title = $titleLink.attr('title')?.trim();
            const videoPageUrl = $titleLink.attr('href');
            const duration = $elem.find('span.duration').text()?.trim();
            const thumbnail = $elem.find('div.thumb-inside img').attr('data-src');
            const previewVideo = $elem.find('div.thumb-inside img').attr('data-videopreview'); // Often a .gif or short .mp4

            if (title && videoPageUrl) {
                videos.push({
                    title,
                    url: this._makeAbsolute(videoPageUrl, this.baseUrl),
                    thumbnail: this._makeAbsolute(thumbnail, this.baseUrl),
                    duration: duration || 'N/A',
                    preview_video: this._makeAbsolute(previewVideo, this.baseUrl),
                    source: this.name,
                });
            } else {
                log.warn('Skipped an Xvideos video item due to missing title or URL.');
            }
        });
        log.info(`Parsed ${videos.length} video items from Xvideos.`);
        return videos;
    }

    gifUrl(query, page) {
        const xvideosPage = Math.max(0, (parseInt(page, 10) || 1) - 1 + this.firstpage);
        const url = `${this.baseUrl}/gifs/${encodeURIComponent(query)}/${xvideosPage}`; // Example structure
        log.debug(`Constructed Xvideos GIF URL: ${url}`);
        return url;
    }

    async searchGifs(query, page) {
        const url = this.gifUrl(query, page);
        log.info(`Fetching HTML for Xvideos GIFs from: ${url}`);
        try {
            const html = await this._fetchHtml(url);
            const $ = cheerio.load(html);
            return this.gifParser($, html);
        } catch (error) {
            log.error(`Error in Xvideos searchGifs for query "${query}" on page ${page}: ${error.message}`);
            return [];
        }
    }

    gifParser($, rawData) {
        log.info(`Parsing Xvideos GIF data...`);
        const gifs = [];
        // Note: Xvideos GIF selectors are highly speculative and may need significant adjustment.
        $('div.gif-thumb-block, div.thumb-block').each((i, elem) => {
            const $elem = $(elem);
            const $titleLink = $elem.find('p.title a, a.thumb-name');
            const title = $titleLink.attr('title')?.trim() || $titleLink.text()?.trim();
            const gifPageUrl = $titleLink.attr('href');
            const imgElement = $elem.find('div.thumb img, div.thumb-inside img');
            let thumbnail = imgElement.attr('src'); // Static thumbnail
            let previewVideo = imgElement.attr('data-src'); // Often the animated GIF itself for Xvideos

            if (!previewVideo && thumbnail && thumbnail.endsWith('.gif')) { // If data-src is missing but src is a gif
                previewVideo = thumbnail;
            }
            if (previewVideo && !thumbnail) { // If only preview is available, use it as thumbnail too
                thumbnail = previewVideo;
            }

            if (title && gifPageUrl && previewVideo) {
                gifs.push({
                    title,
                    url: this._makeAbsolute(gifPageUrl, this.baseUrl),
                    thumbnail: this._makeAbsolute(thumbnail, this.baseUrl),
                    preview_video: this._makeAbsolute(previewVideo, this.baseUrl),
                    source: this.name,
                });
            } else {
                log.warn('Skipped an Xvideos GIF item due to missing critical data.');
            }
        });
        log.info(`Parsed ${gifs.length} GIF items from Xvideos.`);
        return gifs;
    }
}

module.exports = XvideosScraper;
EOF

# Placeholder stubs for other scrapers mentioned in config.json (commented out)
info "Creating placeholder stubs for other potential scrapers..."
cat << 'EOF' > modules/custom_scrapers/sexComScraper.js
// Placeholder for Sex.com custom scraper
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
class SexComScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    get name() { return 'SexCom'; }
    videoUrl(q,p){ return ''; } async videoParser($d){ return [{title:'SexCom Video Scraper Not Implemented Yet'}];}
    gifUrl(q,p){ return ''; } async gifParser($d){ return [{title:'SexCom GIF Scraper Not Implemented Yet'}];}
}
module.exports = SexComScraper;
EOF
cat << 'EOF' > modules/custom_scrapers/youpornScraper.js
// Placeholder for YouPorn custom scraper
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
// const GifMixin = require('../../core/GifMixin'); // YouPorn might not have a significant GIF section
class YouPornScraper extends AbstractModule.with(VideoMixin) {
    get name() { return 'YouPorn'; }
    videoUrl(q,p){ return ''; } async videoParser($d){ return [{title:'YouPorn Video Scraper Not Implemented Yet'}];}
    // gifUrl(q,p){ return ''; } async gifParser($d){ return [];}
}
module.exports = YouPornScraper;
EOF
cat << 'EOF' > modules/custom_scrapers/xhamsterScraper.js
// Placeholder for Xhamster custom scraper
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
class XhamsterScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    get name() { return 'Xhamster'; }
    videoUrl(q,p){ return ''; } async videoParser($d){ return [{title:'Xhamster Video Scraper Not Implemented Yet'}];}
    gifUrl(q,p){ return ''; } async gifParser($d){ return [{title:'Xhamster GIF Scraper Not Implemented Yet'}];}
}
module.exports = XhamsterScraper;
EOF

cat << 'EOF' > modules/custom_scrapers/motherlessScraper.js
// Placeholder for Motherless custom scraper
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin'); // Or just VideoMixin if GIFs are not distinct
const log = require('../../core/log').child({ module: 'MotherlessScraper' }); // Basic log setup

class MotherlessScraper extends AbstractModule.with(VideoMixin, GifMixin) { // Adjust mixins as needed
    constructor(options) { super(options); this.baseUrl = 'https://motherless.com'; log.info('MotherlessScraper instantiated'); }
    get name() { return 'Motherless'; }
    videoUrl(query, page) { log.warn('Motherless videoUrl not implemented'); return `${this.baseUrl}/term/videos/${encodeURIComponent(query)}?page=${page}`; } // Example URL
    async videoParser($, rawData) { log.warn('Motherless videoParser not implemented'); return [{title:'Motherless Video Scraper Not Implemented Yet', source: this.name}]; }
    gifUrl(query, page) { log.warn('Motherless gifUrl not implemented'); return `${this.baseUrl}/term/images/${encodeURIComponent(query)}?page=${page}`; } // Example URL for images/gifs
    async gifParser($, rawData) { log.warn('Motherless gifParser not implemented'); return [{title:'Motherless GIF Scraper Not Implemented Yet', source: this.name}]; }
}
module.exports = MotherlessScraper;
EOF

cat << 'EOF' > modules/custom_scrapers/redtubeScraper.js
// Placeholder for Redtube custom scraper
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
// const GifMixin = require('../../core/GifMixin'); // Likely not needed for Redtube
const log = require('../../core/log').child({ module: 'RedtubeScraper' }); // Basic log setup

class RedtubeScraper extends AbstractModule.with(VideoMixin) {
    constructor(options) { super(options); this.baseUrl = 'https://www.redtube.com'; log.info('RedtubeScraper instantiated'); }
    get name() { return 'Redtube'; }
    videoUrl(query, page) { log.warn('Redtube videoUrl not implemented'); return `${this.baseUrl}/?search=${encodeURIComponent(query)}&page=${page}`; } // Example URL
    async videoParser($, rawData) { log.warn('Redtube videoParser not implemented'); return [{title:'Redtube Video Scraper Not Implemented Yet', source: this.name}]; }
    gifUrl(query, page) { log.warn('Redtube gifUrl not implemented - site is video focused'); return ''; }
    async gifParser($, rawData) { log.warn('Redtube gifParser not implemented - site is video focused'); return []; }
}
module.exports = RedtubeScraper;
EOF

cat << 'EOF' > modules/custom_scrapers/mockScraper.cjs
// modules/custom_scrapers/mockScraper.cjs
// Basic mock scraper for testing purposes

class MockScraper {
    constructor(options) {
        this.options = options || {};
        this.query = this.options.query;
        this.page = this.options.page || 1;
    }

    get name() { return 'Mock'; } // Used as key in loadedCustomScrapers
    get sourceName() { return 'MockSource'; } // Used in item.source

    async searchGifs(query, page) {
        // console.log(`[MockScraper] searchGifs called with query: ${query}, page: ${page}`);
        return [
            { title: 'Mock GIF 1 from Scraper', url: `https://mock.com/gif/1?q=${query}&p=${page}`, thumbnail: 'https://via.placeholder.com/150/0000FF/808080?Text=MockThumb1.jpg', preview_video: 'https://example.com/mock_preview1.gif', source: this.sourceName, query: query, type: 'gifs' },
            { title: 'Mock GIF 2 from Scraper', url: `https://mock.com/gif/2?q=${query}&p=${page}`, thumbnail: 'https://via.placeholder.com/150/FF0000/FFFFFF?Text=MockThumb2.jpg', preview_video: 'https://example.com/mock_preview2.gif', source: this.sourceName, query: query, type: 'gifs' },
        ];
    }

    async searchVideos(query, page) {
        // console.log(`[MockScraper] searchVideos called with query: ${query}, page: ${page}`);
        return [
            { title: 'Mock Video 1 from Scraper', url: `https://mock.com/video/1?q=${query}&p=${page}`, thumbnail: 'https://via.placeholder.com
