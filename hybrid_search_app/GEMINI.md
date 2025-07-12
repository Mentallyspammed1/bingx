# Project Overview

This is a hybrid search application primarily built with Node.js and JavaScript. Its core functionality revolves around scraping and aggregating content from various adult content websites. The project utilizes a modular structure for its scrapers, built upon an `AbstractModule` base class.

## Key Technologies

*   **Node.js**: Runtime environment.
*   **JavaScript**: Primary programming language.
*   **Cheerio**: Used for parsing HTML and extracting data.
*   **Axios**: For making HTTP requests within the `AbstractModule`.
*   **Babel**: Used for transpilation.

## Project Structure

*   `/`: Root directory containing main application files (`server.js`, `Pornsearch.js`, `config.js`, `config.json`, `package.json`).
*   `__tests__/`: Contains unit tests for various modules and the server.
*   `core/`: Houses core functionalities and base classes for scrapers, suchs as `AbstractModule.js`, `VideoMixin.js`, and `GifMixin.js`.
*   `modules/`: Contains the main scraper implementations (e.g., `Pornhub.js`, `Redtube.js`, `Xhamster.js`, `Xvideos.js`, `Youporn.js`, `Motherless.js`).
*   `modules/custom_scrapers/`: Contains older, potentially deprecated custom scraper implementations.
*   `modules/driver-utils.js`: A centralized utility module for common scraper logic.
*   `modules/mock_html_data/`: Stores mock HTML data for testing purposes.
*   `public/`: Frontend assets (e.g., `index.html`).

## Scraper Information

*   **Modular Design**: Scrapers are organized into individual files within `modules/`. Each scraper extends the `AbstractModule`.
*   **`AbstractModule.js`**: The base class for all scrapers. It provides a shared `axios` HTTP client, a common constructor, and defines the abstract interface (`name`, `baseUrl`, `firstpage`, `hasVideoSupport`, `hasGifSupport`, `parseResults`) that all concrete drivers must implement.
*   **Mixins (`VideoMixin.js`, `GifMixin.js`)**: These are applied to the `AbstractModule` to add abstract methods (`getVideoSearchUrl`, `getGifSearchUrl`) related to specific content types.
*   **`driver-utils.js`**: This utility module centralizes common logic used by scrapers, including `makeAbsolute` for resolving URLs, `extractPreview` for finding preview videos, `validatePreview` for checking URL validity, and `sanitizeText` for cleaning scraped text.
*   **`hasVideoSupport()`/`hasGifSupport()` Methods**: Scrapers now use `hasVideoSupport()` and `hasGifSupport()` methods to declare the content types they can handle. This replaces the previous `supportsVideos`/`supportsGifs` getter properties. `Pornsearch.js` checks for these methods to determine content support.

## Known Scraper Issues (as of last interaction)

*   **Motherless.com Parsing**: The scraper (`modules/Motherless.js`) has been refactored for better structure, but the CSS selectors (`div.content-item`, `div.thumb-container`) are speculative. The site's structure changes frequently, so these selectors may be outdated, leading to "No media items found" warnings. This requires ongoing manual inspection of the live website to keep selectors current.
*   **Spankbang 403 Errors**: Requests to Spankbang.com often result in 403 Forbidden errors, indicating anti-bot measures. The recent refactoring of `modules/Spankbang.js` improves code quality but does not resolve this underlying issue. Bypassing this may require advanced techniques (proxies, headless browsers, user-agent rotation) that are beyond the scope of simple code changes.
*   **Xvideos 404 Handling**: Persistent 404 Not Found errors for Xvideos suggest issues with URL validity or content availability. More robust error handling, retries, or dynamic URL discovery might be needed. This scraper has not yet been refactored.
*   **Xhamster Parsing Robustness**: The `modules/Xhamster.js` scraper has been refactored to a more robust class structure. However, like all scrapers, it remains vulnerable to page structure variations that can cause "Missing: ID" or other property warnings.

## Conventions

