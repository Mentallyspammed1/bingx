const AbstractModule = require('../core/AbstractModule.js');
const VideoMixin = require('../core/VideoMixin.js');
const { makeAbsolute, validatePreview, extractPreview } = require('./driver-utils');

const BaseRedtubeClass = AbstractModule.with(VideoMixin);

class RedtubeDriver extends BaseRedtubeClass {
  constructor() {
    super();
    this.logger = require('../core/log.js').child({ module: 'RedtubeDriver' });
  }

  get name() { return 'Redtube'; }
  get baseUrl() { return 'https://www.redtube.com'; }
  get supportsVideos() { return true; }
  get supportsGifs() { return false; }

  getVideoSearchUrl(query, page) {
    const pageNum = Math.max(1, page || 1);
    const searchQueryPath = encodeURIComponent(query.trim().replace(/\s+/g, '+'));
    const searchUrl = new URL(`/search?q=${searchQueryPath}`, this.baseUrl);
    searchUrl.searchParams.set('page', String(pageNum));
    this.logger.debug(`Forging search URL: ${searchUrl.href}`);
    return searchUrl.href;
  }

  parseResults($, htmlData, options) {
    const { isMock } = options;
    if (!$) {
      this.logger.warn(`Cheerio instance not provided for HTML parsing.`);
      return [];
    }

    if (!isMock) {
        // Check for common indicators of no results or a block page
        const noResultsText = $('div.no_results_message, p.no-results').text();
        if (noResultsText.length > 0) {
            this.logger.warn(`No results found or block page detected for query: "${options.query}". Message: ${noResultsText.trim().substring(0, 100)}`);
            return [];
        }

        // Check for Cloudflare or other common block page elements
        if ($('#age_disclaimer').length > 0 || $('body:contains("Page Not Found")').length > 0) {
            this.logger.error(`Redtube block page or age disclaimer detected for query: "${options.query}".`);
            return [];
        }
    }

    const results = [];
    // Selectors for Redtube's 2025 layout
    const videoItems = $('div.video_bloc, li.video_item, div.video-tile, div.videoBlock');
    this.logger.debug(`Discovered ${videoItems.length} video artifacts.`);

    videoItems.each((i, elem) => {
      this._parseSingleItem($, $(elem), results);
    });
    this.logger.info(`Conjured ${results.length} videos for query "${options.query}".`);
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
        this.logger.warn(`Invalid preview for ${title}: ${previewVideo}`);
      } else if (finalPreview) {
        this.logger.info(`Preview conjured for ${title}: ${finalPreview}`);
      } else {
        this.logger.warn(`No preview found for ${title}`);
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
      this.logger.warn(`Skipping item: missing URL or title.`);
    }
  }
}

module.exports = RedtubeDriver;