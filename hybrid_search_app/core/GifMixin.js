'use strict';

const abstractMethodFactory = require('./abstractMethodFactory');

/**
 * @file GifMixin.js
 * A mixin factory that enhances a base class with abstract GIF-related methods.
 * Classes applying this mixin are contractually obligated to implement `getGifSearchUrl()`
 * and rely on `parseResults()` for GIF parsing capabilities.
 */
module.exports = function GifMixin(BaseClass) {
  const WithGifFeatures = class extends BaseClass {
    /**
     * Indicates if this driver supports GIF searches.
     * Concrete drivers should override this method to return `true`.
     * @returns {boolean}
     */
    hasGifSupport() {
      return false; // Default to false; concrete drivers must explicitly set to true.
    }
  };

  // Use the factory to add the abstract method 'getGifSearchUrl'.
  // This enforces that any class using this mixin must implement the method.
  return abstractMethodFactory(WithGifFeatures, ['getGifSearchUrl']);
};
