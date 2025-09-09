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
    $('div.phimage').each((index, element) => {
      const item = $(element);
      const linkElement = item.find('a').first();
      let videoUrl = linkElement.attr('href');
      let videoId = videoUrl?.match(/viewkey=([a-zA-Z0-9]+)/)?.[1];
      let title = linkElement.attr('title') || item.find('span.title').text().trim() || item.attr('data-video-title');
      const thumbElement = item.find('img').first();
      let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
      if (thumbnailUrl?.includes('nothumb')) thumbnailUrl = undefined;
      let duration = item.find('var.duration, span.duration').text().trim();
      let previewVideoUrl = linkElement.attr('data-mediabook') || linkElement.attr('data-preview-src') || item.find('video').attr('data-src');

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
    $('div.gifImageBlock, div.img-container').each((index, element) => {
      const item = $(element);
      const linkElement = item.find('a').first();
      let gifPageUrl = linkElement.attr('href');
      let gifId = item.attr('data-id') || gifPageUrl?.match(/\/(\d+)\//)?.[1];
      let title = item.find('img').attr('alt') || linkElement.attr('title') || 'Untitled GIF';
      let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
      if (animatedGifUrl?.endsWith('.gif')) {
        animatedGifUrl = this._makeAbsolute(animatedGifUrl, 'https://i.pornhub.com');
      } else {
        const videoPreview = item.find('video source').attr('src') || item.find('video').attr('data-src');
        if (videoPreview) animatedGifUrl = this._makeAbsolute(videoPreview, 'https://www.pornhub.com');
      }
      let staticThumbnailUrl = item.find('img').attr('data-thumb') || item.find('img').attr('src');
      if (!staticThumbnailUrl && animatedGifUrl?.endsWith('.gif')) staticThumbnailUrl = animatedGifUrl;
      if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, 'https://www.pornhub.com');

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
        url.searchParams.set('q', encodedQuery);
        url.searchParams.set('page', String(pageNumber));
        return url.href;
    }
    videoParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.pin').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let videoUrl = linkElement.attr('href');
            let videoId = videoUrl?.match(/\/video\/(\d+)\//)?.[1];
            let title = linkElement.attr('title') || item.find('span.title').text().trim() || item.attr('data-title');
            const thumbElement = item.find('img').first();
            let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
            if (thumbnailUrl?.includes('nothumb')) thumbnailUrl = undefined;
            let duration = item.find('span.duration').text().trim();
            let previewVideoUrl = linkElement.attr('data-preview') || item.find('video').attr('data-src');

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
        url.searchParams.set('q', encodedQuery);
        url.searchParams.set('page', String(pageNumber));
        return url.href;
    }
    gifParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.pin').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let gifPageUrl = linkElement.attr('href');
            let gifId = item.attr('data-id') || gifPageUrl?.match(/\/gif\/(\d+)\//)?.[1];
            let title = item.find('img').attr('alt') || linkElement.attr('title') || 'Untitled GIF';
            let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
            if (animatedGifUrl?.endsWith('.gif')) {
                animatedGifUrl = this._makeAbsolute(animatedGifUrl, 'https://cdn.sex.com');
            } else {
                const videoPreview = item.find('video source').attr('src') || item.find('video').attr('data-src');
                if (videoPreview) animatedGifUrl = this._makeAbsolute(videoPreview, 'https://www.sex.com');
            }
            let staticThumbnailUrl = item.find('img').attr('data-thumb') || item.find('img').attr('src');
            if (!staticThumbnailUrl && animatedGifUrl?.endsWith('.gif')) staticThumbnailUrl = animatedGifUrl;
            if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, 'https://www.sex.com');

            if (!gifPageUrl || !title || !animatedGifUrl || !gifId) return;
            gifPageUrl = this._makeAbsolute(gifPageUrl, 'https://www.sex.com');
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: this.name, type: 'gifs' });
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
        const url = new URL('https://www.redtube.com/search');
        url.searchParams.set('search', encodedQuery);
        url.searchParams.set('page', String(pageNumber));
        return url.href;
    }
    videoParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.video').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let videoUrl = linkElement.attr('href');
            let videoId = videoUrl?.match(/\/(\d+)\//)?.[1];
            let title = linkElement.attr('title') || item.find('span.title').text().trim() || item.attr('data-title');
            const thumbElement = item.find('img').first();
            let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
            if (thumbnailUrl?.includes('nothumb')) thumbnailUrl = undefined;
            let duration = item.find('span.duration').text().trim();
            let previewVideoUrl = linkElement.attr('data-preview') || item.find('video').attr('data-src');

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
        const url = new URL('https://www.redtube.com/gifs');
        url.searchParams.set('search', encodedQuery);
        url.searchParams.set('page', String(pageNumber));
        return url.href;
    }
    gifParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.gif').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let gifPageUrl = linkElement.attr('href');
            let gifId = item.attr('data-id') || gifPageUrl?.match(/\/gif\/(\d+)\//)?.[1];
            let title = item.find('img').attr('alt') || linkElement.attr('title') || 'Untitled GIF';
            let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
            if (animatedGifUrl?.endsWith('.gif')) {
                animatedGifUrl = this._makeAbsolute(animatedGifUrl, 'https://img.redtube.com');
            } else {
                const videoPreview = item.find('video source').attr('src') || item.find('video').attr('data-src');
                if (videoPreview) animatedGifUrl = this._makeAbsolute(videoPreview, 'https://www.redtube.com');
            }
            let staticThumbnailUrl = item.find('img').attr('data-thumb') || item.find('img').attr('src');
            if (!staticThumbnailUrl && animatedGifUrl?.endsWith('.gif')) staticThumbnailUrl = animatedGifUrl;
            if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, 'https://www.redtube.com');

            if (!gifPageUrl || !title || !animatedGifUrl || !gifId) return;
            gifPageUrl = this._makeAbsolute(gifPageUrl, 'https://www.redtube.com');
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: this.name, type: 'gifs' });
        });
        return results;
    }
}

