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
    "Redtube": "./modules/custom_scrapers/redtubeScraper.js"
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
            let thumbnail = $elem.find('img').attr('data-mediumthumb') || $elem.find('img').attr('data-src') || $elem.find('img').attr('src');
            let previewVideo = $elem.find('a.linkVideoThumb').attr('data-mediabook') || $elem.find('img').attr('data-previewvideo');

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
            let previewVideo = $elem.find('video[data-webm]').attr('data-webm') || $elem.find('video source[type="video/webm"]').attr('src');
            let thumbnail = $elem.find('img.thumb').attr('data-src') || $elem.find('img.thumb').attr('src');

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
    videoUrl(query, page) { log.warn('Motherless videoUrl not implemented'); return `\${this.baseUrl}/term/videos/\${encodeURIComponent(query)}?page=\${page}`; } // Example URL
    async videoParser($, rawData) { log.warn('Motherless videoParser not implemented'); return [{title:'Motherless Video Scraper Not Implemented Yet', source: this.name}]; }
    gifUrl(query, page) { log.warn('Motherless gifUrl not implemented'); return `\${this.baseUrl}/term/images/\${encodeURIComponent(query)}?page=\${page}`; } // Example URL for images/gifs
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
    videoUrl(query, page) { log.warn('Redtube videoUrl not implemented'); return `\${this.baseUrl}/?search=\${encodeURIComponent(query)}&page=\${page}`; } // Example URL
    async videoParser($, rawData) { log.warn('Redtube videoParser not implemented'); return [{title:'Redtube Video Scraper Not Implemented Yet', source: this.name}]; }
    gifUrl(query, page) { log.warn('Redtube gifUrl not implemented - site is video focused'); return ''; }
    async gifParser($, rawData) { log.warn('Redtube gifParser not implemented - site is video focused'); return []; }
}
module.exports = RedtubeScraper;
EOF

success "Custom scraper modules created."

# --- Generate server.js ---
info "Generating server.js..."
cat << 'EOF' > server.js
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

// --- Start Server ---
app.listen(PORT, '0.0.0.0', () => {
    log.info(`Hybrid backend server started on http://0.0.0.0:${PORT}`);
    log.info(`Current Global Backend Strategy: ${globalStrategy}`);
    log.info(`Access frontend at http://localhost:${PORT}`);
});

// --- Graceful Shutdown ---
process.on('SIGINT', () => {
    log.info('Shutdown signal received, closing server gracefully.');
    process.exit(0);
});
process.on('SIGTERM', () => {
    log.info('Termination signal received, closing server gracefully.');
    process.exit(0);
});
EOF
success "server.js created."

