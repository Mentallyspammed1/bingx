'use strict';

const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const { logger, makeAbsolute, validatePreview, sanitizeText } = require('./driver-utils.js');

const REDTUBE_API_BASE_URL = 'https://api.redtube.com/';
const REDTUBE_WEB_BASE_URL = 'https://www.redtube.com/';
const DRIVER_NAME = 'Redtube';

const BaseRedtubeClass = AbstractModule.with(VideoMixin);

/**
 * @class RedtubeDriver
 * @classdesc Driver for fetching video content from Redtube using their official API.
 * This driver specifically implements the `VideoMixin` methods.
 */
class RedtubeDriver extends BaseRedtubeClass {
    constructor(options = {}) {
        super(options);
        logger.debug(`[${DRIVER_NAME}] Initialized.`);
    }

    get name() { return DRIVER_NAME; }
    get baseUrl() { return REDTUBE_WEB_BASE_URL; } // For resolving URLs from API response
    hasVideoSupport() { return true; }
    hasGifSupport() { return false; }

    /**
     * Constructs the Redtube API URL for video search.
     * @param {string} query - The search query.
     * @param {number} page - The page number (1-indexed).
     * @returns {string} The full API URL for the search.
     */
    getVideoSearchUrl(query, page) {
        const encodedQuery = encodeURIComponent(query.trim());
        const pageParam = Math.max(1, page || this.firstpage);
        const url = new URL(REDTUBE_API_BASE_URL);
        url.searchParams.set('data', 'redtube.videos.search');
        url.searchParams.set('search', encodedQuery);
        url.searchParams.set('page', pageParam);
        logger.debug(`[${this.name}] Generated video search URL: ${url.href}`);
        return url.href;
    }

    getGifSearchUrl(query, page) {
        logger.warn(`[${this.name}] GIF search is not supported.`);
        return null;
    }

    /**
     * Parses the JSON response from the new Redtube API endpoint.
     * @param {null} $ - Cheerio instance (null for API responses).
     * @param {object} rawData - The raw JSON response object from Redtube API.
     * @param {object} options - Options containing search context.
     * @returns {Array<object>} An array of structured video results.
     */
    parseResults($, rawData, options) {
        const { type, sourceName } = options;
        const results = [];

        if (type !== 'videos') {
            logger.warn(`[${sourceName}] This driver only supports 'videos', not '${type}'.`);
            return [];
        }

        // The new endpoint nests the videos inside a 'videos' property on the 'data' object
        const videoItems = rawData && rawData.data ? rawData.data.videos : [];

        if (!videoItems || !Array.isArray(videoItems) || videoItems.length === 0) {
            logger.warn(`[${sourceName}] Invalid or empty API response. Expected a 'data.videos' array.`, rawData);
            return [];
        }

        logger.info(`[${sourceName}] Parsing ${videoItems.length} video results from API...`);

        videoItems.forEach(apiVideoData => {
            if (!apiVideoData || !apiVideoData.id) {
                logger.warn(`[${sourceName}] Skipping malformed video item from API:`, apiVideoData);
                return;
            }

            const id = apiVideoData.id;
            const title = sanitizeText(apiVideoData.title);
            // The new API provides a full URL in the 'url' field
            const url = apiVideoData.url;
            const duration = sanitizeText(apiVideoData.duration);
            const thumbnail = apiVideoData.media_definitions?.[0]?.default_url; // A more reliable thumbnail source
            const preview_video = apiVideoData.media_definitions?.[0]?.video_url;

            if (!id || !title || !url || !thumbnail) {
                logger.warn(`[${sourceName}] Skipping API video item due to missing essential data:`, { id, title, url, thumbnail });
                return;
            }

            results.push({
                id: id,
                title: title,
                url: url,
                duration: duration,
                thumbnail: thumbnail,
                preview_video: validatePreview(preview_video) ? preview_video : undefined,
                source: sourceName,
                type: 'videos'
            });
        });

        logger.info(`[${sourceName}] Parsed ${results.length} video results.`);
        return results;
    }
}

module.exports = RedtubeDriver;