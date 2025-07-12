const fs = require('fs');
const path = require('path');
const Spankbang = require('../modules/Spankbang'); // Adjust path as needed

describe('Spankbang Driver', () => {
    let spankbang;
    let mockVideoHtml;
    let mockGifHtml;

    beforeAll(() => {
        const mockVideoPath = path.join(__dirname, '../modules/mock_html_data/spankbang_videos_page1.html');
        mockVideoHtml = fs.readFileSync(mockVideoPath, 'utf8');

        const mockGifPath = path.join(__dirname, '../modules/mock_html_data/spankbang_gifs_page1.html');
        mockGifHtml = fs.readFileSync(mockGifPath, 'utf8');
    });

    beforeEach(() => {
        spankbang = new Spankbang();
    });

    test('should correctly parse video results from mock HTML', () => {
        const cheerio = require('cheerio');
        const $ = cheerio.load(mockVideoHtml);
        const results = spankbang.parseResults($, null, { type: 'videos', sourceName: 'Spankbang' });

        expect(results).toBeInstanceOf(Array);
        expect(results.length).toBeGreaterThan(0);
        const firstResult = results[0];
        expect(firstResult).toHaveProperty('id');
        expect(firstResult).toHaveProperty('title');
        expect(firstResult).toHaveProperty('url');
        expect(firstResult).toHaveProperty('thumbnail');
        expect(firstResult.source).toBe('Spankbang');
        expect(firstResult.type).toBe('videos');
    });

    test('should correctly parse GIF results from mock HTML', () => {
        const cheerio = require('cheerio');
        const $ = cheerio.load(mockGifHtml);
        const results = spankbang.parseResults($, null, { type: 'gifs', sourceName: 'Spankbang' });

        expect(results).toBeInstanceOf(Array);
        expect(results.length).toBeGreaterThan(0);
        const firstResult = results[0];
        expect(firstResult).toHaveProperty('id');
        expect(firstResult).toHaveProperty('title');
        expect(firstResult).toHaveProperty('url');
        expect(firstResult).toHaveProperty('thumbnail');
        expect(firstResult).toHaveProperty('preview_video');
        expect(firstResult.source).toBe('Spankbang');
        expect(firstResult.type).toBe('gifs');
    });

    test('should generate a valid video search URL', () => {
        const url = spankbang.getVideoSearchUrl('test', 1);
        expect(url).toBe('https://www.spankbang.com/s/test/?o=new');
    });

    test('should generate a valid GIF search URL', () => {
        const url = spankbang.getGifSearchUrl('test', 1);
        expect(url).toBe('https://www.spankbang.com/gifs/search/test/');
    });
});
