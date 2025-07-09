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
*   `core/`: Houses core functionalities and base classes for scrapers, such as `AbstractModule.js`, `VideoMixin.js`, and `GifMixin.js`.
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