'use strict';

const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const GifMixin = require('../core/GifMixin.js');
const { logger, makeAbsolute, extractPreview, sanitizeText } = require('./driver-utils.js');

// Base URL for Motherless.com
const MOTHERLESS_BASE_URL = 'https://motherless.com';
const MOTHERLESS_VIDEO_SEARCH_PATH = '/videos/search/'; // Path for video search
const MOTHERLESS_IMAGE_SEARCH_PATH = '/images/search/'; // Motherless uses /images for static images and GIFs
const DRIVER_NAME = 'Motherless';

// Apply mixins to AbstractModule.
const BaseMotherlessClass = AbstractModule.with(VideoMixin, GifMixin);

/**
 * @class MotherlessDriver
 * @classdesc Driver for fetching video and GIF content from Motherless.
 * This driver implements both `VideoMixin` and `GifMixin` methods.
 * It relies on HTML scraping, making it susceptible to website layout changes.
 */
class MotherlessDriver extends BaseMotherlessClass {
  /**
   * Constructs a new Motherless driver instance.
   * @param {object} [options={}] - Options for the driver, passed to AbstractModule.
   */
  constructor(options = {}) {
    super(options);
    logger.debug(`[${this.name}] Initialized.`);
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
   * Gets the base URL for the Motherless platform.
   * @type {string}
   * @readonly
   */
  get baseUrl() {
    return MOTHERLESS_BASE_URL;
  }

  /**
   * Gets the default starting page number for searches (1-indexed for Motherless).
   * @type {number}
   * @readonly
   */
  get firstpage() {
    return 1; // Motherless typically uses 1-indexed pagination
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
   * Motherless categorizes GIFs under 'images', so we'll search the image section.
   * @returns {boolean}
   */
  hasGifSupport() {
    return true;
  }

  /**
   * Constructs the URL for searching videos on Motherless.
   * Motherless's video search URL format is typically `/videos/search/<query>/page<page>`.
   *
   * @param {string} query - The search query.
   * @param {number} page - The page number (1-indexed).
   * @returns {string} The full URL for the video search.
   */
  getVideoSearchUrl(query, page) {
    const encodedQuery = encodeURIComponent(query.trim());
    const pageNumber = Math.max(1, page || this.firstpage); // Ensure page is at least 1

    // Example: https://motherless.com/videos/search/anal+sex/page2
    const url = new URL(`${MOTHERLESS_VIDEO_SEARCH_PATH}${encodedQuery}/page${pageNumber}`, this.baseUrl);
    logger.debug(`[${this.name}] Generated video search URL: ${url.href}`);
    return url.href;
  }

  /**
   * Constructs the URL for searching GIFs on Motherless.
   * Motherless categorizes GIFs under images, so we use the image search path.
   * The URL format is typically `/images/search/<query>/page<page>`.
   *
   * @param {string} query - The search query.
   * @param {number} page - The page number (1-indexed).
   * @returns {string} The full URL for the GIF search.
   */
  getGifSearchUrl(query, page) {
    const encodedQuery = encodeURIComponent(query.trim());
    const pageNumber = Math.max(1, page || this.firstpage); // Ensure page is at least 1

    // Example: https://motherless.com/images/search/cat+gif/page1
    const url = new URL(`${MOTHERLESS_IMAGE_SEARCH_PATH}${encodedQuery}/page${pageNumber}`, this.baseUrl);
    logger.debug(`[${this.name}] Generated GIF search URL: ${url.href}`);
    return url.href;
  }

  /**
   * Parses the HTML content from Motherless search results pages (both videos and GIFs/Images).
   * This method fulfills the `parseResults` contract defined in `Pornsearch.js`.
   *
   * @param {import('cheerio').CheerioAPI} $ - Cheerio instance loaded with the HTML content.
   * @param {string | object} rawData - The raw HTML string. (JSON is not expected for Motherless scraping).
   * @param {object} options - Options containing search context.
   * @param {'videos'|'gifs'} options.type - The type of media being parsed ('videos' or 'gifs').
   * @param {string} options.sourceName - The name of the source (e.g., 'Motherless').
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

    // Common selector for all content items (videos, images, GIFs)
    // Motherless often uses `div.content-item` or `div.thumb-container`
    const contentItems = $('div.content-item, div.thumb-container');

    if (!contentItems.length) {
      logger.warn(`[${sourceName}] No content items found with current selectors. Page structure may have changed.`);
      return [];
    }

    contentItems.each((index, element) => {
      const item = $(element);

      // Link to the content page (often wraps the thumbnail)
      const linkElement = item.find('a[href]').first();
      let contentUrl = linkElement.attr('href');

      // Content ID: often part of the URL path (e.g., /videos/1234567) or a data attribute.
      let contentId = contentUrl ? contentUrl.split('/').pop() : null;
      if (!contentId) contentId = item.attr('data-id'); // Fallback to data-id if available

      // Title: often in `alt` or `title` of image, or a dedicated text element.
      let title = item.find('img').attr('alt') || linkElement.attr('title') || item.find('.title, h3 a, .caption').text();
      title = sanitizeText(title);

      // Thumbnail URL: `src` or `data-src` of an `<img>` tag.
      const thumbElement = item.find('img[src], img[data-src]').first();
      let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');

      // Duration (primarily for videos): often in a `<span>` with class like `duration` or `time`.
      let duration = item.find('.duration, .time').text();
      duration = sanitizeText(duration);

      // Preview Video URL / Animated GIF URL: Use `extractPreview` utility.
      // Motherless often uses animated thumbnails (short videos) for both videos and GIFs.
      const previewVideoUrl = extractPreview($, item, sourceName, this.baseUrl);

      // --- Data validation and normalization ---
      if (!contentUrl || !title || !thumbnailUrl || !contentId) {
        logger.warn(`[${sourceName}] Skipping malformed item (missing essential data):`, { title, contentUrl, thumbnailUrl, contentId, index });
        return; // Skip this item if essential data is missing
      }

      // Make URLs absolute using the driver's base URL
      contentUrl = makeAbsolute(contentUrl, this.baseUrl);
      thumbnailUrl = makeAbsolute(thumbnailUrl, this.baseUrl);

      if (!contentUrl || !thumbnailUrl) { // Re-validate after making absolute
         logger.warn(`[${sourceName}] Skipping item "${title}": Failed to resolve absolute URLs.`);
         return;
      }

      // Determine type more precisely for Motherless, as /images can contain both static and animated.
      // If the search type is 'gifs' and a valid preview video URL is found, assume it's a GIF.
      // If search type is 'videos', assume it's a video.
      let finalType = type;
      if (type === 'gifs' && !previewVideoUrl) {
          // If searching for GIFs but no animated preview is found, it's likely a static image.
          // We should skip it or classify it differently if the orchestrator supports 'images'.
          // For now, we'll skip it if it doesn't have a preview for a GIF search.
          logger.debug(`[${sourceName}] Skipping image item "${title}" during GIF search: No animated preview found.`);
          return;
      }

      results.push({
        id: contentId,
        title: title,
        url: contentUrl,
        duration: finalType === 'videos' ? duration : undefined, // Duration only for videos
        thumbnail: thumbnailUrl,
        preview_video: previewVideoUrl,
        source: sourceName,
        type: finalType // Use the determined type
      });
    });

    logger.info(`[${sourceName}] Parsed ${results.length} ${type} results.`);
    return results;
  }
}

module.exports = MotherlessDriver;