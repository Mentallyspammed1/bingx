'use strict';

class OverwriteError extends Error {
  constructor(methodName) {
    super(`Method or property "${methodName}" must be overridden by subclass.`);
    this.name = 'OverwriteError';
  }
}

module.exports = OverwriteError;