*   **Code Style**: Adhere to the existing JavaScript code style, including indentation, variable naming, and comment style.
*   **Modularity**: Maintain the modular design of scrapers, with each driver in its own file extending `AbstractModule`.
*   **Use Utilities**: Use the shared functions in `modules/driver-utils.js` for common tasks like URL resolution and text sanitization to avoid code duplication.
*   **Error Handling**: Follow established patterns for error logging and handling within the scrapers and server.
*   **Absolute Paths**: When using file system operations, always use absolute paths.

## Agent Limitations

As a CLI agent, I have certain limitations:

*   **No Web Browsing**: I cannot directly browse or visually inspect websites. Therefore, tasks requiring manual HTML inspection (e.g., updating Motherless.com selectors based on live site changes) cannot be fully automated by me.
*   **External Services/Libraries**: I cannot directly integrate or set up external services like proxy networks or headless browser environments (e.g., Puppeteer, Selenium).
*   **New Framework Setup**: I cannot set up entirely new testing frameworks or complex build processes. My actions are limited to modifying existing code and running shell commands within the provided environment.
*   **No User Interaction for Shell Commands**: I cannot interact with shell commands that require user input (e.g., interactive prompts).

## Platform Scrapers Overview

Here's a summary of all the individual platform scrapers (drivers) that have been developed and integrated into your Neon Video Search application during our conversation:
 * Pornhub.js: A driver designed to scrape video and GIF content from Pornhub. It implements both VideoMixin and GifMixin and relies on HTML parsing with Cheerio.
 * Redtube.js: This driver focuses on fetching video content from Redtube, primarily by interacting with their official API (JSON responses). It implements VideoMixin.
 * Xhamster.js: A driver for scraping video and GIF content from Xhamster. It uses HTML parsing with Cheerio and implements both VideoMixin and GifMixin. (Note: NedtXhamster.js was provided as an updated version of this).
 * Xvideos.js: This driver is mentioned as being integrated into the Pornsearch orchestrator and server.cjs, indicating it's a platform-specific scraper. (Its code was not explicitly provided in the conversation, but its presence is noted).
 * Youporn.js: Similar to Xvideos, this driver is mentioned in the server.cjs file as one of the integrated platforms. (Its code was not explicitly provided).
 * Spankbang.js: A newly provided driver for scraping video and GIF content from Spankbang, implementing VideoMixin and GifMixin and relying on HTML parsing.
 * Motherless.js: A newly provided driver for scraping video and GIF content from Motherless. It's notable for handling GIFs within Motherless's 'images' section and implements both VideoMixin and GifMixin.
 * MockDriver: An example/test driver included directly within server.cjs to demonstrate how a driver should be structured and how it interacts with the system, without making actual external requests. It implements both VideoMixin and GifMixin.
In essence, your application is built to support 7 distinct external adult content platforms (Pornhub, Redtube, Xhamster, Xvideos, Youporn, Spankbang, Motherless) plus a Mock driver for testing, all managed by the Pornsearch orchestrator and leveraging shared utility functions and mixins for consistent development.

## Driver Details

