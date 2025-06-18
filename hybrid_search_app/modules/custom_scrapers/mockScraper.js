// hybrid_search_app/modules/custom_scrapers/mockScraper.js
'use strict';

const AbstractModule = require('../../core/AbstractModule');
const VideoMixin = require('../../core/VideoMixin');
const GifMixin = require('../../core/GifMixin');

const mockVideoData = [
    {
        title: 'Mock Video 1: Neon Dreams',
        url: 'https://example.com/mockvideo1',
        thumbnail: 'https://via.placeholder.com/320x180.png?text=Mock+Video+1+Thumb',
        preview_video: 'https://www.w3schools.com/html/mov_bbb.mp4', // Sample MP4
        duration: '0:10',
        source: 'MockSource',
        views: '1M',
        tags: ['mock', 'test', 'neon'],
        type: 'videos'
    },
    {
        title: 'Mock Video 2: Cybernetic Future',
        url: 'https://example.com/mockvideo2',
        thumbnail: 'https://via.placeholder.com/320x180.png?text=Mock+Video+2+Thumb',
        preview_video: 'https://www.w3schools.com/tags/movie.mp4', // Sample MP4
        duration: '0:15',
        source: 'MockSource',
        views: '500K',
        tags: ['cyber', 'future', 'mock'],
        type: 'videos'
    }
];

const mockGifData = [
    {
        title: 'Mock GIF 1: Blinking Light',
        url: 'https://example.com/mockgif1',
        thumbnail: 'https://via.placeholder.com/300.gif?text=Mock+GIF+1+Static', // Placeholder static
        preview_video: 'https://media.giphy.com/media/Vh8pbGX3SGRwFDh3V0/giphy.gif', // Sample GIF
        source: 'MockSource',
        tags: ['mock', 'gif', 'blinking'],
        type: 'gifs'
    },
    {
        title: 'Mock GIF 2: Neon Loop',
        url: 'https://example.com/mockgif2',
        thumbnail: 'https://via.placeholder.com/300.gif?text=Mock+GIF+2+Static', // Placeholder static
        preview_video: 'https://media.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif', // Sample GIF
        source: 'MockSource',
        tags: ['mock', 'gif', 'loop', 'neon'],
        type: 'gifs'
    }
];

class MockScraper extends AbstractModule {
    get name() {
        return 'mock';
    }

    get firstpage() {
        return 1; // Mock can be simple, only one page of results
    }

    async searchVideos(query = this.query, page = this.page) {
        console.log(`[MockScraper] searchVideos called with Query: ${query}, Page: ${page}`);
        if (page > this.firstpage) {
            return []; // No more mock results beyond the first page
        }
        // Simulate a delay
        await new Promise(resolve => setTimeout(resolve, 200));
        // Return a copy of the mock data
        return mockVideoData.map(item => ({ ...item, query }));
    }

    async searchGifs(query = this.query, page = this.page) {
        console.log(`[MockScraper] searchGifs called with Query: ${query}, Page: ${page}`);
        if (page > this.firstpage) {
            return []; // No more mock results
        }
        // Simulate a delay
        await new Promise(resolve => setTimeout(resolve, 200));
        // Return a copy of the mock data
        return mockGifData.map(item => ({ ...item, query }));
    }
}

// Apply Mixins if needed, though for mock, it might not be strictly necessary
// unless the core functionality of mixins is to be tested.
// For simplicity, we'll make it a basic class first.
// If VideoMixin and GifMixin are essential for structure AbstractModule expects,
// they can be added like:
// module.exports = AbstractModule.with(VideoMixin, GifMixin)(MockScraper);
// For now, let's export directly if mixins aren't strictly needed for mock data.

module.exports = MockScraper;
