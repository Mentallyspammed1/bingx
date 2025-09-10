'use server';
/**
 * @fileOverview A search flow for scraping content.
 *
 * - search - A function that handles the scraping process.
 */

import axios from 'axios';
import * as cheerio from 'cheerio';
import type { SearchInput, SearchOutput, MediaItem } from '@/ai/types';

// Helper function to make URLs absolute
function makeAbsolute(urlString: string | undefined, baseUrl: string): string | undefined {
  if (!urlString || typeof urlString !== 'string') return undefined;
  if (urlString.startsWith('data:')) return urlString;
  if (urlString.startsWith('//')) return `https:${urlString}`;
  if (urlString.startsWith('http:') || urlString.startsWith('https:')) return urlString;
  try {
    return new URL(urlString, baseUrl).href;
  } catch (e) {
    return undefined;
  }
}

// --- Driver Definitions ---

const pornhub = {
  name: 'Pornhub',
  videoUrl: (query: string, page: number) => `https://www.pornhub.com/video/search?search=${encodeURIComponent(query)}&page=${page}`,
  videoParser: ($: cheerio.CheerioAPI): MediaItem[] => {
    const results: MediaItem[] = [];
    $('li.videoBox').each((_, element) => {
      const item = $(element);
      const link = item.find('a').first();
      const videoUrl = makeAbsolute(link.attr('href'), 'https://www.pornhub.com');
      const videoId = videoUrl?.match(/viewkey=([a-zA-Z0-9]+)/)?.[1];
      const title = item.find('span.title a').text().trim();
      const thumbnail = makeAbsolute(item.find('img').attr('data-src'), 'https://www.pornhub.com');
      const duration = item.find('var.duration').text().trim();
      const preview_video = makeAbsolute(item.find('img').attr('data-mediabook'), 'https://www.pornhub.com');

      if (videoUrl && title && thumbnail && videoId && !thumbnail.includes('nothumb')) {
        results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video, source: 'Pornhub', type: 'videos' });
      }
    });
    return results;
  },
  gifUrl: (query: string, page: number) => `https://www.pornhub.com/gifs/search?search=${encodeURIComponent(query)}&page=${page}`,
  gifParser: ($: cheerio.CheerioAPI): MediaItem[] => {
    const results: MediaItem[] = [];
    $('li.gifVideoBlock').each((_, element) => {
      const item = $(element);
      const link = item.find('a').first();
      const gifPageUrl = makeAbsolute(link.attr('href'), 'https://www.pornhub.com');
      const gifId = item.attr('data-gif-id') || gifPageUrl?.match(/\/view_gif\/(\d+)/)?.[1];
      const title = link.attr('title') || 'Untitled GIF';
      const animatedGifUrl = makeAbsolute(item.find('video').attr('data-src'), 'https://www.pornhub.com');
      const staticThumbnailUrl = makeAbsolute(item.find('img').attr('data-src'), 'https://www.pornhub.com');

      if (gifPageUrl && title && animatedGifUrl && gifId) {
        results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: 'Pornhub', type: 'gifs' });
      }
    });
    return results;
  }
};

const xvideos = {
  name: 'XVideos',
  videoUrl: (query: string, page: number) => `https://www.xvideos.com/?k=${encodeURIComponent(query.replace(/\s+/g, '+'))}&p=${page > 1 ? page - 1 : ''}`,
  videoParser: ($: cheerio.CheerioAPI): MediaItem[] => {
    const results: MediaItem[] = [];
    $('div.thumb-block').each((_, element) => {
      const item = $(element);
      const link = item.find('p.title a').first();
      const videoUrl = makeAbsolute(link.attr('href'), 'https://www.xvideos.com');
      const videoId = item.attr('data-id');
      const title = link.attr('title');
      const img = item.find('div.thumb img').first();
      const thumbnail = makeAbsolute(img.attr('data-src') || img.attr('src'), 'https://www.xvideos.com');
      const duration = item.find('span.duration').text().trim();
      const preview_video = makeAbsolute(img.attr('data-previewvideo'), 'https://www.xvideos.com');

      if (videoUrl && title && thumbnail && videoId) {
        results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video, source: 'XVideos', type: 'videos' });
      }
    });
    return results;
  },
  gifUrl: (query: string, page: number) => `https://www.xvideos.com/gifs/${query ? 'search/' + encodeURIComponent(query) : ''}?p=${page - 1}`,
  gifParser: ($: cheerio.CheerioAPI): MediaItem[] => {
    const results: MediaItem[] = [];
    $('div.gif-thumb-block').each((_, element) => {
      const item = $(element);
      const link = item.find('a').first();
      const gifPageUrl = makeAbsolute(link.attr('href'), 'https://www.xvideos.com');
      const gifId = item.attr('data-id');
      const title = item.find('p.gif-title').text().trim() || 'Untitled GIF';
      const img = item.find('img').first();
      const animatedGifUrl = makeAbsolute(img.attr('data-src'), 'https://www.xvideos.com');
      
      if (gifPageUrl && title && animatedGifUrl && gifId) {
        results.push({ id: gifId, title, url: gifPageUrl, thumbnail: animatedGifUrl, preview_video: animatedGifUrl, source: 'XVideos', type: 'gifs' });
      }
    });
    return results;
  }
};

