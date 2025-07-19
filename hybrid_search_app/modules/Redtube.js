'use strict';

const { makeAbsolute, logger, validatePreview, extractPreview } = require('./driver-utils');
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
    const previewVideo = extractPreview($, $item, this.name, this.baseUrl);

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