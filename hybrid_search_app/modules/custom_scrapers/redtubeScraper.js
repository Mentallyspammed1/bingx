// Redtube custom scraper
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin'); // Assuming VideoMixin provides _fetchHtml and _makeAbsolute or they are on AbstractModule
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
        this.log.info('RedtubeScraper instantiated with updated implementation');
    }

    get name() { return 'Redtube'; }
    get firstpage() { return 1; } // Standard is 1-indexed

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
        this.log.info(`Fetching HTML for Redtube videos from: ${searchUrl}`);

        try {
            const html = await this._fetchHtml(searchUrl, {
                // Redtube might require specific headers, like User-Agent or Cookie for age verification
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    // 'Cookie': 'RNKEY=...; age_verified=1;' // Example, actual cookie might be needed
                }
            });
            const $ = cheerio.load(html);
            const videoItems = [];

            // Common selectors for video blocks on tube sites - these are guesses
            // Option 1: Based on a common structure with <li> elements
            // Option 2: Based on <div> blocks
            // Let's try a more generic approach that might cover both
            const videoElements = $('div.video_bloc, li.video_item, div.video-item, div.video-card, div.videoBlock');

            if(videoElements.length === 0) {
                this.log.warn(`No video items found on page using selectors. HTML length: ${html.length}. URL: ${searchUrl}`);
                // Check for common signs of blocking or empty results
                if (html.includes('age_gate_wrapper') || html.includes('age-verification')) {
                     this.log.warn('Age verification page detected. Scraper needs cookie/header adjustment or cannot bypass.');
                     return [{ title: 'Redtube: Age verification required.', url: searchUrl, source: this.name, thumbnail:'', preview_video:'', duration:'0:00' }];
                }
                if (html.includes('No videos found') || html.includes('no results found')) {
                    this.log.info('Page indicates no results found for query.');
                    return [];
                }
            } else {
                 this.log.info(`Found ${videoElements.length} potential video elements.`);
            }


            videoElements.each((i, el) => {
                const itemHtml = $(el);
                let title, url, thumbnail, preview_video, duration;

                // --- Title ---
                // Try common title selectors: <a> with title, specific class, etc.
                title = itemHtml.find('a.video_title, a.video-title, .video_title_model_name a, a.video_link').attr('title') ||
                        itemHtml.find('a.video_title, a.video-title, .video_title_model_name a, a.video_link').text().trim();
                if (!title) {
                     title = itemHtml.find('span.video_title, span.video-title, .title a').text().trim();
                }


                // --- URL ---
                // Usually an <a> tag wrapping the thumbnail or title
                url = itemHtml.find('a.video_link, a.video_thumb_wrap, a.video_title, a.video-title, .title a').attr('href');
                if (url) {
                    url = this._makeAbsolute(url, this.baseUrl);
                } else {
                    // Try to find any link if specific ones fail
                    const firstLink = itemHtml.find('a').first().attr('href');
                    if(firstLink) url = this._makeAbsolute(firstLink, this.baseUrl);
                }

                // --- Thumbnail ---
                // Common attributes: src, data-src, data-thumb_url
                // Sometimes inside a specific container like .thumb_video_wrapper img
                thumbnail = itemHtml.find('img.thumb, img.video_thumbnail, img.img_lazy_load, img.video_item_thumb').attr('src') ||
                            itemHtml.find('img.thumb, img.video_thumbnail, img.img_lazy_load, img.video_item_thumb').attr('data-src') ||
                            itemHtml.find('img.thumb, img.video_thumbnail, img.img_lazy_load, img.video_item_thumb').attr('data-thumb_url');

                if (thumbnail) {
                    thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);
                } else {
                    // Fallback: try any image if specific ones fail
                    const firstImg = itemHtml.find('img').first().attr('src');
                    if(firstImg) thumbnail = this._makeAbsolute(firstImg, this.baseUrl);
                }


                // --- Preview Video ---
                // This is highly speculative. Look for data attributes or specific media elements.
                // Some sites use 'data-previewvideo', 'data-mediabook', 'data-preview_url' on the item container or image
                preview_video = itemHtml.attr('data-previewvideo') ||
                                itemHtml.attr('data-mediabook') || // Common on some platforms
                                itemHtml.attr('data-preview_url') ||
                                itemHtml.find('img.thumb, img.video_thumbnail').attr('data-previewvideo') ||
                                itemHtml.find('img.thumb, img.video_thumbnail').attr('data-mediabook') ||
                                itemHtml.find('img.thumb, img.video_thumbnail').attr('data-gif_url'); // For GIF previews

                // Sometimes a <video> tag might be hidden inside
                if (!preview_video) {
                    const videoTagSrc = itemHtml.find('video source[src], video[src]').attr('src');
                    if (videoTagSrc) preview_video = videoTagSrc;
                }

                // Check if the thumbnail itself is a GIF that could serve as a preview
                if (!preview_video && thumbnail && thumbnail.toLowerCase().endsWith('.gif')) {
                    preview_video = thumbnail;
                }


                if (preview_video) {
                    preview_video = this._makeAbsolute(preview_video, this.baseUrl);
                }

                // --- Duration ---
                // Often in a span.duration, div.duration, .time, .duration_bg
                duration = itemHtml.find('span.duration, div.duration, span.time, var.duration, div.video_duration, span.video_duration').first().text().trim();
                // Clean up duration (e.g., remove parentheses, extra spaces)
                if (duration) {
                    duration = duration.replace(/[()]/g, '').trim();
                }


                if (title && url) { // Only add if essential data is present
                    videoItems.push({
                        title,
                        url,
                        thumbnail: thumbnail || '',
                        preview_video: preview_video || '', // Fallback to empty if not found
                        duration: duration || 'N/A',
                        source: this.name,
                        query: query // Pass query for context if needed later
                    });
                } else {
                    this.log.debug('Skipped item due to missing title or URL.', itemHtml.html().substring(0,100));
                }
            });

            if (videoItems.length === 0 && videoElements.length > 0) {
                this.log.warn(`Found ${videoElements.length} elements but extracted 0 items. Selectors might need adjustment.`);
            }
            this.log.info(`Extracted ${videoItems.length} video items from ${searchUrl}`);
            return videoItems;

        } catch (error) {
            this.log.error(`Error in searchVideos for query "${query}" on page ${page}: ${error.message}`, error.stack);
            // Check if it's an age verification issue from error
            if (error.message && (error.message.includes('403') || error.message.includes('age verification'))) {
                 return [{ title: 'Redtube: Failed due to age verification or access block.', url: searchUrl, source: this.name, thumbnail:'', preview_video:'', duration:'0:00' }];
            }
            return []; // Return empty array on error
        }
    }

    // No need for separate videoParser if logic is in searchVideos
    // async videoParser($, rawData) { ... }

    gifUrl(query, page) { this.log.warn('Redtube gifUrl not implemented - site is video focused'); return ''; }
    async gifParser($, rawData) { this.log.warn('Redtube gifParser not implemented - site is video focused'); return []; }
}
module.exports = RedtubeScraper;
