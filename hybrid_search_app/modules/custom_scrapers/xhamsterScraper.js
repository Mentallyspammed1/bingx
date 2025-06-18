// Xhamster custom scraper
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const cheerio = require('cheerio');

class XhamsterScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://xhamster.com';
        this.log = {
            debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[XhamsterScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args);},
            info: (message, ...args) => console.log(`[XhamsterScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
            warn: (message, ...args) => console.warn(`[XhamsterScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
            error: (message, ...args) => console.error(`[XhamsterScraper ERROR] ${new Date().toISOString()}: ${message}`, ...args),
        };
        this.log.info('XhamsterScraper instantiated - Final duration refinement attempt');
    }

    get name() { return 'Xhamster'; }
    get firstpage() { return 1; }

    videoUrl(query, page) {
        const pageNumber = page || this.firstpage;
        let url = `${this.baseUrl}/search/${encodeURIComponent(query)}`;
        if (pageNumber > 1) {
            url += `?page=${pageNumber}`;
        }
        this.log.debug(`Constructed video URL: ${url}`);
        return url;
    }

    async searchVideos(query, page) {
        const searchUrl = this.videoUrl(query, page);
        this.log.info(`Xhamster searchVideos: Fetching HTML from ${searchUrl}`);

        try {
            const html = await this._fetchHtml(searchUrl);
            const $ = cheerio.load(html);
            const videoItems = [];

            const videoElements = $('div.thumb-list__item');
            this.log.info(`Found ${videoElements.length} potential video elements using 'div.thumb-list__item'.`);

            videoElements.each((i, el) => {
                const itemHtml = $(el);
                let title = '', url = '', thumbnail = '', preview_video = '', duration = 'N/A';

                const itemAnchor = itemHtml.find('a.video-thumb__image-container, a.video-thumb-link').first();
                if (itemAnchor.length) {
                    url = itemAnchor.attr('href');
                    url = this._makeAbsolute(url, this.baseUrl);
                } else {
                    const fallbackAnchor = itemHtml.find('a').first();
                    url = fallbackAnchor.attr('href');
                    url = this._makeAbsolute(url, this.baseUrl);
                }

                const imgTag = itemHtml.find('img.video-thumb__image, img').first();

                if (imgTag.length) {
                    title = imgTag.attr('alt');
                    thumbnail = imgTag.attr('data-src') || imgTag.attr('src');
                    thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                    preview_video = imgTag.attr('data-previewvideo_url') ||
                                    imgTag.attr('data-preview_url') ||
                                    imgTag.attr('data-sprite');
                }

                if (!title) {
                    title = itemHtml.find('.video-thumb-info__name, .video-thumb__name, .video-title').first().text().trim();
                }
                title = title ? title.trim() : '';

                // Refined Duration selector: Xhamster often uses 'video-thumb__time' or similar within the link/thumb area
                duration = itemAnchor.find('.video-thumb__time, .video-thumb__duration').first().text().trim();
                if (!duration || duration.length === 0) {
                    duration = itemHtml.find('.video-thumb__time, .video-thumb__duration, .duration, [class*="time"]').first().text().trim();
                }
                duration = duration ? duration.replace(/[()]/g, '').trim() : 'N/A';

                if (!preview_video) {
                    preview_video = itemAnchor.attr('data-preview-url') || itemAnchor.attr('data-previewvideo_url') ||
                                    itemHtml.attr('data-preview-url') || itemHtml.attr('data-previewvideo_url');
                }
                if (!preview_video && thumbnail && thumbnail.toLowerCase().endsWith('.gif')) {
                    preview_video = thumbnail;
                }

                preview_video = this._makeAbsolute(preview_video, this.baseUrl);

                if (title && url && title.length > 1) {
                    videoItems.push({
                        title,
                        url,
                        thumbnail: thumbnail || '',
                        preview_video: preview_video || '',
                        duration: duration,
                        source: this.name
                    });
                } else {
                    this.log.debug(`Skipped item due to missing title or URL. URL: ${url}, Title: '${title}'. HTML: ${itemHtml.html() ? itemHtml.html().substring(0,100) : 'N/A'}`);
                }
            });

            this.log.info(`Extracted ${videoItems.length} video items from Xhamster.`);
            return videoItems;

        } catch (error) {
            this.log.error(`Error in Xhamster searchVideos for query "${query}" on page ${page}: ${error.message}`, error.stack);
            return [{title:'Xhamster Scraper Error', source: this.name, error: error.message }];
        }
    }

    gifUrl(query, page) {
        this.log.warn('Xhamster gifUrl not fully implemented.');
        const pageNumber = page || this.firstpage;
        let url = `${this.baseUrl}/search/gifs/${encodeURIComponent(query)}`;
        if (pageNumber > 1) {
            url += `?page=${pageNumber}`;
        }
        return url;
    }

    async gifParser($, rawData) {
        this.log.warn('Xhamster gifParser not implemented.');
        return [{title:'Xhamster GIF Scraper Not Implemented Yet', source: this.name}];
    }

    async searchGifs(query = this.query, page = this.page) {
        const searchUrl = this.gifUrl(query, page);
        this.log.info(`Xhamster searchGifs: Using placeholder URL: ${searchUrl}`);
        try {
            this.log.warn(`Xhamster searchGifs: Full fetch and parse for GIFs is not implemented.`);
            return [{title:'Xhamster GIF Scraper (searchGifs) Not Fully Implemented', source: this.name}];
        } catch (error) {
            this.log.error(`Error in Xhamster searchGifs: ${error.message}`);
            return [{title:'Xhamster GIF Scraper Error', source: this.name, error: error.message }];
        }
    }
}
module.exports = XhamsterScraper;
