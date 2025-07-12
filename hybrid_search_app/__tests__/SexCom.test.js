const fs = require('fs');
const path = require('path');
const SexCom = require('../modules/SexCom'); // Adjust path as needed

describe('Sex.com Driver', () => {
    let sexCom;
    let mockVideoHtml;
    let mockGifHtml;

    beforeAll(() => {
        const mockVideoPath = path.join(__dirname, '../modules/mock_html_data/sexcom_videos_page1.html');
        mockVideoHtml = fs.readFileSync(mockVideoPath, 'utf8');

        const mockGifPath = path.join(__dirname, '../modules/mock_html_data/sexcom_gifs_page1.html');
        mockGifHtml = fs.readFileSync(mockGifPath, 'utf8');
    });

    beforeEach(() => {
        sexCom = new SexCom();
    });

    test('should correctly parse video results from mock HTML', () => {
        const cheerio = require('cheerio');
        const $ = cheerio.load(mockVideoHtml);
        const results = sexCom.parseResults($, null, { type: 'videos', sourceName: 'Sex.com' });

        expect(results).toBeInstanceOf(Array);
        expect(results.length).toBeGreaterThan(0);
        const firstResult = results[0];
        expect(firstResult).toHaveProperty('id');
        expect(firstResult).toHaveProperty('title');
        expect(firstResult).toHaveProperty('url');
        expect(firstResult).toHaveProperty('thumbnail');
        expect(firstResult.source).toBe('Sex.com');
        expect(firstResult.type).toBe('videos');
    });

    test('should correctly parse GIF results from mock HTML', () => {
        const cheerio = require('cheerio');
        const $ = cheerio.load(mockGifHtml);
        const results = sexCom.parseResults($, null, { type: 'gifs', sourceName: 'Sex.com' });

        expect(results).toBeInstanceOf(Array);
        expect(results.length).toBeGreaterThan(0);
        const firstResult = results[0];
        expect(firstResult).toHaveProperty('id');
        expect(firstResult).toHaveProperty('title');
        expect(firstResult).toHaveProperty('url');
        expect(firstResult).toHaveProperty('thumbnail');
        expect(firstResult).toHaveProperty('preview_video');
        expect(firstResult.source).toBe('Sex.com');
        expect(firstResult.type).toBe('gifs');
    });

    test('should generate a valid video search URL', () => {
        const url = sexCom.getVideoSearchUrl('test', 1);
        expect(url).toBe('https://www.sex.com/search/videos?query=test&page=1');
    });

    test('should generate a valid GIF search URL', () => {
        const url = sexCom.getGifSearchUrl('test', 1);
        expect(url).toBe('https://www.sex.com/search/gifs?query=test&page=1');
    });
});