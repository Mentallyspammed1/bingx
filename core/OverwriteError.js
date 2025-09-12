// core/OverwriteError.js
'use strict';

class OverwriteError extends Error {
  constructor(message) {
    super(message);
    this.name = 'OverwriteError';
    // Maintains proper prototype chain for instanceof checks
    // and captures stack trace in V8 environments (Node.js, Chrome)
    if (typeof Error.captureStackTrace === 'function') {
      Error.captureStackTrace(this, this.constructor);
    } else {
      this.stack = (new Error(message)).stack;
    }
  }
}

module.exports = OverwriteError;
