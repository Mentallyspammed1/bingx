// modules/custom_scrapers/youpornScraper.js
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const log = require('../../core/log'); // Uses the newly created log.js
const cheerio = require('cheerio'); // Add cheerio at the top

class YouPornScraper extends AbstractModule.with(VideoMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.youporn.com';
        // log is now directly from the required module, no need to create instance-specific one unless desired
        log.debug(`${this.name} scraper initialized`);
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
        log.info(`Parsing ${this.name} video page...`);
        const videos = [];
        $('div[class*="video-card_video-card_"]').each((i, elem) => {
            try {
                const $elem = $(elem);

                const titleLink = $elem.find('a[data-test-video-tile-title]');
                const title = titleLink.attr('title') || titleLink.text().trim();
                let url = titleLink.attr('href');
                url = this._makeAbsolute(url, this.baseUrl);

                const thumbnailTag = $elem.find('img[data-test-video-tile-img]');
                let thumbnail = thumbnailTag.attr('src') || thumbnailTag.attr('data-src');
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                const durationElement = $elem.find('span[data-test-video-tile-duration], .video-duration');
                const duration = durationElement.first().text().trim();

                let preview_video = thumbnailTag.attr('data-preview') || $elem.find('video.preview, source[type="video/mp4"]').attr('src');
                if(!preview_video && thumbnailTag.attr('onmouseover')) {
                    const mouseoverContent = thumbnailTag.attr('onmouseover');
                    const urlMatch = mouseoverContent.match(/previewUrl['"]:\s*['"]([^'"]+)['"]/);
                    if(urlMatch && urlMatch[1]) {
                        preview_video = urlMatch[1];
                    }
                }
                preview_video = preview_video ? this._makeAbsolute(preview_video, this.baseUrl) : null;

                if (title && url) {
                    const videoData = {
                        title,
                        url,
                        thumbnail,
                        duration,
                        source: this.name,
                    };
                    if (preview_video) {
                        videoData.preview_video = preview_video;
                    }
                    videos.push(videoData);
                } else {
                    log.debug(`Skipping item on ${this.name} due to missing title or URL. Item HTML: ${$elem.html() ? $elem.html().substring(0,100) : 'N/A'}`);
                }
            } catch (e) {
                log.warn(`Error parsing video item on ${this.name}: ${e.message} - Item HTML: ${$(elem).html() ? $(elem).html().substring(0,100) : 'N/A'}`);
            }
        });
        log.info(`Found ${videos.length} videos on ${this.name}`);
        if (videos.length === 0 && rawHtmlOrJsonData && rawHtmlOrJsonData.length > 100) {
            log.warn(`No videos found for ${this.name}, but received HTML. Selectors might be outdated.`);
            if (typeof rawHtmlOrJsonData === 'string' && rawHtmlOrJsonData.includes("initialState")) {
                log.info(`${this.name}: Page seems to contain JSON state, which might hold video data not parsed by current selectors.`);
            }
        }
        return videos;
    }

    // Added searchVideos method
    async searchVideos(query = this.query, page = this.page) {
        const searchUrl = this.videoUrl(query, page); // Corrected to searchUrl
        if (!searchUrl) {
            log.error(`${this.name}: Video URL could not be constructed for query "${query}", page ${page}.`);
            return [];
        }
        log.info(`${this.name}: Fetching HTML for videos from: ${searchUrl}`);
        try {
            const html = await this._fetchHtml(searchUrl); // _fetchHtml from AbstractModule
            // Cheerio is already required at the top of the file
            const $ = cheerio.load(html);
            return this.videoParser($, html); // Call the class's own videoParser
        } catch (error) {
            log.error(`${this.name}: Error in searchVideos for query "${query}" on page ${page}: ${error.message}`);
            return []; // Return empty array on error
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
