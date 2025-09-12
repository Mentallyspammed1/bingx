// core/VideoMixin.js
'use strict';
const enforceAbstractMethods = require('./abstractMethodFactory');

const videoAbstractMethods = [
  'videoUrl',    // Expected to return a string (URL). Params: (query, page)
  'videoParser', // Expected to parse data and return an array. Params: (cheerioInstance, rawHtmlOrJsonData)
];

/**
 * VideoMixin - A factory function that creates a mixin to add video-related abstract method requirements.
 * @param {Function} BaseClass - The base class constructor to extend.
 * @returns {Function} A new class constructor with enforced abstract methods for videos.
 */
module.exports = (BaseClass) => enforceAbstractMethods(BaseClass, videoAbstractMethods);