const redtube = {
  name: 'Redtube',
  videoUrl: (query: string, page: number) => `https://www.redtube.com/?search=${encodeURIComponent(query)}&page=${page}`,
  videoParser: ($: cheerio.CheerioAPI): MediaItem[] => {
    const results: MediaItem[] = [];
    $('div.video_ui_component').each((_, element) => {
        const item = $(element);
        const link = item.find('a.video_link').first();
        const videoUrl = makeAbsolute(link.attr('href'), 'https://www.redtube.com');
        const videoId = item.attr('data-video_id');
        const title = item.find('.video_title').text().trim();
        const img = item.find('img.video_thumb').first();
        const thumbnail = makeAbsolute(img.attr('data-src') || img.attr('src'), 'https://www.redtube.com');
        const duration = item.find('span.duration').text().trim();
        const preview_video = makeAbsolute(item.find('img.preview_thumb').attr('data-src'), 'https://www.redtube.com');

        if (videoUrl && title && thumbnail && videoId) {
            results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video, source: 'Redtube', type: 'videos' });
        }
    });
    return results;
  },
  gifUrl: (query: string, page: number) => `https://www.redtube.com/gifs/search?search=${encodeURIComponent(query)}&page=${page}`,
  gifParser: ($: cheerio.CheerioAPI): MediaItem[] => {
    const results: MediaItem[] = [];
    $('div.gif_card_wrapper').each((_, element) => {
        const item = $(element);
        const link = item.find('a').first();
        const gifPageUrl = makeAbsolute(link.attr('href'), 'https://www.redtube.com');
        const gifId = item.attr('data-id');
        const title = item.find('.gif_card_title').text().trim() || 'Untitled GIF';
        const staticThumbnailUrl = makeAbsolute(item.find('img.gif_card_thumb').attr('src'), 'https://www.redtube.com');
        const animatedGifUrl = makeAbsolute(item.find('video.gif_preview_video source').attr('src'), 'https://www.redtube.com');

        if (gifPageUrl && title && animatedGifUrl && gifId) {
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: 'Redtube', type: 'gifs' });
        }
    });
    return results;
  }
};

const sex = {
  name: 'Sex.com',
  videoUrl: (query: string, page: number) => `https://www.sex.com/search/videos?query=${encodeURIComponent(query)}&page=${page}`,
  videoParser: ($: cheerio.CheerioAPI): MediaItem[] => {
    const results: MediaItem[] = [];
    $('div.thumbnail_container').each((_, element) => {
        const item = $(element);
        const link = item.find('a.video_link').first();
        const videoUrl = makeAbsolute(link.attr('href'), 'https://www.sex.com');
        const videoId = item.attr('data-id');
        const title = item.find('div.title').text().trim();
        const img = item.find('img.video_thumb').first();
        const thumbnail = makeAbsolute(img.attr('data-src') || img.attr('src'), 'https://www.sex.com');
        const duration = item.find('div.duration').text().trim();
        const preview_video = makeAbsolute(item.find('img.preview_thumb').attr('data-src'), 'https://www.sex.com');

        if (videoUrl && title && thumbnail && videoId) {
            results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video, source: 'Sex.com', type: 'videos' });
        }
    });
    return results;
  },
  gifUrl: (query: string, page: number) => `https://www.sex.com/search/gifs?query=${encodeURIComponent(query)}&page=${page}`,
  gifParser: ($: cheerio.CheerioAPI): MediaItem[] => {
    const results: MediaItem[] = [];
    $('div.masonry-thumb').each((_, element) => {
        const item = $(element);
        const link = item.find('a').first();
        const gifPageUrl = makeAbsolute(link.attr('href'), 'https://www.sex.com');
        const gifId = item.attr('data-id');
        const img = item.find('img').first();
        const title = img.attr('alt') || 'Untitled GIF';
        const animatedGifUrl = makeAbsolute(img.attr('data-src') || img.attr('src'), 'https://www.sex.com');

        if (gifPageUrl && title && animatedGifUrl && gifId) {
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: animatedGifUrl, preview_video: animatedGifUrl, source: 'Sex.com', type: 'gifs' });
        }
    });
    return results;
  }
};

