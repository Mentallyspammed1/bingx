// modules/custom_scrapers/xhamsterScraper.js
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const log = require('../../core/log'); // Assuming log is in core

class XhamsterScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://xhamster.com';
        log.debug(`${this.name} scraper initialized`);
    }

    get name() {
        return 'Xhamster';
    }

    get firstpage() {
        // Assuming 1-indexed pagination, can be adjusted later
        return 1;
    }

    videoUrl(query, page) {
        const url = `${this.baseUrl}/search/${encodeURIComponent(query)}?page=${page}`;
        log.debug(`${this.name} video URL: ${url}`);
        return url;
    }

    async videoParser($, rawHtmlOrJsonData) {
        log.info(`Parsing ${this.name} video page...`);
        const videos = [];
        // Updated selector for the new structure
        $('div.video-item').each((i, elem) => {
            try {
                const $elem = $(elem);
                const title = $elem.find('a.video-title').text().trim();
                let url = $elem.find('a.video-title').attr('href');
                url = this._makeAbsolute(url, this.baseUrl);

                let thumbnail = $elem.find('img').attr('src');
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                const duration = ''; // Duration not available in the new structure

                // Preview video not available, fallback to thumbnail
                const preview_video = thumbnail;

                if (title && url) {
                    videos.push({
                        title,
                        url,
                        thumbnail,
                        duration,
                        preview_video: preview_video || thumbnail,
                        source: this.name,
                    });
                }
            } catch (e) {
                log.warn(`Error parsing video item on ${this.name}: ${e.message}`);
            }
        });
        log.info(`Found ${videos.length} videos on ${this.name}`);
        if (videos.length === 0 && rawHtmlOrJsonData && rawHtmlOrJsonData.length > 100) {
            log.warn(`No videos found for ${this.name}, but received HTML. Selectors might be outdated.`);
        }
        return videos;
    }

    gifUrl(query, page) {
        // Assuming GIF search is similar to video, or a specific path like /gifs/search/
        // This needs verification on the actual xhamster site.
        // For now, let's assume it's /gifs/
        const url = `${this.baseUrl}/gifs/search/${encodeURIComponent(query)}?page=${page}`;
        log.debug(`${this.name} GIF URL: ${url}`);
        return url;
    }

    async gifParser($, rawHtmlOrJsonData) {
        log.info(`Parsing ${this.name} GIF page...`);
        const gifs = [];
        // Example selectors, needs verification
        $('div.gif-thumb').each((i, elem) => {
            try {
                const $elem = $(elem);
                const title = $elem.find('a.gif-thumb-link__image').attr('title') || $elem.find('a.gif-thumb-link__image img').attr('alt');
                let url = $elem.find('a.gif-thumb-link__image').attr('href');
                url = this._makeAbsolute(url, this.baseUrl);

                let thumbnail = $elem.find('a.gif-thumb-link__image img').attr('src');
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                // For GIFs, preview_video is often the animated GIF itself
                let preview_video = $elem.find('a.gif-thumb-link__image img').attr('data-src') || $elem.find('a.gif-thumb-link__image img').attr('src');
                preview_video = this._makeAbsolute(preview_video, this.baseUrl);

                if (title && url) {
                    gifs.push({
                        title,
                        url,
                        thumbnail,
                        preview_video,
                        source: this.name,
                    });
                }
            } catch (e) {
                log.warn(`Error parsing GIF item on ${this.name}: ${e.message}`);
            }
        });
        log.info(`Found ${gifs.length} GIFs on ${this.name}`);
         if (gifs.length === 0 && rawHtmlOrJsonData && rawHtmlOrJsonData.length > 100) {
            log.warn(`No GIFs found for ${this.name}, but received HTML. Selectors might be outdated or GIFs are not on this page.`);
        }
        return gifs;
    }
}

module.exports = XhamsterScraper;
