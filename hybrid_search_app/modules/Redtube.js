'use strict';

const { makeAbsolute, logger, validatePreview } = require('./driver-utils');
const cheerio = require('cheerio');
const chalk = require('chalk');

/**
 * @typedef {import('../Pornsearch.js').MediaResult} MediaResult
 */
class RedtubeDriver {
  constructor() {
    this.name = 'Redtube';
    this.baseUrl = 'https://www.redtube.com';
    this.supportsVideos = true;
    this.supportsGifs = false;
  }

  getVideoSearchUrl(query, page) {
    const pageNum = Math.max(1, page || 1);
    const searchQueryPath = encodeURIComponent(query.trim().replace(/\s+/g, '+'));
    const searchUrl = new URL(`/search?q=${searchQueryPath}`, this.baseUrl);
    searchUrl.searchParams.set('page', String(pageNum));
    logger.debug(chalk.cyan(`// [${this.name}] Forging search URL: ${searchUrl.href}`));
    return searchUrl.href;
  }

  parseResults($, htmlData, options) {
    if (!$) {
      logger.warn(chalk.red(`// [${this.name}] Cheerio instance not provided for HTML parsing.`));
      return [];
    }
    const results = [];
    // Selectors for Redtube's 2025 layout
    const videoItems = $('div.video_bloc, li.video_item, div.video-tile, div.videoBlock');
    logger.debug(chalk.cyan(`// [${this.name}] Discovered ${videoItems.length} video artifacts.`));

    videoItems.each((i, elem) => {
      this._parseSingleItem($, $(elem), results);
    });
    logger.info(chalk.green(`// [${this.name}] Conjured ${results.length} videos for query "${options.query}".`));
    return results;
  }

  /** @private */
  _parseSingleItem($, $item, resultsArray) {
    // --- Link and Title ---
    let linkElement = $item.find('a[href*="/"][class*="title"], a[href*="/"][class*="thumb"], a[href*="/"]').first();
    let url = linkElement.attr('href');
    let title = linkElement.attr('title')?.trim() ||
                $item.find('[class*="title"], [class*="name"]').text()?.trim() ||
                $item.find('a[href*="/"]').text()?.trim();

    // --- Image and Thumbnail ---
    const imgElement = $item.find('img[class*="thumb"], img[class*="image"]').first();
    if (!title) title = imgElement.attr('alt')?.trim() || 'Untitled Video';

    let thumbnail = imgElement.attr('data-src') || imgElement.attr('src') || imgElement.attr('data-thumb') || imgElement.attr('data-poster');

    // --- Duration ---
    let duration = $item.find('[class*="duration"], .duration, time').first().text()?.trim();

    // --- Preview Video ---
    let previewVideo;
    logger.debug(chalk.cyan(`// [${this.name}] Seeking preview for item: ${title || 'unknown'}`));

    // 1. Check data attributes on image and container
    if (imgElement.length) {
      previewVideo = imgElement.attr('data-preview') ||
                     imgElement.attr('data-video-preview') ||
                     imgElement.attr('data-video-url') ||
                     imgElement.attr('data-media-url') ||
                     imgElement.attr('data-video');
      logger.debug(chalk.blue(`// [${this.name}] Image data attributes checked: ${previewVideo || 'none'}`));
    }

    if (!previewVideo) {
      previewVideo = $item.attr('data-preview') ||
                     $item.attr('data-video-preview') ||
                     $item.attr('data-video-url') ||
                     $item.attr('data-media-url') ||
                     $item.attr('data-video');
      logger.debug(chalk.blue(`// [${this.name}] Container data attributes checked: ${previewVideo || 'none'}`));
    }

    // 2. Check nested <video> tags
    if (!previewVideo) {
      const nestedVideoTag = $item.find('video[class*="preview"], video[loop], video').first();
      if (nestedVideoTag.length) {
        previewVideo = nestedVideoTag.attr('src') ||
                       nestedVideoTag.find('source').first().attr('src') ||
                       nestedVideoTag.attr('data-src');
        logger.debug(chalk.blue(`// [${this.name}] Video tag checked: ${previewVideo || 'none'}`));
      }
    }

    // 3. Parse data-previewhtml
    if (!previewVideo) {
      const previewHtmlAttr = $item.attr('data-previewhtml') || $item.attr('data-html');
      if (previewHtmlAttr) {
        try {
          const $previewHtml = cheerio.load(previewHtmlAttr);
          const videoInHtml = $previewHtml('video').first();
          if (videoInHtml.length) {
            previewVideo = videoInHtml.attr('src') || videoInHtml.find('source').first().attr('src') || videoInHtml.attr('data-src');
            logger.debug(chalk.blue(`// [${this.name}] data-previewhtml parsed: ${previewVideo || 'none'}`));
          }
        } catch (e) {
          logger.warn(chalk.yellow(`// [${this.name}] Failed to parse data-preview Gahtml: ${e.message}`));
        }
      }
    }

    // 4. Extract from JSON-LD or inline scripts
    if (!previewVideo) {
      const scripts = $item.find('script[type="application/ld+json"], script').toArray();
      for (const script of scripts) {
        const scriptData = $(script).html();
        if (scriptData) {
          try {
            // Try parsing as JSON
            let jsonData;
            try {
              jsonData = JSON.parse(scriptData);
              if (jsonData.contentUrl) {
                previewVideo = jsonData.contentUrl;
              } else if (jsonData.video) {
                previewVideo = jsonData.video.url || jsonData.video.contentUrl;
              } else if (jsonData.preview) {
                previewVideo = jsonData.preview;
              }
            } catch (e) {
              // Fallback to regex
              const jsonMatch = scriptData.match(/"(?:contentUrl|video|preview|videoUrl)":\s*"([^"]+\.(?:mp4|webm|m3u8))"/i);
              if (jsonMatch && jsonMatch[1]) {
                previewVideo = jsonMatch[1];
              }
            }
            if (previewVideo) {
              logger.debug(chalk.blue(`// [${this.name}] Script JSON parsed: ${previewVideo}`));
              break;
            }
          } catch (e) {
            logger.debug(chalk.yellow(`// [${this.name}] Script parsing error: ${e.message}`));
          }
        }
      }
    }

