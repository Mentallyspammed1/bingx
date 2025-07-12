const fs = require('fs');
const path = require('path');
const Youporn = require('../modules/Youporn'); // Adjust path as needed

describe('Youporn Driver', () => {
    let youporn;
    let mockVideoHtml;

    beforeAll(() => {
        const mockVideoPath = path.join(__dirname, '../modules/mock_html_data/youporn_videos_page1.html');
        mockVideoHtml = fs.readFileSync(mockVideoPath, 'utf8');
    });

    beforeEach(() => {
        youporn = new Youporn();
    });

    test('should correctly parse video results from mock HTML', () => {
        const cheerio = require('cheerio');
        const $ = cheerio.load(mockVideoHtml);
        const results = youporn.parseResults($, null, { type: 'videos', sourceName: 'Youporn' });

        expect(results).toBeInstanceOf(Array);
        expect(results.length).toBeGreaterThan(0);
        const firstResult = results[0];
        expect(firstResult).toHaveProperty('id');
        expect(firstResult).toHaveProperty('title');
        expect(firstResult).toHaveProperty('url');
        expect(firstResult).toHaveProperty('thumbnail');
        expect(firstResult.source).toBe('Youporn');
        expect(firstResult.type).toBe('videos');
    });

    test('should generate a valid video search URL', () => {
        const url = youporn.getVideoSearchUrl('test', 1);
        expect(url).toBe('https://www.youporn.com/search/?query=test&page=1');
    });
});
