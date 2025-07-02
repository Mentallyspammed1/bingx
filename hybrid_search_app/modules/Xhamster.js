'use strict';

// Core module and mixins
const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const GifMixin = require('../core/GifMixin.js');

const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL_CONST = 'https://xhamster.com';
const DRIVER_NAME_CONST = 'Xhamster';

// Apply mixins to AbstractModule.
const BaseXhamsterClass = AbstractModule.with(VideoMixin, GifMixin);

class XhamsterDriver extends BaseXhamsterClass {
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
      throw new Error(`[${this.name}] Search query is not set for video search.`);
    }
    const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
    const searchPath = `/search/${encodeURIComponent(sanitizeText(currentQuery))}`;
    const searchUrl = new URL(searchPath, this.baseUrl);
    searchUrl.searchParams.set('page', String(searchPage));
    logger.debug(`[${this.name}] Generated video URL: ${searchUrl.href}`);
    return searchUrl.href;
  }

  getGifSearchUrl(query, page) {
    let currentQuery = query || this.query;
    if (!currentQuery || typeof currentQuery !== 'string' || currentQuery.trim() === '') {
      throw new Error(`[${this.name}] Search query is not set for GIF search.`);
    }
    const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
    const searchPath = `/search/${encodeURIComponent(sanitizeText(currentQuery))}`;
    const searchUrl = new URL(searchPath, this.baseUrl);
    searchUrl.searchParams.set('page', String(searchPage));
    searchUrl.searchParams.set('type', 'photos');
    logger.debug(`[${this.name}] Generated GIF URL: ${searchUrl.href}`);
    return searchUrl.href;
  }

  parseResults($, htmlOrJsonData, parserOptions) {
      if (!$) {
          logger.error(`[${this.name}] Cheerio object ($) is null. Expecting HTML.`);
          return [];
      }

      const results = [];
      const { type, sourceName } = parserOptions;
      const isGifSearch = type === 'gifs';

      const itemSelector = isGifSearch ?
          'div.photo-thumb, div.gif-thumb, div.gallery-thumb, div.thumb-list__item--gif' :
          'div.video-thumb, div.thumb-list__item:not(.thumb-list__item--photo):not(.thumb-list__item--user), div.video-box';


      $(itemSelector).each((i, el) => {
          const item = $(el);
          let title, pageUrl, thumbnailUrl, previewVideoUrl, durationText, mediaId;

          mediaId = item.attr('data-id');

          if (isGifSearch) {
              const linkElement = item.find('a.photo-thumb__image, a.thumb-image__image, a.gallery-thumb__image-container').first();
              pageUrl = linkElement.attr('href');
              title = sanitizeText(linkElement.attr('title')?.trim() ||
                                   item.find('.photo-thumb__title, .gif-thumb__name, .gallery-thumb__name a, .gallery-thumb__name').first().text()?.trim() ||
                                   item.find('img').first().attr('alt')?.trim());

              const imgElement = item.find('img.photo-thumb__img, img.thumb-image__image, img.gallery-thumb__image').first();
              thumbnailUrl = imgElement.attr('data-poster') || imgElement.attr('src');
              previewVideoUrl = imgElement.attr('data-src') || imgElement.attr('data-original') || imgElement.attr('src');
              durationText = undefined;

              if (!mediaId && pageUrl) {
                  const idMatch = pageUrl.match(/\/photos\/(?:gallery\/[^/]+\/[^/]+-|view\/)?(\d+)|gifs\/(\d+)/);
                  if (idMatch) mediaId = idMatch[1] || idMatch[2] || idMatch[3];
              }
          } else {
              const linkElement = item.find('a.video-thumb__image-container, a.thumb-image__image, a.video-thumb-link').first();
              pageUrl = linkElement.attr('href');
              title = sanitizeText(linkElement.attr('title')?.trim() ||
                                   item.find('.video-thumb__name, .video-title, .video-thumb-info__name, .item-title a').first().text()?.trim() ||
                                   item.find('img').first().attr('alt')?.trim());

              const imgElement = item.find('img.video-thumb__image, img.thumb-image__image').first();
              thumbnailUrl = imgElement.attr('data-src') || imgElement.attr('src');
              durationText = sanitizeText(item.find('.video-thumb__duration, .duration, .video-duration, .time, .video-thumb-info__duration').first().text()?.trim());

              previewVideoUrl = item.find('script.video-thumb__player-container').attr('data-previewvideo') ||
                                linkElement.attr('data-preview-url') ||
                                linkElement.attr('data-preview') ||
                                item.find('video.thumb-preview__video').attr('src');

              if (!mediaId && pageUrl) {
                  const idMatch = pageUrl.match(/\/videos\/.*?-(\d+)(?:\.html)?$|\/videos\/(\d+)\//);
                  if (idMatch) mediaId = idMatch[1] || idMatch[2];
              }
          }

          if (!mediaId && pageUrl) {
              const parts = pageUrl.split(/[-/]/);
              mediaId = parts.reverse().find(part => /^\d{6,}$/.test(part));
          }

          if (!pageUrl || !title || !mediaId) {
              logger.warn(`[${this.name}] Item ${i} (${type}): Skipping. Missing: ${!pageUrl?'URL ':''}${!title?'Title ':''}${!mediaId?'ID ':''}`);
              return;
          }

          const absoluteUrl = makeAbsolute(pageUrl, this.baseUrl);
          const absoluteThumbnail = makeAbsolute(thumbnailUrl, this.baseUrl);
          let finalPreview = makeAbsolute(previewVideoUrl, this.baseUrl);

          if (!validatePreview(finalPreview)) {
              finalPreview = extractPreview(item, this.baseUrl, isGifSearch);
          }
          if (!validatePreview(finalPreview) && isGifSearch && absoluteThumbnail?.toLowerCase().endsWith('.gif')) {
               finalPreview = absoluteThumbnail;
          }

          results.push({
              id: mediaId,
              title: title,
              url: absoluteUrl,
              thumbnail: absoluteThumbnail || '',
              duration: durationText || (isGifSearch ? undefined : 'N/A'),
              preview_video: validatePreview(finalPreview) ? finalPreview : '',
              source: sourceName,
              type: type
          });
      });

      logger.debug(`[${this.name}] Parsed ${results.length} ${type} items from mock.`);
      return results;
  }
}

module.exports = XhamsterDriver;