const xhamster = {
  name: 'xHamster',
  videoUrl: (query: string, page: number) => `https://xhamster.com/search/${encodeURIComponent(query)}?page=${page}`,
  videoParser: ($: cheerio.CheerioAPI): MediaItem[] => {
    const results: MediaItem[] = [];
    $('a.video-thumb__image-container').each((_, element) => {
        const item = $(element);
        const videoUrl = makeAbsolute(item.attr('href'), 'https://xhamster.com');
        const videoId = videoUrl?.match(/\/videos\/(.+?)-\d+/)?.[1];
        const img = item.find('img.video-thumb__img');
        const title = img.attr('alt');
        const thumbnail = makeAbsolute(img.attr('src'), 'https://xhamster.com');
        const duration = item.find('.video-thumb__duration').text().trim();
        const preview_video_url_attr = item.attr('onmouseover');
        let preview_video = null;
        if(preview_video_url_attr) {
          const match = preview_video_url_attr.match(/showVideoPreview\([^,]+,\s*'([^']+)'/);
          if (match && match[1]) {
            preview_video = makeAbsolute(match[1], 'https://xhamster.com');
          }
        }

        if (videoUrl && title && thumbnail && videoId) {
            results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video, source: 'xHamster', type: 'videos' });
        }
    });
    return results;
  },
  gifUrl: (query: string, page: number) => `https://xhamster.com/gifs/search?q=${encodeURIComponent(query)}&page=${page}`,
  gifParser: ($: cheerio.CheerioAPI): MediaItem[] => {
    const results: MediaItem[] = [];
    $('a.gif-thumb__image').each((_, element) => {
        const item = $(element);
        const gifPageUrl = makeAbsolute(item.attr('href'), 'https://xhamster.com');
        const gifId = gifPageUrl?.match(/\/gifs\/(.+)/)?.[1];
        const img = item.find('img');
        const title = img.attr('alt') || 'Untitled GIF';
        const staticThumbnailUrl = makeAbsolute(img.attr('src'), 'https://xhamster.com');
        const animatedGifUrl = makeAbsolute(item.attr('data-preview-url'), 'https://xhamster.com');

        if (gifPageUrl && title && animatedGifUrl && gifId) {
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: 'xHamster', type: 'gifs' });
        }
    });
    return results;
  }
};

const youporn = {
  name: 'YouPorn',
  videoUrl: (query: string, page: number) => `https://www.youporn.com/search/?query=${encodeURIComponent(query)}&page=${page}`,
  videoParser: ($: cheerio.CheerioAPI): MediaItem[] => {
    const results: MediaItem[] = [];
    $('div.video-box').each((_, element) => {
        const item = $(element);
        const link = item.find('a').first();
        const videoUrl = makeAbsolute(link.attr('href'), 'https://www.youporn.com');
        const videoId = videoUrl?.match(/\/watch\/(\d+)\//)?.[1];
        const title = item.find('.video-box-title').text().trim();
        const img = item.find('img').first();
        const thumbnail = makeAbsolute(img.attr('data-src') || img.attr('src'), 'https://www.youporn.com');
        const duration = item.find('div.duration').text().trim();
        const preview_video = makeAbsolute(link.attr('data-preview'), 'https://www.youporn.com');

        if (videoUrl && title && thumbnail && videoId) {
            results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video, source: 'YouPorn', type: 'videos' });
        }
    });
    return results;
  },
  gifUrl: (query: string, page: number) => `https://www.youporn.com/search/gifs/?query=${encodeURIComponent(query)}&page=${page}`,
  gifParser: ($: cheerio.CheerioAPI): MediaItem[] => {
    const results: MediaItem[] = [];
    $('div.gif-box').each((_, element) => {
        const item = $(element);
        const link = item.find('a').first();
        const gifPageUrl = makeAbsolute(link.attr('href'), 'https://www.youporn.com');
        const gifId = gifPageUrl?.match(/\/gif\/(\d+)\//)?.[1];
        const title = link.attr('title') || 'Untitled GIF';
        const animatedGifUrl = makeAbsolute(item.find('img').attr('data-src'), 'https://www.youporn.com');

        if (gifPageUrl && title && animatedGifUrl && gifId) {
            results.push({ id: gifId, title, url: gifPageUrl, thumbnail: animatedGifUrl, preview_video: animatedGifUrl, source: 'YouPorn', type: 'gifs' });
        }
    });
    return results;
  }
};

