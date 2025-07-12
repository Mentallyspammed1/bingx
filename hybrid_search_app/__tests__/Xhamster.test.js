const fs = require('fs');
const path = require('path');
const Xhamster = require('../modules/Xhamster'); // Adjust path as needed

describe('Xhamster Driver', () => {
    let xhamster;
    let mockVideoHtml;
    let mockGifHtml;

    beforeAll(() => {
        const mockVideoPath = path.join(__dirname, '../modules/mock_html_data/xhamster_videos_page1.html');
        mockVideoHtml = fs.readFileSync(mockVideoPath, 'utf8');

        const mockGifPath = path.join(__dirname, '../modules/mock_html_data/xhamster_gifs_page1.html');
        mockGifHtml = fs.readFileSync(mockGifPath, 'utf8');
    });

    beforeEach(() => {
        xhamster = new Xhamster();
    });

    test('should correctly parse video results from mock HTML', () => {
        const cheerio = require('cheerio');
        const $ = cheerio.load(mockVideoHtml);
        const results = xhamster.parseResults($, null, { type: 'videos', sourceName: 'Xhamster' });

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

    test('should correctly parse GIF results from mock HTML', () => {
        const cheerio = require('cheerio');
        const $ = cheerio.load(mockGifHtml);
        const results = xhamster.parseResults($, null, { type: 'gifs', sourceName: 'Xhamster' });

        expect(results).toBeInstanceOf(Array);
        expect(results.length).toBeGreaterThan(0);
        const firstResult = results[0];
        expect(firstResult).toHaveProperty('id');
        expect(firstResult).toHaveProperty('title');
        expect(firstResult).toHaveProperty('url');
        expect(firstResult).toHaveProperty('thumbnail');
        expect(firstResult).toHaveProperty('preview_video');
        expect(firstResult.source).toBe('Xhamster');
        expect(firstResult.type).toBe('gifs');
    });

    test('should generate a valid video search URL', () => {
        const url = xhamster.getVideoSearchUrl('test', 1);
        expect(url).toBe('https://www.xhamster.com/videos/search/test/0/');
    });

    test('should generate a valid GIF search URL', () => {
        const url = xhamster.getGifSearchUrl('test', 1);
        expect(url).toBe('https://www.xhamster.com/gifs/search/test/0/');
    });
});
