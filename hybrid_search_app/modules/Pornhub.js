'use strict';

// Core module and mixins
const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const GifMixin = require('../core/GifMixin.js');

// Utility functions for logging, URL handling, and preview extraction
const { logger, makeAbsolute, extractPreview, sanitizeText } = require('./driver-utils.js');

// Base URL for Pornhub.com
const PORNHUB_BASE_URL = 'https://www.pornhub.com';
const PORNHUB_VIDEO_SEARCH_PATH = '/video/search'; // Common path for video search
const PORNHUB_GIF_SEARCH_PATH = '/gifs/search'; // Common path for GIF search
const DRIVER_NAME = 'Pornhub';

// Apply mixins to AbstractModule.
const BasePornhubClass = AbstractModule.with(VideoMixin, GifMixin);

/**
 * @class PornhubDriver
 * @classdesc Driver for fetching video and GIF content from Pornhub.
 * This driver implements both `VideoMixin` and `GifMixin` methods.
 * It primarily relies on HTML scraping, making it susceptible to website layout changes.
 * **CSS selectors used are speculative and WILL REQUIRE LIVE VERIFICATION.**
 */
class PornhubDriver extends BasePornhubClass {
  /**
   * Constructs a new Pornhub driver instance.
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
   * Gets the base URL for the Pornhub platform.
   * @type {string}
   * @readonly
   */
  get baseUrl() {
    return PORNHUB_BASE_URL;
  }

