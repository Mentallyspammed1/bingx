'use strict';

const AbstractModule = require('../core/AbstractModule');
const VideoMixin = require('../core/VideoMixin');
const GifMixin = require('../core/GifMixin');

const BASE_PLATFORM_URL = 'https://www.pornhub.com';

/**
 * PornhubDriver - Scrapes video and gif content from Pornhub.
 */
class PornhubDriver extends AbstractModule.with(VideoMixin, GifMixin) {
  constructor(options = {}) {
    super(options);
  }

  get name() {
    return 'Pornhub';
  }

  get firstpage() {
    return 1;
  }

  getVideoSearchUrl(query, page) {
    const q = encodeURIComponent(query.trim());
    const p = Math.max(1, page || this.firstpage);
    const url = new URL('/video/search', BASE_PLATFORM_URL);
    url.searchParams.set('search', q);
    url.searchParams.set('page', String(p));
    return url.href;
  }

  parseResults($, rawData, options) {
    const results = [];
    if (options.type === 'videos') {
      const items = $('div.phimage, .video-item');
      if (!items.length) {
        console.warn(`[${this.name} parseResults - videos] No video items found.`);
        return results;
      }
      items.each((i, el) => {
        const result = this.mapVideoResult(el, $, this.name, BASE_PLATFORM_URL);
        if (result) {
          results.push(result);
        }
      });
    } else if (options.type === 'gifs') {
      const items = $('div.gifImageBlock, div.img-container, .gif-item');
      if (!items.length) {
        console.warn(`[${this.name} parseResults - gifs] No GIF items found.`);
        return results;
      }
      items.each((i, el) => {
        const result = this.mapGifResult(el, $, this.name, BASE_PLATFORM_URL);
        if (result) {
          results.push(result);
        }
      });
    }
    return results;
  }
}

module.exports = PornhubDriver;
