'use strict';

// Core module and mixins
const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const GifMixin = require('../core/GifMixin.js');

// Utility functions for logging, URL handling, and preview extraction
const { logger, makeAbsolute, extractPreview, sanitizeText } = require('./driver-utils.js');

// Base URL for Xhamster.com
const XHAMSTER_BASE_URL = 'https://www.xhamster.com';
const XHAMSTER_VIDEO_SEARCH_PATH = '/videos/search/'; // Path for video search
const XHAMSTER_GIF_SEARCH_PATH = '/gifs/search/'; // Path for GIF search
const DRIVER_NAME = 'Xhamster';

// Apply mixins to AbstractModule.
const BaseXhamsterClass = AbstractModule.with(VideoMixin, GifMixin);

/**
 * @class XhamsterDriver
 * @classdesc Driver for fetching video and GIF content from Xhamster.
 * This driver implements both `VideoMixin` and `GifMixin` methods.
 * It relies on HTML scraping, making it susceptible to website layout changes.
 */
class XhamsterDriver extends BaseXhamsterClass {
  /**
   * Constructs a new Xhamster driver instance.
   * @param {object} [options={}] - Options for the driver, passed to AbstractModule.
   */
  constructor(options = {}) {
    super(options);
    logger.debug(`[${DRIVER_NAME}] Initialized.`);
  }

  /**
   * Gets the name of the driver.
   * @type {string}
   * @readonly
   */
  get name() {
    return DRIVER_NAME;
  }

  /**
   * Gets the base URL for the Xhamster platform.
   * @type {string}
   * @readonly
   */
  get baseUrl() {
    return XHAMSTER_BASE_URL;
  }

  /**
   * Indicates if this driver supports video searches.
   * @returns {boolean}
   */
  hasVideoSupport() {
    return true;
  }

  /**
   * Indicates if this driver supports GIF searches.
   * @returns {boolean}
   */
  hasGifSupport() {
    return true;
  }

  /**
   * Constructs the URL for searching videos on Xhamster.
   * Xhamster's video search URL format is typically `/videos/search/<query>/<page>`.
   *
   * @param {string} query - The search query.
   * @param {number} page - The page number (0-indexed).
   * @returns {string} The full URL for the video search.
   */
  getVideoSearchUrl(query, page) {
    const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
    const searchUrl = new URL(`/search/${encodeURIComponent(query.trim())}`, this.baseUrl);
    searchUrl.searchParams.set('page', String(pageNumber));
    logger.debug(`[${this.name}] Generated video search URL: ${searchUrl.href}`);
    return searchUrl.href;
  }

  /**
   * Constructs the URL for searching GIFs on Xhamster.
   * Xhamster's GIF search URL format is typically `/gifs/search/<query>/<page>`.
   *
   * @param {string} query - The search query.
   * @param {number} page - The page number (0-indexed).
   * @returns {string} The full URL for the GIF search.
   */
  getGifSearchUrl(query, page) {
    const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
    const searchUrl = new URL(`/search/gif/${encodeURIComponent(query.trim())}`, this.baseUrl);
    searchUrl.searchParams.set('page', String(pageNumber));
    logger.debug(`[${this.name}] Generated GIF search URL: ${searchUrl.href}`);
    return searchUrl.href;
  }

