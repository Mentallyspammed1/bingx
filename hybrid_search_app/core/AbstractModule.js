'use strict';

const OverwriteError = require('./OverwriteError');
const axios = require('axios');
const { logger } = require('../modules/driver-utils.js');

class AbstractModule {
  constructor(options = {}) {
    this.query = (options.query || '').trim();
    this.page = parseInt(options.page, 10) || this.firstpage;

    this.httpClient = axios.create({
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'
      },
      timeout: 20000, // 20 seconds timeout
    });
    logger.debug(`[AbstractModule] Initialized for driver: ${this.name}, Query: "${this.query}", Page: ${this.page}`);
  }

  setQuery(newQuery) {
    if (typeof newQuery !== 'string' || newQuery.trim() === '') {
      logger.warn(`[${this.name || 'AbstractModule'}] Attempted to set an invalid query: "${newQuery}". Query must be a non-empty string.`);
      return;
    }
    this.query = newQuery.trim();
    logger.debug(`[${this.name || 'AbstractModule'}] Query updated to: "${this.query}"`);
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

  parseResults(cheerioInstance, rawData, options) {
    throw new OverwriteError('Method "parseResults" must be implemented by the concrete driver class.');
  }

  async _fetchHtml(url) {
    try {
      const response = await this.httpClient.get(url);
      return response.data;
    } catch (error) {
      if (error.response) {
        logger.error(`[${this.name || 'AbstractModule'} _fetchHtml] Status: ${error.response.status} for URL ${url}`);
      } else if (error.request) {
        logger.error(`[${this.name || 'AbstractModule'} _fetchHtml] No response received for request to ${url}`);
      } else {
        logger.error(`[${this.name || 'AbstractModule'} _fetchHtml] Error fetching URL ${url}:`, error.message);
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
      logger.warn(`[${this.name || 'AbstractModule'}] _makeAbsolute: Failed to resolve URL "${urlString}" with base "${baseUrl}". Error: ${e.message}`);
      return undefined;
    }
  }

  static with(...mixinFactories) {
    let ClassToExtend = this;
    for (const mixinFactory of mixinFactories) {
        if (typeof mixinFactory === 'function') {
            ClassToExtend = mixinFactory(ClassToExtend);
        } else {
            logger.warn('[AbstractModule.with] Encountered a non-function in mixinFactories array:', mixinFactory);
        }
    }
    return ClassToExtend;
  }
}

module.exports = AbstractModule;