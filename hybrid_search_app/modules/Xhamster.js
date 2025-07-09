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
  hasVideoSupport() { return true; }
  hasGifSupport() { return true; }
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
              const linkElement = item.find('a[href], .thumb-link, .item-link').first();
              pageUrl = linkElement.attr('href');
              title = sanitizeText(linkElement.attr('title')?.trim() ||
                                   item.find('.title, .name, .item-title, .video-title, .photo-title, .gif-title').first().text()?.trim() ||
                                   item.find('img').first().attr('alt')?.trim());

              const imgElement = item.find('img[src], img[data-src], .thumb-img, .item-img').first();
              thumbnailUrl = imgElement.attr('data-src') || imgElement.attr('src');
              previewVideoUrl = imgElement.attr('data-src') || imgElement.attr('data-original') || imgElement.attr('src');
              durationText = undefined;

              if (!mediaId && pageUrl) {
                  const idMatch = pageUrl.match(/\/(?:videos|photos|gifs)\/.*?-(\d+)(?:\.html)?$|\/(?:videos|photos|gifs)\/(\d+)\//);
                  if (idMatch) mediaId = idMatch[1] || idMatch[2];
              }
          } else {
              const linkElement = item.find('a[href], .thumb-link, .item-link').first();
              pageUrl = linkElement.attr('href');
              title = sanitizeText(linkElement.attr('title')?.trim() ||
                                   item.find('.title, .name, .item-title, .video-title, .photo-title, .gif-title').first().text()?.trim() ||
                                   item.find('img').first().attr('alt')?.trim());

              const imgElement = item.find('img[src], img[data-src], .thumb-img, .item-img').first();
              thumbnailUrl = imgElement.attr('data-src') || imgElement.attr('src');
              durationText = sanitizeText(item.find('.duration, .video-duration, .time, .item-duration').first().text()?.trim());
              previewVideoUrl = extractPreview(item, this.baseUrl, false);

              if (!mediaId && pageUrl) {
                  const idMatch = pageUrl.match(/\/(?:videos|photos|gifs)\/.*?-(\d+)(?:\.html)?$|\/(?:videos|photos|gifs)\/(\d+)\//);
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
          let finalPreview = validatePreview(previewVideoUrl) ? previewVideoUrl : undefined;

          if (!finalPreview && isGifSearch && absoluteThumbnail?.toLowerCase().endsWith('.gif')) {
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