# --- Generate public/index.html ---
info "Generating public/index.html..."
cat << 'EOF' > public/index.html
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Neon Search | Find Videos & GIFs</title>
    <meta name="description" content="Search for videos and GIFs with a vibrant neon-themed interface. Features history and local favorites.">
    <meta name="keywords" content="video search, gif search, neon theme, online media, adult entertainment search, favorites, history">
    <meta name="author" content="Neon Search Project">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>💡</text></svg>">

    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">

    <style>
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
        html { scroll-behavior: smooth; }
        body {
            background: linear-gradient(145deg, var(--dark-bg-start) 0%, var(--dark-bg-end) 100%);
            color: var(--text-color); font-family: 'Roboto', sans-serif;
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
        .search-container {
            background: rgba(10, 10, 25, 0.9); border: 2px solid var(--neon-pink);
            box-shadow: 0 0 20px var(--neon-pink), 0 0 40px var(--neon-cyan), 0 0 60px var(--neon-purple), inset 0 0 15px rgba(255, 0, 170, 0.5);
            border-radius: 16px; animation: searchContainerGlow 6s infinite alternate ease-in-out;
        }
        @keyframes searchContainerGlow {
            0% { box-shadow: 0 0 20px var(--neon-pink), 0 0 40px var(--neon-cyan), 0 0 60px var(--neon-purple), inset 0 0 15px rgba(255, 0, 170, 0.5); border-color: var(--neon-pink); }
            50% { box-shadow: 0 0 30px var(--neon-cyan), 0 0 50px var(--neon-purple), 0 0 70px var(--neon-pink), inset 0 0 20px rgba(0, 229, 255, 0.5); border-color: var(--neon-cyan); }
            100% { box-shadow: 0 0 20px var(--neon-purple), 0 0 40px var(--neon-pink), 0 0 60px var(--neon-cyan), inset 0 0 15px rgba(157, 0, 255, 0.5); border-color: var(--neon-purple); }
        }
        .title-main { text-shadow: 0 0 10px var(--neon-pink), 0 0 20px var(--neon-cyan), 0 0 30px var(--neon-purple), 0 0 40px #fff; }
        .title-sub { text-shadow: 0 0 5px var(--neon-cyan); }
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
            background-color: rgba(40, 40, 40, 0.7);
            color: #aaa;
            font-weight: bold; text-align: center; padding: 1rem; font-size: 0.9rem;
            border-radius: inherit;
        }
        .duration-overlay {
            position: absolute; bottom: 0.5rem; right: 0.5rem; background: rgba(0, 0, 0, 0.6);
            color: white; font-size: 0.75rem; padding: 0.2rem 0.4rem; border-radius: 4px; z-index: 10;
        }

        .modal {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: var(--modal-bg);
            display: flex; justify-content: center; align-items: center; z-index: 1000;
            opacity: 0; visibility: hidden; transition: opacity 0.3s ease, visibility 0s linear 0.3s;
        }
        .modal.is-open { opacity: 1; visibility: visible; transition-delay: 0s; }
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

        #errorMessage {
            background: var(--error-bg); border: 2px solid var(--error-border);
            box-shadow: 0 0 18px var(--error-border), 0 0 30px var(--neon-pink), inset 0 0 10px var(--neon-pink);
            color: #ffffff; text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.8);
            border-radius: 8px; padding: 1rem; margin-bottom: 1rem; font-weight: bold; word-break: break-word;
        }
        #errorMessage:not(.hidden) { display: block; }

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
                    <option value="Pornhub">Pornhub</option>
                    <option value="Xvideos">XVideos</option>
                    <option value="Redtube" selected>Redtube</option>
                    <!-- Add other drivers from your config.json/customScrapersMap here -->
                    <!-- <option value="SexCom">SexCom</option> -->
                    <!-- <option value="YouPorn">YouPorn</option> -->
                    <!-- <option value="Xhamster">Xhamster</option> -->
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
        const favoritesCountDisplay = document.getElementById('favoritesCountDisplay');
        const favoritesViewCountDisplay = document.getElementById('favoritesViewCountDisplay');
        const favoritesView = document.getElementById('favoritesView');
        const favoritesGrid = document.getElementById('favoritesGrid');
        const noFavoritesMessage = document.getElementById('noFavoritesMessage');

        const appState = {
            isLoading: false, currentPage: 1, currentQuery: '', currentDriver: driverSelect.value, currentType: typeSelect.value,
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

        function renderMediaErrorPlaceholder(container, message = 'Media Error') {
            container.innerHTML = '';
            const errorDiv = document.createElement('div');
            errorDiv.className = 'media-error-placeholder';
            errorDiv.textContent = message;
            container.appendChild(errorDiv);
            log.warn('Rendered media error placeholder:', message);
        }

        function createMediaContainer(item, itemActualType) {
            const mediaContainer = document.createElement('div');
            mediaContainer.className = 'card-media-container';
            const itemTitleForAria = item.title || (itemActualType === 'gifs' ? 'GIF Preview' : 'Video Preview');
            mediaContainer.setAttribute('role', 'figure');
            mediaContainer.setAttribute('aria-label', itemTitleForAria);

            const staticThumbnailUrl = item.thumbnail || item.thumb || PLACEHOLDER_GIF_DATA_URI;
            const animatedPreviewUrl = item.preview_video;

            const staticThumbImg = document.createElement('img');
            staticThumbImg.src = staticThumbnailUrl;
            staticThumbImg.alt = '';
            staticThumbImg.loading = 'lazy';
            staticThumbImg.className = 'static-thumb';
            staticThumbImg.onerror = () => {
                log.warn(`Static thumbnail load failed: ${staticThumbnailUrl} for "${item.title}". Using placeholder.`);
                staticThumbImg.src = PLACEHOLDER_GIF_DATA_URI;
                if (!animatedPreviewUrl && !mediaContainer.querySelector('.media-error-placeholder')) {
                    renderMediaErrorPlaceholder(mediaContainer, 'Thumb Error');
                }
            };
            mediaContainer.appendChild(staticThumbImg);

            if (animatedPreviewUrl) {
                const isDirectGifPreview = animatedPreviewUrl.toLowerCase().endsWith('.gif');
                if (isDirectGifPreview && itemActualType === 'gifs') {
                    const gifPreviewImg = document.createElement('img');
                    gifPreviewImg.src = animatedPreviewUrl;
                    gifPreviewImg.alt = '';
                    gifPreviewImg.loading = 'lazy';
                    gifPreviewImg.className = 'preview-gif-image';
                    gifPreviewImg.onerror = () => { log.warn(`Animated GIF preview load failed: ${animatedPreviewUrl}`); gifPreviewImg.remove(); };
                    mediaContainer.appendChild(gifPreviewImg);
                } else if (!isDirectGifPreview && itemActualType === 'videos') {
                    const videoPreviewEl = document.createElement('video');
                    videoPreviewEl.src = animatedPreviewUrl;
                    videoPreviewEl.poster = staticThumbnailUrl;
                    videoPreviewEl.muted = true; videoPreviewEl.loop = true; videoPreviewEl.playsInline = true; videoPreviewEl.preload = 'metadata';
                    videoPreviewEl.className = 'preview-video';
                    videoPreviewEl.onerror = (e) => { log.warn(`Preview video load failed: ${animatedPreviewUrl}`, e); videoPreviewEl.remove(); };
                    mediaContainer.appendChild(videoPreviewEl);
                } else {
                     log.warn(`Preview URL ${animatedPreviewUrl} type does not match item type ${itemActualType} or is not a recognized video format. Static thumb will be shown.`);
                }
            }

            if (itemActualType === 'videos' && item.duration && item.duration !== 'N/A' && item.duration !== '00:00') {
                const durationOverlay = document.createElement('span');
                durationOverlay.className = 'duration-overlay';
                durationOverlay.textContent = item.duration;
                mediaContainer.appendChild(durationOverlay);
            }
            return mediaContainer;
        }

        function openModal(itemData, itemTypeFromCard) {
            appState.lastFocusedElement = document.activeElement;
            modalContent.innerHTML = '';
            modalLinkContainer.innerHTML = '';

            const displayType = itemTypeFromCard || itemData.type || appState.currentType;
            const titleText = itemData.title || (displayType === 'gifs' ? 'GIF' : 'Video');

            let mediaSourceUrl = itemData.preview_video || itemData.url;
            let isVideoForModal = displayType === 'videos';

            if (displayType === 'gifs') {
                if (itemData.preview_video && itemData.preview_video.toLowerCase().endsWith('.gif')) {
                    mediaSourceUrl = itemData.preview_video;
                } else if (itemData.url && itemData.url.toLowerCase().endsWith('.gif')) {
                    mediaSourceUrl = itemData.url;
                } else {
                    mediaSourceUrl = itemData.thumbnail || itemData.thumb || PLACEHOLDER_GIF_DATA_URI;
                }
                isVideoForModal = false;
            } else {
                if (itemData.preview_video && (itemData.preview_video.toLowerCase().endsWith('.mp4') || itemData.preview_video.toLowerCase().endsWith('.webm'))) {
                    mediaSourceUrl = itemData.preview_video;
                } else {
                    mediaSourceUrl = itemData.thumbnail || itemData.thumb || PLACEHOLDER_GIF_DATA_URI;
                    isVideoForModal = false;
                }
            }

            if (!mediaSourceUrl || mediaSourceUrl === PLACEHOLDER_GIF_DATA_URI) {
                renderMediaErrorPlaceholder(modalContent, 'Media not available for modal display.');
            } else {
                let mediaElement;
                if (isVideoForModal) {
                    mediaElement = document.createElement('video');
                    mediaElement.src = mediaSourceUrl;
                    mediaElement.controls = true; mediaElement.autoplay = true; mediaElement.loop = false;
                } else {
                    mediaElement = document.createElement('img');
                    mediaElement.src = mediaSourceUrl; mediaElement.alt = titleText;
                }
                mediaElement.style.maxHeight = 'calc(95vh - 100px)';
                mediaElement.style.maxWidth = '100%';
                mediaElement.onerror = () => renderMediaErrorPlaceholder(modalContent, 'Error loading media in modal.');
                modalContent.appendChild(mediaElement);
            }

            const sourceLink = document.createElement('a');
            sourceLink.href = itemData.url;
            sourceLink.target = '_blank'; sourceLink.rel = 'noopener noreferrer';
            sourceLink.className = 'modal-link';
            sourceLink.textContent = `View on ${itemData.source || 'Source'}: "${itemData.title || 'Untitled'}"`;
            modalLinkContainer.appendChild(sourceLink);

            mediaModal.classList.add('is-open');
            mediaModal.setAttribute('aria-hidden', 'false');
            requestAnimationFrame(() => closeModalBtn.focus());
            log.modal('Modal opened for:', itemData.title);
        }

        function debounce(func, delay) {
            let timeout;
            return function(...args) {
                const context = this;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), delay);
            };
        }

        function loadFavorites() {
            try {
                const storedFavorites = localStorage.getItem(FAVORITES_STORAGE_KEY);
                appState.favorites = storedFavorites ? JSON.parse(storedFavorites) : [];
                log.favorites(`Loaded ${appState.favorites.length} favorites from localStorage.`);
                updateFavoritesCountDisplay();
            } catch (e) {
                log.error('Failed to load favorites from localStorage:', e);
                appState.favorites = [];
            }
        }

        function saveFavorites() {
            try {
                localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(appState.favorites));
                log.favorites(`Saved ${appState.favorites.length} favorites to localStorage.`);
                updateFavoritesCountDisplay();
            } catch (e) {
                log.error('Failed to save favorites to localStorage:', e);
            }
        }

        function isFavorite(item) {
            return appState.favorites.some(fav => fav.url === item.url && fav.source === item.source);
        }

        function toggleFavorite(item) {
            const itemIdentifier = { url: item.url, source: item.source, title: item.title, thumbnail: item.thumbnail, preview_video: item.preview_video, duration: item.duration, type: item.type || appState.currentType };
            const existingFavIndex = appState.favorites.findIndex(fav => fav.url === itemIdentifier.url && fav.source === itemIdentifier.source);

            if (existingFavIndex > -1) {
                appState.favorites.splice(existingFavIndex, 1);
                log.favorites('Removed from favorites:', item.title);
            } else {
                appState.favorites.push(itemIdentifier);
                log.favorites('Added to favorites:', item.title);
            }
            saveFavorites();

            const cardElement = document.querySelector(`.card[data-url="${CSS.escape(item.url)}"][data-source="${CSS.escape(item.source)}"]`);
            if (cardElement) {
                const favBtn = cardElement.querySelector('.favorite-btn');
                if (favBtn) {
                    favBtn.classList.toggle('is-favorite', isFavorite(item));
                    favBtn.innerHTML = isFavorite(item) ? '★' : '♡';
                    favBtn.setAttribute('aria-label', isFavorite(item) ? 'Remove from favorites' : 'Add to favorites');
                    favBtn.title = isFavorite(item) ? 'Remove from favorites' : 'Add to favorites';
                }
            }
            if (appState.showingFavorites) displayFavoritesView();
        }

        function updateFavoritesCountDisplay() {
            const count = appState.favorites.length;
            if (favoritesCountDisplay) favoritesCountDisplay.textContent = count;
            if (favoritesViewCountDisplay) favoritesViewCountDisplay.textContent = `(${count})`;
            if (appState.showingFavorites && noFavoritesMessage) {
                noFavoritesMessage.classList.toggle('hidden', count > 0);
            }
        }

        function displayFavoritesView() {
            if (appState.isLoading) { log.favorites('Cannot display favorites while loading.'); return; }
            appState.showingFavorites = true;
            resultsDiv.classList.add('hidden');
            paginationControls.classList.add('hidden');
            initialMessage?.classList.add('hidden');
            favoritesView.classList.remove('hidden');
            favoritesGrid.innerHTML = '';

            if (appState.favorites.length === 0) {
                noFavoritesMessage?.classList.remove('hidden');
            } else {
                noFavoritesMessage?.classList.add('hidden');
                renderItems(appState.favorites, favoritesGrid);
            }
            updateFavoritesCountDisplay();
            log.favorites('Displaying favorites view.');
            if (toggleFavoritesBtn) toggleFavoritesBtn.innerHTML = `Back to Search`;
            updateURL(true);
        }

        function hideFavoritesView() {
            appState.showingFavorites = false;
            favoritesView.classList.add('hidden');
            resultsDiv.classList.remove('hidden');

            if (appState.resultsCache.length > 0) {
                displaySearchResults(appState.resultsCache);
                 initialMessage?.classList.add('hidden');
            } else {
                resultsDiv.innerHTML = '';
                initialMessage?.classList.remove('hidden');
                paginationControls.classList.add('hidden');
            }
            log.favorites('Hiding favorites, returning to search results.');
            if (toggleFavoritesBtn) toggleFavoritesBtn.innerHTML = `View Favorites (<span id="favoritesCountDisplay">${appState.favorites.length}</span>)`;
            updateURL(true);
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
                const data = Array.isArray(response.data.data) ? response.data.data : [];
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

        function showSkeletons(count = SKELETON_COUNT, targetGrid = resultsDiv) {
            targetGrid.innerHTML = '';
            if (targetGrid === resultsDiv && !appState.showingFavorites) initialMessage?.classList.add('hidden');

            targetGrid.setAttribute('aria-busy', 'true');
            targetGrid.removeAttribute('aria-live'); // Avoid announcing skeleton addition

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
                    if(appState.isLoading && ( (targetGrid === resultsDiv && !appState.showingFavorites) || (targetGrid === favoritesGrid && appState.showingFavorites) ) ){
                        targetGrid.appendChild(fragment);
                    }
                }
            }, 100);
        }

        function setSearchState(isLoading) {
            appState.isLoading = isLoading;
            [searchInput, typeSelect, driverSelect, searchBtn, toggleFavoritesBtn].forEach(el => { if(el) el.disabled = isLoading; });

            if (isLoading) {
                searchBtnText.classList.add('hidden');
                loadingIndicator.classList.remove('hidden');
                if (!appState.showingFavorites) showSkeletons(SKELETON_COUNT, resultsDiv);
                 else showSkeletons(SKELETON_COUNT, favoritesGrid);
            } else {
                searchBtnText.classList.remove('hidden');
                loadingIndicator.classList.add('hidden');
                if (resultsDiv.getAttribute('aria-busy') === 'true') resultsDiv.setAttribute('aria-busy', 'false'); // Reset only if it was set
                if (favoritesGrid.getAttribute('aria-busy') === 'true') favoritesGrid.setAttribute('aria-busy', 'false');
                if (!appState.showingFavorites) resultsDiv.setAttribute('aria-live', 'polite'); // Restore live region for results
                else favoritesGrid.setAttribute('aria-live', 'polite'); // Restore live region for favorites
            }
        }

        function createCard(itemData) {
            const itemActualType = itemData.type || (appState.showingFavorites && itemData.type ? itemData.type : appState.currentType);
            const card = document.createElement('div');
            card.className = 'card relative group';
            card.setAttribute('data-url', itemData.url);
            card.setAttribute('data-source', itemData.source);
            card.tabIndex = 0;

            const favBtn = document.createElement('button');
            favBtn.type = 'button';
            favBtn.className = 'favorite-btn';
            const isCurrentlyFavorite = isFavorite(itemData);
            favBtn.innerHTML = isCurrentlyFavorite ? '★' : '♡';
            favBtn.setAttribute('aria-label', isCurrentlyFavorite ? 'Remove from favorites' : 'Add to favorites');
            favBtn.title = isCurrentlyFavorite ? 'Remove from favorites' : 'Add to favorites';
            if (isCurrentlyFavorite) favBtn.classList.add('is-favorite');

            favBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleFavorite(itemData);
            });
            card.appendChild(favBtn);

            const mediaContainer = createMediaContainer(itemData, itemActualType);
            card.appendChild(mediaContainer);

            const infoDiv = document.createElement('div');
            infoDiv.className = 'card-info';
            const title = document.createElement('h3');
            title.className = 'card-title';
            title.textContent = itemData.title || 'Untitled';
            title.title = itemData.title || 'Untitled';
            infoDiv.appendChild(title);

            const sourceLink = document.createElement('a');
            sourceLink.href = itemData.url;
            sourceLink.target = '_blank';
            sourceLink.rel = 'noopener noreferrer';
            sourceLink.className = 'card-link';
            sourceLink.textContent = `View on ${itemData.source || 'Source'}`;
            sourceLink.addEventListener('click', (e) => e.stopPropagation());
            infoDiv.appendChild(sourceLink);
            card.appendChild(infoDiv);

            card.addEventListener('click', () => openModal(itemData, itemActualType));
            card.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openModal(itemData, itemActualType); }
            });

            if (itemActualType === 'videos') {
                const videoPreview = mediaContainer.querySelector('video.preview-video');
                if (videoPreview) {
                    const playVideo = () => videoPreview.play().catch(e => {if (e.name !== 'AbortError') log.warn('Preview play error:', e.message);});
                    const pauseVideo = () => { videoPreview.pause(); if (videoPreview.readyState > 0) videoPreview.currentTime = 0; };
                    card.addEventListener('mouseenter', () => { clearTimeout(appState.hoverPauseTimeout); appState.hoverPlayTimeout = setTimeout(playVideo, HOVER_PLAY_DELAY_MS); });
                    card.addEventListener('focusin', (e) => { if(card.contains(e.target)) {clearTimeout(appState.hoverPauseTimeout); appState.hoverPlayTimeout = setTimeout(playVideo, HOVER_PLAY_DELAY_MS);}});
                    card.addEventListener('mouseleave', () => { clearTimeout(appState.hoverPlayTimeout); appState.hoverPauseTimeout = setTimeout(pauseVideo, HOVER_PAUSE_DELAY_MS); });
                    card.addEventListener('focusout', (e) => { if (!card.contains(e.relatedTarget)) { clearTimeout(appState.hoverPlayTimeout); appState.hoverPauseTimeout = setTimeout(pauseVideo, HOVER_PAUSE_DELAY_MS); }});
                }
            }
            return card;
        }

        function renderItems(items, targetGridElement) {
            targetGridElement.innerHTML = '';
            targetGridElement.setAttribute('aria-busy', 'false');
             // Set live region only if it's the main resultsDiv and not showing favorites
            if (targetGridElement === resultsDiv && !appState.showingFavorites) {
                targetGridElement.setAttribute('aria-live', 'polite');
            }


            if (!items || items.length === 0) {
                const messageP = document.createElement('p');
                messageP.className = 'text-center text-xl col-span-full text-gray-400 py-10';
                if (targetGridElement === resultsDiv) {
                    messageP.textContent = `No results found for "${appState.currentQuery}".`;
                    messageP.style.textShadow = '0 0 5px var(--neon-purple)';
                } else if (targetGridElement === favoritesGrid) {
                     // This is now handled by noFavoritesMessage visibility, so this part might not be needed
                     // Or, ensure noFavoritesMessage is used consistently
                }
                targetGridElement.appendChild(messageP); // Append if noFavoritesMessage isn't the primary way
                return;
            }

            const fragment = document.createDocumentFragment();
            items.forEach(item => fragment.appendChild(createCard(item)));
            targetGridElement.appendChild(fragment);
        }

        function displaySearchResults(results) {
            appState.resultsCache = results; // Store for pagination/history
            initialMessage?.classList.add('hidden');
            favoritesView.classList.add('hidden');
            resultsDiv.classList.remove('hidden');
            renderItems(results, resultsDiv);
            updatePaginationButtons();
        }

        function closeModal() {
            if (!mediaModal.classList.contains('is-open')) return;
            log.modal('Closing modal.');
            const modalVideo = modalContent.querySelector('video');
            if (modalVideo) {
                modalVideo.pause(); modalVideo.removeAttribute('src'); modalVideo.load();
            }
            modalContent.innerHTML = ''; modalLinkContainer.innerHTML = '';
            mediaModal.classList.remove('is-open');
            mediaModal.setAttribute('aria-hidden', 'true');
            if (appState.lastFocusedElement) {
                requestAnimationFrame(() => {
                    try { appState.lastFocusedElement.focus({ preventScroll: true }); }
                    catch (e) { searchInput.focus(); } // Fallback focus
                });
            } else { searchInput.focus(); }
            appState.lastFocusedElement = null;
        }

        function updatePaginationButtons() {
            if (appState.isLoading || appState.showingFavorites || !errorMessage.classList.contains('hidden') ) {
                 paginationControls.classList.add('hidden'); return;
            }
            const hasResults = appState.resultsCache.length > 0;
            const likelyMorePages = hasResults && appState.resultsCache.length >= appState.maxResultsHeuristic;
            const showPagination = hasResults || appState.currentPage > 1;

            paginationControls.classList.toggle('hidden', !showPagination);
            if (showPagination) {
                prevBtn.disabled = appState.currentPage <= 1;
                nextBtn.disabled = !likelyMorePages;
                pageIndicator.textContent = `Page ${appState.currentPage}`;
            }
        }

        function updateURL(replace = false) {
            let newUrl;
            const currentPath = window.location.pathname; // Keep current path
            if (appState.showingFavorites) {
                newUrl = `${currentPath}#favorites`;
            } else {
                const params = new URLSearchParams();
                if (appState.currentQuery) params.set('q', appState.currentQuery);
                if (appState.currentDriver) params.set('driver', appState.currentDriver);
                if (appState.currentType) params.set('type', appState.currentType);
                if (appState.currentPage > 1) params.set('page', appState.currentPage);
                newUrl = `${currentPath}${params.toString() ? '?' + params.toString() : ''}`;
            }
            const historyMethod = replace ? window.history.replaceState : window.history.pushState;
            // Store less data in history state to avoid exceeding limits
            historyMethod.call(window.history, {
                currentQuery: appState.currentQuery,
                currentDriver: appState.currentDriver,
                currentType: appState.currentType,
                currentPage: appState.currentPage,
                showingFavorites: appState.showingFavorites
            }, '', newUrl);
            log.info(`${replace ? 'Replaced' : 'Pushed'} history state: ${newUrl}`);
        }

        async function handleUrlOrState(state = window.history.state) {
            log.info('Handling URL/State:', { pathname: window.location.pathname, search: window.location.search, hash: window.location.hash, state: state ? {...state, resultsCache: '[omitted]' } : null });

            const params = new URLSearchParams(window.location.search);
            const urlHasFavoritesHash = window.location.hash === '#favorites';

            const query = params.get('q') || state?.currentQuery || '';
            const driver = params.get('driver') || state?.currentDriver || driverSelect.value;
            const type = params.get('type') || state?.currentType || typeSelect.value;
            const page = parseInt(params.get('page'), 10) || state?.currentPage || 1;
            const showingFavoritesFromState = state?.showingFavorites || urlHasFavoritesHash;

            searchInput.value = query;
            driverSelect.value = driver;
            typeSelect.value = type;

            if (showingFavoritesFromState) {
                displayFavoritesView();
                if (urlHasFavoritesHash && !(state?.showingFavorites)) updateURL(true);
                return;
            }

            if (appState.showingFavorites) hideFavoritesView(); // Ensure we switch from fav view if needed

            if (query) {
                appState.currentQuery = query;
                appState.currentDriver = driver;
                appState.currentType = type;
                // appState.currentPage will be set by performSearch
                await performSearch(page, false);
            } else {
                resultsDiv.innerHTML = '';
                initialMessage?.classList.remove('hidden');
                paginationControls.classList.add('hidden');
                hideError();
                setSearchState(false);
                appState.currentQuery = ''; appState.currentPage = 1; appState.resultsCache = [];
                if (window.location.search || window.location.hash) {
                    updateURL(true); // Clean URL if it had params/hash but no query
                }
            }
        }

        async function performSearch(page = 1, isUserInitiated = true) {
            if (appState.isLoading) { log.info('Search prevented: Already loading.'); return; }

            const query = searchInput.value.trim();
            const driver = driverSelect.value;
            const type = typeSelect.value;

            if (isUserInitiated && !query) { showError('Please enter a search query.'); searchInput.focus(); return; }

            const isNewSearchContext = query !== appState.currentQuery || driver !== appState.currentDriver || type !== appState.currentType;
            const targetPage = (isUserInitiated && isNewSearchContext) ? 1 : Math.max(1, page);

            appState.currentQuery = query;
            appState.currentDriver = driver;
            appState.currentType = type;
            appState.currentPage = targetPage;

            if (appState.showingFavorites && isUserInitiated) hideFavoritesView();

            hideError();
            setSearchState(true);
            log.info(`PerformSearch: Q='${query}', D='${driver}', T='${type}', P=${targetPage}, UserInitiated=${isUserInitiated}`);

            const apiResponse = await fetchResultsFromApi(query, driver, type, targetPage);

            if (query === appState.currentQuery && driver === appState.currentDriver && type === appState.currentType && targetPage === appState.currentPage) {
                setSearchState(false);
                if (apiResponse.success) {
                    displaySearchResults(apiResponse.data);
                    updateURL(isUserInitiated ? false : true);
                } else if (!apiResponse.isAbort) {
                    showError(apiResponse.error || 'Failed to fetch results.');
                    displaySearchResults([]);
                }
            } else {
                log.info('Search result discarded, state changed during request.');
            }
        }

        // Event Listeners
        searchBtn.addEventListener('click', () => performSearch(1, true));
        searchInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') performSearch(1, true); });
        clearSearchBtn.addEventListener('click', () => {
            searchInput.value = '';
            clearSearchBtn.style.display = 'none';
            searchInput.focus();
            if (!appState.showingFavorites) {
                resultsDiv.innerHTML = '';
                initialMessage?.classList.remove('hidden');
                paginationControls.classList.add('hidden');
                hideError();
                appState.currentQuery = ''; appState.currentPage = 1; appState.resultsCache = [];
                updateURL(true);
            }
        });
        searchInput.addEventListener('input', () => { clearSearchBtn.style.display = searchInput.value.length > 0 ? 'block' : 'none'; });
        typeSelect.addEventListener('change', () => performSearch(1, true));
        driverSelect.addEventListener('change', () => performSearch(1, true));
        prevBtn.addEventListener('click', () => { if (!prevBtn.disabled && !appState.isLoading) performSearch(appState.currentPage - 1, true); });
        nextBtn.addEventListener('click', () => { if (!nextBtn.disabled && !appState.isLoading) performSearch(appState.currentPage + 1, true); });
        closeModalBtn.addEventListener('click', closeModal);
        mediaModal.addEventListener('click', (e) => { if (e.target === mediaModal) closeModal(); });
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && mediaModal.classList.contains('is-open')) closeModal(); });

        modal.addEventListener('keydown', (e) => {
            if (e.key === 'Tab' && mediaModal.classList.contains('is-open')) {
                const focusableElements = Array.from(
                    mediaModal.querySelectorAll('button, [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')
                ).filter(el => el.offsetParent !== null);
                if (!focusableElements.length) { e.preventDefault(); return; }
                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];
                if (e.shiftKey) { if (document.activeElement === firstElement) { lastElement.focus(); e.preventDefault(); } }
                else { if (document.activeElement === lastElement) { firstElement.focus(); e.preventDefault(); } }
            }
        });

        if (toggleFavoritesBtn) {
            toggleFavoritesBtn.addEventListener('click', () => {
                if (appState.isLoading) return;
                if (appState.showingFavorites) hideFavoritesView();
                else displayFavoritesView();
            });
        }

        document.addEventListener('DOMContentLoaded', () => {
            log.info('DOM fully loaded.');
            loadFavorites();
            handleUrlOrState();
            clearSearchBtn.style.display = searchInput.value.length > 0 ? 'block' : 'none';
        });

    </script>
</body>
</html>
