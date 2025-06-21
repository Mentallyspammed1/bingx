// Redtube custom scraper
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin'); // Added GifMixin
const cheerio = require('cheerio');

class RedtubeScraper extends AbstractModule.with(VideoMixin, GifMixin) { // Added GifMixin
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.redtube.com';
        this.log = {
            debug: (message, ...args) => { if (process.env.DEBUG === 'true') console.log(`[RedtubeScraper DEBUG] ${new Date().toISOString()}: ${message}`, ...args);},
            info: (message, ...args) => console.log(`[RedtubeScraper INFO] ${new Date().toISOString()}: ${message}`, ...args),
            warn: (message, ...args) => console.warn(`[RedtubeScraper WARN] ${new Date().toISOString()}: ${message}`, ...args),
            error: (message, ...args) => console.error(`[RedtubeScraper ERROR] ${new Date().toISOString()}: ${message}`, ...args),
        };
        this.log.info('RedtubeScraper instantiated - GIF Implementation Attempt');
    }

    get name() { return 'Redtube'; }
    get firstpage() { return 1; }

    // --- Video Methods ---
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
                headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' }
            });
            const $ = cheerio.load(html);
            const videoItems = [];
            const videoElements = $('li[id^="video_"], div[class*="video_item"], div.video-block, article.video-item, div.card, div.videoBox, div.videoCard');
            if(videoElements.length === 0) {
                this.log.warn(`No video items found on page using selector 'li[id^="video_"], div[class*="video_item"], div.video-block, article.video-item, div.card, div.videoBox, div.videoCard'. HTML length: ${html.length}.`);
                this.log.warn('HTML (first 1000 chars): ' + html.substring(0, 1000)); // Added logging
                if (html.toLowerCase().includes('cookie')) { // Added cookie check
                    this.log.warn('Cookie consent banner likely present and may be obscuring content.');
                }
                if (html.includes('age_gate_wrapper') || html.includes('age-verification')) {
                     this.log.warn('Age verification page detected.');
                     return [{ title: 'Redtube: Age verification required.', url: searchUrl, source: this.name }];
                }
                if (html.includes('No videos found') || html.includes('no results found')) {
                    this.log.info('Page indicates no results found for query.');
                }
                return [];
            }
            this.log.info(`Found ${videoElements.length} potential video elements using new composite selector.`);
            videoElements.each((i, el) => {
                const itemHtml = $(el);
                let title = '', url = '', thumbnail = '', preview_video = '', duration = 'N/A';

                // Title
                const titleElement = itemHtml.find('a.video_title, a.title, .video_title_link, .video-card-title, .title a, a span').first();
                title = (titleElement.attr('title') || titleElement.text() || '').trim();

                // URL
                url = titleElement.attr('href'); // Try from title element first
                if (!url) { // Fallback to any first link if not found on title element
                    const anyLink = itemHtml.find('a').first();
                    url = anyLink.attr('href');
                    if (!title) { // If title is still missing, try to get it from this link
                        title = (anyLink.attr('title') || anyLink.text() || '').trim();
                    }
                }
                if (url) url = this._makeAbsolute(url, this.baseUrl);

                // Thumbnail
                const thumbImg = itemHtml.find('img[class*="thumb"], img[class*="video_thumbnail"], img.video_thumbnail_img, img.thumb-image').first();
                thumbnail = thumbImg.attr('src') || thumbImg.attr('data-src');
                if (thumbnail) thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                // Preview Video (existing logic seems fine, let's keep it for now, but ensure it uses the new thumbImg)
                preview_video = thumbImg.attr('data-previewvideo_url') || itemHtml.attr('data-preview-url') || itemHtml.attr('data-previewvideo') || itemHtml.attr('data-mediabook') || thumbImg.attr('data-gif_url');
                if (!preview_video) {
                    const videoTagSrc = itemHtml.find('video source[src], video[src]').attr('src');
                    if (videoTagSrc) preview_video = videoTagSrc;
                }
                if (!preview_video && thumbnail && thumbnail.toLowerCase().endsWith('.gif')) preview_video = thumbnail;
                if (preview_video) preview_video = this._makeAbsolute(preview_video, this.baseUrl);

                // Duration
                const durationElement = itemHtml.find('span.duration, span.video_duration, .time, .video_length_display').first();
                duration = (durationElement.text() || '').trim();
                if (duration) duration = duration.replace(/[()]/g, '').trim();
                else duration = 'N/A';

                if (title && url) videoItems.push({ title, url, thumbnail: thumbnail || '', preview_video: preview_video || '', duration, source: this.name });
                else this.log.debug(`Skipped video item due to missing title or URL.`);
            });
            this.log.info(`Extracted ${videoItems.length} video items.`);
            return videoItems;
        } catch (error) {
            this.log.error(`Error in searchVideos for query "${query}" on page ${page}: ${error.message}`, error.stack);
            if (error.message && (error.message.includes('403') || error.message.includes('age verification'))) {
                 return [{ title: 'Redtube: Failed due to age verification or access block.', url: searchUrl, source: this.name, thumbnail:'', preview_video:'', duration:'0:00' }];
            }
            return [];
        }
    }

    // --- GIF Methods Implementation ---
    gifUrl(query, page) {
        const pageNumber = page || this.firstpage;
        // Guessed URL: https://www.redtube.com/gifs?search=QUERY&page=PAGE
        const url = `${this.baseUrl}/gifs?search=${encodeURIComponent(query)}&page=${pageNumber}`;
        this.log.info(`${this.name} GIF search: Constructed URL: ${url}`);
        return url;
    }

    async gifParser($, rawHtml) {
        this.log.info(`Parsing ${this.name} GIF page...`);
        const gifs = [];
        // Common selectors for gif items: div.gif_item, li.gif_card, div.gif-masonry__item, div.gif_card_wrapper
        const gifElements = $('div.gif_item, li.gif_card, div.gif-masonry__item, div.gif_card_wrapper');
        this.log.info(`Found ${gifElements.length} potential GIF elements.`);

        gifElements.each((i, el) => {
            const itemHtml = $(el);
            let title = '', url = '', thumbnail = '', preview_video = '';

            const itemAnchor = itemHtml.find('a.gif_link, a.gif_thumb_link').first(); // Common link classes for gifs
            url = itemAnchor.attr('href');
            url = this._makeAbsolute(url, this.baseUrl);

            const imgTag = itemAnchor.find('img.gif_image, img.gif_img').first(); // Common image classes for gifs
            if (imgTag.length) {
                title = imgTag.attr('alt') || itemAnchor.attr('title');
                thumbnail = imgTag.attr('src') || imgTag.attr('data-src'); // Static thumbnail

                // Preview GIF URL: often in data-src, data-mp4, data-gif, or the src itself if it's a .gif
                preview_video = imgTag.attr('data-gif') ||
                                imgTag.attr('data-mp4') || // some sites use mp4 for "gifs"
                                imgTag.attr('data-src-gif') ||
                                imgTag.attr('src'); // if src is already the .gif

                // If preview_video is not a .gif, but thumbnail is, use thumbnail
                if (preview_video && !preview_video.toLowerCase().endsWith('.gif') && thumbnail && thumbnail.toLowerCase().endsWith('.gif')) {
                    preview_video = thumbnail;
                }
                 // If no preview_video and thumbnail is a .gif, it's the preview
                if (!preview_video && thumbnail && thumbnail.toLowerCase().endsWith('.gif')) {
                    preview_video = thumbnail;
                }

            } else { // Fallback if specific image tag not found
                title = itemAnchor.attr('title') || itemAnchor.text().trim();
                // Try to find any image if specific one fails for preview/thumb
                const anyImg = itemAnchor.find('img').first();
                thumbnail = anyImg.attr('src') || anyImg.attr('data-src');
                preview_video = anyImg.attr('src'); // Simplistic fallback for preview
            }

            title = title ? title.trim() : 'GIF';
            thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);
            preview_video = this._makeAbsolute(preview_video, this.baseUrl);

            if (title && url && preview_video && preview_video.toLowerCase().endsWith('.gif')) {
                gifs.push({ title, url, thumbnail: thumbnail || preview_video, preview_video, source: this.name, type: 'gifs' });
            } else {
                this.log.debug(`Skipped GIF item: title='${title}', url='${url}', potential_preview='${preview_video}'. Does not meet .gif criteria.`);
            }
        });
        this.log.info(`Extracted ${gifs.length} GIFs from Redtube.`);
        return gifs;
    }

    async searchGifs(query = this.query, page = this.page) {
        const searchUrl = this.gifUrl(query, page);
        this.log.info(`${this.name} searchGifs: Fetching HTML from ${searchUrl}`);
        if (!searchUrl) {
            this.log.warn(`${this.name} GIF search: No URL returned by gifUrl.`);
            return [];
        }
        try {
            const html = await this._fetchHtml(searchUrl);
            const $ = cheerio.load(html);
            return this.gifParser($, html);
        } catch (error) {
            this.log.error(`Error in ${this.name} searchGifs for query "${query}" on page ${page}: ${error.message}`);
            if (error.message && error.message.includes('404')) {
                this.log.warn(`${this.name} GIF search: Received 404 for URL ${searchUrl}.`);
            }
            return [];
        }
    }
}
module.exports = RedtubeScraper;
