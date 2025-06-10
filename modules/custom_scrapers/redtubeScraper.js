// modules/custom_scrapers/redtubeScraper.js
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
// const GifMixin = require('../../core/GifMixin'); // Not including for now, assuming video-focused
const log = require('../../core/log');

class RedtubeScraper extends AbstractModule.with(VideoMixin) { // No GifMixin initially
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.redtube.com';
        log.debug(`${this.name} scraper initialized`);
    }

    get name() {
        return 'Redtube';
    }

    get firstpage() {
        // Assuming 1-indexed pagination
        return 1;
    }

    videoUrl(query, page) {
        // Example: https://www.redtube.com/?search=test&page=2 (This is a common pattern)
        // Redtube might use specific paths like /redtube/test/page/2 or query params.
        // The provided example seems plausible.
        const url = `${this.baseUrl}/?search=${encodeURIComponent(query)}&page=${page}`;
        log.debug(`${this.name} video URL: ${url}`);
        return url;
    }

    async videoParser($, rawHtmlOrJsonData) {
        log.info(`Parsing ${this.name} video page... Query URL: ${$._originalUrl || 'N/A'}`);
        const videos = [];
        // Common selectors: 'div.video_item', 'li.tile', '.video-tile', 'div.video_bloc'
        // Redtube's structure might involve 'li' elements with a specific class for video items.
        // Let's try a selector for list items that look like video blocks.
        $('li.video_tile_wrapper').each((i, elem) => { // Speculative selector based on potential Redtube structure
            try {
                const $elem = $(elem);

                const titleLink = $elem.find('a.video_link');
                const title = titleLink.attr('title') || $elem.find('.video_title').text().trim();
                let url = titleLink.attr('href');
                url = this._makeAbsolute(url, this.baseUrl);

                const thumbnailTag = $elem.find('img.video_thumbnail, img.preview_thumb_image');
                let thumbnail = thumbnailTag.attr('data-src') || thumbnailTag.attr('src'); // data-src is common for lazy loading
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                const durationElement = $elem.find('.duration, .video_duration');
                const duration = durationElement.first().text().trim();

                // Preview video: Often in 'data-previewhtml5' or similar, or from mouseover events.
                // Redtube might use a specific attribute or a script to load previews.
                let preview_video = thumbnailTag.attr('data-mediabook') || thumbnailTag.attr('data-previewvideo'); // data-mediabook is seen on some similar sites
                if (preview_video && preview_video.startsWith "[" ) { // if it's a JSON array of sources
                    try {
                        const sources = JSON.parse(preview_video);
                        preview_video = sources[0].src; // take the first source
                    } catch (jsonErr) {
                        log.warn(`Could not parse preview_video JSON on ${this.name}: ${preview_video}`);
                        preview_video = null;
                    }
                }
                preview_video = this._makeAbsolute(preview_video, this.baseUrl);

                if (title && url) {
                    videos.push({
                        title,
                        url,
                        thumbnail,
                        duration,
                        preview_video: preview_video || thumbnail, // Fallback to thumbnail
                        source: this.name,
                    });
                } else {
                    // log.debug(`Skipping item on ${this.name} due to missing title or URL. HTML: ${$elem.html().substring(0,100)}`);
                }
            } catch (e) {
                log.warn(`Error parsing video item on ${this.name}: ${e.message} - Item HTML: ${$(elem).html().substring(0,100)}`);
            }
        });
        log.info(`Found ${videos.length} videos on ${this.name} page: ${$._originalUrl || 'N/A'}`);
        if (videos.length === 0 && rawHtmlOrJsonData && rawHtmlOrJsonData.length > 100) {
            log.warn(`No videos found for ${this.name} on ${$._originalUrl || 'N/A'}, but received HTML. Selectors might be outdated or page uses JS rendering heavily.`);
             // Redtube and similar sites sometimes embed data in JSON within <script> tags
            if (rawHtmlOrJsonData.includes("window.pageData") || rawHtmlOrJsonData.includes("window.initialData")) {
                log.info(`${this.name}: Page might contain JSON data (e.g., window.pageData) not parsed by current selectors.`);
            }
        }
        return videos;
    }

    gifUrl(query, page) {
        log.warn(`${this.name} is primarily a video site. Dedicated GIF search is assumed not available. Returning empty URL.`);
        return "";
    }

    async gifParser($, rawHtmlOrJsonData) {
        log.warn(`${this.name} does not process GIFs as it's video-focused. Returning empty array.`);
        return [];
    }
}

module.exports = RedtubeScraper;
