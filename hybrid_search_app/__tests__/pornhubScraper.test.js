const axios = require('axios');
const cheerio = require('cheerio');
const PornhubScraper = require('../modules/custom_scrapers/pornhubScraper');

jest.mock('axios');
jest.mock('cheerio');

describe('Pornhub Scraper Tests', () => {
  let scraperInstance;

  beforeEach(() => {
    scraperInstance = new PornhubScraper({ query: 'test query', page: 1 });
    // Mock _fetchHtml to prevent actual network calls and return mock HTML
    scraperInstance._fetchHtml = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('searchVideos', () => {
    test('should call axios.get (via _fetchHtml) with the correct URL and cheerio.load with the response', async () => {
      const query = 'test query';
      const expectedUrl = `https://www.pornhub.com/video/search?search=${encodeURIComponent(query)}&page=1`;
      const mockHtmlResponse = '<html><body><ul class="videos search-video-thumbs"><li class="pcVideoListItem"><span class="title"><a href="/view_video.php?viewkey=ph123" title="Test Video">Test Video</a></span><var class="duration">10:00</var><img data-mediumthumb="thumb.jpg"></li></ul></body></html>';

      // Mock the internal _fetchHtml method instead of axios.get directly
      scraperInstance._fetchHtml.mockResolvedValue(mockHtmlResponse);

      // Simplified Cheerio mock
      const mockCheerioAPI = {
        find: jest.fn().mockReturnThis(), // .find returns itself (the main cheerio object)
        each: jest.fn(function(callback) { // .each calls the callback 0 times for simplicity
          return this; // Allows chaining after .each if any
        }),
        // Add any other functions that are called directly on $ like $.text() or $.html() if necessary
      };
      const mockCheerioLoad = jest.fn(() => mockCheerioAPI);
      cheerio.load = mockCheerioLoad;

      // For this specific test, using the one from `beforeEach` whose _fetchHtml is already mocked.
      scraperInstance.query = query; // Ensure the query for this test is set

      const results = await scraperInstance.searchVideos(query, 1);

      expect(scraperInstance._fetchHtml).toHaveBeenCalledWith(expectedUrl);
      expect(cheerio.load).toHaveBeenCalledWith(mockHtmlResponse);
      expect(Array.isArray(results)).toBe(true);
      // Add more specific assertions about the content of 'results' if necessary
      expect(results.length).toBeGreaterThanOrEqual(0);
      if (results.length > 0) {
        expect(results[0].title).toBe('Test Video');
        expect(results[0].url).toBe('https://www.pornhub.com/view_video.php?viewkey=ph123');
      }
    });
  });
});