```json
{
  "drivers_details": [
    {
      "name": "Pornhub",
      "baseUrl": "https://www.example.com",
      "supportsVideos": true,
      "supportsGifs": true,
      "videoSearch": {
        "urlPattern": "https://www.example.com/video/search?search={query}&page={page}",
        "itemSelectors": [
          "div.phimage",
          ".video-item",
          ".videoblock"
        ],
        "linkSelector": "a[href*=\"\/view_video.php\"], a[href*=\"\/video\/\"], a.link-videos",
        "titleExtraction": "From link 'title' attribute, image 'alt' attribute, or text content of '.title, .video-title'.",
        "thumbnailSelector": "img[src], img[data-src]",
        "durationSelector": "var.duration, span.duration",
        "idExtraction": "From URL (viewkey=ID or /video/ID/) or item 'data-id' attribute.",
        "previewVideoExtraction": "Uses 'extractPreview' utility (checks 'data-mediabook', video tags, etc.)."
      },
      "gifSearch": {
        "urlPattern": "https://www.example.com/gifs/search?search={query}&page={page}",
        "itemSelectors": [
          "div.gifImageBlock",
          ".gif-item",
          ".gif-thumb"
        ],
        "linkSelector": "a[href*=\"\/gifs\/\"], a.link-gifs",
        "titleExtraction": "From link 'title' attribute, image 'alt' attribute, or text content of '.title, .gif-title'.",
        "thumbnailSelector": "img[src], img[data-src]",
        "idExtraction": "From URL (/gifs/ID/) or item 'data-id' attribute.",
        "previewVideoExtraction": "Uses 'extractPreview' utility (checks video tags, data attributes, etc.)."
      }
    },
    {
      "name": "Redtube",
      "baseUrl": "https://www.redtube.com/",
      "apiBaseUrl": "https://api.redtube.com/",
      "supportsVideos": true,
      "supportsGifs": false,
      "videoSearch": {
        "urlPattern": "https://api.redtube.com/?data=redtube.videos.search&search={query}&page={page}",
        "parsingMethod": "Parses JSON API response.",
        "jsonPathForItems": "rawData.videos[].video",
        "keyExtraction": {
          "id": "video_id",
          "title": "title",
          "url": "url",
          "duration": "duration",
          "thumbnail": "default_thumb",
          "preview_video": "thumb (or potentially embed_url)"
        }
      },
      "gifSearch": {
        "urlPattern": "N/A (Not supported via API)",
        "parsingMethod": "N/A"
      }
    },
    {
      "name": "Xhamster",
      "baseUrl": "https://www.xhamster.com",
      "supportsVideos": true,
      "supportsGifs": true,
      "videoSearch": {
        "urlPattern": "https://www.xhamster.com/videos/search/{query_hyphenated}/{page}/",
        "itemSelectors": [
          "div.video-item",
          "li.video-thumb",
          "div.video-box"
        ],
        "linkSelector": "a.video-link, a[href*=\"\/videos\/\"]",
        "titleExtraction": "From image 'alt' attribute, link 'title' attribute, or text content of '.title, h3 a'.",
        "thumbnailSelector": "img[src], img[data-src]",
        "durationSelector": ".duration, .time",
        "idExtraction": "From URL (/-ID/ or last path segment) or item 'data-id' attribute.",
        "previewVideoExtraction": "Uses 'extractPreview' utility."
      },
      "gifSearch": {
        "urlPattern": "https://www.xhamster.com/gifs/search/{query_hyphenated}/{page}/",
        "itemSelectors": [
          "div.gif-item",
          "li.gif-thumb",
          "div.gif-box"
        ],
        "linkSelector": "a.gif-link, a[href*=\"\/gifs\/\"]",
        "titleExtraction": "From image 'alt' attribute, link 'title' attribute, or text content of '.title, h3 a'.",
        "thumbnailSelector": "img[src], img[data-src]",
        "idExtraction": "From URL (/-ID/ or last path segment) or item 'data-id' attribute.",
        "previewVideoExtraction": "Uses 'extractPreview' utility."
      }
    },
    {
      "name": "Spankbang",
      "baseUrl": "https://spankbang.com",
      "supportsVideos": true,
      "supportsGifs": true,
      "videoSearch": {
        "urlPattern": "https://spankbang.com/s/{query}/{page}/",
        "itemSelectors": [
          "div.video-item",
          "li.video-box",
          "div.video-list-item"
        ],
        "linkSelector": "a[href*=\"\/video\/\"], a.video-link",
        "titleExtraction": "From image 'alt' attribute, link 'title' attribute, or text content of '.title, h3 a'.",
        "thumbnailSelector": "img[src], img[data-src]",
        "durationSelector": ".duration, .time",
        "idExtraction": "From URL (/video/ID/) or item 'data-id' attribute.",
        "previewVideoExtraction": "Uses 'extractPreview' utility."
      },
      "gifSearch": {
        "urlPattern": "https://spankbang.com/gifs/{query}/{page}/",
        "itemSelectors": [
          "div.gif-item",
          "li.gif-box",
          "div.gif-list-item"
        ],
        "linkSelector": "a[href*=\"\/gifs\/\"], a.gif-link",
        "titleExtraction": "From image 'alt' attribute, link 'title' attribute, or text content of '.title, h3 a'.",
        "thumbnailSelector": "img[src], img[data-src]",
        "idExtraction": "From URL (/gifs/ID/) or item 'data-id' attribute.",
        "previewVideoExtraction": "Uses 'extractPreview' utility."
      }
    },
    {
      "name": "Motherless",
      "baseUrl": "https://motherless.com",
      "supportsVideos": true,
      "supportsGifs": true,
      "videoSearch": {
        "urlPattern": "https://motherless.com/videos/search/{query}/page{page}",
        "itemSelectors": [
          "div.content-item",
          "div.thumb-container"
        ],
        "linkSelector": "a[href]",
        "titleExtraction": "From image 'alt' attribute, link 'title' attribute, or text content of '.title, h3 a, .caption'.",
        "thumbnailSelector": "img[src], img[data-src]",
        "durationSelector": ".duration, .time",
        "idExtraction": "From URL (last path segment) or item 'data-id' attribute.",
        "previewVideoExtraction": "Uses 'extractPreview' utility."
      },
      "gifSearch": {
        "urlPattern": "https://motherless.com/images/search/{query}/page{page}",
        "itemSelectors": [
          "div.content-item",
          "div.thumb-container"
        ],
        "linkSelector": "a[href]",
        "titleExtraction": "From image 'alt' attribute, link 'title' attribute, or text content of '.title, h3 a, .caption'.",
        "thumbnailSelector": "img[src], img[data-src]",
        "idExtraction": "From URL (last path segment) or item 'data-id' attribute.",
        "previewVideoExtraction": "Uses 'extractPreview' utility (items without animated preview are skipped in GIF search)."
      }
    },
    {
      "name": "Xvideos",
      "baseUrl": "N/A (Code not provided)",
      "supportsVideos": "N/A (Code not provided)",
      "supportsGifs": "N/A (Code not provided)",
      "videoSearch": {
        "urlPattern": "N/A (Code not provided)",
        "itemSelectors": "N/A (Code not provided)",
        "linkSelector": "N/A (Code not provided)",
        "titleExtraction": "N/A (Code not provided)",
        "thumbnailSelector": "N/A (Code not provided)",
        "durationSelector": "N/A (Code not provided)",
        "idExtraction": "N/A (Code not provided)",
        "previewVideoExtraction": "N/A (Code not provided)"
      },
      "gifSearch": {
        "urlPattern": "N/A (Code not provided)",
        "itemSelectors": "N/A (Code not provided)",
        "linkSelector": "N/A (Code not provided)",
        "titleExtraction": "N/A (Code not provided)",
        "thumbnailSelector": "N/A (Code not provided)",
        "idExtraction": "N/A (Code not provided)",
        "previewVideoExtraction": "N/A (Code not provided)"
      }
    },
    {
      "name": "Youporn",
      "baseUrl": "N/A (Code not provided)",
      "supportsVideos": "N/A (Code not provided)",
      "supportsGifs": "N/A (Code not provided)",
      "videoSearch": {
        "urlPattern": "N/A (Code not provided)",
        "itemSelectors": "N/A (Code not provided)",
        "linkSelector": "N/A (Code not provided)",
        "titleExtraction": "N/A (Code not provided)",
        "thumbnailSelector": "N/A (Code not provided)",
        "durationSelector": "N/A (Code not provided)",
        "idExtraction": "N/A (Code not provided)",
        "previewVideoExtraction": "N/A (Code not provided)"
      },
      "gifSearch": {
        "urlPattern": "N/A (Code not provided)",
        "itemSelectors": "N/A (Code not provided)",
        "linkSelector": "N/A (Code not provided)",
        "titleExtraction": "N/A (Code not provided)",
        "thumbnailSelector": "N/A (Code not provided)",
        "idExtraction": "N/A (Code not provided)",
        "previewVideoExtraction": "N/A (Code not provided)"
      }
    },
    {
      "name": "Mock",
      "baseUrl": "http://mock.com",
      "supportsVideos": true,
      "supportsGifs": true,
      "videoSearch": {
        "urlPattern": "http://mock.com/videos?q={query}&page={page}",
        "parsingMethod": "Returns hardcoded mock results. Does not scrape HTML."
      },
      "gifSearch": {
        "urlPattern": "http://mock.com/gifs?q={query}&page={page}",
        "parsingMethod": "Returns hardcoded mock results. Does not scrape HTML."
      }
    }
  ]
}
```