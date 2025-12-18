#!/usr/bin/env node

const express = require('express');
const cors = require('cors');
const path = require('path');
const axios = require('axios');
const cheerio = require('cheerio');

const AbstractModule = require('./core/AbstractModule');
const VideoMixin = require('./core/VideoMixin');
const GifMixin = require('./core/GifMixin');

const Redtube = require('./modules/Redtube');
const Pornhub = require('./modules/Pornhub');
const Xvideos = require('./modules/Xvideos');
const Xhamster = require('./modules/Xhamster');
const Youporn = require('./modules/Youporn');
const Sex = require('./modules/Sex');

const drivers = {
  'redtube': Redtube,
  'pornhub': Pornhub,
  'xvideos': Xvideos,
  'xhamster': Xhamster,
  'youporn': Youporn,
  'sex': Sex,
  'mock': class MockDriver extends AbstractModule.with(VideoMixin, GifMixin) {
    constructor(opts) { super(opts); }
    get name() { return 'Mock'; }
    get firstpage() { return 1; }
    videoUrl(q, p) { return `http://mock.com/videos?q=${encodeURIComponent(q)}&page=${p}`; }
    videoParser($, raw) {
      return Array.from({length:5}, (_,i) => ({
        id: `mock-video-${i}-${Date.now()}`,
        title: `Mock Video ${this.query} Page ${this.page} - #${i+1}`,
        url: `http://mock.com/video/${i}`,
        duration: '0:30',
        thumbnail: `https://placehold.co/320x180/00e5ff/000000?text=Mock+Video+${i+1}`,
        preview_video: `https://www.w3schools.com/html/mov_bbb.mp4`,
        source: this.name,
        type: 'videos'
      }));
    }
    gifUrl(q, p) { return `http://mock.com/gifs?q=${encodeURIComponent(q)}&page=${p}`; }
    gifParser($, raw) {
      return Array.from({length:5}, (_,i) => ({
        id: `mock-gif-${i}-${Date.now()}`,
        title: `Mock GIF ${this.query} Page ${this.page} - #${i+1}`,
        url: `http://mock.com/gif/${i}`,
        thumbnail: `https://placehold.co/320x180/ff00aa/000000?text=Mock+GIF+${i+1}`,
        preview_video: `https://i.giphy.com/media/VbnUQpnihPSIgIXuZv/giphy.gif`,
        source: this.name,
        type: 'gifs'
      }));
    }
  }
};

const app = express();
app.use(cors());
app.use(express.static(__dirname)); // For index.html

app.get('/api/search', async (req, res) => {
  try {
    const { query, driver: driverName, type, page } = req.query;
    if (!query || !driverName || !type)
      return res.status(400).json({ error: 'Missing query, driver, or type parameters.' });

    const DriverClass = drivers[driverName.toLowerCase()];
    if (!DriverClass)
      return res.status(400).json({ error: `Unsupported driver: ${driverName}` });

    const driver = new DriverClass({ query });
    driver.setQuery(query);
    driver.page = Number(page) || driver.firstpage;

    const axiosConfig = {
      timeout: 30000,
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36' }
    };

    let url = '';
    let results = [];
    let rawData;

    if (type === 'videos' && driver.videoUrl && driver.videoParser) {
      url = driver.videoUrl(query, driver.page);
      const response = await axios.get(url, axiosConfig);
      rawData = response.data;
      const $ = ['pornhub', 'xvideos', 'xhamster', 'youporn', 'sex'].includes(driverName.toLowerCase()) ? cheerio.load(rawData) : null;
      results = await driver.videoParser($, rawData);
    }
    else if (type === 'gifs' && driver.gifUrl && driver.gifParser) {
      url = driver.gifUrl(query, driver.page);
      const response = await axios.get(url, axiosConfig);
      rawData = response.data;
      const $ = ['pornhub', 'xhamster', 'sex', 'youporn'].includes(driverName.toLowerCase()) ? cheerio.load(rawData) : null;
      results = await driver.gifParser($, rawData);
    }
    else {
      return res.status(400).json({ error: `Unsupported search type '${type}' for driver '${driverName}'.` });
    }

    results = results.map(item => ({ ...item, source: driver.name }));
    res.json(results);

  } catch (error) {
    console.error(`[Backend][${req.query.driver}][${req.query.type}] Error:`, error?.message || error);
    if (error.response) {
      res.status(error.response.status).json({ error: `Failed to fetch from upstream: ${error.response.status}` });
    } else if (error.request) {
      res.status(504).json({ error: `No response from upstream server.` });
    } else {
      res.status(500).json({ error: error.message });
    }
  }
});

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Neon Video Search backend started on http://0.0.0.0:${PORT}`);
});
