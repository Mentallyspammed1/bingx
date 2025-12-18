'use strict';

const AbstractModule = require('../core/AbstractModule');
const VideoMixin = require('../core/VideoMixin');
const GifMixin = require('../core/GifMixin');

const BASE_PLATFORM_URL = 'https://www.pornhub.com';
const GIF_DOMAIN = 'https://i.pornhub.com';

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

  videoUrl(query, page) {
    const q = encodeURIComponent(query.trim());
    const p = Math.max(1, page || this.firstpage);
    const url = new URL('/video/search', BASE_PLATFORM_URL);
    url.searchParams.set('search', q);
    url.searchParams.set('page', String(p));
    return url.href;
  }

  videoParser($, rawHtml) {
    const results = [];
    const items = $('div.phimage');
    if (!items.length) {
      console.warn(`[${this.name} videoParser] No video items found.`);
      return results;
    }
    items.each((i, el) => {
      const item = $(el);
      const link = item.find('a').first();
      let url = link.attr('href');
      let id = url ? (url.match(/viewkey=([a-zA-Z0-9]+)/) || [])[1] : null;
      let title = link.attr('title') || item.find('span.title').text().trim() || item.attr('data-video-title');
      let thumb = item.find('img').first().attr('data-src') || item.find('img').first().attr('src');
      const duration = item.find('var.duration, span.duration').text().trim() || 'N/A';
      if (thumb && thumb.includes('nothumb')) thumb = undefined;
      if (!id || !url || !title || !thumb) return; // Skip malformed
      url = this._makeAbsolute(url, BASE_PLATFORM_URL);
      thumb = this._makeAbsolute(thumb, BASE_PLATFORM_URL);
      results.push({
        id,
        title,
        url,
        thumbnail: thumb,
        duration,
        source: this.name,
        type: 'videos'
      });
    });
    return results;
  }

  gifUrl(query, page) {
    const q = encodeURIComponent(query.trim());
    const p = Math.max(1, page || this.firstpage);
    const url = new URL('/gifs/search', BASE_PLATFORM_URL);
    url.searchParams.set('search', q);
    url.searchParams.set('page', String(p));
    return url.href;
  }

  gifParser($, rawHtml) {
    const results = [];
    const items = $('div.gifImageBlock,div.img-container');
    if (!items.length) {
      console.warn(`[${this.name} gifParser] No GIF items found.`);
      return results;
    }
    items.each((i, el) => {
      const item = $(el);
      const link = item.find('a').first();
      let pageUrl = link.attr('href');
      let id = item.attr('data-id') || (pageUrl ? pageUrl.match(/\/(\d+)\//) : null)?.[1];
      let title = item.find('img').attr('alt') || link.attr('title') || 'Untitled GIF';
      let animated = item.find('img').attr('data-src') || item.find('img').attr('src');
      if (animated && animated.endsWith('.gif')) {
        animated = this._makeAbsolute(animated, GIF_DOMAIN);
      }
      if (!id || !pageUrl || !animated) return; // Skip malformed
      pageUrl = this._makeAbsolute(pageUrl, BASE_PLATFORM_URL);
      results.push({
        id,
        title,
        url: pageUrl,
        thumbnail: animated,
        preview_video: animated,
        source: this.name,
        type: 'gifs'
      });
    });
    return results;
  }

  _makeAbsolute(url, base) {
    if (!url || typeof url !== 'string') return undefined;
    if (url.startsWith('data:')) return url;
    if (url.startsWith('//')) return `https:${url}`;
    if (url.startsWith('http:') || url.startsWith('https:')) return url;
    try {
      return new URL(url, base).href;
    } catch (e) { return undefined; }
  }
}

module.exports = PornhubDriver;
