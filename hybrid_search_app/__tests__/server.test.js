const app = require('../server'); // This is the Express app instance
const http = require('http');
const axios = require('axios'); // Added axios

describe('Server Tests', () => {
  let server; // To hold the server instance

  beforeAll((done) => {
    server = http.createServer(app); // Create an HTTP server with the Express app
    server.listen(0, () => { // Listen on a random available port (0)
      // console.log(`Test server running on port ${server.address().port}`);
      done();
    });
  });

  afterAll((done) => {
    if (server) {
      server.close(done);
    } else {
      done();
    }
  });

  test('should import server.js (Express app) without errors', () => {
    expect(app).toBeDefined();
  });

  test('app object should have listen method (characteristic of Express app)', () => {
    expect(typeof app.listen).toBe('function');
  });

  // Add a simple test to see if the server is responding (optional)
  // test('should respond to a simple GET request', async () => {
  //   const port = server.address().port;
  //   try {
  //     const response = await axios.get(`http://localhost:${port}/`);
  //     expect(response.status).toBe(200);
  //   } catch (error) {
  //     // If it's a 404 for '/', that's also fine for this basic test if no / route is defined
  //     expect(error.response.status).toBe(404);
  //   }
  // });

  test('should return mock GIF data for /api/search?driver=mock&type=gifs', async () => {
    const port = server.address().port; // Get the port from the running test server
    try {
      const response = await axios.get(`http://localhost:${port}/api/search?query=test&driver=mock&type=gifs`);

      expect(response.status).toBe(200);
      expect(response.data).toBeDefined();
      expect(response.data.message).toContain("Results from custom scraper 'mock'");
      expect(Array.isArray(response.data.data)).toBe(true);
      expect(response.data.data.length).toBeGreaterThan(0); // mockScraper returns 2 items

      // Check structure of the first mock GIF item
      const firstGif = response.data.data[0];
      expect(firstGif.title).toBeDefined();
      expect(firstGif.url).toBeDefined();
      expect(firstGif.thumbnail).toBeDefined();
      expect(firstGif.preview_video).toBeDefined();
      expect(firstGif.preview_video.endsWith('.gif')).toBe(true); // Crucial for mock GIF
      expect(firstGif.source).toBe('MockSource'); // As defined in mockScraper.js
      expect(firstGif.query).toBe('test'); // mockScraper adds the query to items

    } catch (error) {
      // If the request itself fails, log details and fail the test
      console.error('API test error details:', error.response ? error.response.data : error.message);
      throw error; // Re-throw to fail the test
    }
  });
});
