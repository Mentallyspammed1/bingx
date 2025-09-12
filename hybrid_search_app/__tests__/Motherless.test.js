const fs = require('fs');
const path = require('path');
const Motherless = require('../modules/Motherless'); // Adjust path as needed

describe('Motherless Driver', () => {
    let motherless;
    let mockVideoHtml;
    let mockGifHtml;

    beforeAll(() => {
        const mockVideoPath = path.join(__dirname, '../modules/mock_html_data/motherless_videos_page1.html');
        mockVideoHtml = fs.readFileSync(mockVideoPath, 'utf8');

        const mockGifPath = path.join(__dirname, '../modules/mock_html_data/motherless_gifs_page1.html');
        mockGifHtml = fs.readFileSync(mockGifPath, 'utf8');
    });

    beforeEach(() => {
        motherless = new Motherless();
    });

    test('should correctly parse video results from mock HTML', () => {
        if (mockVideoHtml.includes('Cloudflare')) {
            console.warn('Skipping Motherless video parse test: mock HTML contains Cloudflare block page.');
            return;
        }
        const cheerio = require('cheerio');
        const $ = cheerio.load(mockVideoHtml);
        const results = motherless.parseResults($, null, { type: 'videos', sourceName: 'Motherless' });

        expect(results).toBeInstanceOf(Array);
        expect(results.length).toBeGreaterThan(0);
        const firstResult = results[0];
        expect(firstResult).toHaveProperty('id');
        expect(firstResult).toHaveProperty('title');
        expect(firstResult).toHaveProperty('url');
        expect(firstResult).toHaveProperty('thumbnail');
        expect(firstResult.source).toBe('Motherless');
        expect(firstResult.type).toBe('videos');
    });

    test('should correctly parse GIF results from mock HTML', () => {
        if (mockGifHtml.includes('Cloudflare')) {
            console.warn('Skipping Motherless GIF parse test: mock HTML contains Cloudflare block page.');
            return;
        }
        const cheerio = require('cheerio');
        const $ = cheerio.load(mockGifHtml);
        const results = motherless.parseResults($, null, { type: 'gifs', sourceName: 'Motherless' });

        expect(results).toBeInstanceOf(Array);
        expect(results.length).toBeGreaterThan(0);
        const firstResult = results[0];
        expect(firstResult).toHaveProperty('id');
        expect(firstResult).toHaveProperty('title');
        expect(firstResult).toHaveProperty('url');
        expect(firstResult).toHaveProperty('thumbnail');
        expect(firstResult).toHaveProperty('preview_video');
        expect(firstResult.source).toBe('Motherless');
        expect(firstResult.type).toBe('gifs');
    });

    test('should generate a valid video search URL', () => {
        const url = motherless.getVideoSearchUrl('test', 1);
        expect(url).toBe('https://motherless.com/term/videos/test?page=1');
    });

    test('should generate a valid GIF search URL', () => {
        const url = motherless.getGifSearchUrl('test', 1);
        expect(url).toBe('https://motherless.com/term/images/test?page=1');
    });
});
