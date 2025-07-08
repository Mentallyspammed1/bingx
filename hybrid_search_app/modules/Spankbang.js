'use strict';

// Core module and mixins
const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const GifMixin = require('../core/GifMixin.js');

const { logger, makeAbsolute, extractPreview, validatePreview, sanitizeText } = require('./driver-utils.js');

const BASE_URL_CONST = 'https://www.spankbang.com';
const DRIVER_NAME_CONST = 'Spankbang';

// Apply mixins to AbstractModule
const BaseSpankbangClass = AbstractModule.with(VideoMixin, GifMixin);

class SpankbangDriver extends BaseSpankbangClass {
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
      throw new Error(`[${this.name}] Video search query is not set.`);
    }
    const encodedQuery = encodeURIComponent(sanitizeText(currentQuery).replace(/\s+/g, '+'));
    const pageNum = Math.max(1, parseInt(page, 10) || this.firstpage);
    const pageSegment = pageNum > 1 ? `${pageNum}/` : '';
    const urlPath = `/s/${encodedQuery}/${pageSegment}`;
    const searchUrl = new URL(urlPath, this.baseUrl);
    searchUrl.searchParams.set('o', 'new');
    logger.debug(`[${this.name}] Generated videoUrl: ${searchUrl.href}`);
    return searchUrl.href;
  }

  getGifSearchUrl(query, page) {
    let currentQuery = query || this.query;
    if (!currentQuery || typeof currentQuery !== 'string' || currentQuery.trim() === '') {
      throw new Error(`[${this.name}] GIF search query is not set.`);
    }
    const encodedQuery = encodeURIComponent(sanitizeText(currentQuery).replace(/\s+/g, '+'));
    const pageNum = Math.max(1, parseInt(page, 10) || this.firstpage);
    const pageSegment = pageNum > 1 ? `${pageNum}/` : '';
    const url = `${this.baseUrl}/gifs/search/${encodedQuery}/${pageSegment}`;
    logger.debug(`[${this.name}] Generated gifUrl: ${url}`);
    return url;
  }

  parseResults($, rawHtmlOrJsonData, parserOptions) {
    const { type, sourceName } = parserOptions;
    const results = [];
    if (!$) {
      logger.error(`[${this.name} Parser] Cheerio instance is null or undefined.`);
      return [];
    }

    const mediaItems = $('div.video-item, article.video-item');

    if (!mediaItems || mediaItems.length === 0) {
      logger.warn(`[${this.name} Parser] No media items found with current selectors for type '${type}'.`);
      return [];
    }

    mediaItems.each((i, el) => {
      const item = $(el);

      const itemHref = item.find('a.thumb').attr('href');
      if (type === 'gifs' && itemHref && !itemHref.includes('/gif/')) {
          if(item.hasClass('video_item') && !item.hasClass('gif_item') && itemHref && itemHref.includes('/video/')) return;
      }
      if (type === 'videos' && itemHref && itemHref.includes('/gif/')) {
          return;
      }

      const linkElement = item.find('a.thumb').first();
      let relativeUrl = linkElement.attr('href');
      let titleText = sanitizeText(linkElement.attr('title')?.trim());

      if (!titleText) {
          titleText = sanitizeText(item.find('div.inf > p > a, p.title_video a, p.title_gif a, p.name a').first().text()?.trim());
      }
       if (!titleText && relativeUrl) {
           const parts = relativeUrl.split('/');
           const slug = parts.filter(p=> p && p!==type.slice(0,-1) && !/^[a-z0-9]{5,10}$/.test(p) && p !== 's').pop();
           if(slug) titleText = sanitizeText(slug.replace(/[-_]/g, ' ').trim());
       }

      let id = item.attr('data-id');
      if (!id && relativeUrl) {
          const idMatch = relativeUrl.match(/^\/([a-zA-Z0-9]+)\//);
          if (idMatch && idMatch[1]) id = idMatch[1];
      }

      const imgElement = item.find('img.lazy, img.thumb_video_screen, img.thumb_gif_screen').first();
      let thumbnailUrl = imgElement.attr('data-src')?.trim() || imgElement.attr('src')?.trim();

      const durationText = type === 'videos' ? sanitizeText(item.find('div.l, div.dur, span.duration').first().text()?.trim()) : undefined;
      const previewVideoUrl = extractPreview(item, this.baseUrl, type === 'gifs');

      if (!titleText || !relativeUrl || !id) {
        logger.warn(`[${this.name} Parser] Item ${i} (${type}): Skipping. Missing: ${!titleText?'Title ':''}${!relativeUrl?'URL ':''}${!id?'ID ':''}`);
        return;
      }

      const absoluteUrl = makeAbsolute(relativeUrl, this.baseUrl);
      const absoluteThumbnailUrl = makeAbsolute(thumbnailUrl, this.baseUrl);
      let finalPreviewVideoUrl = validatePreview(previewVideoUrl) ? previewVideoUrl : undefined;

       if (!finalPreviewVideoUrl && type === 'gifs' && absoluteThumbnailUrl?.toLowerCase().endsWith('.gif')) {
          finalPreviewVideoUrl = absoluteThumbnailUrl;
       }

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

module.exports = SpankbangDriver;
