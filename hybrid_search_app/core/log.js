// Basic console logger utility
const log = {
    debug: (message, ...args) => { if (process.env.NODE_ENV === 'development') console.log(`[DEBUG] ${new Date().toISOString()}: `, message, ...args); },
    info: (message, ...args) => console.log(`[INFO] ${new Date().toISOString()}: `, message, ...args),
    warn: (message, ...args) => console.warn(`[WARN] ${new Date().toISOString()}: `, message, ...args),
    error: (message, ...args) => console.error(`[ERROR] ${new Date().toISOString()}: `, message, ...args),
    child: function(bindings) { // Added basic child-like behavior
        return {
            debug: (message, ...args) => this.debug(`[${bindings.module || 'child'}] `, message, ...args),
            info: (message, ...args) => this.info(`[${bindings.module || 'child'}] `, message, ...args),
            warn: (message, ...args) => this.warn(`[${bindings.module || 'child'}] `, message, ...args),
            error: (message, ...args) => this.error(`[${bindings.module || 'child'}] `, message, ...args),
        };
    }
};
module.exports = log;