    // 5. Fallback to thumbnail if it’s a video
    if (!previewVideo && thumbnail && thumbnail.match(/\.(mp4|webm|m3u8)$/i)) {
      previewVideo = thumbnail;
      logger.debug(chalk.blue(`// [${this.name}] Using thumbnail as preview fallback: ${previewVideo}`));
    }

    // --- ID ---
    let idFromAttr = $item.attr('data-id') || $item.attr('id') || $item.attr('data-video-id') || $item.attr('data-video');
    let idFromUrl;
    if (url) {
      const match = url.match(/\/([0-9]+)$/);
      if (match) {
        idFromUrl = match[1];
      }
    }
    const id = idFromAttr || idFromUrl || `rt_${Date.now().toString(36)}${resultsArray.length}`;

    // --- Final Assembly ---
    if (url && title) {
      const finalPreview = validatePreview(previewVideo) ? makeAbsolute(previewVideo, this.baseUrl) : undefined;
      if (previewVideo && !finalPreview) {
        logger.warn(chalk.yellow(`// [${this.name}] Invalid preview for ${title}: ${previewVideo}`));
      } else if (finalPreview) {
        logger.info(chalk.green(`// [${this.name}] Preview conjured for ${title}: ${finalPreview}`));
      } else {
        logger.warn(chalk.yellow(`// [${this.name}] No preview found for ${title}`));
      }

      resultsArray.push({
        id: id,
        title: title,
        url: makeAbsolute(url, this.baseUrl),
        thumbnail: makeAbsolute(thumbnail, this.baseUrl) || '',
        duration: duration || undefined,
        preview_video: finalPreview,
        source: this.name,
        type: 'videos'
      });
    } else {
      logger.warn(chalk.red(`// [${this.name}] Skipping item: missing URL or title.`));
    }
  }
}

module.exports = RedtubeDriver;