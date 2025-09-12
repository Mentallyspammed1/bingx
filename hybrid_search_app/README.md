# Agent Instructions for hybrid_search_app

This document provides instructions for working with the `hybrid_search_app`, a Node.js Express application.

## Setup and Dependencies

1.  **Navigate to the app directory:**
    ```bash
    cd hybrid_search_app
    ```
2.  **Install dependencies:**
    Make sure you have Node.js and npm installed. Then, run the following command to install the project's dependencies:
    ```bash
    npm install
    ```

## Running the Server

1.  **Start the server:**
    ```bash
    npm start
    ```
    Alternatively, you can run:
    ```bash
    node server.js
    ```
    The server will typically start on `http://localhost:3000` (or the port specified in your `.env` file or system environment variable `PORT`).

## Running Tests

1.  **Execute tests:**
    The project uses Jest for testing. To run all tests:
    ```bash
    npm test
    ```
    This command will execute test files located in the `__tests__` directory.

## Configuration (`config.json`)

The application uses a `config.json` file in the `hybrid_search_app` directory to manage its scraping behavior.

*   **`defaultStrategy`**: Can be `"custom"` or `"pornsearch"`. This determines the default method used for sites not explicitly listed in `siteOverrides`.
*   **`siteOverrides`**: An object where keys are lowercase site driver names (e.g., `"pornhub"`) and values are the strategy (`"custom"` or `"pornsearch"`) to use for that specific site.
*   **`customScrapersMap`**: An object where keys are site driver names (e.g., `"Pornhub"`, `"Redtube"`) and values are paths (relative to `hybrid_search_app`) to the custom scraper module files.

Example `config.json`:
```json
{
  "defaultStrategy": "custom",
  "siteOverrides": {
    "redtube": "pornsearch"
  },
  "customScrapersMap": {
    "Pornhub": "modules/custom_scrapers/pornhubScraper.js",
    "Mock": "modules/custom_scrapers/mockScraper.cjs"
  }
}
```

Ensure this configuration is correctly set up, especially the paths in `customScrapersMap`, for the application to function as expected with custom scrapers.

## Development Notes

*   The main server logic is in `server.js`.
*   Custom scraper modules are typically located in `modules/custom_scrapers/`.
*   Scrapers should extend or follow the pattern of `core/AbstractModule.js`.
*   When adding new custom scrapers, ensure they are mapped correctly in `config.json`.
*   Always run `npm test` after making changes to ensure no existing functionality is broken.