const wow = {
  name: 'Wow.xxx',
  videoUrl: (query: string, page: number) => `https://www.wow.xxx/search/?q=${encodeURIComponent(query)}${page > 1 ? `&page=${page}` : ''}`,
  videoParser: ($: cheerio.CheerioAPI): MediaItem[] => {
      const results: MediaItem[] = [];
      $('div.video-item').each((_, element) => {
          const item = $(element);
          const link = item.find('a').first();
          const videoUrl = makeAbsolute(link.attr('href'), 'https://www.wow.xxx');
          const videoId = videoUrl?.match(/video\/(.+?)\/$/)?.[1];
          const title = item.find('.video-title').text().trim();
          const img = item.find('img').first();
          const thumbnail = makeAbsolute(img.attr('data-src') || img.attr('src'), 'https://www.wow.xxx');
          const duration = item.find('.video-duration').text().trim();
          const preview_video = makeAbsolute(img.attr('data-preview'), 'https://www.wow.xxx');

          if (videoUrl && title && thumbnail && videoId) {
              results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video, source: 'Wow.xxx', type: 'videos' });
          }
      });
      return results;
  },
  gifUrl: (query: string, page: number) => `https://www.wow.xxx/search/gifs/?q=${encodeURIComponent(query)}${page > 1 ? `&page=${page}` : ''}`,
  gifParser: ($: cheerio.CheerioAPI): MediaItem[] => {
      const results: MediaItem[] = [];
      $('div.gif-item').each((_, element) => {
          const item = $(element);
          const link = item.find('a').first();
          const gifPageUrl = makeAbsolute(link.attr('href'), 'https://www.wow.xxx');
          const gifId = gifPageUrl?.match(/\/gif\/(.+?)\/$/)?.[1];
          const img = item.find('img').first();
          const title = img.attr('alt') || 'Untitled GIF';
          const animatedGifUrl = makeAbsolute(img.attr('data-src') || img.attr('src'), 'https://www.wow.xxx');

          if (gifPageUrl && title && animatedGifUrl && gifId) {
              results.push({ id: gifId, title, url: gifPageUrl, thumbnail: animatedGifUrl, preview_video: animatedGifUrl, source: 'Wow.xxx', type: 'gifs' });
          }
      });
      return results;
  }
};


const mock = {
    name: 'Mock',
    videoUrl: (query: string, page: number) => `http://mock.com/videos?q=${query}&page=${page}`,
    videoParser: (input: SearchInput): MediaItem[] => {
        return Array.from({ length: 10 }, (_, i) => ({
            id: `mock-video-${i}-${Date.now()}`,
            title: `Mock Video ${input.query} - Page ${input.page} - Item ${i + 1}`,
            url: `http://mock.com/video/${i}`,
            duration: '0:30',
            thumbnail: `https://placehold.co/320x180/6353F2/FFFFFF?text=Mock+Video+${i+1}`,
            preview_video: `https://www.w3schools.com/html/mov_bbb.mp4`,
            source: 'Mock',
            type: 'videos',
        }));
    },
    gifUrl: (query: string, page: number) => `http://mock.com/gifs?q=${query}&page=${page}`,
    gifParser: (input: SearchInput): MediaItem[] => {
        return Array.from({ length: 10 }, (_, i) => ({
            id: `mock-gif-${i}-${Date.now()}`,
            title: `Mock GIF ${input.query} - Page ${input.page} - Item ${i + 1}`,
            url: `http://mock.com/gif/${i}`,
            thumbnail: `https://placehold.co/320x180/BE52F2/FFFFFF?text=Mock+GIF+${i+1}`,
            preview_video: `https://i.giphy.com/media/VbnUQpnihPSIgIXuZv/giphy.gif`,
            source: 'Mock',
            type: 'gifs'
        }));
    }
}

const drivers: Record<string, any> = { pornhub, xvideos, redtube, sex, xhamster, youporn, 'wow.xxx': wow, mock };

export async function search(input: SearchInput): Promise<SearchOutput> {
  const { query, driver: driverName, type, page } = input;
  const driver = drivers[driverName.toLowerCase()];

  if (!driver) {
    throw new Error(`Unsupported driver: ${driverName}.`);
  }

  const isVideos = type === 'videos';
  const urlFn = isVideos ? driver.videoUrl : driver.gifUrl;
  const parserFn = isVideos ? driver.videoParser : driver.gifParser;

  if (!urlFn || !parserFn) {
    throw new Error(`Driver ${driverName} does not support type '${type}'.`);
  }

  if (driverName.toLowerCase() === 'mock') {
    return parserFn(input);
  }

  const url = urlFn(query, page);

  try {
    const response = await axios.get(url, {
      timeout: 30000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
      }
    });

    const $ = cheerio.load(response.data);
    return parserFn($);
    
  } catch (error: any) {
    console.error(`Error fetching from ${driver.name}: ${error.message}`);
    if (error.response?.status === 404) {
      return [];
    }
    throw new Error(`Failed to fetch results from ${driver.name}. The site may be down or has changed its structure.`);
  }
}
