'use strict';

// Core module and mixins
const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const GifMixin = require('../core/GifMixin.js');

const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL_CONST = 'https://www.sex.com';
const DRIVER_NAME_CONST = 'Sex.com';

// Apply mixins to AbstractModule
const BaseSexComClass = AbstractModule.with(VideoMixin, GifMixin);

class SexComDriver extends BaseSexComClass {
  constructor(options = {}) {
    super(options);
    logger.debug(`[${DRIVER_NAME_CONST}] Initialized.`);
  }

  get name() { return DRIVER_NAME_CONST; }
  get baseUrl() { return BASE_URL_CONST; }
  hasVideoSupport() { return true; }
  hasGifSupport() { return true; }
  get firstpage() { return 1; }

  getVideoSearchUrl(query, page) {
    let currentQuery = query || this.query;
    if (!currentQuery || typeof currentQuery !== 'string' || currentQuery.trim() === '') {
      throw new Error('[Sex.com Driver] Search query is not set or is empty for video search.');
    }
    const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
    const searchUrl = new URL('/search/videos', this.baseUrl);
    searchUrl.searchParams.set('query', sanitizeText(currentQuery));
    searchUrl.searchParams.set('page', String(pageNumber));
    logger.debug(`[${this.name}] Generated videoUrl: ${searchUrl.href}`);
    return searchUrl.href;
  }

  getGifSearchUrl(query, page) {
    let currentQuery = query || this.query;
    if (!currentQuery || typeof currentQuery !== 'string' || currentQuery.trim() === '') {
      throw new Error('[Sex.com Driver] Search query is not set or is empty for GIF search.');
    }
    const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
    const searchUrl = new URL('/search/gifs', this.baseUrl);
    searchUrl.searchParams.set('query', sanitizeText(currentQuery));
    searchUrl.searchParams.set('page', String(pageNumber));
    logger.debug(`[${this.name}] Generated gifUrl: ${searchUrl.href}`);
    return searchUrl.href;
  }

  parseResults($, htmlOrJsonData, parserOptions) {
    const { type, sourceName } = parserOptions;
    const results = [];
    if (!$) {
      logger.error(`[${this.name} Parser] Cheerio instance is null or undefined.`);
      return [];
    }

    const itemSelector = type === 'videos' ?
      'div.masonry_box.video, div.video_preview_box' :
      'div.masonry_box.gif, div.gif_preview_box';

    $(itemSelector).each((i, el) => {
      const item = $(el);

      const linkElement = item.find('a.image_wrapper, a.box_link, .video_shortlink_container a').first();
      let pageUrl = linkElement.attr('href');

      let title = sanitizeText(
          linkElement.attr('title')?.trim() ||
          item.find('p.title, h2.title, div.video_title').first().text()?.trim()
      );
      if (!title && item.find('p.title a').length) {
          title = sanitizeText(item.find('p.title a').first().text()?.trim() || item.find('p.title a').first().attr('title')?.trim());
      }
      if (!title && item.find('h2.title a').length) {
           title = sanitizeText(item.find('h2.title a').first().text()?.trim() || item.find('h2.title a').first().attr('title')?.trim());
      }

      let id = item.attr('data-id');
      if (!id && pageUrl) {
          const match = pageUrl.match(/\/(?:video|gifs|pin)\/(\d+)/);
          if (match && match[1]) id = match[1];
      }

      const imgElement = item.find('img.responsive_image, img.main_image').first();
      let thumbnailUrl = imgElement.attr('data-src') || imgElement.attr('src');

      const previewVideoUrl = extractPreview($, item, this.name, this.baseUrl);
      const durationText = type === 'videos' ? sanitizeText(item.find('span.duration, span.video_duration').text()?.trim()) : undefined;

      if (!pageUrl || !title || !id) {
        logger.warn(`[${this.name} Parser] Item ${i} (${type}): Skipping. Missing: ${!pageUrl?'URL ':''}${!title?'Title ':''}${!id?'ID ':''}`);
        return;
      }

      const absoluteUrl = makeAbsolute(pageUrl, this.baseUrl);
      const absoluteThumbnailUrl = makeAbsolute(thumbnailUrl, this.baseUrl);
      let finalPreviewVideoUrl = validatePreview(previewVideoUrl) ? previewVideoUrl : undefined;

       if (!finalPreviewVideoUrl && type === 'gifs' && absoluteThumbnailUrl?.toLowerCase().endsWith('.gif')) {
           finalPreviewVideoUrl = absoluteThumbnailUrl;
       }

      results.push({
        id: id,
        title: title,
        url: absoluteUrl,
        thumbnail: absoluteThumbnailUrl || '',
        duration: durationText || (type === 'videos' ? 'N/A' : undefined),
        preview_video: finalPreviewVideoUrl || '',
        source: sourceName,
        type: type
      });
    });
    logger.debug(`[${this.name} Parser] Parsed ${results.length} items for type '${type}'.`);
    return results;
  }
}

module.exports = SexComDriver;