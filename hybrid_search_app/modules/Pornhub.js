'use strict';






const _possibleConstructorReturn = require('@babel/runtime/helpers/possibleConstructorReturn');
const _inherits = require('@babel/runtime/helpers/inherits');
const { VideoMixin, AbstractModule } = require('../core/index');
const config = require('../config');
const { makeAbsolute, extractPreview, logger } = require('../core/utils');

const BASE_URL = 'https://www.pornhub.com';
const NAME = 'pornhub';
const SEARCH_PATH = '/video/search';
const VIDEO_PATTERN = '/view_video.php';
const ID_PATTERN = /viewkey=([\w-]+)/;

if (!AbstractModule?.with) {
  throw new Error('AbstractModule.with is undefined');
}

/**
 * @typedef {Object} MediaResult
 * @property {string} id
 * @property {string} title
 * @property {string} url
 * @property {string} [preview_video]
 * @property {string} [thumbnail]
 * @property {string} [duration]
 */

/**
 * @class Pornhub
 * @extends AbstractModule
 * @mixes VideoMixin
 */
const Pornhub = (function (_AbstractModule$with) {
  (0, _inherits)(Pornhub, _AbstractModule$with);

  function Pornhub() {
    (0, _classCallCheck)(this, Pornhub);
    return (0, _possibleConstructorReturn)(this, (Pornhub.__proto__ || (0, _getPrototypeOf)(Pornhub)).apply(this, arguments));
  }

  (0, _createClass)(Pornhub, [{
    key: 'videoUrl',
    value: function videoUrl(page) {
      if (!this.query) {
        throw new Error(`pornhub: Search query is not set`);
      }
      const searchUrl = new URL(SEARCH_PATH, BASE_URL);
      searchUrl.searchParams.set('search', encodeURIComponent(this.query.trim().replace(/\s+/g, ' ')));
      const pageNum = page !== undefined ? page : this.firstpage;
      searchUrl.searchParams.set(config.drivers[NAME].pageParam, String(pageNum + 1));
      logger.info(`Forging video URL for pornhub`, { url: searchUrl.href });
      return searchUrl.href;
    }
  }, {
    key: 'videoParser',
    value: function videoParser($) {
      // IMPORTANT: Verify selectors using browser DevTools (Inspect Element on https://www.pornhub.com/video/search?search=test).
      // These are speculative and may need adjustment based on live HTML structure.
      const selectors = [
        'li.pcVideoListItem',
        'li.videoBox',
        'div.videoWrapper'
      ];
      const videoItems = selectors.reduce((items, sel) => items.length ? items : $(sel), $([]));
      if (!videoItems.length) {
        logger.warn(`No videos found for pornhub`, { selectors });
        return [];
      }

      const results = [];
      videoItems.each((i, el) => {
        const item = $(el);
        const link = item.find('a[href*="/view_video.php"]').first();
        const title = item.find('span.title a').text()?.trim() ||
                      item.find('img').attr('alt')?.trim();
        const url = link.attr('href');

        if (!title || !url || !url.includes('/view_video.php')) {
          logger.warn(`Skipping video ${i} for pornhub: invalid data`, { title, url });
          return;
        }

        const duration = item.find('var.duration').text()?.trim();
        const img = item.find('img[data-mediumthumb]').first();
        const thumbnail = img.attr('data-mediumthumb')?.trim() || img.attr('src')?.trim();
        const preview = extractPreview($, item, 'pornhub');

        const idMatch = url.match(ID_PATTERN);
        const id = idMatch ? idMatch[1] : url;

        if (i < 1) {
          // Uncomment for debugging: console.log(item.html());
          logger.info(`Parsed video ${i} for pornhub`, { title, url, preview });
        }

        results.push({
          id: id || 'N/A',
          title: title || 'Untitled',
          url: makeAbsolute(url, BASE_URL),
          duration: duration || 'N/A',
          thumbnail: makeAbsolute(thumbnail, BASE_URL),
          preview_video: makeAbsolute(preview, BASE_URL)
        });
      });

      logger.info(`Parsed ${results.length} videos for pornhub`);
      return results;
    }
  }, {
    key: 'name',
    get: function get() {
      return NAME;
    }
  }, {
    key: 'firstpage',
    get: function get() {
      return config.drivers[NAME].firstPage;
    }
  }]);
  return Pornhub;
})(AbstractModule.with(VideoMixin));

exports.default = Pornhub;
module.exports = exports['default'];
