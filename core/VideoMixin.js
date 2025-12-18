'use strict';

const OverwriteError = require('./OverwriteError');

/**
 * VideoMixin adds videoUrl and videoParser contract methods to base class.
 */
const VideoMixin = (BaseClass) => class extends BaseClass {
  videoUrl(query, page) {
    throw new OverwriteError('videoUrl');
  }

  videoParser($, rawData) {
    throw new OverwriteError('videoParser');
  }
};

module.exports = VideoMixin;
