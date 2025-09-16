# Neon Video Search App

## Overview
The Neon Video Search App is a hybrid web application designed for searching adult video and GIF content across multiple platforms. It features a modular driver architecture for easy extensibility, AI-powered search suggestions, and a responsive user interface with a modern neon aesthetic. The project combines a Node.js/Express.js backend with a Next.js/React frontend, complemented by Python scripts for advanced scraping and utility tasks.

## Features
*   **Modular Driver Architecture**: Easily extendable system allowing for the addition or removal of content sources (platforms) without modifying core application logic.
*   **Multi-Platform Support**: Integrates with various adult content platforms (e.g., Pornhub, Redtube, Xhamster, Spankbang, Motherless) for comprehensive search results.
*   **AI-Powered Search Suggestions**: Leverages Google's Gemini API via Genkit to provide intelligent search term suggestions, enhancing the user experience.
*   **Responsive & Modern UI**: Built with Next.js, React, Tailwind CSS, and Radix UI, offering a sleek, neon-themed interface optimized for various screen sizes.
*   **Real-time Previews**: Provides dynamic video previews on hover for search results, offering a quick glance at content.
*   **Robust Web Scraping & API Integration**: Utilizes both direct API calls and advanced web scraping techniques (including browser automation with Selenium/ChromeDriver) to gather content efficiently.
*   **Centralized Logging, Dynamic Configuration & API Caching**: Ensures operational stability, allows for on-the-fly updates to strategies, and improves performance by reducing redundant requests.
*   **Comprehensive Testing Suite**: Includes unit and integration tests for platform drivers and core functionalities, ensuring reliability and maintainability.

## Technologies Used

### Frontend
*   **Next.js**: React framework for building server-rendered and static web applications.
*   **React**: JavaScript library for building user interfaces.
*   **Tailwind CSS**: Utility-first CSS framework for rapid UI development.
*   **Radix UI**: Open-source UI component library for building high-quality, accessible design systems.
*   **TypeScript**: Superset of JavaScript that adds static types.

### Backend
*   **Node.js**: JavaScript runtime for server-side logic.
*   **Express.js**: Fast, unopinionated, minimalist web framework for Node.js (likely used in `server.cjs`).
*   **Genkit**: Framework for building AI-powered applications, integrating with Google's Gemini API.
*   **Cheerio**: Fast, flexible, and lean implementation of core jQuery specifically designed for the server to parse HTML and XML.

### Scraping & Utilities
*   **Python**: Used for various utility scripts, advanced scraping, image processing, and data handling.
    *   `requests`: HTTP library for making web requests.
    *   `Pillow`: Python Imaging Library for image manipulation.
    *   `imagehash`: Perceptual hashing for images.
    *   `bing-image-downloader`: For downloading images.
*   **Selenium / ChromeDriver**: Browser automation framework for web scraping tasks that require JavaScript execution or interaction.

### Other Key Libraries & Tools
*   **Firebase**: (Mentioned in `package.json`) Potentially used for backend services, authentication, or real-time database.
*   **Axios**: Promise-based HTTP client for the browser and Node.js.
*   **Dotenv**: Loads environment variables from a `.env` file.
*   **Date-fns**: Modern JavaScript date utility library.
*   **Zod**: TypeScript-first schema declaration and validation library.

## Project Structure (High-Level)

```
.
├── hybrid_search_app/          # Core Node.js application logic, drivers, orchestrator
│   ├── core/                   # Abstract classes, mixins (AbstractModule, VideoMixin, GifMixin)
│   ├── modules/                # Individual platform drivers (Pornhub, Redtube, Xhamster, etc.)
│   └── ...
├── public/                     # Static assets for the Next.js frontend
├── src/                        # Next.js frontend source code (components, pages, AI integration)
├── tests/                      # Unit and integration tests for drivers and core functionalities
├── scraper_output/             # Directory for scraped data output
├── downloaded_thumbnails/      # Directory for downloaded image thumbnails
├── *.py                        # Various Python scripts for scraping, image processing, and utilities
├── server.cjs                  # Main Node.js backend server (Express.js)
├── package.json                # Node.js project metadata and dependencies
├── requirements.txt            # Python project dependencies
├── config.json                 # Application configuration
├── .env                        # Environment variables (API keys, etc.)
├── chromedriver-linux64/       # ChromeDriver binaries
└── ...                         # Other configuration files, logs, and temporary files
```

## Setup and Installation

### Prerequisites
Before you begin, ensure you have the following installed:
*   **Node.js** (LTS version recommended) and **npm** (or yarn)
*   **Python 3.x** and **pip**
*   **ChromeDriver**: Download the appropriate version for your Chrome browser and place it in your system's PATH or within the project's `chromedriver-linux64/` directory.

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd neon-video-search-app # Or your project's root directory
    ```

2.  **Install Node.js dependencies:**
    ```bash
    npm install
    # or yarn install
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration:**
    *   Create a `.env` file in the project root based on a `.env.example` (if available) or by adding necessary environment variables (e.g., API keys for Gemini, Firebase credentials).
    *   Review and adjust `config.json` for application-specific settings, such as caching, rate limits, or custom scraper configurations.

## Usage

### Starting the Backend Server (Node.js)
The main backend server is `server.cjs`.
```bash
node server.cjs
```
This will start the Express.js server, which handles API requests and serves the Next.js frontend.

### Starting the Frontend Development Server (Next.js)
If you are developing the frontend, you can start the Next.js development server:
```bash
npm run dev
```
This typically runs on `http://localhost:3000` (or `http://localhost:9002` as per `package.json` script).

### Running Python Scripts
Individual Python scripts can be run directly:
```bash
python scrape.py
# or
python vid_search.py
```
Refer to individual Python scripts for their specific usage and arguments.

### Accessing the Application
Once the backend server and frontend development server (if applicable) are running, open your web browser and navigate to the appropriate URL (e.g., `http://localhost:9002` or the address where `server.cjs` is serving the frontend).

## Contributing
Contributions are welcome! Please refer to `CONTRIBUTING.md` (if available) for guidelines on how to contribute to this project.

## License
This project is licensed under the [MIT License](LICENSE) - see the `LICENSE` file for details.