class XvideosDriver extends AbstractModule {
    get name() { return 'XVideos'; }
    get firstpage() { return 1; }
    videoUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageNumber = Math.max(1, page || this.firstpage);
        const url = new URL('https://www.xvideos.com/video-search');
        url.searchParams.set('k', encodedQuery);
        url.searchParams.set('p', String(pageNumber - 1));
        return url.href;
    }
    videoParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.thumb-block').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let videoUrl = linkElement.attr('href');
            let videoId = videoUrl?.match(/\/video(\d+)\//)?.[1];
            let title = linkElement.attr('title') || item.find('p.title').text().trim() || item.attr('data-title');
            const thumbElement = item.find('img').first();
            let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
            if (thumbnailUrl?.includes('nothumb')) thumbnailUrl = undefined;
            let duration = item.find('span.duration').text().trim();
            let previewVideoUrl = thumbElement.attr('data-src') || item.find('video').attr('data-src');

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
        $('div.thumb-block, div.img-block').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let gifPageUrl = linkElement.attr('href');
            let gifId = item.attr('data-id') || gifPageUrl?.match(/\/gif(\d+)\//)?.[1];
            let title = item.find('img').attr('alt') || linkElement.attr('title') || 'Untitled GIF';
            let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
            if (animatedGifUrl?.endsWith('.gif')) {
                animatedGifUrl = this._makeAbsolute(animatedGifUrl, 'https://img-hw.xvideos-cdn.com');
            } else {
                const videoPreview = item.find('video source').attr('src') || item.find('video').attr('data-src');
                if (videoPreview) animatedGifUrl = this._makeAbsolute(videoPreview, 'https://www.xvideos.com');
            }
            let staticThumbnailUrl = item.find('img').attr('data-thumb') || item.find('img').attr('src');
            if (!staticThumbnailUrl && animatedGifUrl?.endsWith('.gif')) staticThumbnailUrl = animatedGifUrl;
            if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, 'https://www.xvideos.com');

            if (!gifPageUrl || !title || !animatedGifUrl || !gifId) return;
            gifPageUrl = this._makeAbsolute(gifPageUrl, 'https://www.xvideos.com');
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: this.name, type: 'gifs' });
        });
        return results;
    }
}

