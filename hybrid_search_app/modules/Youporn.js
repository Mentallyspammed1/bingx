'use strict';

// Core module and mixins
const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
// const GifMixin = require('../core/GifMixin.js'); // Youporn does not support GIFs

const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL_CONST = 'https://www.youporn.com';
const DRIVER_NAME_CONST = 'Youporn';

// Apply mixins to AbstractModule
let BaseYoupornClass = AbstractModule;
BaseYoupornClass = VideoMixin(BaseYoupornClass);
// If GifMixin were used: BaseYoupornClass = GifMixin(BaseYoupornClass);

class YoupornDriver extends BaseYoupornClass {
  constructor(options = {}) {
    super(options);
    logger.debug(`[${this.name}] Initialized.`);
  }

  get name() { return DRIVER_NAME_CONST; }
  get baseUrl() { return BASE_URL_CONST; }
  hasVideoSupport() { return true; }
  hasGifSupport() { return false; } // Explicitly false
  get firstpage() { return 1; }

  getVideoSearchUrl(query, page) {
    let currentQuery = query || this.query;
    if (!currentQuery || typeof currentQuery !== 'string' || currentQuery.trim() === '') {
          throw new Error('YoupornDriver: Search query is not set or is empty for video search.');
    }
    const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
    const searchUrl = new URL('/search/', this.baseUrl);
    searchUrl.searchParams.set('query', sanitizeText(currentQuery));
    searchUrl.searchParams.set('page', String(pageNumber));
    logger.debug(`[${this.name}] Generated videoUrl: ${searchUrl.href}`);
    return searchUrl.href;
  }

  // getGifSearchUrl is not needed as supportsGifs is false.
  // If called, AbstractMethodEnforcer (if active in mixin) would throw.

  parseResults($, htmlOrJsonData, parserOptions) {
    const { type, sourceName } = parserOptions;
    const results = [];
    if (!$) {
      logger.error(`[${this.name} Parser] Cheerio instance is null or undefined.`);
      return [];
    }

    // Selectors based on mock HTML for youporn_videos_page1.html
    const videoItems = $('div.video-box, li.video-item, div.thumbnail-video-container');

    if (!videoItems || videoItems.length === 0) {
      logger.warn(`[${this.name} Parser] No video items found with selectors for type '${type}'.`);
      return [];
    }

    videoItems.each((i, el) => {
      const item = $(el);
      const linkElement = item.find('a.video-box-link, a.video-link, a.video-thumb-link').first();
      let relativeUrl = linkElement.attr('href');
      let titleText = sanitizeText(linkElement.attr('title')?.trim() ||
                      item.find('.video-title, .title-text, .title, .videoDetails > p.video-title, .title-wrapper > p.title').first().text()?.trim());

      let id = item.attr('data-id');
      if (!id && relativeUrl) {
          const idMatch = relativeUrl.match(/\/watch\/(\d+)\//);
          if (idMatch && idMatch[1]) id = idMatch[1];
      }

      const imgElement = item.find('img.video-thumbnail, img.thumb, img.video-thumb-img').first();
      let staticThumbnailUrl = imgElement.attr('data-src') || imgElement.attr('src');

      const durationText = sanitizeText(item.find('span.video-duration, span.duration-text, span.duration, span.time').first().text()?.trim());

      let animatedPreviewUrl = extractPreview(item, this.baseUrl);

      if (!titleText || !relativeUrl || !id) {
        logger.warn(`[${this.name} Parser] Item ${i}: Skipping due to missing title, URL, or ID. Title: ${titleText}, URL: ${relativeUrl}, ID: ${id}`);
        return;
      }

      const absoluteUrl = makeAbsolute(relativeUrl, this.baseUrl);
      const absoluteThumbnailUrl = makeAbsolute(staticThumbnailUrl, this.baseUrl);
      const finalPreviewVideoUrl = validatePreview(animatedPreviewUrl) ? animatedPreviewUrl : undefined;

      results.push({
        id: id,
        title: titleText,
        url: absoluteUrl,
        duration: durationText || 'N/A',
        thumbnail: absoluteThumbnailUrl || '',
        preview_video: finalPreviewVideoUrl || '',
        source: sourceName,
        type: type
      });
    });
    logger.debug(`[${this.name} Parser] Parsed ${results.length} items for type '${type}'.`);
    return results;
  }
}

module.exports = YoupornDriver;
