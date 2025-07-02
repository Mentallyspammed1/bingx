// modules/custom_scrapers/youpornScraper.js
'use strict';

const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin'); // Uncommented for completeness
const cheerio = require('cheerio');

const log = {
    debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[YouPornScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args);},
    info: (message, ...args) => console.log(`[YouPornScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
    warn: (message, ...args) => console.warn(`[YouPornScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
    error: (message, ...args) => console.error(`[YouPornScraper ERROR] ${new Date().toISOString()}: ${message}`, ...args),
};

class YouPornScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.youporn.com';
        log.debug(`YouPornScraper instantiated. Query: "${this.query}", Page: ${this.page}`);
    }

    get name() { return 'YouPorn'; }
    get firstpage() { return 1; }

    // --- Video Search Methods ---
    videoUrl(query, page) {
        const searchPage = page || this.firstpage;
        const url = `${this.baseUrl}/search/?query=${encodeURIComponent(query)}&page=${searchPage}`;
        log.debug(`Constructed video URL: ${url}`);
        return url;
    }

    async searchVideos(query, page) {
        const url = this.videoUrl(query, page);
        log.info(`Fetching HTML for YouPorn videos from: ${url}`);
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
        log.info(`Parsing YouPorn video data...`);
        const videos = [];
        // These selectors are placeholders and likely need adjustment based on actual YouPorn HTML
        $('li.video-box').each((i, elem) => {
            const $elem = $(elem);
            const title = $elem.find('a.video-title').attr('title')?.trim();
            const videoPageUrl = $elem.find('a.video-title').attr('href');
            const duration = $elem.find('span.duration').text()?.trim();
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
                log.warn('Skipped a YouPorn video item due to missing title or URL.');
            }
        });
        log.info(`Parsed ${videos.length} video items from YouPorn.`);
        return videos;
    }

    // --- GIF Search Methods ---
    gifUrl(query, page) {
        const searchPage = page || this.firstpage;
        // YouPorn might not have a dedicated GIF search, or it might be integrated into video search
        // This is a placeholder URL, adjust if YouPorn has a specific GIF section
        const url = `${this.baseUrl}/gifs/search?query=${encodeURIComponent(query)}&page=${searchPage}`;
        log.debug(`Constructed GIF URL: ${url}`);
        return url;
    }

    async searchGifs(query, page) {
        const url = this.gifUrl(query, page);
        log.info(`Fetching HTML for YouPorn GIFs from: ${url}`);
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
        log.info(`Parsing YouPorn GIF data...`);
        const gifs = [];
        // These selectors are placeholders and likely need adjustment based on actual YouPorn HTML
        $('li.gif-box').each((i, elem) => {
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
                log.warn('Skipped a YouPorn GIF item due to missing title or URL.');
            }
        });
        log.info(`Parsed ${gifs.length} GIF items from YouPorn.`);
        return gifs;
    }
}

module.exports = YouPornScraper;