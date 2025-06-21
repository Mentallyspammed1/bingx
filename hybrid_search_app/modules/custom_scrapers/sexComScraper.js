// Placeholder for Sex.com custom scraper
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const cheerio = require('cheerio'); // Required for parsing, even if placeholder

class SexComScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.sex.com'; // Example base URL
        this.log = {
            debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[SexComScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args);},
            info: (message, ...args) => console.log(`[SexComScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
            warn: (message, ...args) => console.warn(`[SexComScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
            error: (message, ...args) => console.error(`[SexComScraper ERROR] ${new Date().toISOString()}: ${message}`, ...args),
        };
        this.log.info('SexComScraper instantiated');
    }

    get name() { return 'SexCom'; }

    async searchVideos(query, page = 1) {
        const url = this.videoUrl(query, page);
        this.log.info(`SexCom searchVideos: Fetching HTML from ${url}`);
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
            this.log.error(`Error in SexCom searchVideos for query "${query}" on page ${page}: ${error.message}`);
            this.log.debug(error.stack);
            return [];
        }
    }

    videoUrl(query, page = 1) {
        // Common pattern: https://www.sex.com/search/videos?query=<query>&page=<page_number>
        const url = `${this.baseUrl}/search/videos?query=${encodeURIComponent(query)}&page=${page}`;
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
        const itemSelector = 'div.box.masonry-thumb, div.video-block, article.box, div.video-item, .video_selector_class'; // Added a placeholder for future
        const items = $(itemSelector);

        if (items.length === 0 && rawHtml) {
            this.log.warn(`${this.name} videoParser: Main item selector '${itemSelector}' found 0 elements. HTML (first 500 chars): ${rawHtml.substring(0, 500)}`);
            return videos;
        }
        this.log.info(`Found ${items.length} potential video items using selector: '${itemSelector}'`);

        items.each((i, element) => {
            const $item = $(element);
            try {
                const linkElement = $item.find('a.title, a[href*="/videos/"], a.video_title, h3 a, h4 a').first();
                let url = linkElement.attr('href');
                let title = (linkElement.attr('title') || linkElement.text() || '').trim();

                if (!title) { // Fallback for title
                    title = ($item.find('img').first().attr('alt') || '').trim();
                }
                 if (!title) { // Try another common title location
                    title = ($item.find('.video_title, .thumb_title, .block_title').first().text() || '').trim();
                }

                url = this._makeAbsolute(url, this.baseUrl);

                const imgElement = $item.find('img.thumb, img.video-thumbnail, img[class*="thumb"], img[class*="thumbnail"]').first();
                let thumbnail = imgElement.attr('data-src') || imgElement.attr('src');
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                let duration = ($item.find('span.duration, .video-duration, span.time, .thumb_duration_display').first().text() || '').trim();

                let preview_video = imgElement.attr('data-previewvideo_url') ||
                                    imgElement.attr('data-preview') ||
                                    $item.attr('data-preview-video') ||
                                    imgElement.attr('data-gif_url') ||
                                    imgElement.attr('data-gif');
                preview_video = this._makeAbsolute(preview_video, this.baseUrl);

                if (title && url && (url.includes('/videos/') || url.includes('/video/'))) { // Basic validation
                    videos.push({
                        title,
                        url,
                        thumbnail: thumbnail || undefined,
                        duration: duration || undefined,
                        preview_video: preview_video || undefined,
                        source: this.name,
                    });
                } else {
                     this.log.debug(`${this.name} videoParser: Skipped item. Title: '${title}', URL: '${url}'. Item HTML snippet: ${$item.html().substring(0, 100)}`);
                }
            } catch (e) {
                this.log.warn(`${this.name} videoParser: Error parsing video item: ${e.message}. Item HTML: ${$item.html().substring(0,100)}`);
            }
        });

        if (videos.length === 0 && items.length > 0) {
            this.log.warn(`${this.name} videoParser: Found ${items.length} items with selector '${itemSelector}' but extracted 0 videos. Sub-selectors or filtering might be the issue.`);
        } else if (videos.length > 0) {
            this.log.info(`Parsed ${videos.length} video items from ${this.name} on ${$._originalUrl || 'current page'}`);
        }
        // If items.length was 0, initial log already covered it.
        return videos;
    }

    async searchGifs(query, page = 1) {
        const url = this.gifUrl(query, page);
        this.log.info(`${this.name} searchGifs: Fetching HTML from ${url}`);
        try {
            const html = await this._fetchHtml(url);
            if (!html) {
                this.log.warn(`No HTML content received from ${url} for ${this.name} GIF search.`);
                return [];
            }
            const $ = cheerio.load(html);
            $._originalUrl = url;
            return this.gifParser($, html);
        } catch (error) {
            this.log.error(`Error in ${this.name} searchGifs for query "${query}" on page ${page}: ${error.message}`);
            this.log.debug(error.stack);
            return [];
        }
    }

    gifUrl(query, page = 1) {
        const url = `${this.baseUrl}/en/gifs?search=${encodeURIComponent(query)}&page=${page}`;
        this.log.info(`Constructed ${this.name} GIF URL: ${url}`);
        return url;
    }

    async gifParser($, rawHtml) {
        const gifs = [];
        if (!$) {
            this.log.warn(`${this.name} gifParser received no cheerio object to process.`);
            return gifs;
        }
        this.log.info(`Parsing ${this.name} GIF page: ${$._originalUrl || 'URL not available'}`);
        const itemSelector = 'div.box.masonry-thumb, div.gif-block, article.box, div.gif_item, .gif_selector_class';
        const items = $(itemSelector);

        if (items.length === 0 && rawHtml) {
            this.log.warn(`${this.name} gifParser: Main item selector '${itemSelector}' found 0 elements. HTML (first 500 chars): ${rawHtml.substring(0, 500)}`);
            return gifs;
        }
        this.log.info(`Found ${items.length} potential GIF items using selector: '${itemSelector}'`);

        items.each((i, element) => {
            const $item = $(element);
            try {
                const linkElement = $item.find('a.title, a[href*="/gifs/"], a.gif_title, h3 a, h4 a').first();
                let url = linkElement.attr('href');
                let title = (linkElement.attr('title') || linkElement.text() || '').trim();

                if (!title) {
                    title = ($item.find('img').first().attr('alt') || 'GIF').trim();
                }
                 if (!title && title !== 'GIF') { // Try another common title location
                    title = ($item.find('.gif_title, .thumb_title, .block_title').first().text() || 'GIF').trim();
                }
                url = this._makeAbsolute(url, this.baseUrl);

                const imgElement = $item.find('img.thumb, img.gif-thumbnail, img[class*="thumb"], img[class*="thumbnail"]').first();
                let thumbnail = imgElement.attr('data-src') || imgElement.attr('src'); // Static thumb
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                let preview_video = imgElement.attr('data-gif_url') ||
                                    imgElement.attr('data-gif') ||
                                    imgElement.attr('data-src') || // If src is already the animated one
                                    imgElement.attr('data-original_url') ||
                                    imgElement.attr('data-original');
                preview_video = this._makeAbsolute(preview_video, this.baseUrl);

                // Ensure preview_video is likely a GIF
                if (preview_video && !preview_video.toLowerCase().endsWith('.gif') && thumbnail && thumbnail.toLowerCase().endsWith('.gif')) {
                     preview_video = thumbnail; // Fallback to thumbnail if it's a gif and preview isn't
                }
                 if (preview_video && !preview_video.toLowerCase().endsWith('.gif')) {
                    // If still not a gif, this might not be a valid gif item or needs specific handling
                    this.log.debug(`${this.name} gifParser: Item found but preview_video is not a .gif: ${preview_video}. URL: ${url}`);
                    // Set to null or skip if strict GIF policy is needed
                    // preview_video = null;
                }


                if (title && url && preview_video && (url.includes('/gif/') || url.includes('/gifs/'))) { // Basic validation
                    gifs.push({
                        title,
                        url,
                        thumbnail: thumbnail || preview_video, // Fallback thumb to preview_video if static not found
                        preview_video,
                        source: this.name,
                        type: 'gifs'
                    });
                } else {
                     this.log.debug(`${this.name} gifParser: Skipped item. Title: '${title}', URL: '${url}', Preview: '${preview_video}'. Item HTML snippet: ${$item.html().substring(0, 100)}`);
                }
            } catch (e) {
                this.log.warn(`${this.name} gifParser: Error parsing GIF item: ${e.message}. Item HTML: ${$item.html().substring(0,100)}`);
            }
        });

        if (gifs.length === 0 && items.length > 0) {
            this.log.warn(`${this.name} gifParser: Found ${items.length} items with selector '${itemSelector}' but extracted 0 GIFs. Sub-selectors or filtering might be the issue.`);
        } else if (gifs.length > 0) {
            this.log.info(`Parsed ${gifs.length} GIF items from ${this.name} on ${$._originalUrl || 'current page'}`);
        }
        return gifs;
    }
}
module.exports = SexComScraper;
