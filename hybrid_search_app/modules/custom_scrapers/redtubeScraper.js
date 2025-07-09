// modules/custom_scrapers/redtubeScraper.js
'use strict';

const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const cheerio = require('cheerio');

const log = {
    debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[RedtubeScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args);},
    info: (message, ...args) => console.log(`[RedtubeScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
    warn: (message, ...args) => console.warn(`[RedtubeScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
    error: (message, ...args) => console.error(`[RedtubeScraper ERROR] ${new Date().toISOString()}: ${message}`, ...args),
};

class RedtubeScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        log.debug(`RedtubeScraper instantiated. Query: "${this.query}", Page: ${this.page}`);
    }

    get name() { return 'Redtube'; }
    get baseUrl() { return 'https://www.redtube.com'; }
    get firstpage() { return 1; }

    // --- Video Search Methods ---
    videoUrl(query, page) {
        const searchPage = page || this.firstpage;
        const url = `${this.baseUrl}/?search=${encodeURIComponent(query)}&page=${searchPage}`;
        log.debug(`Constructed video URL: ${url}`);
        return url;
    }

    async searchVideos(query, page) {
        const url = this.videoUrl(query, page);
        log.info(`Fetching HTML for Redtube videos from: ${url}`);
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
        log.info(`Parsing Redtube video data...`);
        const videos = [];
        // These selectors are placeholders and likely need adjustment based on actual Redtube HTML
        $('div.video_item').each((i, elem) => {
            const $elem = $(elem);
            const title = $elem.find('a.video_title').attr('title')?.trim();
            const videoPageUrl = $elem.find('a.video_title').attr('href');
            const duration = $elem.find('span.duration').text()?.trim();
            const thumbnail = $elem.find('img.video_thumbnail').attr('src');
            const previewVideo = $elem.find('video.video_preview').attr('src'); // Assuming a video tag for preview

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
                log.warn('Skipped a Redtube video item due to missing title or URL.');
            }
        });
        log.info(`Parsed ${videos.length} video items from Redtube.`);
        return videos;
    }

    // --- GIF Search Methods ---
    gifUrl(query, page) {
        const searchPage = page || this.firstpage;
        // Redtube is primarily video-focused, but including a placeholder for consistency
        const url = `${this.baseUrl}/gifs/?search=${encodeURIComponent(query)}&page=${searchPage}`;
        log.debug(`Constructed GIF URL: ${url}`);
        return url;
    }

    async searchGifs(query, page) {
        const url = this.gifUrl(query, page);
        log.info(`Fetching HTML for Redtube GIFs from: ${url}`);
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
        log.info(`Parsing Redtube GIF data...`);
        const gifs = [];
        // These selectors are placeholders and likely need adjustment based on actual Redtube HTML
        $('div.gif_item').each((i, elem) => {
            const $elem = $(elem);
            const title = $elem.find('a.gif_title').attr('title')?.trim();
            const gifPageUrl = $elem.find('a.gif_title').attr('href');
            const thumbnail = $elem.find('img.gif_thumbnail').attr('src');
            const previewVideo = $elem.find('video.gif_preview').attr('src'); // Assuming a video tag for preview

            if (title && gifPageUrl) {
                gifs.push({
                    title,
                    url: this._makeAbsolute(gifPageUrl, this.baseUrl),
                    thumbnail: this._makeAbsolute(thumbnail, this.baseUrl),
                    preview_video: this._makeAbsolute(previewVideo, this.baseUrl),
                    source: this.name,
                });
            } else {
                log.warn('Skipped a Redtube GIF item due to missing title or URL.');
            }
        });
        log.info(`Parsed ${gifs.length} GIF items from Redtube.`);
        return gifs;
    }
}

module.exports = RedtubeScraper;