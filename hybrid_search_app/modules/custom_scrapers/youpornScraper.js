// modules/custom_scrapers/youpornScraper.js
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const log = require('../../core/log');
const cheerio = require('cheerio');

class YouPornScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.youporn.com';
        log.debug(`${this.name} scraper initialized for Video & GIF Implementation Attempt (new GIF URL)`);
    }

    get name() {
        return 'YouPorn';
    }

    get firstpage() {
        return 1;
    }

    // --- Video Methods (from previous successful implementation) ---
    videoUrl(query, page) {
        const url = `${this.baseUrl}/search/?query=${encodeURIComponent(query)}&page=${page}`;
        log.debug(`${this.name} video URL: ${url}`);
        return url;
    }

    async videoParser($, rawHtmlOrJsonData) {
        log.info(`Parsing ${this.name} video page ...`);
        const videos = [];
        const videoElements = $('div.video-box');
        log.info(`Found ${videoElements.length} potential video elements using 'div.video-box'.`);
        videoElements.each((i, elem) => {
            try {
                const $elem = $(elem);
                const itemLink = $elem.find('a').first();
                let url = itemLink.attr('href');
                url = this._makeAbsolute(url, this.baseUrl);
                let title = itemLink.attr('title');
                const imgTag = itemLink.find('img').first();
                if (!title && imgTag.length) {
                    title = imgTag.attr('alt');
                }
                if (!title) {
                    title = itemLink.text().trim();
                }
                title = title ? title.trim() : '';
                let thumbnail = imgTag.attr('data-src') || imgTag.attr('src');
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);
                let duration = $elem.find('span.video-duration, [class*="duration"], [class*="time"]').first().text().trim();
                duration = duration ? duration.replace(/[()]/g, '').trim() : 'N/A';
                let preview_video = imgTag.attr('data-previewvideo') ||
                                    imgTag.attr('data-preview_url') ||
                                    imgTag.attr('data-gif_preview') ||
                                    imgTag.attr('data-gif-url') ||
                                    imgTag.attr('data-thumb_video') ||
                                    imgTag.attr('data-hover_video') ||
                                    itemLink.attr('data-preview-url') ||
                                    itemLink.attr('data-previewvideo') ||
                                    itemLink.attr('data-hover-url');
                if (!preview_video) {
                    preview_video = $elem.attr('data-preview-url') ||
                                    $elem.attr('data-previewvideo') ||
                                    $elem.attr('data-video-preview');
                }
                if (!preview_video && imgTag.length) {
                    const imgDataAttrs = imgTag.data();
                    for (const key in imgDataAttrs) {
                        const value = imgDataAttrs[key];
                        if (typeof value === 'string' && (value.includes('.gif') || value.includes('.mp4') || value.includes('.webm'))) {
                            if (value.startsWith('http') || value.startsWith('/')) {
                                preview_video = value;
                                log.debug(`Found potential video preview in img data-attr: data-${key}=${value}`);
                                break;
                            }
                        }
                    }
                }
                if (!preview_video && itemLink.length) {
                    const linkDataAttrs = itemLink.data();
                    for (const key in linkDataAttrs) {
                        const value = linkDataAttrs[key];
                        if (typeof value === 'string' && (value.includes('.gif') || value.includes('.mp4') || value.includes('.webm'))) {
                             if (value.startsWith('http') || value.startsWith('/')) {
                                preview_video = value;
                                log.debug(`Found potential video preview in link data-attr: data-${key}=${value}`);
                                break;
                            }
                        }
                    }
                }
                if (!preview_video) {
                    const videoTagSrc = $elem.find('video.preview, source[type="video/mp4"]').attr('src');
                    if (videoTagSrc) preview_video = videoTagSrc;
                }
                if (!preview_video && thumbnail && thumbnail.toLowerCase().endsWith('.gif')) {
                    preview_video = thumbnail;
                }
                preview_video = preview_video ? this._makeAbsolute(preview_video, this.baseUrl) : null;
                if (title && url && title.length > 2) {
                    const videoData = { title, url, thumbnail: thumbnail || '', duration: duration, source: this.name };
                    if (preview_video) videoData.preview_video = preview_video;
                    videos.push(videoData);
                } else {
                    log.debug(`Skipping video item on ${this.name} due to missing/invalid title or URL. Title: '${title}', URL: '${url}'.`);
                }
            } catch (e) {
                log.warn(`Error parsing video item on ${this.name}: ${e.message}`);
            }
        });
        log.info(`Extracted ${videos.length} videos on ${this.name}.`);
        return videos;
    }

    async searchVideos(query = this.query, page = this.page) {
        const searchUrl = this.videoUrl(query, page);
        if (!searchUrl) {
            log.error(`${this.name}: Video URL could not be constructed for query "${query}", page ${page}.`);
            return [];
        }
        log.info(`${this.name}: Fetching HTML for videos from: ${searchUrl}`);
        try {
            const html = await this._fetchHtml(searchUrl);
            const $ = cheerio.load(html);
            return this.videoParser($, html);
        } catch (error) {
            log.error(`${this.name}: Error in searchVideos for query "${query}" on page ${page}: ${error.message}`);
            return [];
        }
    }

    // --- GIF Methods Implementation Attempt ---
    gifUrl(query, page = this.firstpage) {
        const pageNumber = page || this.firstpage;
        // New Attempt: Parameter-based on main search URL
        const url = `${this.baseUrl}/search/?query=${encodeURIComponent(query)}&type=gif&page=${pageNumber}`;
        log.info(`${this.name} GIF search: Constructed URL (attempt 2): ${url}`);
        return url;
    }

    async gifParser($, rawHtml, sourceUrl = '') { // Added sourceUrl parameter
        log.info(`Parsing ${this.name} GIF page... Source URL: ${sourceUrl || 'Not provided'}`);
        if (sourceUrl && sourceUrl.includes('type=gif')) {
            log.info(`${this.name} gifParser: Source URL confirms 'type=gif' parameter was used.`);
        } else if (sourceUrl) {
            log.warn(`${this.name} gifParser: Source URL does not confirm 'type=gif' parameter. URL: ${sourceUrl}`);
        }

        const gifs = [];
        const gifElements = $('div.gif-box, div.gif-item, li.gif-card'); // Removed div.video-box
        log.info(`Found ${gifElements.length} potential GIF elements using selectors: 'div.gif-box, div.gif-item, li.gif-card'.`);

        if (gifElements.length === 0 && rawHtml && rawHtml.length > 0) {
            log.warn(`${this.name} gifParser: No GIF elements found with current selectors. HTML (first 500 chars): ${rawHtml.substring(0, 500)}`);
        }

        gifElements.each((i, elem) => {
            try {
                const $elem = $(elem);
                const itemLink = $elem.find('a').first();
                let url = itemLink.attr('href');
                url = this._makeAbsolute(url, this.baseUrl);

                const imgTag = itemLink.find('img').first();
                let title = imgTag.attr('alt') || itemLink.attr('title') || itemLink.text().trim();
                title = title ? title.trim() : 'GIF';

                let thumbnail = imgTag.attr('data-src') || imgTag.attr('src');
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                let preview_video = imgTag.attr('data-gif-src') ||
                                   imgTag.attr('data-original') ||
                                   imgTag.attr('data-src') ||
                                   imgTag.attr('src');

                if (preview_video && !preview_video.toLowerCase().endsWith('.gif')) {
                    if (thumbnail && thumbnail.toLowerCase().endsWith('.gif')) {
                        preview_video = thumbnail;
                    } else {
                        const imgDataAttrs = imgTag.data();
                        for (const key in imgDataAttrs) {
                            const value = imgDataAttrs[key];
                            if (typeof value === 'string' && value.toLowerCase().endsWith('.gif')) {
                                if (value.startsWith('http') || value.startsWith('/')) {
                                    preview_video = value;
                                    log.debug(`Found .gif preview for GIF item in img data-attr: data-${key}=${value}`);
                                    break;
                                }
                            }
                        }
                    }
                }
                 preview_video = this._makeAbsolute(preview_video, this.baseUrl);

                if (preview_video && !preview_video.toLowerCase().endsWith('.gif') && thumbnail && thumbnail.toLowerCase().endsWith('.gif')) {
                    preview_video = thumbnail;
                }
                if (!preview_video && thumbnail && thumbnail.toLowerCase().endsWith('.gif')) {
                    preview_video = thumbnail;
                }

                if (title && url && preview_video && preview_video.toLowerCase().endsWith('.gif')) {
                    gifs.push({
                        title,
                        url,
                        thumbnail: thumbnail || preview_video,
                        preview_video,
                        source: this.name,
                        type: 'gifs'
                    });
                } else {
                    log.debug(`Skipping GIF item on ${this.name} due to missing title, URL, or non-GIF preview. Title: '${title}', URL: '${url}', Preview: '${preview_video}'`);
                }
            } catch (e) {
                log.warn(`Error parsing GIF item on ${this.name}: ${e.message}`);
            }
        });
        log.info(`Extracted ${gifs.length} GIFs on ${this.name}.`);
        return gifs;
    }

    async searchGifs(query = this.query, page = this.page) {
        log.info(`${this.name} GIF search: Starting searchGifs for query "${query}", page ${page}.`);
        const searchUrl = this.gifUrl(query, page);

        if (!searchUrl) {
            log.warn(`${this.name} GIF search: No URL returned by gifUrl. Aborting GIF search.`);
            return [];
        }

        log.info(`${this.name}: Fetching HTML for GIFs from: ${searchUrl}`);
        try {
            const html = await this._fetchHtml(searchUrl);
            if (process.env.DEBUG === 'true' && html) {
                log.debug(`${this.name} searchGifs: Received HTML (first 500 chars): ${html.substring(0, 500)}`);
            }
            const $ = cheerio.load(html);
            return this.gifParser($, html, searchUrl); // Pass searchUrl
        } catch (error) {
            log.error(`${this.name}: Error in searchGifs for query "${query}" on page ${page}: ${error.message}`);
            if (error.message && error.message.includes('404')) {
                log.warn(`${this.name} GIF search: Received 404 for URL ${searchUrl}. The GIF search URL structure is likely incorrect.`);
            }
            return [];
        }
    }
}

module.exports = YouPornScraper;
