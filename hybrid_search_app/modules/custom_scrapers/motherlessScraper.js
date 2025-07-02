// modules/custom_scrapers/motherlessScraper.js
'use strict';

const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const cheerio = require('cheerio');

const log = {
    debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[MotherlessScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args);},
    info: (message, ...args) => console.log(`[MotherlessScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
    warn: (message, ...args) => console.warn(`[MotherlessScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
    error: (message, ...args) => console.error(`[MotherlessScraper ERROR] ${new Date().toISOString()}: ${message}`, ...args),
};

class MotherlessScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://motherless.com';
        log.debug(`MotherlessScraper instantiated. Query: "${this.query}", Page: ${this.page}`);
    }

    get name() { return 'Motherless'; }
    get firstpage() { return 1; }

    // --- Video Search Methods ---
    videoUrl(query, page) {
        const searchPage = page || this.firstpage;
        // Motherless uses /term/ for general searches, and then filters by type
        const url = `${this.baseUrl}/term/${encodeURIComponent(query)}?page=${searchPage}`;
        log.debug(`Constructed video URL: ${url}`);
        return url;
    }

    async searchVideos(query, page) {
        const url = this.videoUrl(query, page);
        log.info(`Fetching HTML for Motherless videos from: ${url}`);
        try {
            const html = await this._fetchHtml(url);
            const $ = cheerio.load(html);
            return this.videoParser($, html);
        } catch (error) {
            log.error(`Error in searchVideos for query "${query}" on page ${page}: ${error.message}`);
            return [];
        }
    }

    videoParser($, rawData) {
        log.info(`Parsing Motherless video data...`);
        const videos = [];
        // These selectors are placeholders and likely need adjustment based on actual Motherless HTML
        $('div.content-item.video').each((i, elem) => {
            const $elem = $(elem);
            const title = $elem.find('a.title').attr('title')?.trim();
            const videoPageUrl = $elem.find('a.title').attr('href');
            const duration = $elem.find('.duration').text()?.trim();
            const thumbnail = $elem.find('img.img-responsive').attr('src');
            const previewVideo = $elem.find('video.preview-video').attr('src'); // Assuming a video tag for preview

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
                log.warn('Skipped a Motherless video item due to missing title or URL.');
            }
        });
        log.info(`Parsed ${videos.length} video items from Motherless.`);
        return videos;
    }

    // --- GIF Search Methods ---
    gifUrl(query, page) {
        const searchPage = page || this.firstpage;
        // Motherless uses /term/ for general searches, and then filters by type
        const url = `${this.baseUrl}/term/${encodeURIComponent(query)}?page=${searchPage}`;
        log.debug(`Constructed GIF URL: ${url}`);
        return url;
    }

    async searchGifs(query, page) {
        const url = this.gifUrl(query, page);
        log.info(`Fetching HTML for Motherless GIFs from: ${url}`);
        try {
            const html = await this._fetchHtml(url);
            const $ = cheerio.load(html);
            return this.gifParser($, html);
        } catch (error) {
            log.error(`Error in searchGifs for query "${query}" on page ${page}: ${error.message}`);
            return [];
        }
    }

    gifParser($, rawData) {
        log.info(`Parsing Motherless GIF data...`);
        const gifs = [];
        // These selectors are placeholders and likely need adjustment based on actual Motherless HTML
        $('div.content-item.image').each((i, elem) => {
            const $elem = $(elem);
            const title = $elem.find('a.title').attr('title')?.trim();
            const gifPageUrl = $elem.find('a.title').attr('href');
            const thumbnail = $elem.find('img.img-responsive').attr('src');
            const previewVideo = $elem.find('video.preview-video').attr('src'); // Assuming a video tag for preview

            if (title && gifPageUrl) {
                gifs.push({
                    title,
                    url: this._makeAbsolute(gifPageUrl, this.baseUrl),
                    thumbnail: this._makeAbsolute(thumbnail, this.baseUrl),
                    preview_video: this._makeAbsolute(previewVideo, this.baseUrl),
                    source: this.name,
                });
            } else {
                log.warn('Skipped a Motherless GIF item due to missing title or URL.');
            }
        });
        log.info(`Parsed ${gifs.length} GIF items from Motherless.`);
        return gifs;
    }
}

module.exports = MotherlessScraper;