  /**
   * Gets the default starting page number for searches (1-indexed for Pornhub).
   * @type {number}
   * @readonly
   */
  get firstpage() {
    return 1; // Pornhub typically uses 1-indexed pagination
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
   * Constructs the URL for searching videos on Pornhub.
   * Pornhub's video search URL format is typically `/video/search?search=<query>&page=<page>`.
   *
   * @param {string} query - The search query.
   * @param {number} page - The page number (1-indexed).
   * @returns {string} The full URL for the video search.
   */
  getVideoSearchUrl(query, page) {
    const encodedQuery = encodeURIComponent(query.trim());
    const pageNumber = Math.max(1, page || this.firstpage); // Ensure page is at least 1

    const url = new URL(PORNHUB_VIDEO_SEARCH_PATH, this.baseUrl);
    url.searchParams.set('search', encodedQuery);
    url.searchParams.set('page', String(pageNumber));

    logger.debug(`[${this.name}] Generated video search URL: ${url.href}`);
    return url.href;
  }

  /**
   * Constructs the URL for searching GIFs on Pornhub.
   * Pornhub's GIF search URL format is typically `/gifs/search?search=<query>&page=<page>`.
   *
   * @param {string} query - The search query.
   * @param {number} page - The page number (1-indexed).
   * @returns {string} The full URL for the GIF search.
   */
  getGifSearchUrl(query, page) {
    const encodedQuery = encodeURIComponent(query.trim());
    const pageNumber = Math.max(1, page || this.firstpage); // Ensure page is at least 1

    const url = new URL(PORNHUB_GIF_SEARCH_PATH, this.baseUrl);
    url.searchParams.set('search', encodedQuery);
    url.searchParams.set('page', String(pageNumber));

    logger.debug(`[${this.name}] Generated GIF search URL: ${url.href}`);
    return url.href;
  }

  /**
   * Parses the HTML content from Pornhub search results pages (both videos and GIFs).
   * This method fulfills the `parseResults` contract defined in `Pornsearch.js`.
   *
   * @param {import('cheerio').CheerioAPI} $ - Cheerio instance loaded with the HTML content.
   * @param {string | object} rawData - The raw HTML string. (JSON is not expected for Pornhub scraping).
   * @param {object} options - Options containing search context.
   * @param {'videos'|'gifs'} options.type - The type of media being parsed ('videos' or 'gifs').
   * @param {string} options.sourceName - The name of the source (e.g., 'Pornhub').
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
      // --- SPECULATIVE VIDEO CSS SELECTORS - VERIFY THESE! ---
      // Pornhub video items are often within a `div.phimage` or similar container.
      const videoItems = $('div.phimage, .video-item, .videoblock');

      if (!videoItems.length) {
        logger.warn(`[${sourceName}] No video items found with current selectors. Page structure may have changed.`);
        return [];
      }

      videoItems.each((index, element) => {
        const item = $(element);

        // Video URL: The `a` tag inside `div.phimage` often links to the video page.
        const linkElement = item.find('a[href*="/view_video.php"], a[href*="/video/"], a.link-videos').first();
        let videoUrl = linkElement.attr('href');

        // Video ID: Often extracted from the video URL (e.g., `viewkey=phXXXXX` or `/video/ID/`).
        let videoId = videoUrl ? videoUrl.match(/viewkey=([a-zA-Z0-9]+)/)?.[1] : null;
        if (!videoId && videoUrl) { // Fallback for other URL patterns
            const pathSegments = videoUrl.split('/');
            // Try to get ID from a numeric segment, e.g., /video/123456789/title
            videoId = pathSegments[pathSegments.length - 2];
            if (videoId && !/^\d+$/.test(videoId)) videoId = null; // Ensure it's numeric if from path
        }
        if (!videoId) videoId = item.attr('data-id'); // Fallback to data-id on container

        // Video Title: Often in `alt` or `title` of image, or a sibling text element.
        let title = linkElement.attr('title') || item.find('img').attr('alt') || item.find('.title, .video-title').text();
        title = sanitizeText(title);

        // Thumbnail URL: `src` or `data-src` of an `<img>` tag.
        const thumbElement = item.find('img[src], img[data-src]').first();
        let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
        // Discard known placeholder thumbnails
        if (thumbnailUrl && thumbnailUrl.includes('nothumb')) thumbnailUrl = undefined;

        // Duration: Typically a `span` or `var` with class `duration`.
        let duration = item.find('var.duration, span.duration').text();
        duration = sanitizeText(duration);

        // Preview Video URL: Use `extractPreview` utility. Pornhub often uses `data-mediabook` on `a` tag.
        const previewVideoUrl = extractPreview($, item, sourceName, this.baseUrl);

        // --- Data validation and normalization ---
        if (!videoUrl || !title || !thumbnailUrl || !videoId) {
          logger.warn(`[${sourceName}] Skipping malformed video item (missing essential data):`, { title, videoUrl, thumbnailUrl, videoId, index });
          return; // Skip this item if essential data is missing
        }

        // Make URLs absolute using the driver's base URL
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
      // Pornhub GIF items are often within `div.gifImageBlock` or similar.
      const gifItems = $('div.gifImageBlock, .gif-item, .gif-thumb');

      if (!gifItems.length) {
        logger.warn(`[${sourceName}] No GIF items found with current selectors. Page structure may have changed.`);
        return [];
      }

      gifItems.each((index, element) => {
        const item = $(element);

        // GIF Page URL: The `a` tag wrapping the GIF.
        const linkElement = item.find('a[href*="/gifs/"], a.link-gifs').first();
        let gifPageUrl = linkElement.attr('href');

        // GIF ID: Often part of the URL path (e.g., `/gifs/ID/`) or a data attribute.
        let gifId = gifPageUrl ? gifPageUrl.match(/\/gifs\/([a-zA-Z0-9]+)/)?.[1] : null;
        if (!gifId) gifId = item.attr('data-id'); // Fallback to data-id on container

        // GIF Title: Often in `alt` or `title` of image, or a sibling text element.
        let title = linkElement.attr('title') || item.find('img').attr('alt') || item.find('.title, .gif-title').text();
        title = sanitizeText(title);

        // Animated GIF URL (the actual .gif file or WebM/MP4 preview)
        // Use `extractPreview` here, as Pornhub GIFs often have video previews.
        const animatedGifUrl = extractPreview($, item, sourceName, this.baseUrl);

        // Static Thumbnail URL: Often `src` or `data-src` of an `<img>` tag, or a `poster` attribute.
        const thumbElement = item.find('img[src], img[data-src]').first();
        let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
        if (thumbnailUrl && thumbnailUrl.includes('nothumb')) thumbnailUrl = undefined; // Discard placeholders

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

module.exports = PornhubDriver;