class XhamsterDriver extends AbstractModule {
    get name() { return 'Xhamster'; }
    get firstpage() { return 1; }
    videoUrl(query: string, page: number) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageNumber = Math.max(1, page || this.firstpage);
        const url = new URL('https://xhamster.com/search');
        url.searchParams.set('q', encodedQuery);
        url.searchParams.set('p', String(pageNumber));
        return url.href;
    }
    videoParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.video').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let videoUrl = linkElement.attr('href');
            let videoId = videoUrl?.match(/\/videos\/([a-zA-Z0-9-]+)\//)?.[1];
            let title = linkElement.attr('title') || item.find('span.title').text().trim() || item.attr('data-title');
            const thumbElement = item.find('img').first();
            let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
            if (thumbnailUrl?.includes('nothumb')) thumbnailUrl = undefined;
            let duration = item.find('span.duration').text().trim();
            let previewVideoUrl = linkElement.attr('data-preview') || item.find('video').attr('data-src');

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
        const url = new URL('https://xhamster.com/gifs');
        url.searchParams.set('q', encodedQuery);
        url.searchParams.set('p', String(pageNumber));
        return url.href;
    }
    gifParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.gif').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let gifPageUrl = linkElement.attr('href');
            let gifId = item.attr('data-id') || gifPageUrl?.match(/\/gifs\/([a-zA-Z0-9-]+)\//)?.[1];
            let title = item.find('img').attr('alt') || linkElement.attr('title') || 'Untitled GIF';
            let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
            if (animatedGifUrl?.endsWith('.gif')) {
                animatedGifUrl = this._makeAbsolute(animatedGifUrl, 'https://static.xhamster.com');
            } else {
                const videoPreview = item.find('video source').attr('src') || item.find('video').attr('data-src');
                if (videoPreview) animatedGifUrl = this._makeAbsolute(videoPreview, 'https://xhamster.com');
            }
            let staticThumbnailUrl = item.find('img').attr('data-thumb') || item.find('img').attr('src');
            if (!staticThumbnailUrl && animatedGifUrl?.endsWith('.gif')) staticThumbnailUrl = animatedGifUrl;
            if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, 'https://xhamster.com');

            if (!gifPageUrl || !title || !animatedGifUrl || !gifId) return;
            gifPageUrl = this._makeAbsolute(gifPageUrl, 'https://xhamster.com');
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
        const url = new URL('https://www.youporn.com/search');
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
            let title = linkElement.attr('title') || item.find('span.title').text().trim() || item.attr('data-title');
            const thumbElement = item.find('img').first();
            let thumbnailUrl = thumbElement.attr('data-src') || thumbElement.attr('src');
            if (thumbnailUrl?.includes('nothumb')) thumbnailUrl = undefined;
            let duration = item.find('span.duration').text().trim();
            let previewVideoUrl = linkElement.attr('data-preview') || item.find('video').attr('data-src');

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
        const url = new URL('https://www.youporn.com/gifs');
        url.searchParams.set('query', encodedQuery);
        url.searchParams.set('page', String(pageNumber));
        return url.href;
    }
    gifParser($: cheerio.CheerioAPI) {
        const results: any[] = [];
        $('div.gif-box, div.img-container').each((index, element) => {
            const item = $(element);
            const linkElement = item.find('a').first();
            let gifPageUrl = linkElement.attr('href');
            let gifId = item.attr('data-id') || gifPageUrl?.match(/\/gif\/(\d+)\//)?.[1];
            let title = item.find('img').attr('alt') || linkElement.attr('title') || 'Untitled GIF';
            let animatedGifUrl = item.find('img').attr('data-src') || item.find('img').attr('src');
            if (animatedGifUrl?.endsWith('.gif')) {
                animatedGifUrl = this._makeAbsolute(animatedGifUrl, 'https://cdn.youporn.com');
            } else {
                const videoPreview = item.find('video source').attr('src') || item.find('video').attr('data-src');
                if (videoPreview) animatedGifUrl = this._makeAbsolute(videoPreview, 'https://www.youporn.com');
            }
            let staticThumbnailUrl = item.find('img').attr('data-thumb') || item.find('img').attr('src');
            if (!staticThumbnailUrl && animatedGifUrl?.endsWith('.gif')) staticThumbnailUrl = animatedGifUrl;
            if (staticThumbnailUrl) staticThumbnailUrl = this._makeAbsolute(staticThumbnailUrl, 'https://www.youporn.com');

            if (!gifPageUrl || !title || !animatedGifUrl || !gifId) return;
            gifPageUrl = this._makeAbsolute(gifPageUrl, 'https://www.youporn.com');
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: this.name, type: 'gifs' });
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
    'mock': MockDriver,
};

export const SearchInputSchema = z.object({
  query: z.string().describe('The search query'),
  driver: z.string().describe('The search driver to use'),
  type: z.enum(['videos', 'gifs']).describe('The type of content to search for'),
  page: z.number().describe('The page number of results to fetch'),
});
export type SearchInput = z.infer<typeof SearchInputSchema>;

const MediaResultSchema = z.object({
    id: z.string(),
    title: z.string(),
    url: z.string(),
    duration: z.string().optional(),
    thumbnail: z.string().optional(),
    preview_video: z.string().optional(),
    source: z.string(),
    type: z.string(),
});

export const SearchOutputSchema = z.array(MediaResultSchema);
export type SearchOutput = z.infer<typeof SearchOutputSchema>;

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
