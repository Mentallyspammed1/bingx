// modules/custom_scrapers/sexComScraper.js
const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');
const log = require('../../core/log');

class SexComScraper extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(options) {
        super(options);
        this.baseUrl = 'https://www.sex.com';
        log.debug(`${this.name} scraper initialized`);
    }

    get name() {
        return 'SexCom';
    }

    get firstpage() {
        // Assuming 1-indexed pagination, can be adjusted later
        return 1;
    }

    videoUrl(query, page) {
        // Needs verification, example: https://www.sex.com/search/videos?query=test&page=2
        const url = `${this.baseUrl}/search/videos?query=${encodeURIComponent(query)}&page=${page}`;
        log.debug(`${this.name} video URL: ${url}`);
        return url;
    }

    async videoParser($, rawHtmlOrJsonData) {
        log.info(`Parsing ${this.name} video page...`);
        const videos = [];
        // Example selector, needs verification (e.g., 'div.video_item', 'article.video_container', '.masonry_item_video_small')
        // A common pattern from sex.com appears to be items with 'data-id' within a masonry container
        $('.masonry_item[data-id]').each((i, elem) => { // This selector is a guess based on common patterns
            try {
                const $elem = $(elem);
                // Check if it's a video item, sometimes sites mix content or have ads
                // For instance, by looking for a duration element or a specific class
                if ($elem.find('.duration, .video_duration_indicator').length === 0 && !$elem.is('article[data-type="video"]')) {
                    // Not a clear video item, skip (or refine selector)
                    // log.debug(`Skipping non-video item on ${this.name}: ${$elem.html().substring(0,100)}`);
                    return;
                }

                const title = $elem.find('.title a, .video_title a, .video_item_title_small a').attr('title') || $elem.find('.title a, .video_title a, .video_item_title_small a').text().trim();
                let url = $elem.find('.title a, .video_title a, .video_item_title_small a').attr('href');
                url = this._makeAbsolute(url, this.baseUrl);

                // Thumbnails can be tricky: 'src', 'data-src', 'data-poster'
                let thumbnail = $elem.find('img.video_item_img_small, img.video_item_img, img.thumb').attr('data-src') || $elem.find('img.video_item_img_small, img.video_item_img, img.thumb').attr('src');
                if (!thumbnail && $elem.attr('data-defaultthumb')) { // another common pattern
                    thumbnail = $elem.attr('data-defaultthumb');
                }
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                const durationElement = $elem.find('.duration, .video_duration_indicator, .video_item_duration_small');
                const duration = durationElement.first().text().trim();

                // Preview video: 'data-previewvideo', 'data-mp4', or from script tags sometimes
                let preview_video = $elem.attr('data-previewvideo') || $elem.attr('data-mp4');
                if (!preview_video) {
                     // Sometimes it's within a script tag or a more complex attribute
                    const imgTag = $elem.find('img.video_item_img_small, img.video_item_img, img.thumb');
                    preview_video = imgTag.attr('data-preview') || imgTag.attr('onmouseover'); // onmouseover might contain URL
                    if (preview_video && preview_video.includes('url(')) { // Basic parsing if it's in style
                        preview_video = preview_video.substring(preview_video.indexOf('url(') + 4, preview_video.lastIndexOf(')'));
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
        log.info(`Found ${videos.length} videos on ${this.name}`);
        if (videos.length === 0 && rawHtmlOrJsonData && rawHtmlOrJsonData.length > 100) {
            log.warn(`No videos found for ${this.name}, but received HTML. Selectors might be outdated.`);
        }
        return videos;
    }

    gifUrl(query, page) {
        // Needs verification, example: https://www.sex.com/search/gifs?query=test&page=2
        const url = `${this.baseUrl}/search/gifs?query=${encodeURIComponent(query)}&page=${page}`;
        log.debug(`${this.name} GIF URL: ${url}`);
        return url;
    }

    async gifParser($, rawHtmlOrJsonData) {
        log.info(`Parsing ${this.name} GIF page...`);
        const gifs = [];
        // Example selectors, needs verification (e.g., 'div.gif_item', 'a.gif_link', '.masonry_item_gif_small')
        // Similar to videos, items might be in a masonry layout
        $('.masonry_item[data-id]').each((i, elem) => { // This selector is a guess
            try {
                const $elem = $(elem);
                // Check if it's a GIF item, e.g. by data-type or specific class
                if (!$elem.is('article[data-type="gif"]') && $elem.find('img[alt*="GIF"]').length === 0 && !$elem.find('.gif_item_play_icon').length > 0) {
                     // log.debug(`Skipping non-GIF item on ${this.name}: ${$elem.html().substring(0,100)}`);
                    return; // Not a clear GIF item
                }

                const title = $elem.find('.title a, .gif_title a, .gif_item_title_small a').attr('title') || $elem.find('.title a, .gif_title a, .gif_item_title_small a').text().trim() || $elem.find('img').attr('alt');
                let url = $elem.find('.title a, .gif_title a, .gif_item_title_small a').attr('href');
                if (!url) { // Sometimes the whole item is a link
                    url = $elem.find('a').first().attr('href');
                }
                url = this._makeAbsolute(url, this.baseUrl);

                let thumbnail = $elem.find('img.gif_item_img_small, img.gif_image, img.thumb').attr('src'); // Static image
                thumbnail = this._makeAbsolute(thumbnail, this.baseUrl);

                // Animated GIF URL: often 'data-src', 'data-gifurl', 'data-mp4' for "gifv"
                let preview_video = $elem.find('img.gif_item_img_small, img.gif_image, img.thumb').attr('data-src') || $elem.find('img.gif_item_img_small, img.gif_image, img.thumb').attr('data-gifurl') || $elem.attr('data-mp4');
                preview_video = this._makeAbsolute(preview_video, this.baseUrl);

                if (title && url) {
                    gifs.push({
                        title,
                        url,
                        thumbnail, // Static image
                        preview_video: preview_video || thumbnail, // Animated GIF, fallback to static
                        source: this.name,
                    });
                } else {
                    // log.debug(`Skipping GIF item on ${this.name} due to missing title or URL. HTML: ${$elem.html().substring(0,100)}`);
                }
            } catch (e) {
                log.warn(`Error parsing GIF item on ${this.name}: ${e.message} - Item HTML: ${$(elem).html().substring(0,100)}`);
            }
        });
        log.info(`Found ${gifs.length} GIFs on ${this.name}`);
        if (gifs.length === 0 && rawHtmlOrJsonData && rawHtmlOrJsonData.length > 100) {
            log.warn(`No GIFs found for ${this.name}, but received HTML. Selectors might be outdated or no GIFs on page.`);
        }
        return gifs;
    }
}

module.exports = SexComScraper;
