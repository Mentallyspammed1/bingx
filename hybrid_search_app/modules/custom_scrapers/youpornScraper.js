// modules/custom_scrapers/youpornScraper.js
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const log =require('../../core/log');
const cheerio = require('cheerio');

class YouPornScraper extends AbstractModule.with(VideoMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.youporn.com';
        log.debug(`${this.name} scraper initialized with final preview video attempt`);
    }

    get name() {
        return 'YouPorn';
    }

    get firstpage() {
        return 1;
    }

    videoUrl(query, page) {
        const url = `${this.baseUrl}/search/?query=${encodeURIComponent(query)}&page=${page}`;
        log.debug(`${this.name} video URL: ${url}`);
        return url;
    }

    async videoParser($, rawHtmlOrJsonData) {
        log.info(`Parsing ${this.name} video page with final preview video attempt...`);
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

                // Preview Video final attempts
                let preview_video = imgTag.attr('data-previewvideo') ||
                                    imgTag.attr('data-preview_url') ||
                                    imgTag.attr('data-gif_preview') ||
                                    imgTag.attr('data-gif-url') ||
                                    imgTag.attr('data-thumb_video') || // new guess
                                    imgTag.attr('data-hover_video') || // new guess
                                    itemLink.attr('data-preview-url') ||
                                    itemLink.attr('data-previewvideo') ||
                                    itemLink.attr('data-hover-url'); // new guess on link

                if (!preview_video) {
                    preview_video = $elem.attr('data-preview-url') ||
                                    $elem.attr('data-previewvideo') ||
                                    $elem.attr('data-video-preview'); // new guess on main element
                }

                // Iterate through all data attributes on the image tag as a last resort for previews
                if (!preview_video && imgTag.length) {
                    const imgDataAttrs = imgTag.data(); // Cheerio's .data() gets all data-* attributes
                    for (const key in imgDataAttrs) {
                        const value = imgDataAttrs[key];
                        if (typeof value === 'string' && (value.includes('.gif') || value.includes('.mp4') || value.includes('.webm'))) {
                            if (value.startsWith('http') || value.startsWith('/')) { // Basic check for URL-like string
                                preview_video = value;
                                log.debug(`Found potential preview in img data-attr: data-${key}=${value}`);
                                break;
                            }
                        }
                    }
                }
                 // Iterate through all data attributes on the itemLink as well
                if (!preview_video && itemLink.length) {
                    const linkDataAttrs = itemLink.data();
                    for (const key in linkDataAttrs) {
                        const value = linkDataAttrs[key];
                        if (typeof value === 'string' && (value.includes('.gif') || value.includes('.mp4') || value.includes('.webm'))) {
                             if (value.startsWith('http') || value.startsWith('/')) {
                                preview_video = value;
                                log.debug(`Found potential preview in link data-attr: data-${key}=${value}`);
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
                    const videoData = {
                        title,
                        url,
                        thumbnail: thumbnail || '',
                        duration: duration,
                        source: this.name,
                    };
                    if (preview_video) {
                        videoData.preview_video = preview_video;
                    }
                    videos.push(videoData);
                } else {
                    log.debug(`Skipping item on ${this.name} due to missing/invalid title or URL. Title: '${title}', URL: '${url}'. Item HTML: ${$elem.html() ? $elem.html().substring(0,100) : 'N/A'}`);
                }
            } catch (e) {
                log.warn(`Error parsing video item on ${this.name}: ${e.message} - Item HTML: ${$(elem).html() ? $(elem).html().substring(0,100) : 'N/A'}`);
            }
        });

        log.info(`Extracted ${videos.length} videos on ${this.name} after final preview attempt.`);
        if (videos.length === 0 && videoElements.length > 0) {
             log.warn(`Found ${videoElements.length} 'div.video-box' elements but extracted 0 items.`);
        }
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

    gifUrl(query, page) {
        log.warn(`${this.name} does not have a dedicated GIF search section. Returning empty URL.`);
        return "";
    }

    async gifParser($, rawHtmlOrJsonData) {
        log.warn(`${this.name} does not process GIFs as it lacks a dedicated GIF section.`);
        return [];
    }
}

module.exports = YouPornScraper;
