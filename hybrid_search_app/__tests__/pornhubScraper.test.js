const PornhubScraper = require('../modules/custom_scrapers/pornhubScraper');
const cheerio = require('cheerio'); // We'll use the real cheerio for parser tests

// Mock _fetchHtml for the scraper instance to avoid network calls
// This will be done in beforeEach or per test suite
jest.mock('../modules/custom_scrapers/pornhubScraper', () => {
  const OriginalPornhubScraper = jest.requireActual('../modules/custom_scrapers/pornhubScraper');
  OriginalPornhubScraper.prototype._fetchHtml = jest.fn();
  return OriginalPornhubScraper;
});


describe('PornhubScraper', () => {
  let scraper;

  beforeEach(() => {
    scraper = new PornhubScraper({ query: 'test', page: 1 });
    // Reset the mock for each test
    scraper._fetchHtml.mockReset();
  });

  describe('videoParser', () => {
    test('should correctly parse video items including preview_video from data-mediabook', () => {
      const mockVideoHtml = `
        <ul class="videos search-video-thumbs">
          <li class="pcVideoListItem">
            <div class="wrap">
              <div class="phimage">
                <a href="/view_video.php?viewkey=ph123" class="linkVideoThumb">
                  <img data-mediumthumb="https://example.com/thumb.jpg"
                         src="https://example.com/thumb_src.jpg"
                         data-mediabook="https://example.com/preview.webm"
                         alt="Test Video 1" />
                </a>
              </div>
              <span class="title"><a href="/view_video.php?viewkey=ph123" title="Test Video 1">Test Video 1</a></span>
              <var class="duration">10:00</var>
            </div>
          </li>
          <li class="pcVideoListItem">
            <div class="wrap">
              <div class="phimage">
                <a href="/view_video.php?viewkey=ph456" class="linkVideoThumb">
                  <img data-src="https://example.com/thumb2.jpg"
                         data-mediabook="https://example.com/preview2.webm"
                         alt="Test Video 2" />
                </a>
              </div>
              <span class="title"><a href="/view_video.php?viewkey=ph456" title="Test Video 2">Test Video 2</a></span>
              <var class="duration">05:30</var>
            </div>
          </li>
        </ul>
      `;
      const $ = cheerio.load(mockVideoHtml);
      const results = scraper.videoParser($, mockVideoHtml);

      expect(results).toHaveLength(2);

      expect(results[0].title).toBe('Test Video 1');
      expect(results[0].url).toBe('https://www.pornhub.com/view_video.php?viewkey=ph123');
      expect(results[0].thumbnail).toBe('https://example.com/thumb.jpg');
      expect(results[0].preview_video).toBe('https://example.com/preview.webm');
      expect(results[0].duration).toBe('10:00');
      expect(results[0].source).toBe('Pornhub');

      expect(results[1].title).toBe('Test Video 2');
      expect(results[1].url).toBe('https://www.pornhub.com/view_video.php?viewkey=ph456');
      expect(results[1].thumbnail).toBe('https://example.com/thumb2.jpg'); // from data-src
      expect(results[1].preview_video).toBe('https://example.com/preview2.webm');
      expect(results[1].duration).toBe('05:30');
    });

    test('should handle items with missing preview_video gracefully', () => {
      const mockVideoHtmlMissingPreview = `
        <ul class="videos search-video-thumbs">
          <li class="pcVideoListItem">
            <div class="wrap">
              <div class="phimage">
                <a href="/view_video.php?viewkey=ph789" class="linkVideoThumb">
                  <img data-mediumthumb="https://example.com/thumb3.jpg" alt="Test Video 3" />
                </a>
              </div>
              <span class="title"><a href="/view_video.php?viewkey=ph789" title="Test Video 3">Test Video 3</a></span>
              <var class="duration">02:00</var>
            </div>
          </li>
        </ul>
      `;
      const $ = cheerio.load(mockVideoHtmlMissingPreview);
      const results = scraper.videoParser($, mockVideoHtmlMissingPreview);
      expect(results).toHaveLength(1);
      expect(results[0].preview_video).toBeUndefined();
    });
  });

  describe('gifParser', () => {
    test('should correctly parse GIF items including thumbnail from data-poster and preview_video from data-webm', () => {
      const mockGifHtml = `
        <ul class="gifs gifLink">
          <li class="gifVideoBlock">
            <a href="/gif/g123" title="Test GIF 1">
              <video class="gifVideo js-gifVideo"
                     data-poster="https://example.com/gif_thumb1.jpg"
                     data-webm="https://example.com/gif_preview1.webm"
                     data-mp4="https://example.com/gif_preview1.mp4">
              </video>
              <span class="title">Test GIF 1</span>
            </a>
          </li>
          <li class="gifVideoBlock">
            <a href="/gif/g456" title="Test GIF 2">
              <video class="gifVideo js-gifVideo"
                     data-poster="https://example.com/gif_thumb2.jpg"
                     data-webm="https://example.com/gif_preview2.webm">
                     <source type="video/webm" src="https://example.com/gif_preview2_source.webm" />
              </video>
              <span class="title">Test GIF 2 (title in span)</span>
            </a>
          </li>
        </ul>
      `;
      const $ = cheerio.load(mockGifHtml);
      const results = scraper.gifParser($, mockGifHtml);

      expect(results).toHaveLength(2);

      expect(results[0].title).toBe('Test GIF 1');
      expect(results[0].url).toBe('https://www.pornhub.com/gif/g123');
      expect(results[0].thumbnail).toBe('https://example.com/gif_thumb1.jpg');
      expect(results[0].preview_video).toBe('https://example.com/gif_preview1.webm');
      expect(results[0].source).toBe('Pornhub');

      // Test fallback to source src if data-webm is missing (though current logic prefers data-webm)
      // The title should come from the <a> tag's title attribute first
      expect(results[1].title).toBe('Test GIF 2');
      expect(results[1].url).toBe('https://www.pornhub.com/gif/g456');
      expect(results[1].thumbnail).toBe('https://example.com/gif_thumb2.jpg');
      expect(results[1].preview_video).toBe('https://example.com/gif_preview2.webm'); // data-webm takes precedence
    });
  });

  describe('searchVideos (integration with parser)', () => {
    test('should return parsed video objects', async () => {
      const query = 'integration test';
      const page = 1;
      const mockHtmlResponse = `
        <ul class="videos search-video-thumbs">
          <li class="pcVideoListItem">
            <div class="wrap">
              <div class="phimage">
                <a href="/view_video.php?viewkey=ph_int123" class="linkVideoThumb">
                  <img data-mediumthumb="https://example.com/int_thumb.jpg"
                         data-mediabook="https://example.com/int_preview.webm"
                         alt="Integration Test Video" />
                </a>
              </div>
              <span class="title"><a href="/view_video.php?viewkey=ph_int123" title="Integration Test Video">Integration Test Video</a></span>
              <var class="duration">12:34</var>
            </div>
          </li>
        </ul>`;
      scraper._fetchHtml.mockResolvedValue(mockHtmlResponse);

      const results = await scraper.searchVideos(query, page);

      expect(scraper._fetchHtml).toHaveBeenCalledWith(`https://www.pornhub.com/video/search?search=${encodeURIComponent(query)}&page=${page}`);
      expect(results).toHaveLength(1);
      expect(results[0].title).toBe('Integration Test Video');
      expect(results[0].thumbnail).toBe('https://example.com/int_thumb.jpg');
      expect(results[0].preview_video).toBe('https://example.com/int_preview.webm');
    });
  });

  describe('searchGifs (integration with parser)', () => {
    test('should return parsed GIF objects', async () => {
      const query = 'gif integration';
      const page = 1;
      const mockHtmlResponse = `
        <ul class="gifs gifLink">
          <li class="gifVideoBlock">
            <a href="/gif/g_int123" title="Integration Test GIF">
              <video class="gifVideo js-gifVideo"
                     data-poster="https://example.com/gif_int_thumb.jpg"
                     data-webm="https://example.com/gif_int_preview.webm">
              </video>
              <span class="title">Integration Test GIF</span>
            </a>
          </li>
        </ul>`;
      scraper._fetchHtml.mockResolvedValue(mockHtmlResponse);

      const results = await scraper.searchGifs(query, page);

      expect(scraper._fetchHtml).toHaveBeenCalledWith(`https://www.pornhub.com/gifs/search?search=${encodeURIComponent(query)}&page=${page}`);
      expect(results).toHaveLength(1);
      expect(results[0].title).toBe('Integration Test GIF');
      expect(results[0].thumbnail).toBe('https://example.com/gif_int_thumb.jpg');
      expect(results[0].preview_video).toBe('https://example.com/gif_int_preview.webm');
    });
  });

});
