const fs = require('fs')
const path = require('path')
const Xvideos = require('../modules/Xvideos') // Adjust path as needed

describe('Xvideos Driver', () => {
    let xvideos
    let mockVideoHtml
    let mockGifHtml

    beforeAll(() => {
        const mockVideoPath = path.join(__dirname, '../modules/mock_html_data/xvideos_videos_page1.html')
        mockVideoHtml = fs.readFileSync(mockVideoPath, 'utf8')

        const mockGifPath = path.join(__dirname, '../modules/mock_html_data/xvideos_gifs_page1.html')
        mockGifHtml = fs.readFileSync(mockGifPath, 'utf8')
    })

    beforeEach(() => {
        xvideos = new Xvideos()
    })

    test('should correctly parse video results from mock HTML', () => {
        const cheerio = require('cheerio')
        const $ = cheerio.load(mockVideoHtml)
        const results = xvideos.parseResults($, null, { type: 'videos', sourceName: 'Xvideos' })

        expect(results).toBeInstanceOf(Array)
        expect(results.length).toBeGreaterThan(0)
        const firstResult = results[0]
        expect(firstResult).toHaveProperty('id')
        expect(firstResult).toHaveProperty('title')
        expect(firstResult).toHaveProperty('url')
        expect(firstResult).toHaveProperty('thumbnail')
        expect(firstResult.source).toBe('Xvideos')
        expect(firstResult.type).toBe('videos')
    })

    test('should correctly parse GIF results from mock HTML', () => {
        const cheerio = require('cheerio')
        const $ = cheerio.load(mockGifHtml)
        const results = xvideos.parseResults($, null, { type: 'gifs', sourceName: 'Xvideos' })

        expect(results).toBeInstanceOf(Array)
        expect(results.length).toBeGreaterThan(0)
        const firstResult = results[0]
        expect(firstResult).toHaveProperty('id')
        expect(firstResult).toHaveProperty('title')
        expect(firstResult).toHaveProperty('url')
        expect(firstResult).toHaveProperty('thumbnail')
        expect(firstResult).toHaveProperty('preview_video')
        expect(firstResult.source).toBe('Xvideos')
        expect(firstResult.type).toBe('gifs')
    })

    test('should generate a valid video search URL', () => {
        const url = xvideos.getVideoSearchUrl('test', 1)
        expect(url).toBe('https://www.xvideos.com/q/test/0')
    })

    test('should generate a valid GIF search URL', () => {
        const url = xvideos.getGifSearchUrl('test', 1)
        expect(url).toBe('https://www.xvideos.com/gifs/test/0')
    })
})
