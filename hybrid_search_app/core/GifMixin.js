'use strict'

const abstractMethodFactory = require('./abstractMethodFactory')
const { makeAbsolute, extractPreview, sanitizeText } = require('../modules/driver-utils')

/**
 * @file GifMixin.js
 * A mixin factory that enhances a base class with abstract GIF-related methods.
 * Classes applying this mixin are contractually obligated to implement `getGifSearchUrl()`
 * and rely on `parseResults()` for GIF parsing capabilities.
 */
module.exports = function GifMixin(BaseClass) {
  const WithGifFeatures = class extends BaseClass {
    /**
     * Indicates if this driver supports GIF searches.
     * Concrete drivers should override this method to return `true`.
     * @returns {boolean}
     */
    hasGifSupport() {
      return false // Default to false; concrete drivers must explicitly set to true.
    }

    /**
     * Maps raw GIF data from a Cheerio element into a standardized MediaResult format.
     * @param {import('cheerio').Cheerio<import('cheerio').Element>} item - The Cheerio element for the GIF item.
     * @param {import('cheerio').CheerioAPI} $ - The Cheerio instance.
     * @param {string} sourceName - The name of the driver/source.
     * @param {string} baseUrl - The base URL of the platform.
     * @returns {object|undefined} A standardized MediaResult object or undefined if essential data is missing.
     */
    mapGifResult(item, $, sourceName, baseUrl) {
      const link = item.find('a').first();
      let pageUrl = link.attr('href');
      let id = item.attr('data-id') || (pageUrl ? pageUrl.match(/\/(\d+)\//) : null)?.[1];
      let title = item.find('img').attr('alt') || link.attr('title') || 'Untitled GIF';
      let thumbnail = item.find('img').attr('data-src') || item.find('img').attr('src');

      // Sanitize and make absolute
      title = sanitizeText(title);
      pageUrl = makeAbsolute(pageUrl, baseUrl);
      thumbnail = makeAbsolute(thumbnail, baseUrl);

      // Extract preview video using the utility function (which should handle GIFs too)
      const preview_video = extractPreview($, item, sourceName, baseUrl);

      if (!id || !pageUrl || !title || !thumbnail) {
        this.logger.warn(`[${sourceName}] Skipping malformed GIF result: ID=${id}, URL=${pageUrl}, Title=${title}, Thumbnail=${thumbnail}`);
        return undefined;
      }

      return {
        id,
        title,
        url: pageUrl,
        thumbnail,
        preview_video,
        source: sourceName,
        type: 'gifs'
      };
    }
  }

  // Use the factory to add the abstract method 'getGifSearchUrl'.
  // This enforces that any class using this mixin must implement the method.
  return abstractMethodFactory(WithGifFeatures, ['getGifSearchUrl'])
}
