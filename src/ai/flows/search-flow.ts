'use server';
/**
 * @fileOverview A search flow for scraping content.
 *
 * - search - A function that handles the scraping process.
 * - SearchInput - The input type for the search function.
 * - SearchOutput - The return type for the search function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';
import axios from 'axios';
import * as cheerio from 'cheerio';
import type { SearchInput, SearchOutput } from '@/ai/types';
import { SearchInputSchema, SearchOutputSchema } from '@/ai/types';

// Define Abstract Base Class (conceptual)
class AbstractModule {
  query: string;
  options: any;

  constructor(options: {query: string} = {query: ''}) {
    this.query = options.query?.trim() || '';
    this.options = options || {};
  }

  get name(): string {
    throw new Error('"name" must be overridden by subclass.');
  }

  get firstpage(): number {
    throw new Error('"firstpage" must be overridden by subclass.');
  }

  videoUrl(query: string, page: number): string {
    throw new Error('Method or property "videoUrl" must be overridden by subclass.');
  }
  videoParser($: cheerio.CheerioAPI, rawBody: string): any[] {
    throw new Error('Method or property "videoParser" must be overridden by subclass.');
  }
  gifUrl(query: string, page: number): string {
    throw new Error('Method or property "gifUrl" must be overridden by subclass.');
  }
  gifParser($: cheerio.CheerioAPI, rawBody: string): any[] {
    throw new Error('Method or property "gifParser" must be overridden by subclass.');
  }

  _makeAbsolute(urlString: string | undefined, baseUrl: string) {
    if (!urlString || typeof urlString !== 'string') return undefined;
    if (urlString.startsWith('data:')) return urlString;
    if (urlString.startsWith('//')) return `https:${urlString}`;
    if (urlString.startsWith('http:') || urlString.startsWith('https:'))
      return urlString;
    try {
      return new URL(urlString, baseUrl).href;
    } catch (e) {
      return undefined;
    }
  }
}

// Define Drivers
class PornhubDriver extends AbstractModule {
  get name() {
    return 'Pornhub';
  }
  get firstpage() {
    return 1;
  }
  videoUrl(query: string, page: number) {
    const encodedQuery = encodeURIComponent(query.trim());
    const pageNumber = Math.max(1, page || this.firstpage);
    const url = new URL('https://www.pornhub.com/video/search');
    url.searchParams.set('search', encodedQuery);
    url.searchParams.set('page', String(pageNumber));
    return url.href;
  }
  videoParser($: cheerio.CheerioAPI) {
    const results: any[] = [];
    $('li.videoBox').each((index, element) => {
      const item = $(element);
      const linkElement = item.find('a').first();
      let videoUrl = linkElement.attr('href');
      let videoId = videoUrl?.match(/viewkey=([a-zA-Z0-9]+)/)?.[1];
      let title = item.find('span.title a').text().trim();
      const thumbElement = item.find('img').first();
      let thumbnailUrl = thumbElement.attr('data-thumb_url');
      if (thumbnailUrl?.includes('nothumb')) thumbnailUrl = undefined;
      let duration = item.find('var.duration').text().trim();
      let previewVideoUrl = thumbElement.attr('data-mediabook');

      if (videoUrl) videoUrl = this._makeAbsolute(videoUrl, 'https://www.pornhub.com');
      if (thumbnailUrl) thumbnailUrl = this._makeAbsolute(thumbnailUrl, 'https://www.pornhub.com');
      if (previewVideoUrl) previewVideoUrl = this._makeAbsolute(previewVideoUrl, 'https://www.pornhub.com');

      if (!videoUrl || !title || !thumbnailUrl || !videoId) return;
      results.push({ id: videoId, title, url: videoUrl, duration, thumbnail: thumbnailUrl, preview_video: previewVideoUrl, source: this.name, type: 'videos'});
    });
    return results;
  }
  gifUrl(query: string, page: number) {
    const encodedQuery = encodeURIComponent(query.trim());
    const pageNumber = Math.max(1, page || this.firstpage);
    const url = new URL('https://www.pornhub.com/gifs/search');
    url.searchParams.set('search', encodedQuery);
    url.searchParams.set('page', String(pageNumber));
    return url.href;
  }
  gifParser($: cheerio.CheerioAPI) {
    const results: any[] = [];
    $('li.gifVideoBlock').each((index, element) => {
      const item = $(element);
      const linkElement = item.find('a').first();
      let gifPageUrl = linkElement.attr('href');
      let gifId = item.attr('data-gif-id') || gifPageUrl?.match(/\/view_gif\/(\d+)/)?.[1];
      let title = item.find('a').attr('title') || 'Untitled GIF';
      let animatedGifUrl = item.find('video').attr('data-src');
      let staticThumbnailUrl = item.find('img').attr('data-src');
      if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, 'https://www.pornhub.com');
      if (animatedGifUrl) animatedGifUrl = this._makeAbsolute(animatedGifUrl, 'https://www.pornhub.com');

      if (!gifPageUrl || !title || !animatedGifUrl || !gifId) return;
      gifPageUrl = this._makeAbsolute(gifPageUrl, 'https://www.pornhub.com');
      results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: this.name, type: 'gifs' });
    });
    return results;
  }
}

class SexDriver extends AbstractModule {
    get name() { return 'Sex.com'; }
    get firstpage() { return 1; }
    videoUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageNumber = Math.max(1, page || this.firstpage);
        const url = new URL('https://www.sex.com/search/videos');
        url.searchParams.set('query', encodedQuery);
        url.searchParams.set('page', String(pageNumber));
        return url.href;
    }
    videoParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.thumbnail_container').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a.video_link').first();
            let videoUrl = linkElement.attr('href');
            let videoId = item.attr('data-id');
            let title = item.find('div.title').text().trim();
            const thumbElement = item.find('img.video_thumb').first();
            let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
            if (thumbnailUrl?.includes('nothumb')) thumbnailUrl = undefined;
            let duration = item.find('div.duration').text().trim();
            let previewVideoUrl = item.find('img.preview_thumb').attr('data-src');

            if (videoUrl) videoUrl = this._makeAbsolute(videoUrl, 'https://www.sex.com');
            if (thumbnailUrl) thumbnailUrl = this._makeAbsolute(thumbnailUrl, 'https://www.sex.com');
            if (previewVideoUrl) previewVideoUrl = this._makeAbsolute(previewVideoUrl, 'https://www.sex.com');

            if (!videoUrl || !title || !thumbnailUrl || !videoId) return;
            results.push({ id: videoId, title, url: videoUrl, duration, thumbnail: thumbnailUrl, preview_video: previewVideoUrl, source: this.name, type: 'videos' });
        });
        return results;
    }
    gifUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageNumber = Math.max(1, page || this.firstpage);
        const url = new URL('https://www.sex.com/search/gifs');
        url.searchParams.set('query', encodedQuery);
        url.searchParams.set('page', String(pageNumber));
        return url.href;
    }
    gifParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.masonry-thumb').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let gifPageUrl = linkElement.attr('href');
            let gifId = item.attr('data-id');
            let title = item.find('img').attr('alt') || 'Untitled GIF';
            let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
            if (animatedGifUrl) animatedGifUrl = this._makeAbsolute(animatedGifUrl, 'https://www.sex.com');

            if (!gifPageUrl || !title || !animatedGifUrl || !gifId) return;
            gifPageUrl = this._makeAbsolute(gifPageUrl, 'https://www.sex.com');
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: animatedGifUrl, preview_video: animatedGifUrl, source: this.name, type: 'gifs' });
        });
        return results;
    }
}

class RedtubeDriver extends AbstractModule {
    get name() { return 'Redtube'; }
    get firstpage() { return 1; }
    videoUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageNumber = Math.max(1, page || this.firstpage);
        const url = new URL('https://www.redtube.com/');
        url.searchParams.set('search', encodedQuery);
        url.searchParams.set('page', String(pageNumber));
        return url.href;
    }
    videoParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.video_ui_component').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a.video_link').first();
            let videoUrl = linkElement.attr('href');
            let videoId = item.attr('data-video_id');
            let title = item.find('.video_title').text().trim();
            const thumbElement = item.find('img.video_thumb').first();
            let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
            if (thumbnailUrl?.includes('nothumb')) thumbnailUrl = undefined;
            let duration = item.find('span.duration').text().trim();
            let previewVideoUrl = item.find('img.preview_thumb').attr('data-src');

            if (videoUrl) videoUrl = this._makeAbsolute(videoUrl, 'https://www.redtube.com');
            if (thumbnailUrl) thumbnailUrl = this._makeAbsolute(thumbnailUrl, 'https://www.redtube.com');
            if (previewVideoUrl) previewVideoUrl = this._makeAbsolute(previewVideoUrl, 'https://www.redtube.com');

            if (!videoUrl || !title || !thumbnailUrl || !videoId) return;
            results.push({ id: videoId, title, url: videoUrl, duration, thumbnail: thumbnailUrl, preview_video: previewVideoUrl, source: this.name, type: 'videos' });
        });
        return results;
    }
    gifUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageNumber = Math.max(1, page || this.firstpage);
        const url = new URL('https://www.redtube.com/gifs/search');
        url.searchParams.set('search', encodedQuery);
        url.searchParams.set('page', String(pageNumber));
        return url.href;
    }
    gifParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.gif_card_wrapper').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let gifPageUrl = linkElement.attr('href');
            let gifId = item.attr('data-id');
            let title = item.find('.gif_card_title').text().trim() || 'Untitled GIF';
            let animatedGifUrl = item.find('video.gif_preview_video source').attr('src');
            let staticThumbnailUrl = item.find('img.gif_card_thumb').attr('src');

            if (gifPageUrl) gifPageUrl = this._makeAbsolute(gifPageUrl, 'https://www.redtube.com');
            if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, 'https://www.redtube.com');
            if (animatedGifUrl) animatedGifUrl = this._makeAbsolute(animatedGifUrl, 'https://www.redtube.com');

            if (!gifPageUrl || !title || !animatedGifUrl || !gifId) return;
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: this.name, type: 'gifs' });
        });
        return results;
    }
}

class XvideosDriver extends AbstractModule {
    get name() { return 'XVideos'; }
    get firstpage() { return 1; }
    videoUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim().replace(/\s+/g, '+'));
        const pageNumber = Math.max(1, page || this.firstpage);
        if (pageNumber === 1) {
             return `https://www.xvideos.com/?k=${encodedQuery}`;
        }
        return `https://www.xvideos.com/new/${pageNumber-1}/?k=${encodedQuery}`;
    }
    videoParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.thumb-block').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('.thumb-image a').first();
            let videoUrl = linkElement.attr('href');
            let videoId = item.attr('data-id');
            let title = item.find('p.title a').attr('title');
            const thumbElement = item.find('img').first();
            let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
            if (thumbnailUrl?.includes('nothumb')) thumbnailUrl = undefined;
            let duration = item.find('span.duration').text().trim();
            let previewVideoUrl = thumbElement.attr('data-previewvideo');

            if (videoUrl) videoUrl = this._makeAbsolute(videoUrl, 'https://www.xvideos.com');
            if (thumbnailUrl) thumbnailUrl = this._makeAbsolute(thumbnailUrl, 'https://www.xvideos.com');
            if (previewVideoUrl) previewVideoUrl = this._makeAbsolute(previewVideoUrl, 'https://www.xvideos.com');

            if (!videoUrl || !title || !thumbnailUrl || !videoId) return;
            results.push({ id: videoId, title, url: videoUrl, duration, thumbnail: thumbnailUrl, preview_video: previewVideoUrl, source: this.name, type: 'videos' });
        });
        return results;
    }
    gifUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageNumber = Math.max(1, page || this.firstpage);
        const url = new URL('https://www.xvideos.com/gifs');
        url.searchParams.set('k', encodedQuery);
        url.searchParams.set('p', String(pageNumber - 1));
        return url.href;
    }
    gifParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.gif-thumb-block').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let gifPageUrl = linkElement.attr('href');
            let gifId = item.attr('data-id');
            let title = item.find('.gif-title').text().trim() || 'Untitled GIF';
            let animatedGifUrl = item.find('img').attr('data-src');
            let staticThumbnailUrl = item.find('img').attr('src');
            if (animatedGifUrl) animatedGifUrl = this._makeAbsolute(animatedGifUrl, 'https://www.xvideos.com');
            if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, 'https://www.xvideos.com');

            if (!gifPageUrl || !title || !animatedGifUrl || !gifId) return;
            gifPageUrl = this._makeAbsolute(gifPageUrl, 'https://www.xvideos.com');
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: this.name, type: 'gifs' });
        });
        return results;
    }
}

class XhamsterDriver extends AbstractModule {
    get name() { return 'xHamster'; }
    get firstpage() { return 1; }
    videoUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageNumber = Math.max(1, page || this.firstpage);
        const url = new URL('https://xhamster.com/search');
        url.searchParams.set('q', encodedQuery);
        url.searchParams.set('page', String(pageNumber));
        return url.href;
    }
    videoParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('a.video-thumb-image__image').each((index, element) => {
            const item = $(element);
            let videoUrl = item.attr('href');
            let videoId = videoUrl?.match(/\/videos\/(.+?)-\d+/)?.[1];
            let title = item.find('img').attr('alt');
            let thumbnailUrl = item.find('img').attr('src');
            if (thumbnailUrl?.includes('nothumb')) thumbnailUrl = undefined;
            let duration = item.closest('.video-thumb-info__container').find('.video-thumb-info__duration').text().trim();
            let previewVideoUrl = item.attr('data-preview-video-url');

            if (videoUrl) videoUrl = this._makeAbsolute(videoUrl, 'https://xhamster.com');
            if (thumbnailUrl) thumbnailUrl = this._makeAbsolute(thumbnailUrl, 'https://xhamster.com');
            if (previewVideoUrl) previewVideoUrl = this._makeAbsolute(previewVideoUrl, 'https://xhamster.com');

            if (!videoUrl || !title || !thumbnailUrl || !videoId) return;
            results.push({ id: videoId, title, url: videoUrl, duration, thumbnail: thumbnailUrl, preview_video: previewVideoUrl, source: this.name, type: 'videos' });
        });
        return results;
    }
    gifUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageNumber = Math.max(1, page || this.firstpage);
        const url = new URL('https://xhamster.com/gifs/search');
        url.searchParams.set('q', encodedQuery);
        url.searchParams.set('page', String(pageNumber));
        return url.href;
    }
    gifParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('a.gif-thumb__image').each((index, element) => {
            const item = $(element);
            let gifPageUrl = item.attr('href');
            let gifId = gifPageUrl?.match(/\/gifs\/(.+)/)?.[1];
            let title = item.find('img').attr('alt') || 'Untitled GIF';
            let animatedGifUrl = item.attr('data-preview-url');
            let staticThumbnailUrl = item.find('img').attr('src');

            if (gifPageUrl) gifPageUrl = this._makeAbsolute(gifPageUrl, 'https://xhamster.com');
            if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, 'https://xhamster.com');
            if (animatedGifUrl) animatedGifUrl = this._makeAbsolute(animatedGifUrl, 'https://xhamster.com');

            if (!gifPageUrl || !title || !animatedGifUrl || !gifId) return;
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: this.name, type: 'gifs' });
        });
        return results;
    }
}

class YoupornDriver extends AbstractModule {
    get name() { return 'YouPorn'; }
    get firstpage() { return 1; }
    videoUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageNumber = Math.max(1, page || this.firstpage);
        const url = new URL('https://www.youporn.com/search/');
        url.searchParams.set('query', encodedQuery);
        url.searchParams.set('page', String(pageNumber));
        return url.href;
    }
    videoParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.video-box').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let videoUrl = linkElement.attr('href');
            let videoId = videoUrl?.match(/\/watch\/(\d+)\//)?.[1];
            let title = item.find('.video-box-title').text().trim();
            const thumbElement = item.find('img').first();
            let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
            if (thumbnailUrl?.includes('nothumb')) thumbnailUrl = undefined;
            let duration = item.find('div.duration').text().trim();
            let previewVideoUrl = linkElement.attr('data-preview');

            if (videoUrl) videoUrl = this._makeAbsolute(videoUrl, 'https://www.youporn.com');
            if (thumbnailUrl) thumbnailUrl = this._makeAbsolute(thumbnailUrl, 'https://www.youporn.com');
            if (previewVideoUrl) previewVideoUrl = this._makeAbsolute(previewVideoUrl, 'https://www.youporn.com');

            if (!videoUrl || !title || !thumbnailUrl || !videoId) return;
            results.push({ id: videoId, title, url: videoUrl, duration, thumbnail: thumbnailUrl, preview_video: previewVideoUrl, source: this.name, type: 'videos' });
        });
        return results;
    }
    gifUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageNumber = Math.max(1, page || this.firstpage);
        const url = new URL('https://www.youporn.com/search/gifs/');
        url.searchParams.set('query', encodedQuery);
        url.searchParams.set('page', String(pageNumber));
        return url.href;
    }
    gifParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.gif-box').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let gifPageUrl = linkElement.attr('href');
            let gifId = gifPageUrl?.match(/\/gif\/(\d+)\//)?.[1];
            let title = linkElement.attr('title') || 'Untitled GIF';
            let animatedGifUrl = item.find('img').attr('data-src');
            let staticThumbnailUrl = animatedGifUrl;

            if (gifPageUrl) gifPageUrl = this._makeAbsolute(gifPageUrl, 'https://www.youporn.com');
            if (animatedGifUrl) animatedGifUrl = this._makeAbsolute(animatedGifUrl, 'https://www.youporn.com');

            if (!gifPageUrl || !title || !animatedGifUrl || !gifId) return;
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: this.name, type: 'gifs' });
        });
        return results;
    }
}

class WowDriver extends AbstractModule {
    get name() { return 'Wow.xxx'; }
    get firstpage() { return 1; }
    videoUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageNumber = Math.max(1, page || this.firstpage);
        const url = new URL('https://www.wow.xxx/search/');
        url.searchParams.set('q', encodedQuery);
        if (pageNumber > 1) {
            url.pathname += `page/${pageNumber}/`;
        }
        return url.href;
    }
    videoParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.entry-content > div').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a.thumb').first();
            let videoUrl = linkElement.attr('href');
            let videoId = videoUrl?.match(/video\/(.+?)\/$/)?.[1];
            let title = item.find('.title').text().trim();
            const thumbElement = item.find('img').first();
            let thumbnailUrl = thumbElement.attr('src');
            if (thumbnailUrl?.includes('nothumb')) thumbnailUrl = undefined;
            let duration = item.find('span.duration').text().trim();
            let previewVideoUrl = linkElement.attr('data-preview-video') || thumbElement.attr('data-preview-video');

            if (videoUrl) videoUrl = this._makeAbsolute(videoUrl, 'https://www.wow.xxx');
            if (thumbnailUrl) thumbnailUrl = this._makeAbsolute(thumbnailUrl, 'https://www.wow.xxx');
            if (previewVideoUrl) previewVideoUrl = this._makeAbsolute(previewVideoUrl, 'https://www.wow.xxx');

            if (!videoUrl || !title || !thumbnailUrl || !videoId) return;
            results.push({ id: videoId, title, url: videoUrl, duration, thumbnail: thumbnailUrl, preview_video: previewVideoUrl, source: this.name, type: 'videos' });
        });
        return results;
    }
    gifUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageNumber = Math.max(1, page || this.firstpage);
        const url = new URL('https://www.wow.xxx/search/gifs/');
        url.searchParams.set('q', encodedQuery);
        if (pageNumber > 1) {
            url.pathname += `page/${pageNumber}/`;
        }
        return url.href;
    }
    gifParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.entry-content > div.gif').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let gifPageUrl = linkElement.attr('href');
            let gifId = gifPageUrl?.match(/\/gif\/(.+?)\/$/)?.[1];
            let title = item.find('img').attr('alt') || 'Untitled GIF';
            let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
            
            if (gifPageUrl) gifPageUrl = this._makeAbsolute(gifPageUrl, 'https://www.wow.xxx');
            if (animatedGifUrl) animatedGifUrl = this._makeAbsolute(animatedGifUrl, 'https://www.wow.xxx');

            if (!gifPageUrl || !title || !animatedGifUrl || !gifId) return;
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: animatedGifUrl, preview_video: animatedGifUrl, source: this.name, type: 'gifs' });
        });
        return results;
    }
}

class MockDriver extends AbstractModule {
    get name() { return 'Mock'; }
    get firstpage() { return 1; }
    videoUrl(query: string, page: number) { return `http://mock.com/videos?q=${query}&page=${page}`; }
    videoParser() {
        const results: any[] = [];
        for (let i = 0; i < 10; i++) {
            results.push({
                id: `mock-video-${i}-${Date.now()}`,
                title: `Mock Video ${this.query} - Page ${this.options.page} - Item ${i + 1}`,
                url: `http://mock.com/video/${i}`,
                duration: '0:30',
                thumbnail: `https://placehold.co/320x180/00e5ff/000000?text=Mock+Video+${i+1}`,
                preview_video: `https://www.w3schools.com/html/mov_bbb.mp4`,
                source: 'Mock.com',
                type: 'videos',
            });
        }
        return results;
    }
    gifUrl(query: string, page: number) { return `http://mock.com/gifs?q=${query}&page=${page}`; }
    gifParser() {
        const results: any[] = [];
        for (let i = 0; i < 10; i++) {
            results.push({
                id: `mock-gif-${i}-${Date.now()}`,
                title: `Mock GIF ${this.query} - Page ${this.options.page} - Item ${i + 1}`,
                url: `http://mock.com/gif/${i}`,
                thumbnail: `https://placehold.co/320x180/ff00aa/000000?text=Mock+GIF+${i+1}`,
                preview_video: `https://i.giphy.com/media/VbnUQpnihPSIgIXuZv/giphy.gif`,
                source: 'Mock.com',
                type: 'gifs'
            });
        }
        return results;
    }
}


const drivers: {[key: string]: typeof AbstractModule} = {
    'pornhub': PornhubDriver,
    'sex': SexDriver,
    'redtube': RedtubeDriver,
    'xvideos': XvideosDriver,
    'xhamster': XhamsterDriver,
    'youporn': YoupornDriver,
    'wow.xxx': WowDriver,
    'mock': MockDriver,
};

const searchFlow = ai.defineFlow(
  {
    name: 'searchFlow',
    inputSchema: SearchInputSchema,
    outputSchema: SearchOutputSchema,
  },
  async (input) => {
    const { query, driver: driverName, type, page } = input;
    const DriverClass = drivers[driverName.toLowerCase()];
    if (!DriverClass) {
        throw new Error(`Unsupported driver: ${driverName}.`);
    }

    const driverInstance = new DriverClass({ query, page });

    let url = '';
    if (type === 'videos') {
        url = driverInstance.videoUrl(query, page);
    } else {
        url = driverInstance.gifUrl(query, page);
    }

    if (driverName.toLowerCase() === 'mock') {
        if(type === 'videos') {
            return driverInstance.videoParser(cheerio.load(''), '');
        }
        return driverInstance.gifParser(cheerio.load(''), '');
    }

    const response = await axios.get(url, {
        timeout: 30000,
        headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    });
    
    const $ = cheerio.load(response.data);

    if (type === 'videos') {
        return driverInstance.videoParser($, response.data);
    } else {
        return driverInstance.gifParser($, response.data);
    }
  }
);

export async function search(input: SearchInput): Promise<SearchOutput> {
    if (input.driver.toLowerCase() === 'mock') {
        const DriverClass = drivers['mock'];
        const driverInstance = new DriverClass({query: input.query, page: input.page});
        if (input.type === 'videos') {
            return driverInstance.videoParser(cheerio.load(''), '');
        } else {
            return driverInstance.gifParser(cheerio.load(''), '');
        }
    }
    return searchFlow(input);
}
