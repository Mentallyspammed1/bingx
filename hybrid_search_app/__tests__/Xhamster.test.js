const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');
const XhamsterDriver = require('../modules/Xhamster.js');

describe('Xhamster Driver', () => {
    let xhamster;
    let mockVideoHtml;

    beforeAll(() => {
        const mockVideoPath = path.join(__dirname, '../modules/mock_html_data/xhamster_videos_page1.html');
        if (fs.existsSync(mockVideoPath)) {
            mockVideoHtml = fs.readFileSync(mockVideoPath, 'utf8');
        }
    });

    beforeEach(() => {
        xhamster = new XhamsterDriver();
    });

    test('should correctly parse video results from mock HTML', () => {
        if (!mockVideoHtml) {
            console.warn('Skipping Xhamster parse test: mock HTML not found.');
            return;
        }
        const $ = cheerio.load(mockVideoHtml);
        const results = xhamster.parseResults($, mockVideoHtml, { type: 'videos', sourceName: 'Xhamster' });

        expect(results).toBeInstanceOf(Array);
        expect(results.length).toBeGreaterThan(0);
        const firstResult = results[0];
        expect(firstResult).toHaveProperty('id');
        expect(firstResult).toHaveProperty('title');
        expect(firstResult).toHaveProperty('url');
        expect(firstResult).toHaveProperty('thumbnail');
        expect(firstResult.source).toBe('Xhamster');
        expect(firstResult.type).toBe('videos');
    });

    test('should generate a valid video search URL', () => {
        const url = xhamster.getVideoSearchUrl('test', 1);
        expect(url).toBe('https://www.xhamster.com/videos/search/test/1/');
    });
});