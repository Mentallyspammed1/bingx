#!/bin/bash

# ==============================================================================
# NEON SEARCH APP - SETUP AND GENERATION SCRIPT - ENHANCED AND UPGRADED
# ==============================================================================

# This script initializes a Node.js web app for adult content searching with
# modular scrapers, backend API, and minimal frontend.
#
# Usage:
#   1) mkdir neon_search_app && cd neon_search_app
#   2) Save and run this script: bash /path/to/neon_search_app.sh
#   3) npm install express cors axios cheerio babel-runtime
#   4) Start server: node server.js
#   5) Open browser at http://localhost:3000
#
# The app scrapes video and gif content from multiple providers via module drivers.
# HTML parsing depends on current site selectors and requires periodic updates.

echo "Creating directories: core and modules..."
mkdir -p core modules

# core/OverwriteError.js
cat << 'EOF' > core/OverwriteError.js
'use strict';

class OverwriteError extends Error {
  constructor(methodName) {
    super(`Method or property "${methodName}" must be overridden by subclass.`);
    this.name = 'OverwriteError';
  }
}

module.exports = OverwriteError;
EOF

# core/AbstractModule.js
cat << 'EOF' > core/AbstractModule.js
'use strict';

const OverwriteError = require('./OverwriteError');

/**
 * AbstractModule base class for all content scrapers.
 * Requires subclasses to override name, firstpage, and URL/parser methods.
 * Supports mixins to add video or gif scraping methods.
 */
class AbstractModule {
  constructor(options = {}) {
    this.query = (typeof options.query === 'string') ? options.query.trim() : '';
    this.options = options || {};
    this.page = this.firstpage;
  }

  get name() {
    throw new OverwriteError('name');
  }

  get firstpage() {
    throw new OverwriteError('firstpage');
  }

  setQuery(newQuery) {
    this.query = (typeof newQuery === 'string') ? newQuery.trim() : '';
  }

  static with(...mixins) {
    return mixins.reduce((c, mixin) => {
      if(typeof mixin === 'function') return mixin(c);
      console.warn('[AbstractModule.with] Invalid mixin:', mixin);
      return c;
    }, this);
  }
}

module.exports = AbstractModule;
EOF

# core/GifMixin.js
cat << 'EOF' > core/GifMixin.js
'use strict';

const OverwriteError = require('./OverwriteError');

/**
 * GifMixin adds gifUrl and gifParser contract methods to base class.
 */
const GifMixin = (BaseClass) => class extends BaseClass {
  gifUrl(query, page) {
    throw new OverwriteError('gifUrl');
  }

  gifParser($, rawData) {
    throw new OverwriteError('gifParser');
  }
};

module.exports = GifMixin;
EOF

# core/VideoMixin.js
cat << 'EOF' > core/VideoMixin.js
'use strict';

const OverwriteError = require('./OverwriteError');

/**
 * VideoMixin adds videoUrl and videoParser contract methods to base class.
 */
const VideoMixin = (BaseClass) => class extends BaseClass {
  videoUrl(query, page) {
    throw new OverwriteError('videoUrl');
  }

  videoParser($, rawData) {
    throw new OverwriteError('videoParser');
  }
};

module.exports = VideoMixin;
EOF

# Create sample driver template for adult platforms, here Pornhub example.
cat << 'EOF' > modules/Pornhub.js
'use strict';

const AbstractModule = require('../core/AbstractModule');
const VideoMixin = require('../core/VideoMixin');
const GifMixin = require('../core/GifMixin');

const BASE_PLATFORM_URL = 'https://www.pornhub.com';
const GIF_DOMAIN = 'https://i.pornhub.com';

/**
 * PornhubDriver - Scrapes video and gif content from Pornhub.
 */
class PornhubDriver extends AbstractModule.with(VideoMixin, GifMixin) {
  constructor(options = {}) {
    super(options);
  }

  get name() {
    return 'Pornhub';
  }

  get firstpage() {
    return 1;
  }

  videoUrl(query, page) {
    const q = encodeURIComponent(query.trim());
    const p = Math.max(1, page || this.firstpage);
    const url = new URL('/video/search', BASE_PLATFORM_URL);
    url.searchParams.set('search', q);
    url.searchParams.set('page', String(p));
    return url.href;
  }

  videoParser($, rawHtml) {
    const results = [];
    const items = $('div.phimage');
    if (!items.length) {
      console.warn(`[${this.name} videoParser] No video items found.`);
      return results;
    }
    items.each((i, el) => {
      const item = $(el);
      const link = item.find('a').first();
      let url = link.attr('href');
      let id = url ? (url.match(/viewkey=([a-zA-Z0-9]+)/) || [])[1] : null;
      let title = link.attr('title') || item.find('span.title').text().trim() || item.attr('data-video-title');
      let thumb = item.find('img').first().attr('data-src') || item.find('img').first().attr('src');
      const duration = item.find('var.duration, span.duration').text().trim() || 'N/A';
      if (thumb && thumb.includes('nothumb')) thumb = undefined;
      if (!id || !url || !title || !thumb) return; // Skip malformed
      url = this._makeAbsolute(url, BASE_PLATFORM_URL);
      thumb = this._makeAbsolute(thumb, BASE_PLATFORM_URL);
      results.push({
        id,
        title,
        url,
        thumbnail: thumb,
        duration,
        source: this.name,
        type: 'videos'
      });
    });
    return results;
  }

