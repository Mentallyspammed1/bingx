'use strict';

const cheerio = require('cheerio');
const chalk = require('chalk');
const axios = require('axios');
const { HttpsProxyAgent } = require('https-proxy-agent');

/**
 * Custom logger with colorized output and log level control.
 */
const logger = {
  // Set to true to enable debug logs; can be toggled via environment variable
  debugEnabled: process.env.DEBUG_DRIVER_UTILS === 'true' || process.env.DEBUG === 'true', // Allow general DEBUG env var too

  info: (...args) => console.log(chalk.green(`[INFO] ${args.join(' ')}`)),

  warn: (...args) => console.warn(chalk.yellow(`[WARN] ${args.join(' ')}`)),

  error: (...args) => console.error(chalk.red(`[ERROR] ${args.join(' ')}`)),

  debug: (...args) => {
    if (logger.debugEnabled) {
      console.log(chalk.cyan(`[DEBUG] ${args.join(' ')}`));
    }
  }
};

/**
 * A list of common User-Agent strings to rotate through.
 */
const USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
    'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36'
];

/**
 * Selects a random User-Agent from the list.
 * @returns {string} A User-Agent string.
 */
function getRandomUserAgent() {
    return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
}

/**
 * Fetches a URL with a retry mechanism, exponential backoff, and proxy support.
 * @param {string} url - The URL to fetch.
 * @param {object} axiosOptions - Options to pass to axios.
 * @param {number} retries - The maximum number of retries.
 * @param {number} delay - The initial delay in milliseconds.
 * @returns {Promise<object>} The axios response object.
 */
