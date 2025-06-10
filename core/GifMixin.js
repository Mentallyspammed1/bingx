// core/GifMixin.js
'use strict';
const enforceAbstractMethods = require('./abstractMethodFactory');

const gifAbstractMethods = [
  'gifUrl',    // Expected to return a string (URL). Params: (query, page)
  'gifParser', // Expected to parse data and return an array. Params: (cheerioInstance, rawHtmlOrJsonData)
];

/**
 * GifMixin - A factory function that creates a mixin to add GIF-related abstract method requirements.
 * @param {Function} BaseClass - The base class constructor to extend.
 * @returns {Function} A new class constructor with enforced abstract methods for GIFs.
 */
module.exports = (BaseClass) => enforceAbstractMethods(BaseClass, gifAbstractMethods);