  /**
   * Parses the HTML content from Xhamster search results pages (both videos and GIFs).
   * This method fulfills the `parseResults` contract defined in `Pornsearch.js`.
   *
   * @param {import('cheerio').CheerioAPI} $ - Cheerio instance loaded with the HTML content.
   * @param {string | object} rawData - The raw HTML string. (JSON is not expected for Xhamster scraping).
   * @param {object} options - Options containing search context.
   * @param {'videos'|'gifs'} options.type - The type of media being parsed ('videos' or 'gifs').
   * @param {string} options.sourceName - The name of the source (e.g., 'Xhamster').
   * @returns {Array<import('../Pornsearch').MediaResult>} An array of structured media results.
   */
  parseResults($, rawData, options) {
    const { type, sourceName } = options;
    const results = [];

    if (!$) {
      logger.error(`[${sourceName}] parseResults received null Cheerio instance. Expected HTML for parsing.`);
      return [];
    }

    logger.info(`[${sourceName}] Parsing ${type} results...`);

    if (type === 'videos') {
      const videoItems = $('div.video-thumb');

      if (!videoItems.length) {
        logger.warn(`[${sourceName}] No video items found with current selectors. Page structure may have changed.`);
        return [];
      }

      videoItems.each((index, element) => {
        const item = $(element);

        const linkElement = item.find('a.video-thumb__image-container').first();
        let videoUrl = linkElement.attr('href');
        let title = item.find('a.video-thumb__name').text();

        let videoId = item.attr('data-video-id');
        
        const thumbElement = item.find('img.video-thumb__image').first();
        let thumbnailUrl = thumbElement.attr('src');

        let duration = item.find('.video-thumb__duration').text();
        duration = sanitizeText(duration);

        const previewVideoUrl = extractPreview($, item, sourceName, this.baseUrl);

        if (!videoUrl || !title || !thumbnailUrl || !videoId) {
          logger.warn(`[${sourceName}] Skipping malformed video item (missing essential data):`, { title, videoUrl, thumbnailUrl, videoId, index });
          return;
        }

        videoUrl = makeAbsolute(videoUrl, this.baseUrl);
        thumbnailUrl = makeAbsolute(thumbnailUrl, this.baseUrl);

        if (!videoUrl || !thumbnailUrl) { // Re-validate after making absolute
           logger.warn(`[${sourceName}] Skipping video item "${title}": Failed to resolve absolute URLs.`);
           return;
        }

        results.push({
          id: videoId,
          title: title,
          url: videoUrl,
          duration: duration,
          thumbnail: thumbnailUrl,
          preview_video: previewVideoUrl,
          source: sourceName,
          type: 'videos'
        });
      });
      // --- END SPECULATIVE VIDEO CSS SELECTORS ---

    } else if (type === 'gifs') {
      // --- SPECULATIVE GIF CSS SELECTORS - VERIFY THESE! ---
      // Common selectors for GIF items on Xhamster search results.
      // Often similar to video items, but might have different classes or structures.
      // const gifItems = $('div.gif-item, li.gif-thumb, div.gif-box'); // Original
      const gifItems = $('div.photo-thumb, div.gif-thumb, div.gallery-thumb'); // Updated based on xhamster_gifs_page1.html

      if (!gifItems.length) {
        logger.warn(`[${sourceName}] No GIF items found with current selectors. Page structure may have changed.`);
        return [];
      }

      gifItems.each((index, element) => {
        const item = $(element);

        // GIF Page URL: often an `<a>` tag wrapping the GIF.
        // const linkElement = item.find('a.gif-link, a[href*="/gifs/"]').first(); // Original
        const linkElement = item.find('a[href]').first(); // Simplified to find any link with href
        let gifPageUrl = linkElement.attr('href');

        // GIF ID: often part of the URL path or a data attribute.
        let gifId = gifPageUrl ? gifPageUrl.match(/-(\d+)$/)?.[1] || gifPageUrl.split('/').pop() : null;
        if (!gifId) gifId = item.attr('data-id'); // Fallback to data-id

        // GIF Title: usually `alt` or `title` of the image, or a text element.
        let title = item.find('img').attr('alt') || linkElement.attr('title') || item.find('.title, h3 a').text();
        title = sanitizeText(title);

        // Animated GIF URL (the actual .gif file) or a video preview (mp4/webm)
        // Use extractPreview, as GIFs often have video previews or are directly linked.
        const animatedGifUrl = extractPreview($, item, sourceName, this.baseUrl);

        // Static Thumbnail URL: often `src` or `data-src` of an `<img>` tag, or a `poster` attribute.
        const thumbElement = item.find('img[src], img[data-src]').first();
        let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src') || item.attr('data-poster');

        // --- Data validation and normalization ---
        if (!gifPageUrl || !title || !animatedGifUrl || !thumbnailUrl || !gifId) {
          logger.warn(`[${sourceName}] Skipping malformed GIF item (missing essential data):`, { title, gifPageUrl, animatedGifUrl, thumbnailUrl, gifId, index });
          return;
        }

        // Make URLs absolute
        gifPageUrl = makeAbsolute(gifPageUrl, this.baseUrl);
        thumbnailUrl = makeAbsolute(thumbnailUrl, this.baseUrl);

        if (!gifPageUrl || !thumbnailUrl) { // Re-validate after making absolute
           logger.warn(`[${sourceName}] Skipping GIF item "${title}": Failed to resolve absolute URLs.`);
           return;
        }

        results.push({
          id: gifId,
          title: title,
          url: gifPageUrl,
          thumbnail: thumbnailUrl,
          preview_video: animatedGifUrl, // For GIFs, this is usually the animated GIF or a video preview
          source: sourceName,
          type: 'gifs'
        });
      });
      // --- END SPECULATIVE GIF CSS SELECTORS ---
    }

    logger.info(`[${sourceName}] Parsed ${results.length} ${type} results.`);
    return results;
  }
}

module.exports = XhamsterDriver;