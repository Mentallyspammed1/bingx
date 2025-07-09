# Project Overview

This is a hybrid search application primarily built with Node.js and JavaScript. Its core functionality revolves around scraping and aggregating content from various adult content websites. The project utilizes a modular structure for its scrapers, built upon an `AbstractModule` base class.

## Key Technologies

*   **Node.js**: Runtime environment.
*   **JavaScript**: Primary programming language.
*   **Cheerio**: Used for parsing HTML and extracting data.
*   **Axios**: For making HTTP requests.
*   **Babel**: Used for transpilation, which has historically caused some issues with getter properties.

## Project Structure

*   `/`: Root directory containing main application files (`server.js`, `Pornsearch.js`, `config.js`, `config.json`, `package.json`).
*   `__tests__/`: Contains unit tests for various modules and the server.
*   `core/`: Houses core functionalities and base classes for scrapers, such as `AbstractModule.js`.
*   `modules/`: Contains the main scraper implementations (e.g., `Pornhub.js`, `Redtube.js`, `Xhamster.js`, `Xvideos.js`, `Youporn.js`, `Motherless.js`, `mockScraper.cjs`).
*   `modules/custom_scrapers/`: Contains custom scraper implementations (`motherlessScraper.js`, `sexComScraper.js`, `spankbangScraper.js`).
*   `modules/mock_html_data/`: Stores mock HTML data for testing purposes.
*   `public/`: Frontend assets (e.g., `index.html`).

## Scraper Information

*   **Modular Design**: Scrapers are organized into individual files within `modules/` and `modules/custom_scrapers/`.
*   **`AbstractModule`**: All scrapers extend `core/AbstractModule.js`, which defines common methods and properties.
*   **`supportsVideos`/`supportsGifs` to `hasVideoSupport()`/`hasGifSupport()` Migration**:
    *   Originally, scrapers used `get supportsVideos()` and `get supportsGifs()` getters to indicate supported content types.
    *   Due to transpilation issues (specifically with `babel-runtime`), these have been migrated to `hasVideoSupport()` and `hasGifSupport()` methods.
    *   All scrapers now implement these methods, and `Pornsearch.js` checks for these methods to determine content support.
*   **Known Scraper Issues (as of last interaction)**:
    *   **Motherless.com Parsing**: The CSS selectors (`div.content-inner div.thumb`) in `modules/Motherless.js` and `modules/custom_scrapers/motherlessScraper.js` are likely outdated, leading to "No media items found" warnings. This requires manual inspection of the website's HTML to update selectors.
    *   **Spankbang 403 Errors**: Requests to Spankbang.com often result in 403 Forbidden errors, indicating anti-bot measures. Bypassing this may require advanced techniques (proxies, headless browsers, user-agent rotation).
    *   **Xvideos 404 Handling**: Persistent 404 Not Found errors for Xvideos suggest issues with URL validity or content availability. More robust error handling, retries, or dynamic URL discovery might be needed.
    *   **Xhamster Parsing Robustness**: While improved, the Xhamster parsing logic (`modules/Xhamster.js`) may still encounter "Missing: ID" or other property warnings due to variations in page structure. Further testing and refinement are recommended.

## Testing

*   Unit tests are located in the `__tests__/` directory.
*   `scrapers.test.js` and `server.test.js` are key test files.

## Conventions

*   **Code Style**: Adhere to the existing JavaScript code style, including indentation, variable naming, and comment style.
*   **Error Handling**: Follow established patterns for error logging and handling within the scrapers and server.
*   **Modularity**: Maintain the modular design of scrapers.
*   **Absolute Paths**: When using file system operations, always use absolute paths.

## Agent Limitations

As a CLI agent, I have certain limitations:

*   **No Web Browsing**: I cannot directly browse or visually inspect websites. Therefore, tasks requiring manual HTML inspection (e.g., updating Motherless.com selectors based on live site changes) cannot be fully automated by me.
*   **External Services/Libraries**: I cannot directly integrate or set up external services like proxy networks or headless browser environments (e.g., Puppeteer, Selenium).
*   **New Framework Setup**: I cannot set up entirely new testing frameworks or complex build processes. My actions are limited to modifying existing code and running shell commands within the provided environment.
*   **No User Interaction for Shell Commands**: I cannot interact with shell commands that require user input (e.g., interactive prompts).
