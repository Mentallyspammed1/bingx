// hybrid_search_app/core/log.js
// Basic logger implementation to satisfy the require in YouPornScraper

const createLogger = (prefix) => ({
    debug: (...args) => console.log(`[DEBUG]${prefix ? `[${prefix}]` : ''}`, ...args),
    info: (...args) => console.log(`[INFO]${prefix ? `[${prefix}]` : ''}`, ...args),
    warn: (...args) => console.warn(`[WARN]${prefix ? `[${prefix}]` : ''}`, ...args),
    error: (...args) => console.error(`[ERROR]${prefix ? `[${prefix}]` : ''}`, ...args),
});

// YouPornScraper seems to call log.debug(), log.info() directly.
// The server.js defines its own log object.
// For simplicity, let's provide a default logger that matches the expected usage.
const defaultLogger = createLogger();

module.exports = {
    debug: defaultLogger.debug,
    info: defaultLogger.info,
    warn: defaultLogger.warn,
    error: defaultLogger.error,
    createLogger: createLogger // Optional: if other modules use it this way
};
