// modules/custom_scrapers/pornhubScraper.js
'use strict';

const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const cheerio = require('cheerio');

class PornhubScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.pornhub.com';
        // Initialize this.log directly in the constructor
        this.log = {
            debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[PornhubScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args);},
            info: (message, ...args) => console.log(`[PornhubScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
            warn: (message, ...args) => console.warn(`[PornhubScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
            error: (message, ...args) => console.error(`[PornhubScraper ERROR] ${new Date().toISOString()}: ${message}`, ...args),
        };
        this.log.debug(`PornhubScraper instantiated. Query: "${this.query}", Page: ${this.page}`);
    }

    get name() { return 'Pornhub'; }
    get firstpage() { return 1; }

    videoUrl(query, page) {
        const searchPage = page || this.firstpage;
        const url = `${this.baseUrl}/video/search?search=${encodeURIComponent(query)}&page=${searchPage}`;
        this.log.debug(`Constructed video URL: ${url}`);
        return url;
    }

    async searchVideos(query, page) {
        const url = this.videoUrl(query, page);
        this.log.info(`Fetching HTML for Pornhub videos from: ${url}`);
        try {
            const html = await this._fetchHtml(url);
            const $ = cheerio.load(html);
            return this.videoParser($, html);
        } catch (error) {
            this.log.error(`Error in searchVideos for query "${query}" on page ${page}: ${error.message}`);
            return [];
        }
    }

    videoParser($, rawData) {
        this.log.info(`Parsing Pornhub video data...`);
        const videos = [];
        $('ul.videos.search-video-thumbs li.pcVideoListItem').each((i, elem) => {
            const $elem = $(elem);
            const title = $elem.find('span.title a').attr('title')?.trim();
            const videoPageUrl = $elem.find('span.title a').attr('href');
            const duration = $elem.find('var.duration').text()?.trim();
            let thumbnail = $elem.find('img').attr('data-mediumthumb') || $elem.find('img').attr('data-src') || $elem.find('img').attr('src');
            let previewVideo = $elem.find('a.linkVideoThumb').attr('data-mediabook') || $elem.find('img').attr('data-previewvideo');

            if (title && videoPageUrl) {
                videos.push({
                    title,
                    url: this._makeAbsolute(videoPageUrl, this.baseUrl),
                    thumbnail: this._makeAbsolute(thumbnail, this.baseUrl),
                    duration: duration || 'N/A',
                    preview_video: this._makeAbsolute(previewVideo, this.baseUrl),
                    source: this.name,
                });
            } else {
                this.log.warn('Skipped a Pornhub video item due to missing title or URL.');
            }
        });
        this.log.info(`Parsed ${videos.length} video items from Pornhub.`);
        return videos;
    }

    gifUrl(query, page) {
        const searchPage = page || this.firstpage;
        const url = `${this.baseUrl}/gifs/search?search=${encodeURIComponent(query)}&page=${searchPage}`;
        this.log.debug(`Constructed GIF URL: ${url}`);
        return url;
    }

    async searchGifs(query, page) {
        const url = this.gifUrl(query, page);
        this.log.info(`Fetching HTML for Pornhub GIFs from: ${url}`);
        try {
            const html = await this._fetchHtml(url);
            const $ = cheerio.load(html);
            return this.gifParser($, html);
        } catch (error) {
            this.log.error(`Error in searchGifs for query "${query}" on page ${page}: ${error.message}`);
            return [];
        }
    }

    gifParser($, rawData) {
        this.log.info(`Parsing Pornhub GIF data...`);
        const gifs = [];
        $('ul.gifs.gifLink li.gifVideoBlock').each((i, elem) => {
            const $elem = $(elem);
            const title = $elem.find('a').attr('title')?.trim() || $elem.find('.title').text()?.trim();
            const gifPageUrl = $elem.find('a').attr('href');
            let previewVideo = $elem.find('video[data-webm]').attr('data-webm') || $elem.find('video source[type="video/webm"]').attr('src');
            let thumbnail = $elem.find('img.thumb').attr('data-src') || $elem.find('img.thumb').attr('src');

            if (title && gifPageUrl) {
                gifs.push({
                    title,
                    url: this._makeAbsolute(gifPageUrl, this.baseUrl),
                    thumbnail: this._makeAbsolute(thumbnail, this.baseUrl),
                    preview_video: this._makeAbsolute(previewVideo, this.baseUrl),
                    source: this.name,
                });
            } else {
                this.log.warn('Skipped a Pornhub GIF item due to missing title or URL.');
            }
        });
        this.log.info(`Parsed ${gifs.length} GIF items from Pornhub.`);
        return gifs;
    }
}

module.exports = PornhubScraper;