async function fetchWithRetry(url, axiosOptions = {}, retries = 3, delay = 1000) {
    const proxyUrl = process.env.HTTP_PROXY || process.env.HTTPS_PROXY;
    if (proxyUrl) {
        logger.debug(`Using proxy: ${proxyUrl}`);
        axiosOptions.httpsAgent = new HttpsProxyAgent(proxyUrl);
        axiosOptions.proxy = false; // Axios needs this to be false when using an agent
    }

    for (let i = 0; i < retries; i++) {
        try {
            const response = await axios(url, axiosOptions);
            return response;
        } catch (error) {
            const isRetryable = error.response && (error.response.status === 429 || error.response.status >= 500);
            logger.error(`[fetchWithRetry] Attempt ${i + 1}/${retries} failed for ${url}: ${error.message}`);

            if (isRetryable && i < retries - 1) {
                logger.warn(`[fetchWithRetry] Retrying in ${delay}ms...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                delay *= 2; // Exponential backoff
            } else {
                throw error; // Re-throw if not retryable or all retries fail
            }
        }
    }
}


/**
 * Common video formats and HLS streams regex.
 * Added 'mov' as it's common, though might require specific browser support.
 */
const PREVIEW_VALID_FORMATS_REGEX = /\.(mp4|webm|m3u8|gif|mov)$/i;

/**
 * Regex to discard common placeholder/error images that might accidentally match.
 */
const PREVIEW_PLACEHOLDER_REGEX = /(no-preview|nothumb|placeholder|default-thumbnail|error|404|coming_soon|blank)\.(jpg|png|gif|jpeg)$/i;

/**
 * Common data attributes to check for preview video URLs.
 */
const PREVIEW_DATA_ATTRIBUTES = [
  'data-preview', 'data-video-preview', 'data-videopreview', 'data-video-url',
  'data-media-url', 'data-previewvideo', 'data-src', 'data-webm', 'data-mp4',
  'data-gifsrc', 'data-preview-url', 'data-poster-url', 'data-gif-url'
];

/**
 * Regex to find video URLs within script tags or data-html attributes.
 * Enhanced to look for more key names and formats.
 */
const INLINE_VIDEO_URL_REGEX = /"(?:contentUrl|video|preview|videoUrl|videoPreviewUrl|src|url|webm|mp4|m3u8|gifUrl)":\s*"([^"]+\.(?:mp4|webm|m3u8|gif|mov))"/i;


/**
 * Makes a URL absolute if it's relative, handling edge cases.
 * @param {string|undefined} url - The URL to process.
 * @param {string} baseUrl - The base URL to prepend if the URL is relative.
 * @returns {string|undefined} The absolute URL or undefined.
 */
function makeAbsolute(url, baseUrl) {
  if (!url || typeof url !== 'string') {
    logger.debug(chalk.yellow(`Invalid or missing URL input for makeAbsolute: ${url}`));
    return undefined;
  }
  if (!baseUrl || typeof baseUrl !== 'string' || !baseUrl.match(/^https?:\/\//)) {
    logger.warn(chalk.red(`Invalid base URL provided to makeAbsolute: ${baseUrl}`));
    return undefined;
  }

  // Handle protocol-relative URLs (//example.com)
  if (url.startsWith('//')) {
    return `https:${url}`;
  }
  // Return absolute URLs unchanged
  if (url.match(/^https?:\/\//)) {
    return url;
  }

  try {
    // Use URL constructor for robust relative path resolution
    const absoluteUrl = new URL(url, baseUrl).href;
    logger.debug(chalk.blue(`Forged absolute URL: ${absoluteUrl} (from ${url} and ${baseUrl})`));
    return absoluteUrl;
  } catch (e) {
    logger.warn(chalk.yellow(`Failed to forge absolute URL for "${url}" with base "${baseUrl}": ${e.message}`));
    return undefined;
  }
}

/**
 * Validates if a preview URL is valid.
 * @param {string|undefined} url - The preview URL.
 * @returns {boolean} True if valid.
 */
function validatePreview(url) {
  if (!url || typeof url !== 'string') {
    logger.debug(chalk.yellow(`Preview URL is not a string or is empty: ${url}`));
    return false;
  }

  const isValidUrlScheme = url.match(/^https?:\/\/.+/i);

  if (!isValidUrlScheme) {
    logger.debug(chalk.yellow(`Preview URL "${url}" does not have a valid http/https scheme.`));
    return false;
  }
  if (!PREVIEW_VALID_FORMATS_REGEX.test(url)) {
    logger.debug(chalk.yellow(`Preview URL "${url}" does not match a valid video/gif format.`));
    return false;
  }
  if (PREVIEW_PLACEHOLDER_REGEX.test(url)) {
    logger.debug(chalk.yellow(`Preview URL "${url}" appears to be a placeholder image.`));
    return false;
  }

  return true;
}


/**
 * Extracts preview video URL from an item, centralizing logic for drivers.
 * This function attempts multiple strategies to find the most likely preview video.
 * It now attempts to make URLs absolute before validation.
 * @param {import('cheerio').CheerioAPI} $ - Cheerio instance.
 * @param {import('cheerio').Cheerio<import('cheerio').Element>} item - The Cheerio element for the item.
 * @param {string} driverName - Name of the driver for context.
 * @param {string} baseUrl - The base URL for the current driver/website, used to make relative URLs absolute.
 * @returns {string|undefined} URL of the preview video or undefined.
 */
function extractPreview($, item, driverName, baseUrl) {
  if (typeof $ !== 'function' || !item || !driverName || !baseUrl) {
    logger.warn(chalk.red(`[${driverName || 'N/A'}] Invalid arguments for extractPreview. Required: $, item, driverName, baseUrl.`));
    return undefined;
  }

  let previewVideoCandidate;
  let absolutePreviewUrl;
  logger.debug(chalk.cyan(`[${driverName}] Attempting to extract preview video for item...`));

  // Strategy 1: Check for nested <video> tags first (most direct and reliable)
  const videoTag = item.find('video[src], video[data-src], video[data-video-src], video[data-preview-src], video').first();
  if (videoTag.length) {
    previewVideoCandidate = videoTag.attr('src') ||
      videoTag.attr('data-src') ||
      videoTag.attr('data-video-src') ||
      videoTag.attr('data-preview-src') ||
      videoTag.attr('data-webm') || // Added data-webm
      videoTag.find('source[src], source[data-src]').first().attr('src') ||
      videoTag.find('source[src], source[data-src]').first().attr('data-src');

    if (previewVideoCandidate) {
      logger.debug(chalk.blue(`[${driverName}] Found raw preview from <video> tag: ${previewVideoCandidate}`));
      absolutePreviewUrl = makeAbsolute(previewVideoCandidate, baseUrl);
      if (absolutePreviewUrl && validatePreview(absolutePreviewUrl)) {
        return absolutePreviewUrl;
      } else {
        logger.debug(chalk.yellow(`[${driverName}] <video> tag preview candidate "${previewVideoCandidate}" (absolute: ${absolutePreviewUrl}) failed validation.`));
      }
    }
  }

  // Strategy 2: Check common data attributes on link, image and container
  const linkElement = item.find('a').first();
  const imgElement = item.find('img[class*="thumb"], img[class*="image"], img').first();

  for (const attr of PREVIEW_DATA_ATTRIBUTES) {
    if (linkElement.length && linkElement.attr(attr)) {
      previewVideoCandidate = linkElement.attr(attr);
      logger.debug(chalk.blue(`[${driverName}] Found raw preview from link data attribute "${attr}": ${previewVideoCandidate}`));
      absolutePreviewUrl = makeAbsolute(previewVideoCandidate, baseUrl);
      if (absolutePreviewUrl && validatePreview(absolutePreviewUrl)) return absolutePreviewUrl;
    }
    if (imgElement.length && imgElement.attr(attr)) {
      previewVideoCandidate = imgElement.attr(attr);
      logger.debug(chalk.blue(`[${driverName}] Found raw preview from image data attribute "${attr}": ${previewVideoCandidate}`));
      absolutePreviewUrl = makeAbsolute(previewVideoCandidate, baseUrl);
      if (absolutePreviewUrl && validatePreview(absolutePreviewUrl)) return absolutePreviewUrl;
    }
    if (item.attr(attr)) {
      previewVideoCandidate = item.attr(attr);
      logger.debug(chalk.blue(`[${driverName}] Found raw preview from container data attribute "${attr}": ${previewVideoCandidate}`));
      absolutePreviewUrl = makeAbsolute(previewVideoCandidate, baseUrl);
      if (absolutePreviewUrl && validatePreview(absolutePreviewUrl)) return absolutePreviewUrl;
    }
  }

  // Strategy 3: Parse data-previewhtml (often contains a video tag or direct URL)
  const previewHtmlAttr = item.attr('data-previewhtml') || item.attr('data-html');
  if (previewHtmlAttr) {
    try {
      const $previewHtml = cheerio.load(previewHtmlAttr);
      const videoInHtml = $previewHtml('video[src], video[data-src], source[src], source[data-src]').first();
      if (videoInHtml.length) {
        previewVideoCandidate = videoInHtml.attr('src') || videoInHtml.attr('data-src');
        if (previewVideoCandidate) {
          logger.debug(chalk.blue(`[${driverName}] Found raw preview from data-previewhtml (cheerio): ${previewVideoCandidate}`));
          absolutePreviewUrl = makeAbsolute(previewVideoCandidate, baseUrl);
          if (absolutePreviewUrl && validatePreview(absolutePreviewUrl)) return absolutePreviewUrl;
        }
      }
      // Also check for direct video URLs in the raw HTML string if no video tag found
      if (!previewVideoCandidate) {
        const urlMatch = previewHtmlAttr.match(INLINE_VIDEO_URL_REGEX);
        if (urlMatch && urlMatch[1]) {
          previewVideoCandidate = urlMatch[1];
          logger.debug(chalk.blue(`[${driverName}] Found raw preview from data-previewhtml regex: ${previewVideoCandidate}`));
          absolutePreviewUrl = makeAbsolute(previewVideoCandidate, baseUrl);
          if (absolutePreviewUrl && validatePreview(absolutePreviewUrl)) return absolutePreviewUrl;
        }
      }
    } catch (e) {
      logger.warn(chalk.yellow(`[${driverName}] Failed to parse data-previewhtml: ${e.message}`));
    }
  }

  // Strategy 4: Check JSON-LD or inline scripts for video URLs
  const scripts = item.find('script[type="application/ld+json"], script:not([src])').toArray(); // Exclude external scripts
  for (const script of scripts) {
    const scriptData = $(script).html();
    if (scriptData) {
      try {
        let jsonData;
        try {
          jsonData = JSON.parse(scriptData);
          // Check common JSON-LD video properties
          if (jsonData[' @type'] === 'VideoObject' && jsonData.contentUrl) {
            previewVideoCandidate = jsonData.contentUrl;
          } else if (jsonData.video && (jsonData.video.contentUrl || jsonData.video.url)) {
            previewVideoCandidate = jsonData.video.contentUrl || jsonData.video.url;
          } else if (jsonData.preview) { // Direct preview property
            previewVideoCandidate = jsonData.preview;
          }
        } catch (e) {
          // If JSON parsing fails or doesn't find, try regex for common video URL patterns in scripts
          const match = scriptData.match(INLINE_VIDEO_URL_REGEX);
          if (match && match[1]) {
            previewVideoCandidate = match[1];
          }
        }
        if (previewVideoCandidate) {
          logger.debug(chalk.blue(`[${driverName}] Found raw preview from script JSON/Regex: ${previewVideoCandidate}`));
          absolutePreviewUrl = makeAbsolute(previewVideoCandidate, baseUrl);
          if (absolutePreviewUrl && validatePreview(absolutePreviewUrl)) return absolutePreviewUrl;
        }
      } catch (e) {
        logger.debug(chalk.yellow(`[${driverName}] Script content processing error: ${e.message}`));
      }
    }
  }

  // Strategy 5: Fallback to thumbnail if it’s a video format (animated thumbnail)
  const currentThumbnail = imgElement.attr('data-src') || imgElement.attr('src') || imgElement.attr('data-poster');
  if (currentThumbnail) {
    logger.debug(chalk.blue(`[${driverName}] Found raw current thumbnail candidate: ${currentThumbnail}`));
    absolutePreviewUrl = makeAbsolute(currentThumbnail, baseUrl);
    if (absolutePreviewUrl && validatePreview(absolutePreviewUrl)) { // Use validatePreview for thumbnail too
      logger.debug(chalk.blue(`[${driverName}] Using thumbnail as preview fallback: ${absolutePreviewUrl}`));
      return absolutePreviewUrl;
    }
  }

  logger.warn(chalk.yellow(`[${driverName}] No valid preview video found after all attempts for item.`));
  return undefined;
}

/**
 * Sanitizes scraped text by removing extra whitespace and control characters.
 * @param {string|undefined} text - The text to sanitize.
 * @returns {string|undefined} Sanitized text or undefined.
 */
function sanitizeText(text) {
  if (typeof text !== 'string') return undefined; // Handle null/undefined/non-string inputs
  const sanitized = text.trim().replace(/\s+/g, ' ').replace(/[\n\r\t]/g, '');
  logger.debug(chalk.blue(`Sanitized text: "${text}" -> "${sanitized}"`));
  return sanitized.length > 0 ? sanitized : undefined;
}

/**
 * Centralized error handler for drivers.
 * @param {Error} error - The error object.
 * @param {string} driverName - The name of the driver where the error occurred.
 * @param {string} context - The context of the error (e.g., 'fetching', 'parsing').
 */
function handleError(error, driverName, context) {
    logger.error(`[${driverName}] Error during ${context}:`, error.message);
    if (error.response) {
        logger.error(`[${driverName}] Status: ${error.response.status}`);
    }
}

module.exports = {
  makeAbsolute,
  extractPreview,
  validatePreview,
  sanitizeText,
  logger,
  handleError,
  getRandomUserAgent,
  fetchWithRetry
};