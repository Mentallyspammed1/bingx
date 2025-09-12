const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');
const SpankbangDriver = require('../modules/Spankbang.js');

describe('Spankbang Driver', () => {
    let spankbang;
    let mockVideoHtml;

    beforeAll(() => {
        const mockVideoPath = path.join(__dirname, '../modules/mock_html_data/spankbang_videos_page1.html');
        if (fs.existsSync(mockVideoPath)) {
            mockVideoHtml = fs.readFileSync(mockVideoPath, 'utf8');
        }
    });

    beforeEach(() => {
        spankbang = new SpankbangDriver();
    });

    test('should correctly parse video results from mock HTML', () => {
        if (!mockVideoHtml) {
            console.warn('Skipping Spankbang parse test: mock HTML not found.');
            return;
        }
        if (mockVideoHtml.includes('Cloudflare')) {
            console.warn('Skipping Spankbang parse test: mock HTML contains Cloudflare block page.');
            return;
        }
        const $ = cheerio.load(mockVideoHtml);
        const results = spankbang.parseResults($, mockVideoHtml, { type: 'videos', sourceName: 'Spankbang' });

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

    test('should generate a valid video search URL', () => {
        const url = spankbang.getVideoSearchUrl('test', 1);
        expect(url).toBe('https://www.spankbang.com/s/test/?o=new');
    });
});