'use strict';

// No AbstractModule needed for mock if it's self-contained and doesn't use shared methods like _makeAbsolute
// However, to fit the orchestrator's loading pattern, it should ideally export a class.

const BASE_URL = 'https://mock.com'; // Dummy base URL for mock data
const DRIVER_NAME = 'Mock'; // Should match the value in the frontend dropdown

/**
 * @class MockDriver
 * @classdesc Mock driver for testing the search interface.
 * It returns predefined data without making external calls.
 */
class MockDriver {
    constructor(query) { // Orchestrator might pass query
        this.query = query; // Store query if needed for mock data generation
        // Properties expected by the orchestrator
        this.name = DRIVER_NAME;
        this.baseUrl = BASE_URL;
        this.supportsVideos = true;
        this.supportsGifs = true;
        this.firstpage = 1;
    }

    /**
     * Constructs a mock URL for searching videos.
     * @param {string} query - The search query string.
     * @param {number} page - The page number.
     * @returns {string} A mock search URL.
     */
    getVideoSearchUrl(query, page) {
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        return `${this.baseUrl}/search/videos?query=${encodeURIComponent(query)}&page=${searchPage}`;
    }

    /**
     * Constructs a mock URL for searching GIFs.
     * @param {string} query - The search query string.
     * @param {number} page - The page number.
     * @returns {string} A mock search URL.
     */
    getGifSearchUrl(query, page) {
        const searchPage = Math.max(1, parseInt(page, 10) || this.firstpage);
        return `${this.baseUrl}/search/gifs?query=${encodeURIComponent(query)}&page=${searchPage}`;
    }

    /**
     * Returns mock search results.
     * This method is called by the orchestrator.
     * @param {null} $ - Cheerio object (null for mock, as no HTML is parsed).
     * @param {null} htmlOrJsonData - Raw HTML or JSON (null for mock).
     * @param {object} parserOptions - Options including type, sourceName, query, page.
     * @returns {Array<object>} An array of mock MediaResult objects.
     */
    parseResults($, htmlOrJsonData, parserOptions) {
        const { type, query, page } = parserOptions;
        // console.log(`[${this.name}] Generating mock ${type} for query: "${query}", page: ${page}`);

        const results = [];
        const numResults = Math.floor(Math.random() * 5) + 1; // Generate 1-5 mock results

        for (let i = 0; i < numResults; i++) {
            const mockId = `${type.slice(0,3)}_${page}_${i}_${Math.random().toString(36).substring(2, 7)}`;
            if (type === 'videos') {
                results.push({
                    id: mockId,
                    title: `Mock Video ${i + 1} for "${query}" (Page ${page})`,
                    url: `${this.baseUrl}/video/${mockId}`,
                    thumbnail: `https://via.placeholder.com/320x180.png/002244/FFFFFF?text=MockVideo+${i + 1}`,
                    duration: `${String(Math.floor(Math.random() * 10) + 1).padStart(2, '0')}:${String(Math.floor(Math.random() * 60)).padStart(2, '0')}`,
                    preview_video: `${this.baseUrl}/preview/video/${mockId}.mp4`,
                    source: this.name, // Should be set by orchestrator, but good practice
                    type: 'videos'    // Should be set by orchestrator
                });
            } else if (type === 'gifs') {
                results.push({
                    id: mockId,
                    title: `Mock GIF ${i + 1} for "${query}" (Page ${page})`,
                    url: `${this.baseUrl}/gif/${mockId}`,
                    thumbnail: `https://via.placeholder.com/300x200.png/440022/FFFFFF?text=MockGIF+${i + 1}`,
                    // For GIFs, preview_video is often the GIF URL itself or a WebM/MP4.
                    // The frontend's createMediaContainer handles .gif in preview_video as an <img>
                    preview_video: `${this.baseUrl}/animated/${mockId}.gif`,
                    duration: undefined, // GIFs don't have duration in this context
                    source: this.name,
                    type: 'gifs'
                });
            }
        }
        return results;
    }

    // No _makeAbsolute needed as all URLs are constructed as absolute.
}

module.exports = MockDriver; // Export class for the orchestrator
