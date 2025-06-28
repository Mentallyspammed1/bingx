// modules/custom_scrapers/mockScraper.cjs
// Basic mock scraper for testing purposes

class MockScraper {
    constructor(options) {
        this.options = options || {};
        this.query = this.options.query;
        this.page = this.options.page || 1;
    }

    get name() { return 'Mock'; } // Used as key in loadedCustomScrapers
    get sourceName() { return 'MockSource'; } // Used in item.source

    async searchGifs(query, page) {
        // console.log(`[MockScraper] searchGifs called with query: ${query}, page: ${page}`);
        return [
            { title: 'Mock GIF 1 from Scraper', url: `https://mock.com/gif/1?q=${query}&p=${page}`, thumbnail: 'https://via.placeholder.com/150/0000FF/808080?Text=MockThumb1.jpg', preview_video: 'https://example.com/mock_preview1.gif', source: this.sourceName, query: query, type: 'gifs' },
            { title: 'Mock GIF 2 from Scraper', url: `https://mock.com/gif/2?q=${query}&p=${page}`, thumbnail: 'https://via.placeholder.com/150/FF0000/FFFFFF?Text=MockThumb2.jpg', preview_video: 'https://example.com/mock_preview2.gif', source: this.sourceName, query: query, type: 'gifs' },
        ];
    }

    async searchVideos(query, page) {
        // console.log(`[MockScraper] searchVideos called with query: ${query}, page: ${page}`);
        return [
            { title: 'Mock Video 1 from Scraper', url: `https://mock.com/video/1?q=${query}&p=${page}`, thumbnail: 'https://via.placeholder.com/150/00FF00/000000?Text=MockVidThumb1.jpg', preview_video: 'https://example.com/mock_vid_preview1.mp4', duration: '01:23', source: this.sourceName, query: query, type: 'videos' },
        ];
    }
}

module.exports = MockScraper;
