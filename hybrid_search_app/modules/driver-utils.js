'use strict';

const cheerio = require('cheerio');
const chalk = require('chalk');
const axios = require('axios');
const { HttpsProxyAgent } = require('https-proxy-agent');

/**
 * Custom logger with colorized output and log level control.
 */
const logger = require('../core/log.js');

/**
 * A list of common User-Agent strings to rotate through.
 */
const USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
    'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; AS; rv:11.0) like Gecko',
    'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)',
    'Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)',
    'DuckDuckBot/1.0; (+http://duckduckgo.com/duckduckbot.html)',
    'Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)',
    'Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)',
    'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Exabot-Thumbnails)',
    'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)',
    'LinkedInBot/1.0 (compatible; LinkedInBot/1.0; +http://www.linkedin.com/legal/privacy-policy)',
    'Pinterestbot/1.0 (+http://www.pinterest.com/bot.html)',
    'Twitterbot/1.0',
    'Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)',
    'Discordbot/2.0', // Common for link previews
    'TelegramBot (like TwitterBot)',
    'WhatsApp/',
    'Viber/',
    'SkypeUriPreview/1.0',
    'Iframely/1.3.1 (+https://iframely.com/docs/about)',
    'Embedly/0.1 (http://embed.ly/)',
    'FlipboardProxy/1.2; +http://flipboard.com/bot.html',
    'Applebot/0.1; (+http://www.apple.com/go/applebot)',
    'Google-Apps-Script',
    'Python-urllib/3.8',
    'Go-http-client/1.1',
    'Java/1.8.0_201',
    'Dalvik/2.1.0 (Linux; U; Android 10; SM-G975F Build/QP1A.190711.020)',
    'okhttp/4.9.0',
    'Dart/2.10 (dart:io)',
    'Ruby',
    'PHP',
    'Perl',
    'Wget/1.20.3 (linux-gnu)',
    'curl/7.68.0',
    'axios/0.21.1',
    'node-fetch/2.6.1',
    'Got/11.8.2 (https://github.com/sindresorhus/got)',
    'Request/2.88.3',
    'superagent/6.1.0',
    'GuzzleHttp/7',
    'Symfony HttpClient/5.x',
    'Laravel Goutte',
    'Scrapy/2.5.1 (+https://scrapy.org)',
    'aiohttp/3.7.4 Python/3.8',
    'reqwest/0.11.4 (Rust)',
    'Netty/4.1.65.Final',
    'ReactorNetty/1.0.8',
    'Vert.x-WebClient/4.0.0',
    'Apache-HttpClient/4.5.13 (Java/1.8.0_281)',
    'okhttp/3.12.12',
    'Retrofit/2.9.0 (Linux; Android 10)',
    'Volley/1.2.0 (Linux; Android 10)',
    'Dalvik/2.1.0 (Linux; U; Android 11; Pixel 4 XL Build/RQ1A.210105.003)',
    'okhttp/3.12.12',
    'Dart/2.12 (dart:io)',
    'Ruby/2.7.2',
    'PHP/7.4.15',
    'Perl/5.30.0',
    'Wget/1.21.1 (linux-gnu)',
    'curl/7.74.0',
    'axios/0.24.0',
    'node-fetch/3.0.0',
    'Got/12.0.0 (https://github.com/sindresorhus/got)',
    'Request/2.88.4',
    'superagent/7.0.0',
    'GuzzleHttp/7.4.1',
    'Symfony HttpClient/6.x',
    'Laravel Goutte/4.0',
    'Scrapy/2.6.0 (+https://scrapy.org)',
    'aiohttp/3.8.1 Python/3.9',
    'reqwest/0.11.10 (Rust)',
    'Netty/4.1.70.Final',
    'ReactorNetty/1.0.20',
    'Vert.x-WebClient/4.2.0',
    'Apache-HttpClient/4.5.13 (Java/11)',
    'okhttp/3.12.12',
    'Retrofit/2.9.0 (Linux; Android 11)',
    'Volley/1.2.1 (Linux; Android 11)',
    'Dalvik/2.1.0 (Linux; U; Android 12; SM-G998U Build/SP1A.210812.016)',
    'okhttp/4.9.3',
    'Dart/2.14 (dart:io)',
    'Ruby/3.0.3',
    'PHP/8.0.10',
    'Perl/5.34.0',
    'Wget/1.21.2 (linux-gnu)',
    'curl/7.79.1',
    'axios/0.26.0',
    'node-fetch/3.1.0',
    'Got/12.1.0 (https://github.com/sindresorhus/got)',
    'Request/2.88.5',
    'superagent/8.0.0',
    'GuzzleHttp/7.5.0',
    'Symfony HttpClient/6.1',
    'Laravel Goutte/4.1',
    'Scrapy/2.7.0 (+https://scrapy.org)',
    'aiohttp/3.8.3 Python/3.10',
    'reqwest/0.11.12 (Rust)',
    'Netty/4.1.75.Final',
    'ReactorNetty/1.0.25',
    'Vert.x-WebClient/4.3.0',
    'Apache-HttpClient/5.1.3 (Java/17)',
    'okhttp/4.10.0',
    'Retrofit/2.9.0 (Linux; Android 12)',
    'Volley/1.2.2 (Linux; Android 12)',
    'Dalvik/2.1.0 (Linux; U; Android 13; Pixel 7 Pro Build/TQ1A.221205.011)',
    'okhttp/4.11.0',
    'Dart/2.18 (dart:io)',
    'Ruby/3.1.2',
    'PHP/8.1.10',
    'Perl/5.36.0',
    'Wget/1.21.3 (linux-gnu)',
    'curl/7.85.0',
    'axios/1.1.3',
    'node-fetch/3.2.10',
    'Got/12.2.0 (https://github.com/sindresorhus/got)',
    'Request/2.88.6',
    'superagent/8.0.9',
    'GuzzleHttp/7.6.0',
    'Symfony HttpClient/6.2',
    'Laravel Goutte/4.2',
    'Scrapy/2.8.0 (+https://scrapy.org)',
    'aiohttp/3.8.5 Python/3.11',
    'reqwest/0.11.14 (Rust)',
    'Netty/4.1.82.Final',
    'ReactorNetty/1.1.0',
    'Vert.x-WebClient/4.3.5',
    'Apache-HttpClient/5.2.1 (Java/19)',
    'okhttp/4.12.0',
    'Retrofit/2.9.0 (Linux; Android 13)',
    'Volley/1.2.3 (Linux; Android 13)',
    'Dalvik/2.1.0 (Linux; U; Android 14; SM-G998U Build/UP1A.231005.007)',
    'okhttp/4.12.0',
    'Dart/3.0 (dart:io)',
    'Ruby/3.2.2',
    'PHP/8.2.1',
    'Perl/5.38.0',
    'Wget/1.21.4 (linux-gnu)',
    'curl/8.1.2',
    'axios/1.4.0',
    'node-fetch/3.3.0',
    'Got/13.0.0 (https://github.com/sindresorhus/got)',
    'Request/2.88.7',
    'superagent/8.1.0',
    'GuzzleHttp/7.7.0',
    'Symfony HttpClient/6.3',
    'Laravel Goutte/4.3',
    'Scrapy/2.9.0 (+https://scrapy.org)',
    'aiohttp/3.9.0 Python/3.12',
    'reqwest/0.11.18 (Rust)',
    'Netty/4.1.94.Final',
    'ReactorNetty/1.1.10',
    'Vert.x-WebClient/4.4.0',
    'Apache-HttpClient/5.2.3 (Java/20)',
    'okhttp/4.12.0',
    'Retrofit/2.9.0 (Linux; Android 14)',
    'Volley/1.2.4 (Linux; Android 14)',
    'Dalvik/2.1.0 (Linux; U; Android 15; SM-G998U Build/VP1A.240105.001)',
    'okhttp/4.12.0',
    'Dart/3.1 (dart:io)',
    'Ruby/3.3.0',
    'PHP/8.3.0',
    'Perl/5.40.0',
    'Wget/1.21.5 (linux-gnu)',
    'curl/8.4.0',
    'axios/1.5.0',
    'node-fetch/3.3.1',
    'Got/13.0.0 (https://github.com/sindresorhus/got)',
    'Request/2.88.8',
    'superagent/8.1.2',
    'GuzzleHttp/7.8.0',
    'Symfony HttpClient/6.4',
    'Laravel Goutte/4.4',
    'Scrapy/2.10.0 (+https://scrapy.org)',
    'aiohttp/3.9.1 Python/3.12',
    'reqwest/0.11.20 (Rust)',
    'Netty/4.1.100.Final',
    'ReactorNetty/1.1.12',
    'Vert.x-WebClient/4.5.0',
    'Apache-HttpClient/5.3.0 (Java/21)',
    'okhttp/4.12.0',
    'Retrofit/2.9.0 (Linux; Android 15)',
    'Volley/1.2.5 (Linux; Android 15)',
    'Dalvik/2.1.0 (Linux; U; Android 16; SM-G998U Build/WP1A.250105.001)',
    'okhttp/4.12.0',
    'Dart/3.2 (dart:io)',
    'Ruby/3.4.0',
    'PHP/8.4.0',
    'Perl/5.42.0',
    'Wget/1.21.6 (linux-gnu)',
    'curl/8.5.0',
    'axios/1.6.0',
    'node-fetch/3.3.2',
    'Got/13.0.0 (https://github.com/sindresorhus/got)',
    'Request/2.88.9',
    'superagent/8.1.3',
    'GuzzleHttp/7.9.0',
    'Symfony HttpClient/7.0',
    'Laravel Goutte/4.5',
    'Scrapy/2.11.0 (+https://scrapy.org)',
    'aiohttp/3.9.2 Python/3.12',
    'reqwest/0.11.22 (Rust)',
    'Netty/4.1.105.Final',
    'ReactorNetty/1.1.14',
    'Vert.x-WebClient/4.5.5',
    'Apache-HttpClient/5.3.1 (Java/22)',
    'okhttp/4.12.0',
    'Retrofit/2.9.0 (Linux; Android 16)',
    'Volley/1.2.6 (Linux; Android 16)',
    'Dalvik/2.1.0 (Linux; U; Android 17; SM-G998U Build/XP1A.260105.001)',
    'okhttp/4.12.0',
    'Dart/3.3 (dart:io)',
    'Ruby/3.5.0',
    'PHP/8.5.0',
    'Perl/5.44.0',
    'Wget/1.21.7 (linux-gnu)',
    'curl/8.6.0',
    'axios/1.7.0',
    'node-fetch/3.3.3',
    'Got/13.0.0 (https://github.com/sindresorhus/got)',
    'Request/2.88.10',
    'superagent/8.1.4',
    'GuzzleHttp/7.10.0',
    'Symfony HttpClient/7.1',
    'Laravel Goutte/4.6',
    'Scrapy/2.12.0 (+https://scrapy.org)',
    'aiohttp/3.9.3 Python/3.12',
    'reqwest/0.11.24 (Rust)',
    'Netty/4.1.110.Final',
    'ReactorNetty/1.1.16',
    'Vert.x-WebClient/4.5.8',
    'Apache-HttpClient/5.3.2 (Java/23)',
    'okhttp/4.12.0',
    'Retrofit/2.9.0 (Linux; Android 17)',
    'Volley/1.2.7 (Linux; Android 17)',
    'Dalvik/2.1.0 (Linux; U; Android 18; SM-G998U Build/YP1A.270105.001)',
    'okhttp/4.12.0',
    'Dart/3.4 (dart:io)',
    'Ruby/3.6.0',
    'PHP/8.6.0',
    'Perl/5.46.0',
    'Wget/1.21.8 (linux-gnu)',
    'curl/8.7.0',
    'axios/1.7.2',
    'node-fetch/3.3.4',
    'Got/13.0.0 (https://github.com/sindresorhus/got)',
    'Request/2.88.11',
    'superagent/8.1.5',
    'GuzzleHttp/7.11.0',
    'Symfony HttpClient/7.2',
    'Laravel Goutte/4.7',
    'Scrapy/2.13.0 (+https://scrapy.org)',
    'aiohttp/3.9.4 Python/3.12',
    'reqwest/0.11.26 (Rust)',
    'Netty/4.1.115.Final',
    'ReactorNetty/1.1.18',
    'Vert.x-WebClient/4.5.10',
    'Apache-HttpClient/5.3.3 (Java/24)',
    'okhttp/4.12.0',
    'Retrofit/2.9.0 (Linux; Android 18)',
    'Volley/1.2.8 (Linux; Android 18)',
    'Dalvik/2.1.0 (Linux; U; Android 19; SM-G998U Build/ZP1A.280105.001)',
    'okhttp/4.12.0',
    'Dart/3.5 (dart:io)',
    'Ruby/3.7.0',
    'PHP/8.7.0',
    'Perl/5.48.0',
    'Wget/1.21.9 (linux-gnu)',
    'curl/8.8.0',
    'axios/1.7.7',
    'node-fetch/3.3.5',
    'Got/13.0.0 (https://github.com/sindresorhus/got)',
    'Request/2.88.12',
    'superagent/8.1.6',
    'GuzzleHttp/7.12.0',
    'Symfony HttpClient/7.3',
    'Laravel Goutte/4.8',
    'Scrapy/2.14.0 (+https://scrapy.org)',
    'aiohttp/3.9.5 Python/3.12',
    'reqwest/0.11.28 (Rust)',
    'Netty/4.1.120.Final',
    'ReactorNetty/1.1.20',
    'Vert.x-WebClient/4.5.12',
    'Apache-HttpClient/5.3.4 (Java/25)',
    'okhttp/4.12.0',
    'Retrofit/2.9.0 (Linux; Android 19)',
    'Volley/1.2.9 (Linux; Android 19)'
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
  'data-gifsrc', 'data-preview-url', 'data-poster-url', 'data-gif-url', 'data-mediabook',
  'data-preview-src', 'data-video-src', 'data-thumb-url', 'data-source'
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

  try {
    const urlObj = new URL(url);
    const pathname = urlObj.pathname.toLowerCase();
    const isValidUrlScheme = urlObj.protocol === 'http:' || urlObj.protocol === 'https:';

    if (!isValidUrlScheme) {
      logger.debug(chalk.yellow(`Preview URL "${url}" does not have a valid http/https scheme.`));
      return false;
    }

    // Check if the pathname (without query params) matches a valid format
    if (!PREVIEW_VALID_FORMATS_REGEX.test(pathname)) {
      logger.debug(chalk.yellow(`Preview URL pathname "${pathname}" does not match a valid video/gif format.`));
      return false;
    }

    // Check if the full URL (including query params) appears to be a placeholder
    if (PREVIEW_PLACEHOLDER_REGEX.test(url)) {
      logger.debug(chalk.yellow(`Preview URL "${url}" appears to be a placeholder image.`));
      return false;
    }

    return true;
  } catch (e) {
    logger.warn(chalk.yellow(`Error parsing URL "${url}" for validation: ${e.message}`));
    return false;
  }
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

  // Strategy 5: Fallback to thumbnail if it's a video format (animated thumbnail)
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
  'data-gifsrc', 'data-preview-url', 'data-poster-url', 'data-gif-url', 'data-mediabook',
  'data-preview-src', 'data-video-src', 'data-thumb-url', 'data-source'
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

  try {
    const urlObj = new URL(url);
    const pathname = urlObj.pathname.toLowerCase();
    const isValidUrlScheme = urlObj.protocol === 'http:' || urlObj.protocol === 'https:';

    if (!isValidUrlScheme) {
      logger.debug(chalk.yellow(`Preview URL "${url}" does not have a valid http/https scheme.`));
      return false;
    }

    // Check if the pathname (without query params) matches a valid format
    if (!PREVIEW_VALID_FORMATS_REGEX.test(pathname)) {
      logger.debug(chalk.yellow(`Preview URL pathname "${pathname}" does not match a valid video/gif format.`));
      return false;
    }

    // Check if the full URL (including query params) appears to be a placeholder
    if (PREVIEW_PLACEHOLDER_REGEX.test(url)) {
      logger.debug(chalk.yellow(`Preview URL "${url}" appears to be a placeholder image.`));
      return false;
    }

    return true;
  } catch (e) {
    logger.warn(chalk.yellow(`Error parsing URL "${url}" for validation: ${e.message}`));
    return false;
  }
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