'use strict';

const OverwriteError = require('./OverwriteError');

/**
 * GifMixin adds gifUrl and gifParser contract methods to base class.
 */
const GifMixin = (BaseClass) => class extends BaseClass {
  gifUrl(query, page) {
    throw new OverwriteError('gifUrl');
  }

  gifParser($, rawData) {
    throw new OverwriteError('gifParser');
  }
};

module.exports = GifMixin;
