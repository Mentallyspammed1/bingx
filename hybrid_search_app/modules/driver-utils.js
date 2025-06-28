'use strict';

const chalk = require('chalk'); // Ensure chalk is a dependency
const config = require('../config'); // Assumes config.js is in the parent directory (e.g., hybrid_search_app/config.js)

const logLevels = {
    silly: 0,
    debug: 1,
    info: 2,
    warn: 3,
    error: 4
};
const currentLogLevel = logLevels[(config.global.logLevel || 'info').toLowerCase()] || logLevels.info;

/**
 * Centralized logger for drivers.
 */
const logger = {
    silly: (message, ...args) => {
        if (currentLogLevel <= logLevels.silly) console.log(chalk.gray(`[SILLY] ${message}`), ...args);
    },
    debug: (message, ...args) => {
        if (currentLogLevel <= logLevels.debug) console.log(chalk.blue(`[DEBUG] ${message}`), ...args);
    },
    info: (message, ...args) => {
        if (currentLogLevel <= logLevels.info) console.log(chalk.white(`[INFO] ${message}`), ...args);
    },
    warn: (message, ...args) => {
        if (currentLogLevel <= logLevels.warn) console.warn(chalk.yellow(`[WARN] ${message}`), ...args);
    },
    error: (message, ...args) => {
        if (currentLogLevel <= logLevels.error) console.error(chalk.red(`[ERROR] ${message}`), ...args);
    }
};

/**
 * Helper to ensure URLs are absolute.
 * @param {string | undefined | null} urlString - The URL string to convert.
 * @param {string} baseUrl - The base URL to use for resolving relative URLs.
 * @returns {string | undefined} The absolute URL, or undefined if input is invalid.
 */
function makeAbsolute(urlString, baseUrl) {
    if (!urlString || typeof urlString !== 'string' || urlString.trim() === '') return undefined;
    if (urlString.startsWith('data:')) return urlString; // Data URIs are absolute

    try {
        if (urlString.startsWith('//')) {
            return new URL(`https:${urlString}`).href; // Protocol-relative URLs
        }
        // Check if it's already absolute
        if (urlString.startsWith('http:') || urlString.startsWith('https:')) {
            return new URL(urlString).href; // Validate and normalize
        }
        // Otherwise, resolve against the base URL
        return new URL(urlString, baseUrl).href;
    } catch (e) {
        logger.warn(`[URL Helper] Failed to resolve URL: "${urlString}" with base "${baseUrl}". Error: ${e.message}`);
        return undefined;
    }
}

/**
 * Extracts a consistent preview URL from various possible attributes on a Cheerio element.
 * @param {import('cheerio').Cheerio<import('cheerio').Element>} $item - The Cheerio element (item context) to inspect.
 * @param {string} baseUrl - The base URL for resolving relative paths.
 * @param {boolean} [isGif=false] - Hint if parsing for a GIF, to prioritize GIF-like sources.
 * @returns {string|undefined} The absolute URL to a preview video/gif, or undefined.
 */
function extractPreview($item, baseUrl, isGif = false) {
    let previewUrl;

    // Prioritize data attributes commonly used for video previews
    previewUrl = $item.attr('data-previewvideo') ||
                 $item.attr('data-preview') ||
                 $item.attr('data-preview-url') ||
                 $item.attr('data-mediabook') || // Common on Pornhub for sprites, but sometimes video
                 $item.attr('data-webm') ||
                 $item.attr('data-mp4');

    // If no data attribute found, look for <video> tags within the item
    if (!previewUrl) {
        const videoTag = $item.find('video').first();
        if (videoTag.length) {
            previewUrl = videoTag.attr('src') || videoTag.find('source').first().attr('src');
        }
    }

    // For GIFs, or if still no preview, check image attributes (sometimes animated GIFs are in data-src)
    if (isGif && !previewUrl) {
        const imgTag = $item.find('img').first();
        if (imgTag.length) {
            const dataSrc = imgTag.attr('data-src');
            const src = imgTag.attr('src');
            if (dataSrc && dataSrc.toLowerCase().endsWith('.gif')) {
                previewUrl = dataSrc;
            } else if (src && src.toLowerCase().endsWith('.gif')) {
                previewUrl = src;
            }
        }
    }

    // If a URL was found, make it absolute
    return previewUrl ? makeAbsolute(previewUrl, baseUrl) : undefined;
}


/**
 * Validates if a preview URL is usable (not a common placeholder or empty).
 * @param {string | undefined | null} url - The URL to validate.
 * @returns {boolean} True if the URL is likely a valid media preview.
 */
function validatePreview(url) {
    if (!url || typeof url !== 'string' || url.trim() === '') return false;

    const lowerUrl = url.toLowerCase();
    // Avoid common placeholder image strings or data URIs that aren't actual media
    if (url.startsWith('data:image/') && !url.startsWith('data:image/gif') && !url.startsWith('data:image/webp')) { // Allow animated data URIs
        return false;
    }
    return !lowerUrl.includes('nothumb') &&
           !lowerUrl.includes('no_thumb') &&
           !lowerUrl.includes('placeholder') &&
           !lowerUrl.includes('default_image') &&
           !lowerUrl.includes('blank.gif') &&
           !lowerUrl.includes('pixel.gif');
}

/**
 * Sanitize text by removing extra whitespace, newlines, and trimming.
 * @param {string|null|undefined} text - The input text.
 * @returns {string|undefined} The sanitized text, or undefined if input is empty or not a string.
 */
function sanitizeText(text) {
    if (typeof text !== 'string') return undefined;
    const cleanedText = text.replace(/\s+/g, ' ').trim(); // Replace multiple spaces/newlines with single, then trim.
    return cleanedText === '' ? undefined : cleanedText; // Return undefined if empty after cleaning.
}


module.exports = {
    logger,
    makeAbsolute,
    extractPreview,
    validatePreview,
    sanitizeText
};
