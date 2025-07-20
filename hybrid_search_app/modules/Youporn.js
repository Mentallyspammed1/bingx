'use strict';

// Core module and mixins
const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');

const { logger, makeAbsolute, extractPreview, sanitizeText } = require('./driver-utils.js');

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
  get supportsVideos() { return true; }
  get supportsGifs() { return false; } // Explicitly false

  getVideoSearchUrl(query, page) {
    const currentQuery = query || this.query;
    if (!currentQuery || typeof currentQuery !== 'string' || currentQuery.trim() === '') {
      throw new Error('YoupornDriver: Search query is not set or is empty for video search.');
    }
    const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
    const searchUrl = new URL('/search/', this.baseUrl);
    searchUrl.searchParams.set('query', sanitizeText(currentQuery));
    if (pageNumber > 1) {
        searchUrl.searchParams.set('page', String(pageNumber));
    }
    logger.debug(`[${this.name}] Generated video URL: ${searchUrl.href}`);
    return searchUrl.href;
  }

  parseResults($, htmlOrJsonData, parserOptions) {
    if (!$) {
        logger.error(`[${this.name}] Cheerio object ($) is null. Expecting HTML.`);
        return [];
    }

    const results = [];
    const { type, sourceName } = parserOptions;

    const itemSelector = 'div.video-box';

    $(itemSelector).each((i, el) => {
        const item = $(el);
        const videoId = item.attr('data-video-id');
        const titleLink = item.find('a.video-box-image');
        const title = sanitizeText(item.find('div.video-title-wrapper span').text());
        const pageUrl = titleLink.attr('href');
        const durationText = sanitizeText(item.find('div.duration').text());
        const imgElement = item.find('img.video-box-image__image');
        const thumbnailUrl = imgElement.attr('src');

        if (!pageUrl || !title || !videoId) {
            logger.warn(`[${this.name}] Item ${i} (${type}): Skipping. Missing: ${!pageUrl?'URL ':''}${!title?'Title ':''}${!videoId?'ID ':''}`);
            return;
        }

        const previewVideoUrl = extractPreview($, item, this.name, this.baseUrl);
        const absoluteUrl = makeAbsolute(pageUrl, this.baseUrl);
        const absoluteThumbnail = makeAbsolute(thumbnailUrl, this.baseUrl);

        results.push({
            id: videoId,
            title: title,
            url: absoluteUrl,
            thumbnail: absoluteThumbnail || '',
            duration: durationText || 'N/A',
            preview_video: previewVideoUrl || '',
            source: sourceName,
            type: type
        });
    });

    this.logger.debug(`Parsed ${results.length} ${type} items.`);
    return results;
  }
}

module.exports = YoupornDriver;
