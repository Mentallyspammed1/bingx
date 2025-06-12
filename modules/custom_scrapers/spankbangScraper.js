// modules/custom_scrapers/spankbangScraper.js
'use strict';

const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const log = require('../../core/log');
const cheerio = require('cheerio'); // Will be needed for parsing

class SpankbangScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.spankbang.com'; // Assuming this is the correct base URL
        log.debug(`${this.name} scraper initialized`);
    }

    get name() {
        return 'SpankBang';
    }

    get firstpage() {
        // SpankBang uses 1-indexed pagination for search results (e.g., /s/query/2/)
        // but the actual page number for the first page is often not explicitly shown as '1'
        // or it might be part of the path without a query param.
        // For /s/query/ (first page) vs /s/query/2/ (second page), 1 seems appropriate.
        return 1;
    }

    // --- Video Search Methods ---
    videoUrl(query, page) {
        // Example structure: https://www.spankbang.com/s/test/2/?o=new (page 2)
        // First page: https://www.spankbang.com/s/test/?o=new
        // The page number seems to be part of the path.
        // The 'o=new' sorts by new, other options: o=trending, o=popular, o=longest, o=shortest
        const pageSegment = (parseInt(page, 10) || 1) > 1 ? `${(parseInt(page, 10) || 1)}/` : '';
        const url = `${this.baseUrl}/s/${encodeURIComponent(query)}/${pageSegment}?o=new`;
        log.debug(`Constructed ${this.name} video URL: ${url}`);
        return url;
    }

    async searchVideos(query, page) {
        const url = this.videoUrl(query, page);
        log.info(`Fetching HTML for ${this.name} videos from: ${url}`);
        try {
            const html = await this._fetchHtml(url);
            const $ = cheerio.load(html);
            return this.videoParser($, html);
        } catch (error) {
            log.error(`Error in ${this.name} searchVideos for query "${query}" on page ${page}: ${error.message}`);
            return []; // Return empty array on error
        }
    }

    videoParser($, rawData) {
        log.info(`Parsing ${this.name} video data...`);
        const videos = [];
        // Common SpankBang selectors: div.video-item, article.video-item
        $('div.video-item').each((i, elem) => {
            try {
                const $elem = $(elem);

                const $titleLink = $elem.find('a.thumb');
                let title = $titleLink.attr('title')?.trim();
                if (!title) { // Fallback to an inner element if title attribute is missing
                    title = $elem.find('div.inf > p > a[href*="/video"]').text()?.trim();
                }
                let videoPageUrl = $titleLink.attr('href');

                const $imgElement = $elem.find('img.lazy');
                let thumbnail = $imgElement.attr('data-src') || $imgElement.attr('src');

                // Preview video: SpankBang uses a 'data-preview' attribute on the <a> tag with class 'thumb'
                // or sometimes on a specific <picture> element.
                let previewVideo = $titleLink.attr('data-preview');
                if (!previewVideo) { // Fallback if not on <a>
                    previewVideo = $elem.find('picture > source[type="video/mp4"]').attr('data-preview');
                }


                const duration = $elem.find('div.l').text()?.trim(); // Duration often in a div with class 'l' or similar

                if (title && videoPageUrl) {
                    const videoData = {
                        title,
                        url: this._makeAbsolute(videoPageUrl, this.baseUrl),
                        thumbnail: this._makeAbsolute(thumbnail, this.baseUrl),
                        duration: duration || 'N/A',
                        source: this.name,
                    };
                    if (previewVideo) {
                        // Preview video URL on SpankBang is often relative or needs cleaning
                        videoData.preview_video = this._makeAbsolute(previewVideo, this.baseUrl);
                    }
                    videos.push(videoData);
                } else {
                    log.warn(`${this.name}: Skipped an item due to missing title or URL. URL: ${videoPageUrl}`);
                }
            } catch (error) {
                log.error(`${this.name} videoParser item error: ${error.message}. Item HTML: ${$(elem).html().substring(0, 200)}`);
            }
        });
        log.info(`Parsed ${videos.length} video items from ${this.name}.`);
        return videos;
    }

    // --- GIF Search Methods (Placeholder) ---
    gifUrl(query, page) {
        // SpankBang has a GIF section: https://spankbang.com/gifs/search/QUERY/PAGE/
        const pageSegment = (parseInt(page, 10) || 1) > 1 ? `${(parseInt(page, 10) || 1)}/` : '';
        const url = `${this.baseUrl}/gifs/search/${encodeURIComponent(query)}/${pageSegment}`;
        log.debug(`Constructed ${this.name} GIF URL: ${url}`);
        return url;
    }

    async searchGifs(query, page) {
        const url = this.gifUrl(query, page);
        log.info(`Fetching HTML for ${this.name} GIFs from: ${url}`);
        try {
            const html = await this._fetchHtml(url);
            const $ = cheerio.load(html);
            return this.gifParser($, html);
        } catch (error) {
            log.error(`Error in ${this.name} searchGifs for query "${query}" on page ${page}: ${error.message}`);
            return [];
        }
    }

    gifParser($, rawData) {
        log.info(`Parsing ${this.name} GIF data...`);
        const gifs = [];
        // GIF items on SpankBang might be similar to video items, e.g., within 'div.video-item' or a specific 'div.gif-item'
        $('div.video-item').each((i, elem) => { // Using 'video-item' as it's common, adjust if specific GIF item selector exists
            try {
                const $elem = $(elem);
                const $titleLink = $elem.find('a.thumb'); // GIFs also use a.thumb
                const title = $titleLink.attr('title')?.trim();
                let gifPageUrl = $titleLink.attr('href');

                const $imgElement = $elem.find('img.lazy');
                let thumbnail = $imgElement.attr('data-src') || $imgElement.attr('src'); // Static thumbnail for GIF

                // Preview for GIF is the GIF itself. SpankBang uses 'data-preview' for this too.
                let previewGif = $titleLink.attr('data-preview');

                if (title && gifPageUrl && previewGif) {
                     gifs.push({
                        title,
                        url: this._makeAbsolute(gifPageUrl, this.baseUrl), // Link to the GIF's page
                        thumbnail: this._makeAbsolute(thumbnail, this.baseUrl), // Static thumbnail
                        preview_video: this._makeAbsolute(previewGif, this.baseUrl), // The animated GIF itself
                        source: this.name,
                    });
                } else {
                    log.warn(`${this.name} GIF Parser: Skipped an item due to missing title, page URL, or preview GIF URL.`);
                }
            } catch (error) {
                log.error(`${this.name} gifParser item error: ${error.message}. Item HTML: ${$(elem).html().substring(0, 200)}`);
            }
        });
        log.info(`Parsed ${gifs.length} GIF items from ${this.name}.`);
        return gifs;
    }
}

module.exports = SpankbangScraper;
