const fs = require('fs');
const path = require('path');
const Eporner = require('../modules/Eporner'); // Adjust path as needed

describe('Eporner Driver', () => {
    let eporner;
    let mockHtml;

    beforeAll(() => {
        // Load the mock HTML content from a file
        const mockHtmlPath = path.join(__dirname, '../modules/mock_html_data/eporner_videos_page1.html');
        mockHtml = fs.readFileSync(mockHtmlPath, 'utf8');
    });

    beforeEach(() => {
        eporner = new Eporner();
    });

    test('should correctly parse video results from mock HTML', () => {
        const cheerio = require('cheerio');
        const $ = cheerio.load(mockHtml);

        const results = eporner.parseResults($, null, { type: 'videos', sourceName: 'Eporner' });

        expect(results).toBeInstanceOf(Array);
        expect(results.length).toBeGreaterThan(0);

        const firstResult = results[0];
        expect(firstResult).toHaveProperty('id');
        expect(firstResult).toHaveProperty('title');
        expect(firstResult).toHaveProperty('url');
        expect(firstResult).toHaveProperty('duration');
        expect(firstResult).toHaveProperty('thumbnail');
        expect(firstResult).toHaveProperty('preview_video');
        expect(firstResult.source).toBe('Eporner');
        expect(firstResult.type).toBe('videos');
    });

    test('should return an empty array if no items are found', () => {
        const cheerio = require('cheerio');
        const $ = cheerio.load('<div>No results here</div>');
        const results = eporner.parseResults($, null, { type: 'videos', sourceName: 'Eporner' });
        expect(results).toEqual([]);
    });

    test('should generate a valid video search URL', () => {
        const url = eporner.getVideoSearchUrl('test', 1);
        expect(url).toBe('https://www.eporner.com/search/test/');
    });

    test('should handle paged video search URL correctly', () => {
        const url = eporner.getVideoSearchUrl('test', 3);
        expect(url).toBe('https://www.eporner.com/search/test/3');
    });
});
