const app = require('../server'); // This is the Express app instance
const http = require('http');

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
});
