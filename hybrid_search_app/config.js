const path = require('path')

module.exports = {
    global: {
        defaultUserAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        requestTimeout: 15000, // 15 seconds
        concurrencyLimit: 5, // Max 5 concurrent requests
        maxRetries: 3,
        retryDelayMs: 1000, // 1 second
        logLevel: process.env.LOG_LEVEL || 'info', // silly, debug, info, warn, error
        // Corrected path assuming Pornsearch.js and config.js are in hybrid_search_app/
        // and modules/ is also in hybrid_search_app/
        mockDataDir: path.join(__dirname, 'modules', 'mock_html_data'),
    },
    // Driver specific configurations can go here if needed
    drivers: {
        // Example:
        // YouPorn: {
        //     pageParam: 'page', // If youporn used a different page param name
        //     someCustomSetting: 'value'
        // },
        // SexCom: { // Example if its key needs to be different than display name
        //    apiKey: 'some_api_key_if_needed'
        // }
    }
}
