'use strict';

const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const GifMixin = require('../core/GifMixin.js');
const { makeAbsolute, extractPreview, logger, sanitizeText } = require('./driver-utils.js');

const BASE_URL = 'https://www.pornhub.com';
const NAME = 'Pornhub';
const ID_PATTERN = /viewkey=([\w-]+)/;

// Compose the base class with both Video and Gif functionalities
const BasePornhubClass = AbstractModule.with(VideoMixin, GifMixin);

class PornhubDriver extends BasePornhubClass {
  constructor(options = {}) {
    super(options);
    this.logger = logger.child({ module: 'PornhubDriver' });
  }

  get name() {
    return NAME;
  }

  get baseUrl() {
    return BASE_URL;
  }

  hasVideoSupport() {
    return true;
  }

  hasGifSupport() {
    return true;
  }

  getVideoSearchUrl(query, page) {
    const pageNum = Math.max(1, page || 1);
    const searchQuery = encodeURIComponent(query.trim().replace(/\s+/g, '+'));
    const searchUrl = new URL('/video/search', this.baseUrl);
    searchUrl.searchParams.set('search', searchQuery);
    searchUrl.searchParams.set('page', String(pageNum));
    this.logger.info(`Forging video URL: ${searchUrl.href}`);
    return searchUrl.href;
  }

  getGifSearchUrl(query, page) {
    const pageNum = Math.max(1, page || 1);
    const searchQuery = encodeURIComponent(query.trim().replace(/\s+/g, '+'));
    const searchUrl = new URL('/gifs/search', this.baseUrl);
    searchUrl.searchParams.set('search', searchQuery);
    searchUrl.searchParams.set('page', String(pageNum));
    this.logger.info(`Forging GIF URL: ${searchUrl.href}`);
    return searchUrl.href;
  }

  parseResults($, htmlData, options) {
    const { isMock } = options;
    this.logger.debug(`Parsing results for query: "${options.query}", type: "${options.type}", isMock: ${isMock}`);

    if (!isMock) {
        // Check for common indicators of no results or a block page
        const noResultsText = $('div.no-results-message, p.no-results').text();
        if (noResultsText.length > 0) {
            this.logger.warn(`No results found or block page detected for query: "${options.query}". Message: ${noResultsText.trim().substring(0, 100)}`);
            return [];
        }

        // Check for Cloudflare or other common block page elements
        if ($('#cf-wrapper').length > 0 || $('body:contains("Attention Required!")').length > 0) {
            this.logger.error(`Cloudflare or similar block page detected for query: "${options.query}".`);
            return [];
        }
    }

    return options.type === 'gifs'
      ? this.parseGifResults($, options)
      : this.parseVideoResults($, options);
  }

  parseVideoResults($, options) {
    const results = [];
    const videoItems = $('li.pcVideoListItem, li.videoBox, div.videoWrapper');
    this.logger.debug(`Found ${videoItems.length} potential video items.`);

    if (!videoItems.length) {
      this.logger.warn(`No videos found for query: "${options.query}"`);
      return [];
    }

    videoItems.each((i, el) => {
      const item = $(el);
      const link = item.find('a[href*="/view_video.php"]').first();
      const url = link.attr('href');
      const title = sanitizeText(item.find('span.title a').text() || item.find('img').attr('alt'));

      if (!title || !url) {
        this.logger.debug(`Skipping video item ${i}: missing title or URL.`);
        return;
      }

      const idMatch = url.match(ID_PATTERN);
      const id = idMatch ? idMatch[1] : null;
      if (!id) {
        this.logger.warn(`Could not extract ID from video URL: ${url}`);
        return;
      }

      const duration = item.find('var.duration').text()?.trim();
      const img = item.find('img[data-mediumthumb]').first();
      const thumbnail = img.attr('data-mediumthumb')?.trim() || img.attr('src')?.trim();
      const preview = extractPreview($, item, this.name, this.baseUrl);

      results.push({
        id,
        title,
        url: makeAbsolute(url, this.baseUrl),
        duration: duration || undefined,
        thumbnail: makeAbsolute(thumbnail, this.baseUrl),
        preview_video: preview, // Already absolute
        source: this.name,
        type: 'videos'
      });
    });

    this.logger.info(`Parsed ${results.length} videos for query: "${options.query}"`);
    return results;
  }

  parseGifResults($, options) {
    const results = [];
    const gifItems = $('li.gifVideoBlock'); // Selector for GIF items
    this.logger.debug(`Found ${gifItems.length} potential GIF items.`);

    if (!gifItems.length) {
      this.logger.warn(`No GIFs found for query: "${options.query}"`);
      return [];
    }

    gifItems.each((i, el) => {
      const item = $(el);
      const link = item.find('a').first();
      const url = link.attr('href');
      const title = sanitizeText(link.attr('title') || item.find('.gifTooltip__title').text());

      if (!title || !url) {
        this.logger.debug(`Skipping GIF item ${i}: missing title or URL.`);
        return;
      }

      const idMatch = url.match(/gif\/(\d+)/); // e.g., /gif/12345
      const id = idMatch ? idMatch[1] : null;
      if (!id) {
        this.logger.warn(`Could not extract ID from GIF URL: ${url}`);
        return;
      }

      const img = item.find('img').first();
      const thumbnail = img.attr('src');
      const preview = item.find('video.gifTooltip__video source[type="video/mp4"]').attr('src');

      results.push({
        id,
        title,
        url: makeAbsolute(url, this.baseUrl),
        thumbnail: makeAbsolute(thumbnail, this.baseUrl),
        preview_video: makeAbsolute(preview, this.baseUrl),
        source: this.name,
        type: 'gifs'
      });
    });

    this.logger.info(`Parsed ${results.length} GIFs for query: "${options.query}"`);
    return results;
  }
}

module.exports = PornhubDriver;
