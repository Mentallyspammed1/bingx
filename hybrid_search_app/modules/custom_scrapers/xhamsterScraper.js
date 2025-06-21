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
        this.log.info('XhamsterScraper instantiated - GIF Implementation Attempt');
    }

    get name() { return 'Xhamster'; }
    get firstpage() { return 1; }

    // --- Video Methods (previously implemented) ---
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

                    // Refined preview_video logic
                    let temp_preview = imgTag.attr('data-previewvideo_url') || imgTag.attr('data-preview_url');
                    if (temp_preview) {
                        preview_video = temp_preview;
                    } else {
                        const dataSprite = imgTag.attr('data-sprite');
                        if (dataSprite && (dataSprite.endsWith('.mp4') || dataSprite.endsWith('.webm') || dataSprite.endsWith('.gif') || dataSprite.startsWith('http') || dataSprite.startsWith('/'))) {
                            // Basic check if it's a URL path or full URL, and common video/gif extensions
                            // More robust validation might be needed if data-sprite contains non-URL strings often
                            if (dataSprite.includes('http') || dataSprite.startsWith('/')) { // Ensure it's a link
                                preview_video = dataSprite;
                                this.log.debug(`Used data-sprite for preview: ${preview_video}`);
                            } else {
                                this.log.debug(`data-sprite content '${dataSprite}' skipped as it's not a valid URL path for preview.`);
                            }
                        } else if (dataSprite) {
                             this.log.debug(`data-sprite content '${dataSprite}' skipped as it did not appear to be a media URL.`);
                        }
                    }
                }
                if (!title) {
                    title = itemHtml.find('.video-thumb-info__name, .video-thumb__name, .video-title').first().text().trim();
                }
                title = title ? title.trim() : '';
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
                    videoItems.push({ title, url, thumbnail: thumbnail || '', preview_video: preview_video || '', duration: duration, source: this.name });
                } else {
                    this.log.debug(`Skipped video item due to missing title or URL. URL: ${url}, Title: '${title}'.`);
                }
            });
            this.log.info(`Extracted ${videoItems.length} video items from Xhamster.`);
            return videoItems;
        } catch (error) {
            this.log.error(`Error in Xhamster searchVideos for query "${query}" on page ${page}: ${error.message}`, error.stack);
            return [{title:'Xhamster Scraper Error', source: this.name, error: error.message }];
        }
    }

    // --- GIF Methods Implementation ---
    gifUrl(query, page) {
        const pageNumber = page || this.firstpage;
        // Using structure: xhamster.com/search/gifs/QUERY?page=PAGE_NUMBER
        // Or xhamster.com/gifs/search/QUERY?page=PAGE_NUMBER
        // Let's try the /search/gifs/ path first as it's a common pattern.
        let url = `${this.baseUrl}/search/gifs/${encodeURIComponent(query)}`;
        if (pageNumber > 1) {
            url += `?page=${pageNumber}`;
        }
        this.log.info(`${this.name} GIF search: Constructed URL: ${url}`);
        return url;
    }

    async gifParser($, rawHtml) {
        this.log.info(`Parsing ${this.name} GIF page...`);
        const gifs = [];
        // Guessing selectors for GIFs. They might be in similar containers as videos or specific ones.
        // Common item selectors: 'div.gif-thumb-container', 'div.gif-item', 'li.thumb-gif-cell'
        // Or perhaps they reuse 'div.thumb-list__item' but have an internal structure indicating it's a GIF.
        const gifElements = $('div.thumb-list__item'); // Start by assuming similar container as videos

        this.log.info(`Found ${gifElements.length} potential GIF parent elements using 'div.thumb-list__item'.`);

        gifElements.each((i, el) => {
            const itemHtml = $(el);
            let title = '', url = '', thumbnail = '', preview_video = ''; // preview_video must be a .gif

            const itemAnchor = itemHtml.find('a.video-thumb__image-container, a.video-thumb-link, a').first(); // Generalize link finding
            url = itemAnchor.attr('href');
            url = this._makeAbsolute(url, this.baseUrl);

            const imgTag = itemAnchor.find('img').first(); // Generalize image finding within link
            if (imgTag.length) {
                title = imgTag.attr('alt');
                // For GIFs, data-src might point to a static thumb, src might be the animated one or vice-versa
                // Or a specific data-gif-src attribute
                thumbnail = imgTag.attr('data-src') || imgTag.attr('src'); // Static thumbnail

                preview_video = imgTag.attr('data-gif-src') || // Preferred if exists
                                imgTag.attr('data-original') || // Common for full version
                                imgTag.attr('src');             // If src itself is the animated gif

                // If preview_video from above isn't a .gif, but thumbnail is, use thumbnail.
                if (preview_video && !preview_video.toLowerCase().endsWith('.gif') && thumbnail && thumbnail.toLowerCase().endsWith('.gif')) {
                    preview_video = thumbnail;
                }
                // If no preview_video found yet, and thumbnail is a .gif, it's likely the preview.
                if (!preview_video && thumbnail && thumbnail.toLowerCase().endsWith('.gif')) {
                    preview_video = thumbnail;
                }
                // Fallback: check data attributes on itemAnchor if imgTag specific ones fail
                if (!preview_video) {
                    preview_video = itemAnchor.attr('data-gif-src') || itemAnchor.attr('data-preview-url');
                }

            }

            title = title ? title.trim() : (itemAnchor.attr('title') || 'GIF');
            thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);
            preview_video = this._makeAbsolute(preview_video, this.baseUrl);

            if (title && url && preview_video && preview_video.toLowerCase().endsWith('.gif')) {
                gifs.push({
                    title,
                    url,
                    thumbnail: (thumbnail && !thumbnail.toLowerCase().endsWith('.gif')) ? thumbnail : preview_video, // Prefer static thumb if available
                    preview_video, // Must be the .gif
                    source: this.name,
                    type: 'gifs'
                });
            } else {
                if (imgTag.length > 0) { // Only log skip if we actually found an image tag to inspect
                     this.log.debug(`Skipped GIF item: title='${title}', url='${url}', potential_preview='${preview_video}', thumb='${thumbnail}'. Does not meet GIF criteria.`);
                }
            }
        });

        if (gifs.length === 0 && gifElements.length > 0) {
            this.log.warn(`Found ${gifElements.length} 'div.thumb-list__item' elements, but none yielded a valid .gif preview_video.`);
        } else if (gifElements.length === 0) {
            this.log.warn("No elements matched main GIF selector 'div.thumb-list__item'. Page might not contain GIFs or uses different structure.");
        }
        this.log.info(`Extracted ${gifs.length} GIFs from Xhamster.`);
        return gifs;
    }

    async searchGifs(query = this.query, page = this.page) {
        const searchUrl = this.gifUrl(query, page);
        this.log.info(`${this.name} searchGifs: Fetching HTML from ${searchUrl}`);

        if (!searchUrl) { // Should not happen with current gifUrl, but good check
            this.log.warn(`${this.name} GIF search: No URL returned by gifUrl. Aborting.`);
            return [];
        }

        try {
            const html = await this._fetchHtml(searchUrl);
            const $ = cheerio.load(html);
            return this.gifParser($, html);
        } catch (error) {
            this.log.error(`Error in ${this.name} searchGifs for query "${query}" on page ${page}: ${error.message}`, error.stack);
            if (error.message && error.message.includes('404')) {
                this.log.warn(`${this.name} GIF search: Received 404 for URL ${searchUrl}. The GIF search URL structure is likely incorrect.`);
            }
            return [{ title: `${this.name} GIF Scraper Error`, source: this.name, error: error.message }];
        }
    }
}
module.exports = XhamsterScraper;
