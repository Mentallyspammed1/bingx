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

    async searchVideos(query, page = 1) {
        const url = this.videoUrl(query, page);
        this.log.info(`Xhamster searchVideos: Fetching HTML from ${url}`);
        try {
            const html = await this._fetchHtml(url);
            if (!html) {
                this.log.warn(`No HTML content received from ${url} for ${this.name}`);
                return [];
            }
            const $ = cheerio.load(html);
            $._originalUrl = url; // Store the URL for context in parser
            return this.videoParser($, html);
        } catch (error) {
            this.log.error(`Error in Xhamster searchVideos for query "${query}" on page ${page}: ${error.message}`);
            this.log.debug(error.stack);
            return [];
        }
    }

    videoUrl(query, page = 1) {
        // Common pattern: https://xhamster.com/search/<query>?page=<page_number>
        const url = `${this.baseUrl}/search/${encodeURIComponent(query)}?page=${page}`;
        this.log.info(`Constructed ${this.name} video URL: ${url}`);
        return url;
    }

    async videoParser($, rawHtml) {
        const videos = [];
        if (!$) {
            this.log.warn(`${this.name} videoParser received no cheerio object to process.`);
            return videos;
        }
        this.log.info(`Parsing ${this.name} video page: ${$._originalUrl || 'URL not available'}`);

        // Selectors for xHamster might include: 'div.video-thumb__image-container a', 'div.thumb-list__item video-thumb a.video-thumb-info__name'
        // 'div.thumb-list__item.video-thumb', 'article.video-thumb', '.video-thumb__image-container a'
        $('div.thumb-list__item.video-thumb, article.video-thumb, .video-thumb__image-container a, div.video-item').each((i, element) => {
            try {
                const $item = $(element);

                let title, url, thumbnail, duration, preview_video;

                // Try to get data from common xHamster structures
                const $link = $item.is('a') ? $item : $item.find('a.video-thumb-info__name, a.video-thumb__image-link, a');

                title = $link.attr('title') || $link.text().trim();
                if (!title) {
                     // Fallback if title is in a specific element within the item
                    title = $item.find('.video-thumb-info__name, .video-title').text().trim();
                }
                if (!title) { // Try image alt as last resort for title
                    title = $item.find('img').attr('alt');
                }

                url = $link.attr('href');
                if (url) url = this._makeAbsolute(url, this.baseUrl);

                const $img = $item.find('img.video-thumb__image, img.thumb');
                thumbnail = $img.attr('data-src') || $img.attr('src');
                if (thumbnail) thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                // Duration often in a specific span
                duration = $item.find('span.video-duration, .duration, .video-thumb__duration').text().trim();

                // Preview video (GIF or short clip)
                // xHamster might use data-previewvideo on img or data-previewhtml5 on video tag
                preview_video = $item.find('img[data-previewvideo]').attr('data-previewvideo') ||
                                $item.find('video[data-previewhtml5]').attr('data-previewhtml5') ||
                                $item.attr('data-previewvideo'); // if on main item
                if (preview_video) preview_video = this._makeAbsolute(preview_video, this.baseUrl);


                if (title && url) {
                    videos.push({
                        title: title.replace(/\s+/g, ' ').trim(), // Clean up whitespace
                        url,
                        thumbnail: thumbnail || "N/A",
                        duration: duration || "N/A",
                        preview_video: preview_video || "N/A",
                        source: this.name,
                    });
                } else {
                    // this.log.debug(`Skipping item on ${this.name}, missing title or URL. HTML snippet: ${$item.html().substring(0, 100)}`);
                }
            } catch (e) {
                this.log.warn(`Error parsing video item on ${this.name}: ${e.message}. Item HTML: ${$(element).html().substring(0,100)}`);
            }
        });

        if (videos.length === 0) {
            this.log.warn(`No videos parsed from ${this.name} on ${$._originalUrl || 'current page'}. Selectors might need adjustment or page might be empty.`);
            // this.log.debug(`Raw HTML received for ${this.name} (first 500 chars): ${rawHtml ? rawHtml.substring(0, 500) : 'N/A'}`);
        } else {
            this.log.info(`Parsed ${videos.length} video items from ${this.name} on ${$._originalUrl || 'current page'}`);
        }
        return videos;
    }

    async searchGifs(query, page = 1) {
        const url = this.gifUrl(query, page);
        this.log.info(`Xhamster searchGifs: Fetching HTML from ${url}`);
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

    gifUrl(query, page = 1) {
        this.log.warn('Xhamster gifUrl not implemented');
        // Example: return `${this.baseUrl}/search/gifs/${encodeURIComponent(query)}?page=${page}`;
        return `https://xhamster.com/search/gifs/${encodeURIComponent(query)}?page=${page}`; // Placeholder URL
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
