// core/AbstractModule.js
'use strict';
const OverwriteError = require('./OverwriteError'); // Assuming OverwriteError.js is in the same core directory
const axios = require('axios');

class AbstractModule {
  constructor(options = {}) {
    this.query = (options.query || '').trim();
    // this.driverName = options.driverName || this.name; // driverName will be from the concrete class's name getter
    this.page = parseInt(options.page, 10) || this.firstpage; // Initialize page based on driver's firstpage

    this.httpClient = axios.create({
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'
      },
      timeout: 20000, // 20 seconds timeout
    });
    // console.log(`[AbstractModule] Initialized for driver: ${this.name}, Query: "${this.query}", Page: ${this.page}`);
  }

  get name() {
    throw new OverwriteError('Getter "name" must be implemented by the concrete scraper class.');
  }

  get baseUrl() {
    throw new OverwriteError('Getter "baseUrl" must be implemented by the concrete scraper class.');
  }

  hasVideoSupport() {
    throw new OverwriteError('Method "hasVideoSupport" must be implemented by the concrete scraper class.');
  }

  hasGifSupport() {
    throw new OverwriteError('Method "hasGifSupport" must be implemented by the concrete scraper class.');
  }

  get firstpage() {
    return 1; // Default first page for most sites (1-indexed)
  }

  // These will be implemented by concrete drivers
  // getVideoSearchUrl(query, page) { throw new OverwriteError('Method "getVideoSearchUrl" must be implemented.'); }
  // getGifSearchUrl(query, page) { throw new OverwriteError('Method "getGifSearchUrl" must be implemented.'); }
  // parseResults($, htmlOrJsonData, parserOptions) { throw new OverwriteError('Method "parseResults" must be implemented.'); }


  async _fetchHtml(url) {
    try {
      // console.log(`[AbstractModule _fetchHtml] Fetching URL: ${url} for driver ${this.name}`);
      const response = await this.httpClient.get(url);
      return response.data;
    } catch (error) {
      // console.error(`[${this.name || 'AbstractModule'} _fetchHtml] Error fetching URL ${url}:`, error.message);
      if (error.response) {
        // console.error(`[${this.name || 'AbstractModule'} _fetchHtml] Status: ${error.response.status}, Headers: ${JSON.stringify(error.response.headers)}`);
      } else if (error.request) {
        // console.error(`[${this.name || 'AbstractModule'} _fetchHtml] No response received for request:`, error.request);
      }
      throw new Error(`Failed to fetch HTML from ${url} for driver ${this.name}. Original error: ${error.message}`);
    }
  }

  _makeAbsolute(urlString, baseUrl) {
    if (!urlString || typeof urlString !== 'string' || urlString.trim() === '') {
        return undefined;
    }
    if (urlString.startsWith('data:')) return urlString;
    if (urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString;
    if (urlString.startsWith('//')) return `https:${urlString}`;

    try {
      const effectiveBase = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
      return new URL(urlString, effectiveBase).href;
    } catch (e) {
      // console.warn(`[${this.name || 'AbstractModule'}] _makeAbsolute: Failed to resolve URL "${urlString}" with base "${baseUrl}". Error: ${e.message}`);
      return undefined;
    }
  }

  // This 'with' static method is how mixins were applied in some of the user's examples.
  // It allows chaining like: AbstractModule.with(VideoMixin, GifMixin)
  // However, the user's LATEST Pornsearch.js and driver examples do NOT use this pattern.
  // They use `class Driver extends AbstractModule.with(VideoMixin)(AbstractModule)` which is a different pattern,
  // or more simply `class Driver extends Mixin(AbstractModule)`.
  // The provided `Pornsearch.js` does NOT use `AbstractModule.with`.
  // The provided drivers like `Motherless.js` use `_AbstractModule2.default.with(_VideoMixin2.default)`
  // This implies `with` is a static method on `AbstractModule` (or its imported version).
  // I'll keep the static `with` here as it was in the original `core/AbstractModule.js`.
  static with(...mixinFactories) {
    let ClassToExtend = this;
    for (const mixinFactory of mixinFactories) {
        if (typeof mixinFactory === 'function') {
            ClassToExtend = mixinFactory(ClassToExtend);
        } else {
            // console.warn('[AbstractModule.with] Encountered a non-function in mixinFactories array:', mixinFactory);
        }
    }
    return ClassToExtend;
  }
}

module.exports = AbstractModule;
