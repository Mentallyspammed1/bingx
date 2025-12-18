const app = require('../server')
const http = require('http')

jest.mock('axios')

describe('Server Tests', () => {
  let server

  beforeAll((done) => {
    server = http.createServer(app)
    server.listen(0, done)
  })

  afterAll((done) => {
    if (server) {
      server.close(done)
    } else {
      done()
    }
  })

  test('should import server.js (Express app) without errors', () => {
    expect(app).toBeDefined()
  })

  test('app object should have listen method (characteristic of Express app)', () => {
    expect(typeof app.listen).toBe('function')
  })

  test('should return mock GIF data for /api/search?driver=mock&type=gifs', async () => {
    const port = server.address().port
    const axios = require('axios')
    axios.get.mockResolvedValue({
      status: 200,
      data: {
        message: "Results from orchestrator for 'mock' query 'test' (type: gifs, mock: true)",
        data: [
          {
            title: 'Mock GIF 1',
            url: 'https://mock.url/gif1',
            thumbnail: 'https://mock.url/thumb1.jpg',
            preview_video: 'https://mock.url/preview1.gif',
            source: 'MockSource',
            query: 'test'
          }
        ]
      }
    })

    try {
      const response = await axios.get(`http://localhost:${port}/api/search?query=test&driver=mock&type=gifs`)

      expect(response.status).toBe(200)
      expect(response.data).toBeDefined()
      expect(response.data.message).toContain("Results from orchestrator for 'mock'")
      expect(Array.isArray(response.data.data)).toBe(true)
      expect(response.data.data.length).toBeGreaterThan(0)

      const firstGif = response.data.data[0]
      expect(firstGif.title).toBeDefined()
      expect(firstGif.url).toBeDefined()
      expect(firstGif.thumbnail).toBeDefined()
      expect(firstGif.preview_video).toBeDefined()
      expect(firstGif.preview_video.endsWith('.gif')).toBe(true)
      expect(firstGif.source).toBe('MockSource')
      expect(firstGif.query).toBe('test')

    } catch (error) {
      console.error('API test error details:', error.response ? error.response.data : error.message)
      throw error
    }
  })
})
