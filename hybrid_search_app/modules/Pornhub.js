'use strict';

const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const { makeAbsolute, extractPreview, logger } = require('./driver-utils.js');

const BASE_URL = 'https://www.pornhub.com';
const NAME = 'Pornhub'; // Consistent naming
const SEARCH_PATH = '/video/search';
const ID_PATTERN = /viewkey=([\w-]+)/;

const BasePornhubClass = AbstractModule.with(VideoMixin);

class PornhubDriver extends BasePornhubClass {
  constructor(options = {}) {
    super(options);
  }

  get name() {
    return NAME;
  }

  get baseUrl() {
    return BASE_URL;
  }

  get supportsVideos() {
    return true;
  }

  get supportsGifs() {
    return false; // Update if GIF support is added
  }

  getVideoSearchUrl(query, page) {
    const pageNum = Math.max(1, page || 1);
    const searchQuery = encodeURIComponent(query.trim().replace(/\s+/g, '+'));
    const searchUrl = new URL(SEARCH_PATH, this.baseUrl);
    searchUrl.searchParams.set('search', searchQuery);
    searchUrl.searchParams.set('page', String(pageNum));
    logger.info(`[${this.name}] Forging video URL: ${searchUrl.href}`);
    return searchUrl.href;
  }

  parseResults($, htmlData, options) {
    const results = [];
    const videoItems = $('li.pcVideoListItem, li.videoBox, div.videoWrapper');
    console.log(`[${this.name}] Found ${videoItems.length} video items.`);

    if (!videoItems.length) {
      logger.warn(`[${this.name}] No videos found for query: ${options.query}`);
      return [];
    }

    videoItems.each((i, el) => {
      const item = $(el);
      const link = item.find('a[href*="/view_video.php"]').first();
      const url = link.attr('href');
      const title = item.find('span.title a').text()?.trim() || item.find('img').attr('alt')?.trim();
      console.log(`[${this.name}] Item ${i}: url=${url}, title=${title}`);

      if (!title || !url) {
        logger.warn(`[${this.name}] Skipping item ${i}: missing title or URL.`);
        return;
      }

      const duration = item.find('var.duration').text()?.trim();
      const img = item.find('img[data-mediumthumb]').first();
      const thumbnail = img.attr('data-mediumthumb')?.trim() || img.attr('src')?.trim();
      const preview = extractPreview($, item, this.name, this.baseUrl);

      const idMatch = url.match(ID_PATTERN);
      const id = idMatch ? idMatch[1] : null;

      if (!id) {
        logger.warn(`[${this.name}] Skipping item ${i}: could not extract ID from URL: ${url}`);
        return;
      }

      results.push({
        id,
        title,
        url: makeAbsolute(url, this.baseUrl),
        duration: duration || undefined,
        thumbnail: makeAbsolute(thumbnail, this.baseUrl),
        preview_video: preview, // extractPreview already makes it absolute
        source: this.name,
        type: 'videos'
      });
    });

    logger.info(`[${this.name}] Parsed ${results.length} videos for query: ${options.query}`);
    return results;
  }
}

module.exports = PornhubDriver;