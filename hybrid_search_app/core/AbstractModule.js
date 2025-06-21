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
