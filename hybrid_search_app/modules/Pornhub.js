'use strict';

const AbstractModule = require('../core/AbstractModule.js');
const { logger, makeAbsolute, extractPreview, sanitizeText } = require('./driver-utils.js');

class Pornhub extends AbstractModule {
  constructor(options = {}) {
    super(options);
  }

  get name() {
    return 'Pornhub';
  }

  get baseUrl() {
    return 'https://www.pornhub.com';
  }

  get firstpage() {
    return 1;
  }

  hasVideoSupport() {
    return true;
  }

  hasGifSupport() {
    return true;
  }

  getVideoSearchUrl(query, page) {
    const encodedQuery = encodeURIComponent(query.trim());
    const pageNumber = Math.max(1, page || this.firstpage);

    const url = new URL('/video/search', this.baseUrl);
    url.searchParams.set('search', encodedQuery);
    url.searchParams.set('page', String(pageNumber));

    return url.href;
  }

  getGifSearchUrl(query, page) {
    const encodedQuery = encodeURIComponent(query.trim());
    const pageNumber = Math.max(1, page || this.firstpage);

    const url = new URL('/gifs/search', this.baseUrl);
    url.searchParams.set('search', encodedQuery);
    url.searchParams.set('page', String(pageNumber));

    return url.href;
  }

  parseResults($, rawData, options) {
    const { type, sourceName } = options;
    const results = [];

    if (!$) {
      return [];
    }

    if ($('#videoSearchResult .no-results-found, .no-results-found-container').length > 0) {
      return [];
    }

    if (type === 'videos') {
      const videoItems = $('div.phimage, .video-item, .videoblock');

      if (!videoItems.length) {
        return [];
      }

      videoItems.each((index, element) => {
        const item = $(element);

        const linkElement = item.find('a[href*="/view_video.php"], a[href*="/video/"], a.link-videos').first();
        let videoUrl = linkElement.attr('href');

        let videoId = videoUrl ? videoUrl.match(/viewkey=([a-zA-Z0-9]+)/)?.[1] : null;
        if (!videoId && videoUrl) {
            const pathSegments = videoUrl.split('/');
            videoId = pathSegments[pathSegments.length - 2];
            if (videoId && !/^\d+$/.test(videoId)) videoId = null;
        }
        if (!videoId) videoId = item.attr('data-id');

        let title = linkElement.attr('title') || item.find('img').attr('alt') || item.find('.title, .video-title').text();
        title = sanitizeText(title);

        const thumbElement = item.find('img[src], img[data-src]').first();
        let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
        if (thumbnailUrl && thumbnailUrl.includes('nothumb')) thumbnailUrl = undefined;

        let duration = item.find('var.duration, span.duration').text();
        duration = sanitizeText(duration);

        const previewVideoUrl = extractPreview($, item, sourceName, this.baseUrl);

        if (!videoUrl || !title || !thumbnailUrl || !videoId) {
          return;
        }

        videoUrl = makeAbsolute(videoUrl, this.baseUrl);
        thumbnailUrl = makeAbsolute(thumbnailUrl, this.baseUrl);

        if (!videoUrl || !thumbnailUrl) {
           return;
        }

        results.push({
          id: videoId,
          title: title,
          url: videoUrl,
          duration: duration,
          thumbnail: thumbnailUrl,
          preview_video: previewVideoUrl,
          source: sourceName,
          type: 'videos'
        });
      });

    } else if (type === 'gifs') {
      const gifItems = $('li.gifVideoBlock, .gif-item, .gif-thumb');

      if (!gifItems.length) {
        return [];
      }

      gifItems.each((index, element) => {
        const item = $(element);

        const linkElement = item.find('a').first();
        let gifPageUrl = linkElement.attr('href');

        let gifId = gifPageUrl ? gifPageUrl.match(/\/gifs\/([a-zA-Z0-9]+)/)?.[1] : null;
        if (!gifId) gifId = item.attr('data-id');

        let title = linkElement.attr('title') || item.find('img').attr('alt') || item.find('.title, .gif-title').text();
        title = sanitizeText(title);

        const animatedGifUrl = extractPreview($, item, sourceName, this.baseUrl);

        const thumbElement = item.find('img[src], img[data-src]').first();
        let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
        if (thumbnailUrl && thumbnailUrl.includes('nothumb')) thumbnailUrl = undefined;

        if (!gifPageUrl || !title || !animatedGifUrl || !thumbnailUrl || !gifId) {
          return;
        }

        gifPageUrl = makeAbsolute(gifPageUrl, this.baseUrl);
        thumbnailUrl = makeAbsolute(thumbnailUrl, this.baseUrl);

        if (!gifPageUrl || !thumbnailUrl) {
           return;
        }

        results.push({
          id: gifId,
          title: title,
          url: gifPageUrl,
          thumbnail: thumbnailUrl,
          preview_video: animatedGifUrl,
          source: sourceName,
          type: 'gifs'
        });
      });
    }
    return results;
  }
}

module.exports = Pornhub;