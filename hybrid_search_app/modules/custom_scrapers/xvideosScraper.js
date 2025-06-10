// modules/custom_scrapers/xvideosScraper.js
'use strict';

const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const cheerio = require('cheerio');

const log = {
    debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[XvideosScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args);},
    info: (message, ...args) => console.log(`[XvideosScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
    warn: (message, ...args) => console.warn(`[XvideosScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
};

class XvideosScraper extends AbstractModule.with(VideoMixin, GifMixin) {
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

    gifUrl(query, page) {
        const xvideosPage = Math.max(0, (parseInt(page, 10) || 1) - 1 + this.firstpage);
        const url = `${this.baseUrl}/gifs/${encodeURIComponent(query)}/${xvideosPage}`; // Example structure
        log.debug(`Constructed Xvideos GIF URL: ${url}`);
        return url;
    }

    async searchGifs(query, page) {
        const url = this.gifUrl(query, page);
        log.info(`Fetching HTML for Xvideos GIFs from: ${url}`);
        try {
            const html = await this._fetchHtml(url);
            const $ = cheerio.load(html);
            return this.gifParser($, html);
        } catch (error) {
            log.error(`Error in Xvideos searchGifs for query "${query}" on page ${page}: ${error.message}`);
            return [];
        }
    }

    gifParser($, rawData) {
        log.info(`Parsing Xvideos GIF data...`);
        const gifs = [];
        // Note: Xvideos GIF selectors are highly speculative and may need significant adjustment.
        $('div.gif-thumb-block, div.thumb-block').each((i, elem) => {
            const $elem = $(elem);
            const $titleLink = $elem.find('p.title a, a.thumb-name');
            const title = $titleLink.attr('title')?.trim() || $titleLink.text()?.trim();
            const gifPageUrl = $titleLink.attr('href');
            const imgElement = $elem.find('div.thumb img, div.thumb-inside img');
            let thumbnail = imgElement.attr('src'); // Static thumbnail
            let previewVideo = imgElement.attr('data-src'); // Often the animated GIF itself for Xvideos

            if (!previewVideo && thumbnail && thumbnail.endsWith('.gif')) { // If data-src is missing but src is a gif
                previewVideo = thumbnail;
            }
            if (previewVideo && !thumbnail) { // If only preview is available, use it as thumbnail too
                thumbnail = previewVideo;
            }

            if (title && gifPageUrl && previewVideo) {
                gifs.push({
                    title,
                    url: this._makeAbsolute(gifPageUrl, this.baseUrl),
                    thumbnail: this._makeAbsolute(thumbnail, this.baseUrl),
                    preview_video: this._makeAbsolute(previewVideo, this.baseUrl),
                    source: this.name,
                });
            } else {
                log.warn('Skipped an Xvideos GIF item due to missing critical data.');
            }
        });
        log.info(`Parsed ${gifs.length} GIF items from Xvideos.`);
        return gifs;
    }
}

module.exports = XvideosScraper;
