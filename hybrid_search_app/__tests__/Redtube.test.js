const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');
const RedtubeDriver = require('../modules/Redtube.js');

describe('Redtube Driver', () => {
    let driver;
    let mockHtml;

    beforeAll(() => {
        driver = new RedtubeDriver();
        const mockHtmlPath = path.join(__dirname, '..', 'modules', 'mock_html_data', 'redtube_videos_page1.html');
        if (fs.existsSync(mockHtmlPath)) {
            mockHtml = fs.readFileSync(mockHtmlPath, 'utf8');
        }
    });

    test('should correctly parse video results from mock HTML', () => {
        if (!mockHtml) {
            console.warn('Skipping Redtube parse test: mock HTML not found.');
            return;
        }
        const $ = cheerio.load(mockHtml);
        const results = driver.parseResults($, mockHtml, { type: 'videos', sourceName: 'Redtube', query: 'test' });

        expect(results).toBeInstanceOf(Array);
        expect(results.length).toBeGreaterThan(0);
        const firstResult = results[0];
        expect(firstResult).toHaveProperty('id');
        expect(firstResult).toHaveProperty('title');
        expect(firstResult).toHaveProperty('url');
        expect(firstResult).toHaveProperty('thumbnail');
        expect(firstResult.source).toBe('Redtube');
        expect(firstResult.type).toBe('videos');
    });

    test('should generate a valid video search URL', () => {
        const url = driver.getVideoSearchUrl('test', 1);
        expect(url).toBe('https://www.redtube.com/search?q=test&page=1');
    });
});
