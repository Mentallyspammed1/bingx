// Redtube custom scraper
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const cheerio = require('cheerio');

class RedtubeScraper extends AbstractModule.with(VideoMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.redtube.com';
        this.log = {
            debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[RedtubeScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args);},
            info: (message, ...args) => console.log(`[RedtubeScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
            warn: (message, ...args) => console.warn(`[RedtubeScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
            error: (message, ...args) => console.error(`[RedtubeScraper ERROR] ${new Date().toISOString()}: ${message}`, ...args),
        };
        this.log.info('RedtubeScraper instantiated with new selectors');
    }

    get name() { return 'Redtube'; }
    get firstpage() { return 1; }

    videoUrl(query, page) {
        const searchPage = page || this.firstpage;
        // Common Redtube search URL pattern, might need adjustment if it changed
        return `${this.baseUrl}/?search=${encodeURIComponent(query)}&page=${searchPage}`;
    }

    async searchVideos(query, page) {
        const searchUrl = this.videoUrl(query, page);
        if (!searchUrl) {
            this.log.error('Video URL could not be constructed.');
            return [];
        }
        this.log.info(`Fetching HTML for Redtube videos from: ${searchUrl} with new selectors.`);

        try {
            const html = await this._fetchHtml(searchUrl, {
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                }
            });
            const $ = cheerio.load(html);
            const videoItems = [];

            // New main item selector
            const videoElements = $('div.video_item');

            if(videoElements.length === 0) {
                this.log.warn(`No video items found on page using selector 'div.video_item'. HTML length: ${html.length}. URL: ${searchUrl}`);
                if (html.includes('age_gate_wrapper') || html.includes('age-verification')) {
                     this.log.warn('Age verification page detected. Scraper needs cookie/header adjustment or cannot bypass.');
                     return [{ title: 'Redtube: Age verification required.', url: searchUrl, source: this.name, thumbnail:'', preview_video:'', duration:'0:00' }];
                }
                if (html.includes('No videos found') || html.includes('no results found')) {
                    this.log.info('Page indicates no results found for query.');
                    return [];
                }
            } else {
                 this.log.info(`Found ${videoElements.length} potential video elements using 'div.video_item'.`);
            }

            videoElements.each((i, el) => {
                const itemHtml = $(el);
                let title, url, thumbnail, preview_video, duration;

                // --- Title & URL ---
                const titleAnchor = itemHtml.find('a.video_title_link');
                title = titleAnchor.attr('title') || titleAnchor.text().trim();
                url = titleAnchor.attr('href');
                if (url) {
                    url = this._makeAbsolute(url, this.baseUrl);
                } else {
                     // Fallback if main title selector fails for URL
                    const anyLink = itemHtml.find('a').first();
                    url = anyLink.attr('href');
                    if(url) url = this._makeAbsolute(url, this.baseUrl);
                    if(!title) title = anyLink.attr('title') || anyLink.text().trim(); // Fallback for title too
                }

                // --- Thumbnail ---
                const thumbImg = itemHtml.find('img.video_thumbnail_img');
                thumbnail = thumbImg.attr('src') || thumbImg.attr('data-src');
                if (thumbnail) {
                    thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);
                }

                // --- Preview Video ---
                preview_video = thumbImg.attr('data-previewvideo_url') || // Specific to new img selector
                                itemHtml.attr('data-preview-url'); // On the main item container

                // Fallback to existing checks if the above are not found
                if (!preview_video) {
                    preview_video = itemHtml.attr('data-previewvideo') ||
                                    itemHtml.attr('data-mediabook') ||
                                    thumbImg.attr('data-previewvideo') || // Broader attributes on thumb
                                    thumbImg.attr('data-mediabook') ||
                                    thumbImg.attr('data-gif_url');
                }
                if (!preview_video) {
                    const videoTagSrc = itemHtml.find('video source[src], video[src]').attr('src');
                    if (videoTagSrc) preview_video = videoTagSrc;
                }
                if (!preview_video && thumbnail && thumbnail.toLowerCase().endsWith('.gif')) {
                    preview_video = thumbnail; // Use thumbnail if it's a GIF and no other preview found
                }

                if (preview_video) {
                    preview_video = this._makeAbsolute(preview_video, this.baseUrl);
                }

                // --- Duration ---
                duration = itemHtml.find('span.video_duration').first().text().trim();
                if (duration) {
                    duration = duration.replace(/[()]/g, '').trim();
                }

                if (title && url) {
                    videoItems.push({
                        title,
                        url,
                        thumbnail: thumbnail || '',
                        preview_video: preview_video || '',
                        duration: duration || 'N/A',
                        source: this.name,
                        query: query
                    });
                } else {
                    this.log.debug('Skipped item due to missing title or URL.', itemHtml.html() ? itemHtml.html().substring(0,100) : 'N/A');
                }
            });

            if (videoItems.length === 0 && videoElements.length > 0) {
                this.log.warn(`Found ${videoElements.length} elements with 'div.video_item' but extracted 0 items. Sub-selectors might need adjustment.`);
            }
            this.log.info(`Extracted ${videoItems.length} video items from ${searchUrl}`);
            return videoItems;

        } catch (error) {
            this.log.error(`Error in searchVideos for query "${query}" on page ${page}: ${error.message}`, error.stack);
            if (error.message && (error.message.includes('403') || error.message.includes('age verification'))) {
                 return [{ title: 'Redtube: Failed due to age verification or access block.', url: searchUrl, source: this.name, thumbnail:'', preview_video:'', duration:'0:00' }];
            }
            return [];
        }
    }

    // No need for separate videoParser if logic is in searchVideos
    // async videoParser($, rawData) { ... }

    gifUrl(query, page) { this.log.warn('Redtube gifUrl not implemented - site is video focused'); return ''; }
    async gifParser($, rawData) { this.log.warn('Redtube gifParser not implemented - site is video focused'); return []; }
}
module.exports = RedtubeScraper;
