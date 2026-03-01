'use strict'

const abstractMethodFactory = require('./abstractMethodFactory')
const { makeAbsolute, extractPreview, sanitizeText } = require('../modules/driver-utils')

/**
 * @core/VideoMixin.js
 * @description Mixin that adds video search functionality to a driver module.
 * Drivers using this mixin must implement `getVideoSearchUrl`.
 */
module.exports = function VideoMixin(BaseClass) {
  const WithVideoFeatures = class extends BaseClass {
    /**
     * Indicates if this driver supports video searches.
     * Concrete drivers should override this method to return `true`.
     * @returns {boolean}
     */
    hasVideoSupport() {
      return false // Default to false; concrete drivers must explicitly set to true.
    }

    /**
     * Maps raw video data from a Cheerio element into a standardized MediaResult format.
     * @param {import('cheerio').Cheerio<import('cheerio').Element>} item - The Cheerio element for the video item.
     * @param {import('cheerio').CheerioAPI} $ - The Cheerio instance.
     * @param {string} sourceName - The name of the driver/source.
     * @param {string} baseUrl - The base URL of the platform.
     * @returns {object|undefined} A standardized MediaResult object or undefined if essential data is missing.
     */
    mapVideoResult(item, $, sourceName, baseUrl) {
      const link = item.find('a').first();
      let url = link.attr('href');
      let id = url ? (url.match(/viewkey=([a-zA-Z0-9]+)/) || [])[1] : null; // Common pattern for video IDs
      let title = link.attr('title') || item.find('span.title').text().trim() || item.attr('data-video-title');
      let thumbnail = item.find('img').first().attr('data-src') || item.find('img').first().attr('src');
      const duration = item.find('var.duration, span.duration').text().trim() || 'N/A';

      // Sanitize and make absolute
      title = sanitizeText(title);
      url = makeAbsolute(url, baseUrl);
      thumbnail = makeAbsolute(thumbnail, baseUrl);

      // Extract preview video using the utility function
      const preview_video = extractPreview($, item, sourceName, baseUrl);

      if (!id || !url || !title || !thumbnail) {
        this.logger.warn(`[${sourceName}] Skipping malformed video result: ID=${id}, URL=${url}, Title=${title}, Thumbnail=${thumbnail}`);
        return undefined;
      }

      return {
        id,
        title,
        url,
        thumbnail,
        duration,
        preview_video,
        source: sourceName,
        type: 'videos'
      };
    }
  }

  // Use the factory to add the abstract method 'getVideoSearchUrl'.
  // This enforces that any class using this mixin must implement the method.
  return abstractMethodFactory(WithVideoFeatures, ['getVideoSearchUrl'])
}
