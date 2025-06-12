// modules/custom_scrapers/xvideosScraper.js
'use strict';

const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
// GifMixin has been removed as Xvideos does not have a reliable separate GIF API
const cheerio = require('cheerio');

const log = {
    debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[XvideosScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args);},
    info: (message, ...args) => console.log(`[XvideosScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
    warn: (message, ...args) => console.warn(`[XvideosScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
};

class XvideosScraper extends AbstractModule.with(VideoMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.xvideos.com';
        log.debug(`XvideosScraper instantiated. Query: "${this.query}", Page: ${this.page}`);
    }

    get name() { return 'Xvideos'; }
    get firstpage() { return 0; } // Xvideos 'p' param is 0-indexed

    videoUrl(query, page) {
        const xvideosPage = Math.max(0, (parseInt(page, 10) || 1) - 1 + this.firstpage); // Adjust for 0-indexed
        const url = `${this.baseUrl}/?k=${encodeURIComponent(query)}&p=${xvideosPage}`;
        log.debug(`Constructed Xvideos video URL: ${url}`);
        return url;
    }

    async searchVideos(query, page) {
        const url = this.videoUrl(query, page);
        log.info(`Fetching HTML for Xvideos videos from: ${url}`);
        try {
            const html = await this._fetchHtml(url);
            const $ = cheerio.load(html);
            return this.videoParser($, html);
        } catch (error) {
            log.error(`Error in Xvideos searchVideos for query "${query}" on page ${page}: ${error.message}`);
            return [];
        }
    }

    videoParser($, rawData) {
        log.info(`Parsing Xvideos video data...`);
        const videos = [];
        $('div.thumb-block').each((i, elem) => {
            const $elem = $(elem);
            const $titleLink = $elem.find('p.title a');
            const title = $titleLink.attr('title')?.trim();
            const videoPageUrl = $titleLink.attr('href');
            const duration = $elem.find('span.duration').text()?.trim();
            const thumbnail = $elem.find('div.thumb-inside img').attr('data-src');
            const previewVideo = $elem.find('div.thumb-inside img').attr('data-videopreview'); // Often a .gif or short .mp4

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
                log.warn('Skipped an Xvideos video item due to missing title or URL.');
            }
        });
        log.info(`Parsed ${videos.length} video items from Xvideos.`);
        return videos;
    }

    // Removed gifUrl, searchGifs, and gifParser methods as Xvideos does not have a distinct GIF search.
    // GIFs appear as short videos and are handled by the video search and parsing logic.
}

module.exports = XvideosScraper;
