const fs = require('fs');
const path = require('path');
const RedtubeDriver = require('../modules/Redtube.js');

describe('Redtube Driver', () => {
    let redtube;
    let mockVideoJson;

    beforeAll(() => {
        const mockVideoPath = path.join(__dirname, '../modules/mock_html_data/redtube_videos_page1.json');
        // To be created
        if (fs.existsSync(mockVideoPath)) {
            mockVideoJson = JSON.parse(fs.readFileSync(mockVideoPath, 'utf8'));
        }
    });

    beforeEach(() => {
        redtube = new RedtubeDriver();
    });

    test('should correctly parse video results from mock JSON', () => {
        if (!mockVideoJson) {
            console.warn('Skipping Redtube parse test: mock JSON not found.');
            return;
        }
        const results = redtube.parseResults(null, mockVideoJson, { type: 'videos', sourceName: 'Redtube' });

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
        const url = redtube.getVideoSearchUrl('test', 1);
        expect(url).toBe('https://www.redtube.com/redtube/search/videos?search=test&page=1');
    });
});
