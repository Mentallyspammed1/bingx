// core/AbstractModule.js
'use strict';
const OverwriteError = require('./OverwriteError');
const axios = require('axios');

class AbstractModule {
  constructor(options = {}) {
    this.query = (options.query || '').trim();
    this.driverName = options.driverName || this.name; // Get driverName from options or from abstract name getter
    this.page = parseInt(options.page, 10) || this.firstpage; // Initialize page

    // Initialize a shared HTTP client instance
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
    // Removed HttpsProxyAgent and hardcoded proxy.
    // The existing this.httpClient instance will be used.
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
      // Rethrow a more specific error or an error that can be caught and handled by the main API endpoint
      throw new Error(`Failed to fetch HTML from ${url} for driver ${this.name}. Original error: ${error.message}`);
    }
  }

  // Utility method to construct absolute URLs
  _makeAbsolute(urlString, baseUrl) {
    if (!urlString || typeof urlString !== 'string') {
        // console.warn(`[${this.name || 'AbstractModule'}] _makeAbsolute: Invalid urlString provided:`, urlString);
        return undefined;
    }
    if (urlString.startsWith('data:')) return urlString; // Data URIs are already absolute
    if (urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString; // Already absolute
    if (urlString.startsWith('//')) return `https:${urlString}`; // Protocol-relative URL

    try {
      // Ensure baseUrl ends with a slash if it's a domain root, for correct resolution
      const effectiveBase = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
      return new URL(urlString, effectiveBase).href;
    } catch (e) {
      console.warn(`[${this.name || 'AbstractModule'}] _makeAbsolute: Failed to resolve URL "${urlString}" with base "${baseUrl}". Error: ${e.message}`);
      return undefined;
    }
  }

  static with(...mixinFactories) {
    // 'this' refers to the class calling 'with' (e.g., AbstractModule or a class already extended by mixins)
    return mixinFactories.reduce((c, mixinFactory) => {
        if (typeof mixinFactory !== 'function') {
            console.warn('[AbstractModule.with] Encountered a non-function in mixinFactories array:', mixinFactory);
            return c; // Return the class unmodified if mixinFactory is not a function
        }
        return mixinFactory(c);
    }, this);
  }
}

module.exports = AbstractModule;
