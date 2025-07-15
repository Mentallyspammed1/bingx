'use strict';

// Core module and mixins
const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');

const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL_CONST = 'https://www.youporn.com';
const DRIVER_NAME_CONST = 'Youporn';

// Apply mixins to AbstractModule
const BaseYoupornClass = AbstractModule.with(VideoMixin);

class YoupornDriver extends BaseYoupornClass {
  constructor(options = {}) {
    super(options);
    logger.debug(`[${DRIVER_NAME_CONST}] Initialized.`);
  }

  get name() { return DRIVER_NAME_CONST; }
  get baseUrl() { return BASE_URL_CONST; }
  hasVideoSupport() { return true; }
  hasGifSupport() { return false; } // Explicitly false

  getVideoSearchUrl(query, page) {
    const currentQuery = query || this.query;
    if (!currentQuery || typeof currentQuery !== 'string' || currentQuery.trim() === '') {
      throw new Error('YoupornDriver: Search query is not set or is empty for video search.');
    }
    const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
    // This is the new API endpoint
    const searchUrl = new URL('/api/v4/search/video', this.baseUrl);
    searchUrl.searchParams.set('query', sanitizeText(currentQuery));
    searchUrl.searchParams.set('page', String(pageNumber));
    searchUrl.searchParams.set('size', '42'); // Default size, can be adjusted
    logger.debug(`[${this.name}] Generated API videoUrl: ${searchUrl.href}`);
    return searchUrl.href;
  }

  getCustomHeaders() {
    return {
      'Cookie': 'age_verified=1',
      'Accept': 'application/json' // Important for API requests
    };
  }

  parseResults($, rawData, parserOptions) {
    const { type, sourceName } = parserOptions;
    const results = [];

    if (!rawData || typeof rawData !== 'object') {
      logger.error(`[${this.name} Parser] Expected rawData to be an object (JSON), but got:`, typeof rawData);
      return [];
    }

    const videoItems = rawData.videos;

    if (!videoItems || !Array.isArray(videoItems) || videoItems.length === 0) {
      logger.warn(`[${this.name} Parser] No video items found in the JSON response.`);
      return [];
    }

    videoItems.forEach((item, i) => {
      if (!item || !item.url || !item.title) {
        logger.warn(`[${this.name} Parser] Skipping item ${i} due to missing URL or title.`);
        return;
      }

      const absoluteUrl = makeAbsolute(item.url, this.baseUrl);

      results.push({
        id: item.video_id || item.id,
        title: sanitizeText(item.title),
        url: absoluteUrl,
        duration: item.duration || 'N/A',
        thumbnail: item.default_thumb || item.thumb,
        preview_video: item.preview_url || '',
        source: sourceName,
        type: type
      });
    });

    logger.debug(`[${this.name} Parser] Parsed ${results.length} items from JSON for type '${type}'.`);
    return results;
  }
}

module.exports = YoupornDriver;