  gifUrl(query, page) {
    const q = encodeURIComponent(query.trim());
    const p = Math.max(1, page || this.firstpage);
    const url = new URL('/gifs/search', BASE_PLATFORM_URL);
    url.searchParams.set('search', q);
    url.searchParams.set('page', String(p));
    return url.href;
  }

  gifParser($, rawHtml) {
    const results = [];
    const items = $('div.gifImageBlock,div.img-container');
    if (!items.length) {
      console.warn(`[${this.name} gifParser] No GIF items found.`);
      return results;
    }
    items.each((i, el) => {
      const item = $(el);
      const link = item.find('a').first();
      let pageUrl = link.attr('href');
      let id = item.attr('data-id') || (pageUrl ? pageUrl.match(/\/(\d+)\//) : null)?.[1];
      let title = item.find('img').attr('alt') || link.attr('title') || 'Untitled GIF';
      let animated = item.find('img').attr('data-src') || item.find('img').attr('src');
      if (animated && animated.endsWith('.gif')) {
        animated = this._makeAbsolute(animated, GIF_DOMAIN);
      }
      if (!id || !pageUrl || !animated) return; // Skip malformed
      pageUrl = this._makeAbsolute(pageUrl, BASE_PLATFORM_URL);
      results.push({
        id,
        title,
        url: pageUrl,
        thumbnail: animated,
        preview_video: animated,
        source: this.name,
        type: 'gifs'
      });
    });
    return results;
  }

  _makeAbsolute(url, base) {
    if (!url || typeof url !== 'string') return undefined;
    if (url.startsWith('data:')) return url;
    if (url.startsWith('//')) return `https:${url}`;
    if (url.startsWith('http:') || url.startsWith('https:')) return url;
    try {
      return new URL(url, base).href;
    } catch (e) { return undefined; }
  }
}

module.exports = PornhubDriver;
EOF

# Similarly create other drivers with updated selectors & logic: Xvideos, Xhamster, Youporn, Sex, Redtube, Mock...

# server.js - Express backend with CORS and unified search API
cat << 'EOF' > server.js
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
EOF

# Minimalistic frontend placeholder (index.html)
cat << 'EOF' > index.html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Neon Search | Videos & GIFs</title>
<style>
  body { background-color: #000; color: #0ff; font-family: monospace; text-align: center; padding: 2rem; }
  input, select, button { font-size: 1.2rem; margin: 0.5rem; padding: 0.3rem; }
  #results { margin-top: 20px; }
</style>
</head>
<body>
<h1>Neon Search App</h1>
<p>Enter query and options to search videos or GIFs.</p>
<input id="search" placeholder="Search term" />
<select id="driver">
  <option value="pornhub">Pornhub</option>
  <option value="xvideos">Xvideos</option>
  <option value="xhamster">Xhamster</option>
  <option value="youporn">Youporn</option>
  <option value="sex">Sex.com</option>
  <option value="redtube">Redtube</option>
  <option value="mock">Mock</option>
</select>
<select id="type">
  <option value="videos">Videos</option>
  <option value="gifs">GIFs</option>
</select>
<button onclick="searchNeon()">Search</button>
<div id="results"></div>
<script>
  async function searchNeon() {
    const query = document.getElementById('search').value;
    const driver = document.getElementById('driver').value;
    const type = document.getElementById('type').value;
    if(!query) {
      alert('Enter a search term');
      return;
    }
    const res = await fetch(`/api/search?query=${encodeURIComponent(query)}&driver=${driver}&type=${type}`);
    const data = await res.json();
    if(data.error) {
      document.getElementById('results').textContent = `Error: ${data.error}`;
      return;
    }
    if(data.length === 0) {
      document.getElementById('results').textContent = 'No results.';
      return;
    }
    const html = data.map(item => `
      <div style="margin: 1rem; border: 1px solid #0ff; padding: 1rem;">
        <h3>${item.title}</h3>
        <p>Source: ${item.source} | Type: ${item.type}</p>
        <a href="${item.url}" target="_blank">
          <img src="${item.thumbnail}" alt="${item.title}" width="320" />
        </a>
        ${item.duration ? `<p>Duration: ${item.duration}</p>` : ''}
      </div>
    `).join('');
    document.getElementById('results').innerHTML = html;
  }
</script>
</body>
</html>
EOF

