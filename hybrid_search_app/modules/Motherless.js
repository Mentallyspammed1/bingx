'use strict';

// Core module and mixins
const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const GifMixin = require('../core/GifMixin.js');

const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL_CONST = 'https://motherless.com';
const DRIVER_NAME_CONST = 'Motherless';

// Apply mixins to AbstractModule
const BaseMotherlessClass = AbstractModule.with(VideoMixin, GifMixin);

class MotherlessDriver extends BaseMotherlessClass {
  constructor(options = {}) {
    super(options);
    logger.debug(`[${this.name}] Initialized.`);
  }

  get name() { return DRIVER_NAME_CONST; }
  get baseUrl() { return BASE_URL_CONST; }
  get supportsVideos() { return true; }
  get supportsGifs() { return true; }
  get firstpage() { return 1; }

  getVideoSearchUrl(query, page) {
    let currentQuery = query || this.query;
    if (!currentQuery || typeof currentQuery !== 'string' || currentQuery.trim() === '') {
      throw new Error('MotherlessDriver: Search query is not set or is empty for video search.');
    }
    const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
    const searchUrl = new URL(`/term/videos/${encodeURIComponent(sanitizeText(currentQuery))}`, this.baseUrl);
    searchUrl.searchParams.set('page', String(pageNumber));
    logger.debug(`[${this.name}] Generated videoUrl: ${searchUrl.href}`);
    return searchUrl.href;
  }

  getGifSearchUrl(query, page) {
    let currentQuery = query || this.query;
    if (!currentQuery || typeof currentQuery !== 'string' || currentQuery.trim() === '') {
      throw new Error('MotherlessDriver: Search query is not set or is empty for gif search.');
    }
    const pageNumber = Math.max(1, parseInt(page, 10) || this.firstpage);
    const searchUrl = new URL(`/term/images/${encodeURIComponent(sanitizeText(currentQuery))}`, this.baseUrl);
    searchUrl.searchParams.set('page', String(pageNumber));
    logger.debug(`[${this.name}] Generated gifUrl: ${searchUrl.href}`);
    return searchUrl.href;
  }

  parseResults($, rawHtmlOrJsonData, parserOptions) {
    const { type, sourceName } = parserOptions;
    const results = [];

    if (!$) {
      logger.error(`[${this.name} Parser] Cheerio instance is null or undefined.`);
      return [];
    }

    const mediaItems = $('div.content-inner div.thumb');

    if (!mediaItems || mediaItems.length === 0) {
      logger.warn(`[${this.name} Parser] No media items found with selector 'div.content-inner div.thumb' for type '${type}'.`);
      return [];
    }

    mediaItems.each((i, el) => {
      const item = $(el);

      if (type === 'videos' && !item.hasClass('video')) return;
      if (type === 'gifs' && !item.hasClass('image')) return;

      const linkElement = item.find('a[href]').first();
      let relativeUrl = linkElement.attr('href');

      let titleText = sanitizeText(
          item.find('div.caption').text()?.trim() ||
          item.find('div.thumb-title').text()?.trim() ||
          item.find('div.title').text()?.trim() ||
          linkElement.attr('title')?.trim() ||
          item.find('img').attr('alt')?.trim()
      );

      if (!relativeUrl) {
          logger.warn(`[${this.name} Parser] Item ${i} (${type}): Skipping, no relative URL found.`);
          return;
      }
      if (!titleText) titleText = `Motherless Content ${i + 1}`;

      let id = item.attr('data-id');
      if (!id && relativeUrl) {
          const urlParts = relativeUrl.split('/');
          const potentialId = urlParts.filter(part => /^[A-Z0-9]{6,12}$/.test(part)).pop();
          if (potentialId) {
              id = potentialId;
          } else {
              id = urlParts.filter(Boolean).pop();
          }
      }

      const imgElement = item.find('img').first();
      let thumbnailUrl = imgElement.attr('src')?.trim() || imgElement.attr('data-src')?.trim();
      if (!thumbnailUrl) {
          const bgStyle = item.find('div.preview[style*="background-image"]').attr('style');
          if (bgStyle) {
              const bgMatch = bgStyle.match(/url\(['"]?(.*?)['"]?\)/);
              if (bgMatch && bgMatch[1]) thumbnailUrl = bgMatch[1];
          }
      }

      const durationText = type === 'videos' ? sanitizeText(item.find('.video_length').text()?.trim()) : undefined;
      let previewVideoUrl = type === 'gifs' ? thumbnailUrl : undefined;
      if (type === 'videos') {
          previewVideoUrl = extractPreview(item, this.baseUrl, false);
      }


      if (!titleText || !relativeUrl || !id) {
        logger.warn(`[${this.name} Parser] Item ${i} (${type}): Skipping due to missing critical data. Title: ${titleText}, URL: ${relativeUrl}, ID: ${id}`);
        return;
      }

      const absoluteUrl = makeAbsolute(relativeUrl, this.baseUrl);
      const absoluteThumbnailUrl = makeAbsolute(thumbnailUrl, this.baseUrl);
      const finalPreviewVideoUrl = validatePreview(makeAbsolute(previewVideoUrl, this.baseUrl)) ? makeAbsolute(previewVideoUrl, this.baseUrl) : (type === 'gifs' && absoluteThumbnailUrl ? absoluteThumbnailUrl : undefined);


      results.push({
        id: id,
        title: titleText,
        url: absoluteUrl,
        duration: type === 'videos' ? (durationText || 'N/A') : undefined,
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

module.exports = MotherlessDriver;
