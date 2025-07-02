// modules/custom_scrapers/sexComScraper.js
'use strict';

const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const cheerio = require('cheerio');

const log = {
    debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[SexComScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args);},
    info: (message, ...args) => console.log(`[SexComScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
    warn: (message, ...args) => console.warn(`[SexComScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
    error: (message, ...args) => console.error(`[SexComScraper ERROR] ${new Date().toISOString()}: ${message}`, ...args),
};

class SexComScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.sex.com';
        log.debug(`SexComScraper instantiated. Query: "${this.query}", Page: ${this.page}`);
    }

    get name() { return 'SexCom'; }
    get firstpage() { return 1; }

    // --- Video Search Methods ---
    videoUrl(query, page) {
        const searchPage = page || this.firstpage;
        // Assuming sex.com uses a similar search URL structure
        const url = `${this.baseUrl}/search/videos?query=${encodeURIComponent(query)}&page=${searchPage}`;
        log.debug(`Constructed video URL: ${url}`);
        return url;
    }

    async searchVideos(query, page) {
        const url = this.videoUrl(query, page);
        log.info(`Fetching HTML for SexCom videos from: ${url}`);
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
        log.info(`Parsing SexCom video data...`);
        const videos = [];
        // These selectors are placeholders and likely need adjustment based on actual Sex.com HTML
        $('div.video-item').each((i, elem) => {
            const $elem = $(elem);
            const title = $elem.find('a.video-title').attr('title')?.trim();
            const videoPageUrl = $elem.find('a.video-title').attr('href');
            const duration = $elem.find('.duration').text()?.trim();
            const thumbnail = $elem.find('img.video-thumbnail').attr('src');
            const previewVideo = $elem.find('video.video-preview').attr('src'); // Assuming a video tag for preview

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
                log.warn('Skipped a SexCom video item due to missing title or URL.');
            }
        });
        log.info(`Parsed ${videos.length} video items from SexCom.`);
        return videos;
    }

    // --- GIF Search Methods ---
    gifUrl(query, page) {
        const searchPage = page || this.firstpage;
        // Assuming sex.com uses a similar search URL structure for GIFs
        const url = `${this.baseUrl}/search/gifs?query=${encodeURIComponent(query)}&page=${searchPage}`;
        log.debug(`Constructed GIF URL: ${url}`);
        return url;
    }

    async searchGifs(query, page) {
        const url = this.gifUrl(query, page);
        log.info(`Fetching HTML for SexCom GIFs from: ${url}`);
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
        log.info(`Parsing SexCom GIF data...`);
        const gifs = [];
        // These selectors are placeholders and likely need adjustment based on actual Sex.com HTML
        $('div.gif-item').each((i, elem) => {
            const $elem = $(elem);
            const title = $elem.find('a.gif-title').attr('title')?.trim();
            const gifPageUrl = $elem.find('a.gif-title').attr('href');
            const thumbnail = $elem.find('img.gif-thumbnail').attr('src');
            const previewVideo = $elem.find('video.gif-preview').attr('src'); // Assuming a video tag for preview

            if (title && gifPageUrl) {
                gifs.push({
                    title,
                    url: this._makeAbsolute(gifPageUrl, this.baseUrl),
                    thumbnail: this._makeAbsolute(thumbnail, this.baseUrl),
                    preview_video: this._makeAbsolute(previewVideo, this.baseUrl),
                    source: this.name,
                });
            } else {
                log.warn('Skipped a SexCom GIF item due to missing title or URL.');
            }
        });
        log.info(`Parsed ${gifs.length} GIF items from SexCom.`);
        return gifs;
    }
}

module.exports = SexComScraper;