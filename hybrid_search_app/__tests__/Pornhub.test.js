const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');
const PornhubDriver = require('../modules/Pornhub.js');

describe('PornhubDriver', () => {
  let driver;
  let mockHtml;

  beforeAll(() => {
    driver = new PornhubDriver();
    const mockHtmlPath = path.join(__dirname, '..', 'modules', 'mock_html_data', 'pornhub_videos_page1.html');
    mockHtml = fs.readFileSync(mockHtmlPath, 'utf8');
  });

  it('should parse video results from mock HTML', () => {
    const $ = cheerio.load(mockHtml);
    const results = driver.parseResults($, null, { type: 'videos', sourceName: 'Pornhub' });

    expect(results).toBeInstanceOf(Array);
    expect(results.length).toBeGreaterThan(0);

    const firstResult = results[0];
    expect(firstResult).toHaveProperty('id');
    expect(firstResult).toHaveProperty('title');
    expect(firstResult).toHaveProperty('url');
    expect(firstResult).toHaveProperty('thumbnail');
    expect(firstResult).toHaveProperty('duration');
    expect(firstResult.source).toBe('Pornhub');
    expect(firstResult.type).toBe('videos');
  });
});
